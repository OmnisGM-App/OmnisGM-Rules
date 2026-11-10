"""Tests for merge_gate: evaluate (table), the job verdict of run()/main(), the workflow contract.
Run: python3 .github/scripts/test_merge_gate.py (in a repo copy) / python3 templates/workflows/test_merge_gate.py."""
import io
import os
import unittest
from unittest import mock

import merge_gate as mg

BOT = mg.WORKFLOW_ACTOR
SNAP = "tests/e2e/a.spec.ts-snapshots/x.png"


def pull(labels=(), head="feat/x", base="dev", author="Nemo", sha="head1", default="dev", merge=None):
    return {"labels": [{"name": l} for l in labels], "head": {"ref": head, "sha": sha},
            "base": {"ref": base, "repo": {"default_branch": default}}, "user": {"login": author}, "merge_commit_sha": merge}


def labeled(name, actor=BOT, at="2026-10-20T10:00:00Z"):
    return {"event": "labeled", "label": {"name": name}, "actor": {"login": actor}, "created_at": at}


REVIEW_OK = [labeled("gate/review-passed")]


class Fake:
    def __init__(self, compare=()):
        self.compare = None if compare is None else list(compare)
        self.compared = []

    def compare_files(self, base, head):
        self.compared.append((base, head))
        return self.compare


class SyncFake(Fake):
    """A template-copy PR: `bad` is what template_mismatches returns (at the head, at the merge, settings), `status` what
    file_status returns, `unreadable` what templates_unreadable returns, `merge` the test merge when the pull has none."""
    def __init__(self, bad, status, unreadable=None, merge="m0"):
        super().__init__(); self.bad, self.status, self.unreadable, self.merge, self.asked = bad, status, unreadable, merge, []
    def templates_unreadable(self):
        return self.unreadable
    def merge_commit(self, pull):
        return pull.get("merge_commit_sha") or self.merge
    def template_mismatches(self, files, head, merge, base):
        self.asked.append((tuple(files), head, merge, base)); return self.bad
    def merge_parent(self, sha):
        return "parent-" + sha
    def file_status(self):
        return dict(self.status)


class Recorder(Fake):
    """The GitHub surface run()/main() touch, recording every write; `boom` makes state() raise."""
    def __init__(self, pull, events=(), state=None, boom=None):
        super().__init__()
        self._pull, self._events, self._state, self.boom = pull, list(events), dict(state or {}), boom
        self.removed, self.written = [], []

    def pull(self): return self._pull
    def state(self):
        if self.boom: raise self.boom
        return (None, self._state)
    def files(self): return ["src/a.ts"]
    def events(self): return self._events
    def events_again(self): return self._events
    def write_state(self, comment_id, state): self.written.append(state)
    def remove_label(self, name): self.removed.append(name)


def verdict(gh, call):
    """Runs `call` with the summary on stdout captured; returns (exit code, captured stdout)."""
    with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "", "REPO": "o/r", "PR": "1"}), \
            mock.patch("sys.stdout", new_callable=io.StringIO) as out:
        code = call()
    return code, out.getvalue()


class JobVerdict(unittest.TestCase):
    """The exit code is the job status the ruleset reads: 0 = labels ok, 1 = waiting or blocked (v3, Table#1241)."""

    def test_waiting_is_red_and_says_what_is_awaited(self):
        gh = Recorder(pull())  # no labels at all: matrix pair and review label still awaited
        code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual(code, 1)
        self.assertIn("::error::waiting: ", out)
        self.assertIn("## Merge gate: waiting", out)
        self.assertNotIn("## Merge gate: blocked", out)

    def test_a_contradiction_is_red_as_blocked(self):
        gh = Recorder(pull(["gate/matrix-passed", "gate/matrix-not-needed", "gate/review-passed"]), events=REVIEW_OK,
                      state={"gate/matrix-passed": "head1"})
        code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual(code, 1)
        self.assertIn("## Merge gate: blocked", out)
        self.assertIn("found 2", out)

    def test_every_label_holding_is_green(self):
        gh = Recorder(pull(["gate/matrix-passed", "gate/review-passed"]), events=REVIEW_OK, state={"gate/matrix-passed": "head1"})
        code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual(code, 0)
        self.assertIn("labels ok", out)

    def test_a_label_bound_to_another_head_is_removed_and_the_job_stays_red(self):
        gh = Recorder(pull(["gate/matrix-passed"]), state={"gate/matrix-passed": "head0"})  # bound to another head
        code, _ = verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual(gh.removed, ["gate/matrix-passed"])
        self.assertEqual(gh.written, [{}])  # the stale binding is dropped from the state comment
        self.assertEqual(code, 1)

    def test_main_returns_the_verdict_of_the_live_pull_and_an_api_error_propagates(self):
        gh = Recorder(pull(["gate/matrix-passed", "gate/review-passed"]), events=REVIEW_OK, state={"gate/matrix-passed": "head1"})
        with mock.patch.object(mg, "GitHub", lambda repo, pr: gh):
            self.assertEqual(verdict(gh, mg.main)[0], 0)
        gh = Recorder(pull())  # waiting: `main` must carry run()'s 1 to the process exit code (the job's status)
        with mock.patch.object(mg, "GitHub", lambda repo, pr: gh):
            self.assertEqual(verdict(gh, mg.main)[0], 1)
        gh = Recorder(pull(), boom=OSError("api down"))
        with mock.patch.object(mg, "GitHub", lambda repo, pr: gh), self.assertRaises(OSError):
            verdict(gh, mg.main)

    def test_nothing_is_written_through_the_check_runs_api(self):
        with open(mg.__file__) as f:
            src = f.read()
        self.assertNotIn("check-runs", src)
        self.assertFalse(hasattr(mg.GitHub, "open_check"))


class WorkflowContract(unittest.TestCase):
    """merge-gate.yml next to this file: the job IS the required context — nothing else reports a verdict."""

    def test_the_job_is_named_merge_gate_and_only_runs_the_script(self):
        here = os.path.dirname(os.path.abspath(__file__))
        for candidate in (os.path.join(here, "merge-gate.yml"), os.path.join(here, "..", "workflows", "merge-gate.yml")):
            if os.path.exists(candidate):
                with open(candidate) as f:
                    text = f.read()
                break
        else:
            self.fail("merge-gate.yml not found next to the script or in ../workflows")
        jobs = text.split("\njobs:\n", 1)[1]  # the job's own `name:` (4 spaces), not the workflow's on line 1
        self.assertEqual([l.split("#")[0].rstrip() for l in jobs.splitlines() if l.startswith("    name: ")],
                         ["    name: Merge gate"])  # the ruleset's required context (authoring-workflows 12b)
        on = text.split("\non:\n", 1)[1].split("\n\n", 1)[0]
        types = [l.split("#")[0].strip() for l in on.splitlines() if l.strip().startswith("types:")]
        self.assertEqual(len(types), 1)
        items = {x.strip() for x in types[0].split("[", 1)[1].split("]", 1)[0].split(",")}
        self.assertLessEqual({"labeled", "unlabeled", "synchronize"}, items)  # a label event re-runs the job; "labeled" is not a substring test (News#171)
        self.assertNotIn("workflow_dispatch", on)  # a dispatch run is attached to no PR: never a verdict (Table#1251)
        self.assertNotIn("--fail", text)
        self.assertNotIn("checks: write", text)
        self.assertEqual(text.count("run: python3 .github/scripts/merge_gate.py"), 1)


class Gate(unittest.TestCase):
    def test_bound_labels_on_the_live_head_pass(self):
        rm, fail, st = mg.evaluate(Fake(), pull(["gate/matrix-passed", "gate/review-passed"]), ["src/a.ts"], REVIEW_OK,
                                   {"gate/matrix-passed": "head1"})
        self.assertEqual((rm, fail), ([], []))
        self.assertEqual(st, {"gate/matrix-passed": "head1"})

    def test_labeled_event_records_the_payload_head(self):
        rm, fail, st = mg.evaluate(Fake(), pull(["gate/matrix-passed", "gate/review-passed"]), ["src/a.ts"], REVIEW_OK, {},
                                   event="labeled", event_label="gate/matrix-passed", event_head="head1")
        self.assertEqual((rm, fail), ([], []))
        self.assertEqual(st["gate/matrix-passed"], "head1")

    def test_label_applied_on_an_older_head_than_the_live_one_is_removed(self):
        # the push happened between the labeling and its run: payload head ≠ live head
        rm, _, st = mg.evaluate(Fake(), pull(["gate/matrix-passed"]), ["src/a.ts"], [], {},
                                event="labeled", event_label="gate/matrix-passed", event_head="head0")
        self.assertEqual(rm, ["gate/matrix-passed"])
        self.assertNotIn("gate/matrix-passed", st)

    def test_matrix_label_bound_to_another_head_is_removed_on_any_event(self):
        for ev in ("synchronize", "labeled", "unlabeled", "dispatch", "reopened"):
            rm, fail, st = mg.evaluate(Fake(), pull(["gate/matrix-passed", "gate/review-passed"]), ["src/a.ts"], REVIEW_OK,
                                       {"gate/matrix-passed": "head0"}, event=ev, event_label="area/ci")
            self.assertEqual(rm, ["gate/matrix-passed"], ev)
            self.assertEqual(len(fail), 1, ev)
            self.assertNotIn("gate/matrix-passed", st)

    def test_label_without_a_recorded_head_is_an_error_not_a_removal(self):
        rm, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-passed", "gate/review-passed"]), ["src/a.ts"], REVIEW_OK, {})
        self.assertEqual(rm, [])
        self.assertEqual(len(fail), 1)
        self.assertIn("re-apply", fail[0])

    def test_both_matrix_labels_is_a_failure(self):
        _, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-passed", "gate/matrix-not-needed", "gate/review-passed"]),
                                 ["src/a.ts"], REVIEW_OK, {"gate/matrix-passed": "head1"})
        self.assertEqual(len(fail), 1)
        self.assertIn("found 2", fail[0])

    def test_no_labels_lists_each_missing_requirement(self):
        _, fail, _ = mg.evaluate(Fake(), pull(), [SNAP], [], {})
        self.assertEqual(len(fail), 3)
        self.assertIn("human", fail[0])

    def test_snapshot_approval_survives_a_base_merge_with_foreign_baselines_and_rebinds(self):
        fake = Fake(compare=["tests/e2e/other.spec.ts-snapshots/y.png", "src/b.ts"])  # came from dev
        rm, fail, st = mg.evaluate(fake, pull(["gate/snapshots-approved", "gate/matrix-not-needed", "gate/review-passed"]),
                                   [SNAP], REVIEW_OK, {"gate/snapshots-approved": "head0"})
        self.assertEqual((rm, fail), ([], []))
        self.assertEqual(fake.compared, [("head0", "head1")])
        self.assertEqual(st["gate/snapshots-approved"], "head1")

    def test_snapshot_approval_dies_when_own_baselines_differ_between_the_heads(self):
        fake = Fake(compare=[SNAP])
        rm, fail, st = mg.evaluate(fake, pull(["gate/snapshots-approved", "gate/matrix-not-needed", "gate/review-passed"]),
                                   [SNAP], REVIEW_OK, {"gate/snapshots-approved": "head0"})
        self.assertEqual(rm, ["gate/snapshots-approved"])
        self.assertEqual(len(fail), 1)
        self.assertNotIn("gate/snapshots-approved", st)

    def test_compare_status_behind_or_diverged_is_unknown(self):
        # force-push back to an ancestor: three-dot compare lists no files although the tree differs
        import unittest.mock as um
        for status in ("behind", "diverged"):
            with um.patch.object(mg, "gh_json", return_value=[{"status": status, "files": []}]):
                self.assertIsNone(mg.GitHub("r", "1").compare_files("bound", "head"), status)
        with um.patch.object(mg, "gh_json", return_value=[{"status": "ahead", "files": [{"filename": "a"}]}]):
            self.assertEqual(mg.GitHub("r", "1").compare_files("bound", "head"), ["a"])

    def test_review_label_event_lag_is_retried(self):
        class Lagging(Fake):
            def __init__(self):
                super().__init__(); self.calls = 0
            def events_again(self):
                self.calls += 1
                return REVIEW_OK if self.calls >= 2 else []
        gh = Lagging()
        _, fail, _ = mg.evaluate(gh, pull(["gate/review-passed", "gate/matrix-not-needed"]), ["src/a.ts"], [], {})
        self.assertEqual(fail, [])
        self.assertEqual(gh.calls, 2)
        # a stale human event is retried too, until the bot's event shows up
        class LaggingAfterHuman(Lagging):
            def events_again(self):
                self.calls += 1
                return REVIEW_OK + [labeled("gate/review-passed", actor="Nemo", at="2026-10-20T09:00:00Z")] if self.calls >= 2 else []
        gh = LaggingAfterHuman()
        _, fail, _ = mg.evaluate(gh, pull(["gate/review-passed", "gate/matrix-not-needed"]), ["src/a.ts"],
                                 [labeled("gate/review-passed", actor="Nemo", at="2026-10-20T09:00:00Z")], {})
        self.assertEqual(fail, [])

    def test_state_comment_counts_only_from_the_workflow_actor(self):
        import unittest.mock as um
        comments = [[{"id": 1, "user": {"login": "Nemo"}, "body": mg.render_state({"gate/matrix-passed": "forged"})},
                     {"id": 2, "user": {"login": mg.WORKFLOW_ACTOR}, "body": mg.render_state({"gate/matrix-passed": "real"})}]]
        with um.patch.object(mg, "gh_json", return_value=comments):
            self.assertEqual(mg.GitHub("r", "1").state(), (2, {"gate/matrix-passed": "real"}))

    def test_compare_unknown_is_conservative(self):
        rm, _, _ = mg.evaluate(Fake(compare=None), pull(["gate/snapshots-approved"]), [SNAP], [],
                               {"gate/snapshots-approved": "head0"})
        self.assertEqual(rm, ["gate/snapshots-approved"])

    def test_review_label_counts_only_from_the_workflow_actor(self):
        _, fail, _ = mg.evaluate(Fake(), pull(["gate/review-passed", "gate/matrix-not-needed"]), ["src/a.ts"],
                                 [labeled("gate/review-passed", actor="Nemo")], {})
        self.assertEqual(len(fail), 1)
        self.assertIn("not by the review workflow", fail[0])
        _, fail, _ = mg.evaluate(Fake(), pull(["gate/review-passed", "gate/matrix-not-needed"]), ["src/a.ts"], [], {})
        self.assertEqual(len(fail), 1)
        self.assertIn("not on record yet", fail[0])
        self.assertEqual(mg.split_outcome(fail)[1], [])  # an event lag is "waiting", not a contradiction
        # a later hand-applied event beats an older bot one; the newest event decides
        ev = [labeled("gate/review-passed", at="2026-10-20T09:00:00Z"), labeled("gate/review-passed", actor="Nemo", at="2026-10-20T11:00:00Z")]
        _, fail, _ = mg.evaluate(Fake(), pull(["gate/review-passed", "gate/matrix-not-needed"]), ["src/a.ts"], ev, {})
        self.assertEqual(len(fail), 1)

    def test_dependabot_needs_only_the_matrix_label(self):
        for login in ("dependabot[bot]", "app/dependabot"):
            _, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-not-needed"], author=login), ["package.json"], [], {})
            self.assertEqual(fail, [], login)

    def test_release_pr_needs_only_the_matrix_label(self):
        files = [SNAP, "src/a.ts"]
        _, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-not-needed"], head="release/2026-10-20-1", base="master"), files, [], {})
        self.assertEqual(fail, [])
        for head in ("dev", "feat/x"):  # dev -> master is a feature PR since 2026-10-23: release/* only
            _, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-not-needed"], head=head, base="master"), files, [], {})
            self.assertEqual(len(fail), 2, head)

    def test_template_sync_needs_no_labels_when_every_blob_matches(self):
        files = [".claude/rules/review-response.md", ".claude/rules/code-comments.md"]
        Sync = lambda bad=([], [], []), **kw: SyncFake(bad, {f: "modified" for f in files}, **kw)
        gh = Sync()
        _, fail, _ = mg.evaluate(gh, pull(head="sync/templates-abc1234"), files, [], {})
        self.assertEqual(fail, [])
        self.assertEqual(gh.asked, [(tuple(files), "head1", "m0", "parent-m0")])  # at the live head, all files, against the merge's own base
        gh = Sync()
        mg.evaluate(gh, pull(head="sync/templates-abc1234", merge="m1"), files, [], {})
        self.assertEqual(gh.asked, [(tuple(files), "head1", "m1", "parent-m1")])  # and in the test merge with the base
        _, fail, _ = mg.evaluate(Sync(), pull(["gate/matrix-not-needed"], head="sync/templates-abc1234"), files, [], {})
        self.assertEqual(fail, [])  # a matrix label set by habit does not break it
        _, fail, _ = mg.evaluate(Sync(), pull(["gate/matrix-passed", "gate/matrix-not-needed"], head="sync/templates-abc1234"),
                                 files, [], {"gate/matrix-passed": "head1"})
        self.assertTrue(any("exactly one of" in f and "found 2" in f for f in mg.split_outcome(fail)[1]), fail)
        out = "outside `sync/templates-*`"
        cases = ((Sync(([files[0]], [], [])), ("differ from", "at the head —", out)),
                 (Sync(([], [files[0]], [])), ("in the merge with the base", "run sync-templates.yml", out)),
                 (Sync(([], [], [files[0]])), ("settings lines", "an ordinary PR", out)),
                 (Sync(merge=None), ("no test merge", "Re-run jobs", out)),
                 (Sync(unreadable="TEMPLATES_TOKEN cannot read x"), ("cannot read x",)))
        for gh, whys in cases:
            for labels in ((), ("gate/review-passed", "gate/matrix-not-needed")):
                _, fail, _ = mg.evaluate(gh, pull(list(labels), head="sync/templates-abc1234"), files,
                                         [labeled("gate/review-passed")], {})
                waiting, errors = mg.split_outcome(fail)
                why = whys[0]
                self.assertTrue(any(all(w in e for w in whys) for e in errors), (whys, fail))  # blocked, labels do not lift it
                self.assertEqual(waiting, [], (why, labels))  # no review round or matrix is promised: none would come

    def test_template_sync_exempts_only_modified_copies(self):
        files = [".claude/rules/a.md", ".claude/rules/b.md"]
        for status in ("added", "renamed", "removed", "copied", ""):
            gh = SyncFake(([], [], []), {files[0]: "modified", files[1]: status})
            _, fail, _ = mg.evaluate(gh, pull(head="sync/templates-abc1234"), files, [], {})
            waiting, errors = mg.split_outcome(fail)
            self.assertTrue(any("only modified copies" in e and ".claude/rules/b.md" in e and "outside `sync/templates-*`" in e
                                for e in errors), (status, fail))
            self.assertEqual(waiting, [], status)
            self.assertEqual(gh.asked, [], status)  # blobs are not even compared

    def test_template_sync_rejects_foreign_files_without_reading_blobs(self):
        class Never(Fake):
            def template_mismatches(self, files, head, merge, base):
                raise AssertionError("must not be asked")
            def merge_commit(self, pull):
                raise AssertionError("must not be asked")
            def templates_unreadable(self):
                raise AssertionError("must not be asked")
            def file_status(self):
                raise AssertionError("must not be asked")
        for files in ([".claude/rules/a.md", "src/a.ts"], [".claude/rules/sub/a.md"], [".claude/rules/a.txt"],
                      [".github/workflows/ci.yml"], [".github/scripts/docs_only.py"], [".github/scripts/merge_gate.py", "package.json"],
                      [], [".claude/rules/review-response.md?x=.md"],
                      [".claude/rules/a.md\n"], [".claude/rules/a&ref=x.md"], [".claude/rules/a%3F.md"],
                      [".claude/rules/.hidden.md"], ["x/.claude/rules/a.md"]):
            _, fail, _ = mg.evaluate(Never(), pull(head="sync/templates-abc1234"), files, [], {})
            self.assertTrue(any("template-sync branch but changes" in f and "outside `sync/templates-*`" in f
                                for f in mg.split_outcome(fail)[1]), files)
        # the same rule files on an ordinary branch are an ordinary PR: the review label is awaited
        _, fail, _ = mg.evaluate(Never(), pull(head="docs/rules"), [".claude/rules/a.md"], [], {})
        self.assertTrue(any("gate/review-passed" in f for f in fail))

    def test_template_sync_holds_only_into_the_default_branch(self):
        files = [".claude/rules/a.md"]
        gh = SyncFake(([], [], []), {files[0]: "modified"})
        _, fail, _ = mg.evaluate(gh, pull(head="sync/templates-abc1234", base="master", default="dev"), files, [], {})
        waiting, errors = mg.split_outcome(fail)
        self.assertTrue(any("not the default branch `dev`" in e and "outside `sync/templates-*`" in e for e in errors), fail)
        self.assertEqual(gh.asked, [])
        _, fail, _ = mg.evaluate(SyncFake(([], [], []), {files[0]: "modified"}), pull(head="sync/templates-abc1234", base="main", default="main"),
                                 files, [], {})
        self.assertEqual(fail, [])

    def test_plugin_copy_label_asks_for_the_same_check_on_any_branch(self):
        files = [".github/scripts/merge_gate.py", ".github/workflows/claude-review.yml", ".claude/rules/a.md"]
        gh = SyncFake(([], [], []), {f: "modified" for f in files})
        _, fail, _ = mg.evaluate(gh, pull(["plugin-copy"], head="ci/copies"), files, [], {})
        self.assertEqual((fail, gh.asked), ([], [(tuple(files), "head1", "m0", "parent-m0")]))  # no review, no matrix label
        for bad, why in ((([files[0]], [], []), "differ from"), (([], [], [files[1]]), "settings lines")):
            _, fail, _ = mg.evaluate(SyncFake(bad, {f: "modified" for f in files}),
                                     pull(["plugin-copy", "gate/review-passed"], head="ci/copies"), files, REVIEW_OK, {})
            waiting, errors = mg.split_outcome(fail)
            self.assertTrue(any(why in e and "`plugin-copy` PR:" in e and "Remove `plugin-copy`" in e for e in errors), fail)
            self.assertEqual(waiting, [])  # blocked: the review label does not lift a failed copy check
        _, fail, _ = mg.evaluate(gh, pull(["plugin-copy"], head="ci/copies"), files + ["package.json"], [], {})
        self.assertTrue(any("`plugin-copy` is set but the PR changes 'package.json'" in e for e in mg.split_outcome(fail)[1]), fail)
        _, fail, _ = mg.evaluate(gh, pull(["plugin-copy"], head="ci/copies", base="feat/x"), files, [], {})
        self.assertTrue(any("`plugin-copy` PR into `feat/x`, not the default branch `dev`" in e for e in fail), fail)
        _, fail, _ = mg.evaluate(SyncFake(([], [], []), {}), pull(head="ci/copies"), files, [], {})
        self.assertTrue(any("waiting for `gate/review-passed`" in f for f in fail))  # no label, no sync branch: reviewed

    def test_template_of_maps_rule_files_and_workflow_copies_only(self):
        self.assertEqual(mg.template_of(".claude/rules/a.md"), "templates/a.md")
        self.assertEqual(mg.template_of(".github/workflows/claude-review.yml"), ".github/workflows/claude-review.yml")
        self.assertEqual(mg.template_of(".github/scripts/test_sync_recheck.py"), "templates/workflows/test_sync_recheck.py")
        for f in (".github/workflows/ci.yml", ".claude/rules/sub/a.md", "templates/a.md", ".github/scripts/docs_only.py"):
            self.assertIsNone(mg.template_of(f), f)
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.join(here, "..", "..")
        if os.path.isdir(os.path.join(root, "templates", "workflows")):  # in claude-plugins: every template exists
            for t in mg.WORKFLOW_COPIES.values():
                self.assertTrue(os.path.isfile(os.path.join(root, t)), t)

    def test_settings_lines_are_kept_by_the_sync_and_masked_by_the_check(self):
        node = "      # Self-sufficiency on self-hosted: Node {0} (x)\n      - name: Setup Node {0}\n"
        tpl = ("jobs:\n  x:\n    runs-on: self-hosted   # note\n    env:\n  CI_CHECK: 'Validate'\n" + node.format(22)
               + "          node-version: 22\nend\n")
        copy = ("jobs:\n  x:\n    runs-on: ubuntu-latest\n    env:\n  CI_CHECK: 'Check & Build'\n" + node.format(24)
                + "          node-version: 24\nold\n")
        out = mg.with_settings("a.yml", tpl, copy)
        self.assertEqual(out, "jobs:\n  x:\n    runs-on: ubuntu-latest\n    env:\n  CI_CHECK: 'Check & Build'\n" + node.format(24)
                         + "          node-version: 24\nend\n")
        self.assertEqual(mg.split_settings("a.yml", out)[0], mg.split_settings("a.yml", tpl)[0])
        self.assertEqual(mg.split_settings("a.yml", out)[1], mg.split_settings("a.yml", copy)[1])
        self.assertEqual(mg.split_settings("a.md", tpl), (tpl.split("\n"), {}))  # only a workflow copy has settings
        with self.assertRaises(ValueError):
            mg.with_settings("a.yml", tpl, copy.replace("    runs-on: ubuntu-latest\n", ""))
        with self.assertRaises(ValueError):
            mg.with_settings("a.yml", tpl, copy.replace("node-version: 24", "runs-on: x"))

    def test_settings_lines_stay_with_their_job_when_the_template_reorders_jobs(self):
        # review of #46, round 2: positional substitution moved `runs-on` of one job to another
        copy = "on: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n  b:\n    runs-on: self-hosted\n"
        tpl = "on: push\njobs:\n  b:   # first now\n    runs-on: self-hosted\n    x: 1\n  a:\n    runs-on: self-hosted\n"
        out = mg.with_settings("w.yml", tpl, copy)
        self.assertEqual(out, "on: push\njobs:\n  b:   # first now\n    runs-on: self-hosted\n    x: 1\n  a:\n    runs-on: ubuntu-latest\n")
        self.assertEqual(mg.split_settings("w.yml", out)[1], mg.split_settings("w.yml", copy)[1])
        swapped = out.replace("    runs-on: self-hosted\n    x: 1\n  a:\n    runs-on: ubuntu-latest",
                              "    runs-on: ubuntu-latest\n    x: 1\n  a:\n    runs-on: self-hosted")
        self.assertNotEqual(mg.split_settings("w.yml", swapped)[1], mg.split_settings("w.yml", copy)[1])  # the gate sees a swap
        self.assertEqual(sorted(mg.split_settings("w.yml", "  CI_CHECK: x\njobs:\n  a:\n    runs-on: y\n    runs-on: z\n")[1]),
                         [("", "CI_CHECK:", 0), ("a", "runs-on:", 0), ("a", "runs-on:", 1)])
        with self.assertRaises(ValueError):  # a job added with a settings line does not fit the copy
            mg.with_settings("w.yml", tpl + "  c:\n    runs-on: self-hosted\n", copy)

    def test_file_status_reads_every_page(self):
        gh = mg.GitHub("o/r", "1")
        with mock.patch.object(mg, "gh_json", return_value=[[{"filename": "a", "status": "added"}], [{"filename": "b"}]]):
            self.assertEqual(gh.file_status(), {"a": "added", "b": ""})

    def test_templates_unreadable_names_the_token_on_401_403_404_and_raises_otherwise(self):
        gh = mg.GitHub("o/r", "1")
        with mock.patch.dict(os.environ, {"TEMPLATES_TOKEN": ""}):
            self.assertIn("TEMPLATES_TOKEN is empty", gh.templates_unreadable())
        with mock.patch.dict(os.environ, {"TEMPLATES_TOKEN": "t"}):
            with mock.patch.object(mg, "gh_json", return_value={"full_name": mg.TEMPLATES_REPO}) as call:
                self.assertIsNone(gh.templates_unreadable())
                self.assertEqual(call.call_args.kwargs["token"], "t")
            for code in ("401", "403", "404"):
                with mock.patch.object(mg, "gh_json", side_effect=RuntimeError(f"gh: Not Found (HTTP {code})")):
                    self.assertIn("cannot read", gh.templates_unreadable(), code)
            with mock.patch.object(mg, "gh_json", side_effect=RuntimeError(f"gh api repos/{mg.TEMPLATES_REPO}: gh: Bad credentials (HTTP 401)")):
                self.assertIn("(gh: Bad credentials (HTTP 401))", gh.templates_unreadable())  # the cause, not the call
            for err in ("HTTP 502: Bad Gateway", "gh: API rate limit exceeded for user ID 1. (HTTP 403)"):
                with mock.patch.object(mg, "gh_json", side_effect=RuntimeError(err)):
                    with self.assertRaises(RuntimeError, msg=err):
                        gh.templates_unreadable()

    def test_gh_json_passes_the_token_only_when_given(self):
        ok = mock.Mock(returncode=0, stdout='{"sha": "s"}', stderr="")
        with mock.patch.object(mg.subprocess, "run", return_value=ok) as run:
            mg.gh_json("repos/o/r/contents/x", token="t")
            self.assertEqual(run.call_args.kwargs["env"]["GH_TOKEN"], "t")
            mg.gh_json("repos/o/r/contents/x")
            self.assertIsNone(run.call_args.kwargs["env"])

    def test_file_text_404_is_none_other_errors_raise_and_the_path_is_quoted(self):
        gh = mg.GitHub("o/r", "1")
        ok = mock.Mock(returncode=0, stdout='{"content": "aGkK\\n"}', stderr="")
        with mock.patch.object(mg.subprocess, "run", return_value=ok) as run:
            self.assertEqual(gh.file_text("o/r", ".claude/rules/a b?.md", "h#1"), "hi\n")
            self.assertIn("contents/.claude/rules/a%20b%3F.md?ref=h%231", run.call_args.args[0][2])
        with mock.patch.object(mg.subprocess, "run", return_value=mock.Mock(returncode=1, stdout="", stderr="gh: Not Found (HTTP 404)")):
            self.assertIsNone(gh.file_text("o/r", "x.md", "h"))
        with mock.patch.object(mg.subprocess, "run", return_value=mock.Mock(returncode=1, stdout="", stderr="HTTP 502: Bad Gateway")):
            with self.assertRaises(RuntimeError):
                gh.file_text("o/r", "x.md", "h")

    def test_template_mismatches_compares_texts_with_the_template_repo(self):
        gh = mg.GitHub("o/r", "1")
        T, R = mg.TEMPLATES_REPO, mg.TEMPLATES_REF
        wf = ".github/workflows/merge-gate.yml"
        texts = {(T, "templates/a.md", R): "A", (T, "templates/b.md", R): "B", (T, "templates/gone.md", R): "G",
                 (T, "templates/workflows/merge-gate.yml", R): "x\n    runs-on: self-hosted\ny",
                 ("o/r", ".claude/rules/a.md", "h"): "A", ("o/r", ".claude/rules/b.md", "h"): "other",
                 ("o/r", ".claude/rules/gone.md", "h"): None, ("o/r", wf, "h"): "x\n    runs-on: ubuntu-latest\ny",
                 ("o/r", ".claude/rules/a.md", "m"): "A", ("o/r", wf, "m"): "x\n    runs-on: ubuntu-latest\ny",
                 ("o/r", ".claude/rules/a.md", "t"): "old A", ("o/r", wf, "t"): "old\n    runs-on: ubuntu-latest\n"}
        tokens = []
        def text(repo, path, ref, token=None):
            tokens.append((repo, token)); return texts[(repo, path, ref)]
        gh.file_text = text
        files = [".claude/rules/a.md", ".claude/rules/b.md", ".claude/rules/gone.md", wf]
        with mock.patch.dict(os.environ, {"TEMPLATES_TOKEN": "t"}):
            self.assertEqual(gh.template_mismatches(files, "h", "m", "t"),
                             ([".claude/rules/b.md", ".claude/rules/gone.md"], [], []))  # the runner line is the repo's own
            self.assertTrue(all(tok == "t" for r, tok in tokens if r == T))
            self.assertTrue(all(tok is None for r, tok in tokens if r == "o/r"))  # the PR repo: the job's own token
            texts[("o/r", ".claude/rules/a.md", "m")] = "merged"  # the base changed the copy too
            self.assertEqual(gh.template_mismatches([".claude/rules/a.md"], "h", "m", "t"), ([], [".claude/rules/a.md"], []))
            texts[("o/r", wf, "t")] = "x\n    runs-on: self-hosted\ny"  # the copy moves the repo off its runner
            self.assertEqual(gh.template_mismatches([wf], "h", "m", "t"), ([], [], [wf]))
            texts[("o/r", ".claude/rules/none.md", "h")] = None
            texts[(T, "templates/none.md", R)] = None  # missing on both sides is not "equal"
            self.assertEqual(gh.template_mismatches([".claude/rules/none.md"], "h", "m", "t"), ([".claude/rules/none.md"], [], []))

    def test_merge_commit_is_re_read_until_github_computes_it(self):
        gh = mg.GitHub("o/r", "1")
        with mock.patch("time.sleep") as sleep, mock.patch.object(gh, "merge_parent", return_value="tip"), \
                mock.patch.object(gh, "base_tip", return_value="tip"):
            with mock.patch.object(gh, "pull", side_effect=[{"mergeable": None, "merge_commit_sha": "old"},
                                                            {"mergeable": True, "merge_commit_sha": "m"}]):
                self.assertEqual(gh.merge_commit({"mergeable": None, "merge_commit_sha": "old"}), "m")  # a stale sha is not used
            self.assertEqual(sleep.call_count, 2)
            with mock.patch.object(gh, "pull", return_value={"mergeable": None, "merge_commit_sha": "old"}) as again:
                self.assertIsNone(gh.merge_commit({"mergeable": None, "merge_commit_sha": "old"}))
                self.assertEqual(again.call_count, 3)
            with mock.patch.object(gh, "pull", side_effect=AssertionError("not re-read")):
                self.assertEqual(gh.merge_commit({"mergeable": True, "merge_commit_sha": "m1"}), "m1")
                self.assertIsNone(gh.merge_commit({"mergeable": False, "merge_commit_sha": "m1"}))  # a conflict

    def test_merge_commit_on_a_stale_base_is_not_trusted(self):
        gh = mg.GitHub("o/r", "1")
        parents = {"old-merge": "old-tip", "new-merge": "tip"}
        with mock.patch("time.sleep"), mock.patch.object(gh, "merge_parent", side_effect=parents.get), \
                mock.patch.object(gh, "base_tip", return_value="tip") as tip:
            with mock.patch.object(gh, "pull", return_value={"mergeable": True, "merge_commit_sha": "new-merge"}) as re_read:
                self.assertEqual(gh.merge_commit({"mergeable": True, "merge_commit_sha": "old-merge", "base": {"ref": "dev"}}), "new-merge")
                self.assertEqual(re_read.call_count, 1)
            tip.assert_called_with("dev")
            with mock.patch.object(gh, "pull", return_value={"mergeable": True, "merge_commit_sha": "old-merge"}) as re_read:
                self.assertIsNone(gh.merge_commit({"mergeable": True, "merge_commit_sha": "old-merge", "base": {"ref": "dev"}}))
                self.assertEqual(re_read.call_count, 3)

    def test_merge_parent_and_base_tip_read_the_api(self):
        gh = mg.GitHub("o/r", "1")
        answers = {"repos/o/r/commits/m": {"parents": [{"sha": "p1"}, {"sha": "p2"}]},
                   "repos/o/r/branches/release%2F2026": {"commit": {"sha": "t"}}}
        with mock.patch.object(mg, "gh_json", side_effect=lambda path: answers[path]):
            self.assertEqual(gh.merge_parent("m"), "p1")
            self.assertEqual(gh.base_tip("release/2026"), "t")

    def test_outcome_splits_waiting_from_contradictions(self):
        _, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-passed", "gate/matrix-not-needed"]), [SNAP], [], {"gate/matrix-passed": "head1"})
        waiting, errors = mg.split_outcome(fail)
        self.assertEqual(len(errors), 1)
        self.assertIn("found 2", errors[0])
        self.assertEqual(len(waiting), 2)  # snapshots approval and the review label are awaited, not broken
        _, fail, _ = mg.evaluate(Fake(), pull(), ["src/a.ts"], [], {})
        self.assertEqual(mg.split_outcome(fail)[1], [])
        self.assertFalse(any(f.startswith(mg.WAIT) for f in mg.split_outcome(fail)[0]))

    def test_state_round_trips_through_the_comment_body(self):
        st = {"gate/matrix-passed": "abc", "gate/snapshots-approved": "def"}
        self.assertEqual(mg.parse_state(mg.render_state(st)), st)
        self.assertEqual(mg.parse_state("<!-- merge-gate-state garbage -->"), {})

    def test_unlabeled_drops_the_state_entry(self):
        _, _, st = mg.evaluate(Fake(), pull(["gate/matrix-not-needed", "gate/review-passed"]), ["src/a.ts"], REVIEW_OK,
                               {"gate/matrix-passed": "head1"}, event="unlabeled", event_label="gate/matrix-passed")
        self.assertEqual(st, {})


if __name__ == "__main__":
    unittest.main()
