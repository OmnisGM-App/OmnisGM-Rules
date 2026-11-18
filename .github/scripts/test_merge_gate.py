"""Tests for merge_gate: evaluate (table), the job verdict of run()/main(), the workflow contract.
Run: python3 .github/scripts/test_merge_gate.py (in a repo copy) / python3 templates/workflows/test_merge_gate.py."""
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import merge_gate as mg

BOT = mg.WORKFLOW_ACTOR
SNAP = "tests/e2e/a.spec.ts-snapshots/x.png"


def pull(labels=(), head="feat/x", base="dev", author="Nemo", sha="head1", default="dev", merge=None):
    return {"labels": [{"name": l} for l in labels], "head": {"ref": head, "sha": sha},
            "base": {"ref": base, "sha": "base1", "repo": {"default_branch": default}}, "user": {"login": author}, "merge_commit_sha": merge}


def labeled(name, actor=BOT, at="2026-10-20T10:00:00Z"):
    return {"event": "labeled", "label": {"name": name}, "actor": {"login": actor}, "created_at": at}


REVIEW_OK = [labeled("gate/review-passed")]


class Fake:
    own = ()       # what own_paths returns (None: cannot be told, an Exception: raised)
    owned = None   # the last (bound, head, base_ref) asked
    # what timeline() returns (an Exception: raised): by default the label set by a person after the PR's first commit
    timeline_events = ({"event": "labeled", "label": {"name": "gate/matrix-not-needed"}, "created_at": "2026-10-20T10:00:00Z"},
                       {"event": "committed", "sha": "head1", "committer": {"date": "2026-10-20T09:00:00Z"}})

    def timeline(self):
        if isinstance(self.timeline_events, Exception): raise self.timeline_events
        return list(self.timeline_events)

    def own_paths(self, bound, head, base_ref):
        self.owned = (bound, head, base_ref)
        if isinstance(self.own, Exception): raise self.own
        return None if self.own is None else list(self.own)

    seen = {}      # sha -> when GitHub first saw it (None: no check suite, an Exception: raised); by default the commit's own date in timeline_events

    def first_seen(self, sha, ref):
        self.seen_ref = ref
        got = self.seen[sha] if sha in self.seen else next(
            ((e.get("committer") or {}).get("date") for e in self.timeline_events if isinstance(e, dict) and e.get("sha") == sha), None)
        if isinstance(got, Exception): raise got
        return got.get(ref) if isinstance(got, dict) else got  # a dict: the first push per branch

    def __init__(self, trees=None, own=()):
        self.own = own
        self.trees, self.tree_reads = dict(trees or {}), []

    def tree(self, sha):
        self.tree_reads.append(sha)
        got = self.trees.get(sha)
        if isinstance(got, Exception): raise got
        return got


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
        self.removed, self.written, self.calls = [], [], []

    def pull(self): return self._pull
    def state(self):
        if self.boom: raise self.boom
        return (None, self._state)
    def files(self): return ["src/a.ts"]
    def events(self): return self._events
    def events_again(self): return self._events
    def write_state(self, comment_id, state):
        self.written.append(state)
        self.calls.append("write")
        return comment_id or 7
    def remove_label(self, name): self.removed.append(name)
    repo, matrix_free_list, added = "o/r", None, ()
    def touched_paths(self): return self.files()
    def file_text(self, repo, path, ref, token=None):
        return self.matrix_free_list if (repo, path) == ("o/r", mg.MATRIX_FREE) else None
    def add_label(self, name):
        self.added = (*self.added, name)
        self.calls.append("add")


class ReviewPause(unittest.TestCase):
    SKIP = "gate/review-skipped"

    def gate(self, labels, paused="true", **kw):
        gh = Recorder(pull(["gate/matrix-not-needed", *labels], **kw))
        with mock.patch.dict(os.environ, {"REVIEW_PAUSED": paused, "EVENT": "synchronize"}), contextlib.redirect_stdout(io.StringIO()) as out:
            return gh, mg.run(gh, gh.pull()), out.getvalue()

    def test_paused_opens_the_gate_and_marks_the_pr(self):
        gh, code, _ = self.gate([])
        self.assertEqual((code, gh.added), (0, (self.SKIP,)))

    def test_only_the_exact_true_pauses(self):
        for value in ("", "false", "1", "True", "true "):
            gh, code, out = self.gate([], paused=value)
            self.assertEqual((code, gh.added), (1, ()), value)
            self.assertIn("waiting for `gate/review-passed`", out)

    def test_a_hand_set_marker_opens_nothing_and_is_taken_off(self):
        gh, code, _ = self.gate([self.SKIP], paused="")
        self.assertEqual(code, 1)
        self.assertEqual(gh.removed, [self.SKIP])

    def test_the_marker_stays_without_a_write_during_the_pause(self):
        gh, code, _ = self.gate([self.SKIP])
        self.assertEqual((code, gh.added, gh.removed), (0, (), []))

    def test_a_passed_review_needs_no_marker(self):
        gh = Recorder(pull(["gate/matrix-not-needed", "gate/review-passed", self.SKIP]), events=REVIEW_OK)
        with mock.patch.dict(os.environ, {"REVIEW_PAUSED": "true", "EVENT": "synchronize"}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mg.run(gh, gh.pull()), 0)
        self.assertEqual((gh.added, gh.removed), ((), [self.SKIP]))

    def test_a_hand_set_review_label_is_still_a_contradiction(self):
        gh = Recorder(pull(["gate/matrix-not-needed", "gate/review-passed"]), events=[labeled("gate/review-passed", actor="Nemo")])
        with mock.patch.dict(os.environ, {"REVIEW_PAUSED": "true", "EVENT": "synchronize"}), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(mg.run(gh, gh.pull()), 1)
        self.assertIn("does not count", out.getvalue())

    def test_exempt_prs_get_no_marker(self):
        for kw in ({"author": "dependabot[bot]"}, {"head": "release/2026-11-19", "base": "master"}):
            gh, code, _ = self.gate([], **kw)
            self.assertEqual((code, gh.added), (0, ()), kw)

    def test_the_other_labels_still_hold_during_a_pause(self):
        gh = Recorder(pull([]))
        with mock.patch.dict(os.environ, {"REVIEW_PAUSED": "true", "EVENT": "synchronize"}), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(mg.run(gh, gh.pull()), 1)
        self.assertIn("exactly one of", out.getvalue())

    def test_a_missing_label_is_a_notice_not_a_red_run(self):
        gh = Recorder(pull(["gate/matrix-not-needed"]))
        gh.add_label = mock.Mock(side_effect=subprocess.CalledProcessError(1, "gh"))
        with mock.patch.dict(os.environ, {"REVIEW_PAUSED": "true", "EVENT": "synchronize"}), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(mg.run(gh, gh.pull()), 0)
        self.assertIn("does the label exist", out.getvalue())

    def test_the_workflow_passes_the_switch(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "merge-gate.yml"), encoding="utf-8") as fh:
            self.assertIn("REVIEW_PAUSED: ${{ vars.REVIEW_PAUSED }}", fh.read())


def touch(path):
    with open(path, "w") as fh:
        fh.write("# stub\n")


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

    def test_pr_checks_report_never_changes_the_verdict(self):
        d = tempfile.mkdtemp(prefix="gate-report-")
        try:
            script = os.path.join(d, "run_pr_checks.py")
            summary = os.path.join(d, "summary.md")
            touch(script)
            touch(os.path.join(d, "ci_lint.py"))
            calls, kws = [], []

            def ok(cmd, **kw):
                if calls:   # each finished group is already in the summary: a cancelled job keeps it
                    self.assertIn("**closes** x", read())
                calls.append(cmd)
                kws.append(kw)
                found = "### PR checks (report only)\n- **closes** x\n" if cmd[cmd.index("--only") + 1] == "closes" else mg.PR_CHECKS_NOTHING
                return subprocess.CompletedProcess(cmd, 0, stdout=found, stderr="")

            def read():
                with open(summary) as fh:
                    return fh.read()

            env = {"GITHUB_STEP_SUMMARY": summary, "REPO": "o/r", "PR": "7"}
            with mock.patch.dict(os.environ, env):
                mg.pr_checks_report(script, ok)
                self.assertEqual([c[c.index("--only") + 1] for c in calls], list(mg.PR_CHECKS_GROUPS))   # one process per group
                for c, kw in zip(calls, kws):
                    self.assertEqual(c[c.index("--repo") + 1], "o/r")
                    self.assertEqual(c[c.index("--pr") + 1], "7")
                    self.assertIn("--report", c)
                    self.assertNotIn("--markdown", c)              # run_pr_checks prints plain text; the gate fences it
                    self.assertEqual(kw["timeout"], mg.PR_CHECKS_TIMEOUT)   # a hung gh must not hold the job
                got = read()
                self.assertIn("**closes** x", got)
                self.assertNotIn(mg.PR_CHECKS_NOTHING, got)        # the groups that found nothing add no line
                self.assertTrue(got.startswith("```\n") and got.rstrip().endswith("```"))   # plain text is fenced
                # every group empty: one line, not four
                open(summary, "w").close()
                mg.pr_checks_report(script, lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=mg.PR_CHECKS_NOTHING + "\n", stderr=""))
                self.assertEqual(read(), mg.PR_CHECKS_NOTHING + "\n")
                # the script is missing: nothing runs and the summary says the gap
                calls.clear()
                open(summary, "w").close()
                mg.pr_checks_report(os.path.join(d, "absent.py"), ok)
                self.assertIn("not rolled out in this repo", read())
                open(summary, "w").close()
                # one copy of the two: run_pr_checks.py imports ci_lint at load time, so the line says "not rolled out", not an ImportError
                os.remove(os.path.join(d, "ci_lint.py"))
                mg.pr_checks_report(script, ok)
                self.assertIn("not rolled out in this repo", read())
                self.assertEqual(calls, [])
                touch(os.path.join(d, "ci_lint.py"))
                # a crash, a timeout and a non-zero exit are reported in the summary, never raised
                def boom(cmd, **kw): raise subprocess.TimeoutExpired(cmd, 120)
                def bad(cmd, **kw): return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="gh: no token")
                for fn, needle in ((boom, "TimeoutExpired"), (bad, "exit 2")):
                    open(summary, "w").close()
                    mg.pr_checks_report(script, fn)
                    self.assertIn(needle, read())
                # a hang of ONE group keeps the findings of the others (the point of one process per group)
                def one_hangs(cmd, **kw):
                    if cmd[cmd.index("--only") + 1] == "bot-threads":
                        raise subprocess.TimeoutExpired(cmd, 120)
                    return ok(cmd, **kw)
                open(summary, "w").close()
                mg.pr_checks_report(script, one_hangs)
                got = read()
                self.assertIn("**closes** x", got)
                self.assertIn("[bot-threads] did not run: TimeoutExpired", got)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_the_fence_is_longer_than_any_backtick_run_in_the_foreign_text(self):
        d = tempfile.mkdtemp(prefix="gate-report-")
        try:
            script = os.path.join(d, "run_pr_checks.py")
            touch(script)
            touch(os.path.join(d, "ci_lint.py"))
            summary = os.path.join(d, "summary.md")
            hostile = "[bot-threads] 1 thread(s)\n  - a.py:3 ```suggestion\n  - b ````` c"   # a bot comment / checklist item with fences
            run = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=hostile if "bot-threads" in cmd else mg.PR_CHECKS_NOTHING, stderr="")
            with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": summary, "REPO": "o/r", "PR": "7"}):
                mg.pr_checks_report(script, run)
            with open(summary) as fh:
                lines = fh.read().rstrip("\n").split("\n")
            self.assertEqual(lines[0], "`" * 6)                      # longest run inside is 5
            self.assertEqual(lines[-1], lines[0])
            self.assertEqual(lines[1:-1], hostile.split("\n"))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_an_unwritable_summary_does_not_raise(self):
        d = tempfile.mkdtemp(prefix="gate-report-")
        try:
            script = os.path.join(d, "run_pr_checks.py")
            touch(script)
            touch(os.path.join(d, "ci_lint.py"))
            ok = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="x", stderr="")
            env = {"GITHUB_STEP_SUMMARY": os.path.join(d, "no-such-dir", "summary.md"), "REPO": "o/r", "PR": "7"}
            with mock.patch.dict(os.environ, env):
                for target in (script, os.path.join(d, "absent.py")):   # the script runs / not rolled out: the write fails either way
                    with contextlib.redirect_stdout(io.StringIO()) as out:   # the warning is the contract, not noise on the CI log
                        mg.pr_checks_report(target, ok)
                    self.assertIn("::warning::PR checks report failed", out.getvalue())
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_the_verdict_run_does_not_run_the_report_and_the_report_run_does_not_evaluate(self):
        # the report is a workflow of its own (pr-checks-report.yml): the verdict job's status never waits for it
        calls = []
        gh = Recorder(pull())  # waiting -> 1
        with mock.patch.object(mg, "GitHub", lambda repo, pr: gh), mock.patch.object(mg, "pr_checks_report", lambda: calls.append("report")):
            self.assertEqual(verdict(gh, mg.main)[0], 1)
            self.assertEqual(calls, [])
        calls.clear()
        with mock.patch.object(mg, "GitHub", side_effect=AssertionError("the report run must not read the gate state")), \
                mock.patch.object(mg, "pr_checks_report", lambda: calls.append("report")):
            self.assertEqual(mg.main(["--pr-checks-report"]), 0)    # exit 0 always: it is not a verdict
        self.assertEqual(calls, ["report"])

    def test_the_production_invocation_reads_the_flag_from_sys_argv(self):
        # the workflow runs `python3 .github/scripts/merge_gate.py --pr-checks-report`: main() with argv=None, the flag from sys.argv
        calls = []
        with mock.patch.object(sys, "argv", ["merge_gate.py", "--pr-checks-report"]), \
                mock.patch.object(mg, "GitHub", side_effect=AssertionError("the report run must not read the gate state")), \
                mock.patch.object(mg, "pr_checks_report", lambda: calls.append("report")):
            self.assertEqual(mg.main(), 0)
        self.assertEqual(calls, ["report"])

    def test_the_checks_scripts_are_workflow_copies(self):
        self.assertEqual(mg.template_of(".github/scripts/run_pr_checks.py"), "plugins/omnisgm/scripts/checks/run_pr_checks.py")
        self.assertEqual(mg.template_of(".github/scripts/ci_lint.py"), "plugins/omnisgm/scripts/checks/ci_lint.py")
        self.assertEqual(mg.template_of(".github/workflows/pr-checks-report.yml"), "templates/workflows/pr-checks-report.yml")

    def test_nothing_is_written_through_the_check_runs_api(self):
        with open(mg.__file__) as f:
            src = f.read()
        self.assertNotIn("check-runs", src)
        self.assertFalse(hasattr(mg.GitHub, "open_check"))


class AutoMatrixLabel(unittest.TestCase):
    """The gate sets `gate/matrix-not-needed` itself when every touched path is in `.github/matrix-free-paths` of the base."""
    LIST = "# docs and units\n" + r"[^/]+\.md" + "\n" + r"src/.*\.test\.ts" + "\n"

    def gate(self, labels=(), files=("README.md",), listed=LIST, state=None, head="feat/x", renamed=(), base_sha="b1",
             env=None, changed=None, na_actor=BOT):
        p = pull(labels, head=head)
        p["base"]["sha"] = base_sha
        if changed is not None:
            p["changed_files"] = changed
        na = [labeled("gate/matrix-not-needed", actor=na_actor)] if "gate/matrix-not-needed" in labels else []
        gh = Recorder(p, events=REVIEW_OK + na, state=state)
        gh.matrix_free_list = listed
        gh.files = lambda: list(files)
        gh.touched_paths = lambda: [*files, *renamed]
        seen = []
        real = gh.file_text
        gh.file_text = lambda repo, path, ref, token=None: (seen.append(ref), real(repo, path, ref))[1]
        with mock.patch.dict(os.environ, env or {}):
            code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
        return gh, code, out, seen

    def test_no_list_changes_nothing(self):
        gh, code, out, _ = self.gate(["gate/review-passed"], listed=None)
        self.assertEqual((gh.added, gh.removed, code), ((), [], 1))
        self.assertNotIn("set by the gate", out)

    def test_all_paths_listed_sets_the_label_and_counts_it(self):
        gh, code, out, seen = self.gate(["gate/review-passed"], files=("README.md", "src/a.test.ts"))
        self.assertEqual(gh.added, ("gate/matrix-not-needed",))
        self.assertEqual(seen, ["b1"])  # read at the base: a PR cannot widen its own list
        self.assertEqual(gh.written, [{mg.AUTO_NA: "head1"}])  # once, into the comment it created
        self.assertIn("set by the gate: all 2 touched path(s)", out)
        self.assertEqual(code, 0)

    def test_one_path_outside_sets_nothing(self):
        gh, code, _, _ = self.gate(["gate/review-passed"], files=("README.md", "src/a.ts"))
        self.assertEqual((gh.added, code), ((), 1))

    def test_a_path_is_matched_whole_not_as_a_prefix(self):
        gh, _, _, _ = self.gate(files=("docs/README.md",))  # `[^/]+\.md` is the root only
        self.assertEqual(gh.added, ())

    def test_a_rename_from_outside_sets_nothing(self):
        gh, _, _, _ = self.gate(files=("README.md",), renamed=("src/app.ts",))
        self.assertEqual(gh.added, ())

    def test_an_empty_diff_sets_nothing(self):
        gh, _, _, _ = self.gate(files=())
        self.assertEqual(gh.added, ())

    def test_a_list_of_comments_only_sets_nothing(self):
        gh, _, _, _ = self.gate(listed="# nothing yet\n\n")
        self.assertEqual(gh.added, ())

    def test_its_own_label_is_removed_when_the_diff_leaves_the_list(self):
        gh, code, out, _ = self.gate(["gate/matrix-not-needed", "gate/review-passed"], files=("src/a.ts",),
                                     state={mg.AUTO_NA: "head0"})
        self.assertEqual(gh.removed, ["gate/matrix-not-needed"])
        self.assertEqual(gh.written[-1], {})
        self.assertIn("removed by the gate", out)
        self.assertEqual(code, 1)

    def test_its_own_label_is_kept_and_rebound_while_the_diff_stays_listed(self):
        gh, code, _, _ = self.gate(["gate/matrix-not-needed", "gate/review-passed"], state={mg.AUTO_NA: "head0"})
        self.assertEqual((gh.added, gh.removed, code), ((), [], 0))
        self.assertEqual(gh.written[-1], {mg.AUTO_NA: "head1"})

    def test_a_hand_set_label_is_never_touched(self):
        gh, code, _, _ = self.gate(["gate/matrix-not-needed", "gate/review-passed"], files=("src/a.ts",))
        self.assertEqual((gh.added, gh.removed, code), ((), [], 0))

    def test_a_record_without_its_label_is_dropped_and_the_label_comes_back(self):
        gh, _, _, _ = self.gate(state={mg.AUTO_NA: "head0"})  # someone removed the gate's label: the list still decides
        self.assertEqual(gh.added, ("gate/matrix-not-needed",))

    def test_a_green_matrix_supersedes_the_gates_label(self):
        gh, code, _, _ = self.gate(["gate/matrix-passed", "gate/matrix-not-needed", "gate/review-passed"],
                                   state={"gate/matrix-passed": "head1", mg.AUTO_NA: "head0"})
        self.assertEqual(gh.removed, ["gate/matrix-not-needed"])
        self.assertEqual(code, 0)
        gh, _, out, _ = self.gate(["gate/matrix-passed"], state={"gate/matrix-passed": "head1"})
        self.assertEqual(gh.added, ())
        self.assertNotIn("removed by the gate", out)  # nothing of the gate's was there to remove

    def test_a_matrix_label_held_by_its_tree_is_not_doubled_by_the_gates_label(self):
        # a stacked PR rebased onto the same files: evaluate() keeps matrix-passed by tree, so the list must not add a
        # second matrix label (two of them are a red contradiction)
        with mock.patch.object(Recorder, "tree", lambda self, sha: "t1", create=True):
            gh, code, _, _ = self.gate(["gate/matrix-passed", "gate/review-passed"],
                                       state={"gate/matrix-passed": {"sha": "head0", "tree": "t1"}})
        self.assertEqual((gh.added, gh.removed, code), ((), [], 0))

    def test_a_matrix_label_whose_labeled_run_sees_a_moved_head_with_the_same_tree_is_not_doubled(self):
        # the owner labels head0, the head moves to head1 (same tree) before the `labeled` run: evaluate() keeps the
        # label by tree, so the list must not add a second matrix label in that run either
        env = {"EVENT": "labeled", "EVENT_LABEL": "gate/matrix-passed", "EVENT_HEAD_SHA": "head0"}
        with mock.patch.object(Recorder, "tree", lambda self, sha: "t1", create=True):
            gh, code, _, _ = self.gate(["gate/matrix-passed", "gate/review-passed"], env=env)
        self.assertEqual((gh.added, gh.removed, code), ((), [], 0))
        # a different tree is a moved head: the label goes and the list decides
        trees = {"head0": "t0"}
        with mock.patch.object(Recorder, "tree", lambda self, sha: trees.get(sha, "t1"), create=True):
            gh, _, _, _ = self.gate(["gate/matrix-passed", "gate/review-passed"], env=env)
        self.assertEqual(gh.removed, ["gate/matrix-passed"])

    def test_template_copies_are_left_alone(self):
        gh, _, _, _ = self.gate(head="sync/templates-1")
        self.assertEqual(gh.added, ())
        gh, _, _, _ = self.gate(["plugin-copy"])
        self.assertEqual(gh.added, ())

    def test_a_bad_list_or_an_api_error_is_a_note_not_a_red_gate(self):
        gh, code, out, _ = self.gate(["gate/review-passed"], listed="src/(\n")
        self.assertEqual((gh.added, code), ((), 1))
        self.assertIn("unterminated subpattern", out)
        def boom(*a, **k): raise RuntimeError("gh api 502")
        for bound, removed, want in (("head1", [], 0), ("head0", ["gate/matrix-not-needed"], 1)):
            gh = Recorder(pull(["gate/matrix-not-needed", "gate/review-passed"]), state={mg.AUTO_NA: bound},
                          events=REVIEW_OK + [labeled("gate/matrix-not-needed")])
            gh.file_text, gh.files = boom, (lambda: ["src/App.tsx"])
            code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
            self.assertIn("not applied (RuntimeError: gh api 502)", out)
            # a re-run of the head it was decided for keeps the gate's label; a new head gets no decision and waits
            self.assertEqual((gh.removed, code), (removed, want))


    def test_the_record_is_written_before_the_label(self):
        p = pull(["gate/matrix-passed", "gate/review-passed"])  # matrix-passed of an older head: evaluate removes it
        gh = Recorder(p, events=REVIEW_OK, state={"gate/matrix-passed": "head0"})
        gh.matrix_free_list, gh.files = self.LIST, (lambda: ["README.md"])
        def down(name): raise RuntimeError("gh pr edit: HTTP 502")
        gh.remove_label = down  # an API call after the label fails the run
        with self.assertRaises(RuntimeError), mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}):
            mg.run(gh, gh.pull())
        self.assertEqual((gh.calls, gh.written), (["write", "add"], [{"gate/matrix-passed": "head0", mg.AUTO_NA: "head1"}]))
        # the next push brings UI: the gate still knows the label is its own and takes it back
        nxt, code, _, _ = self.gate(["gate/matrix-not-needed", "gate/review-passed"], files=("src/App.tsx",),
                                    state={mg.AUTO_NA: gh.written[-1][mg.AUTO_NA]})
        self.assertEqual((nxt.removed, code), (["gate/matrix-not-needed"], 1))

    def test_a_matrix_label_of_an_older_head_does_not_block_the_gates_label(self):
        gh, code, _, _ = self.gate(["gate/matrix-passed", "gate/review-passed"], state={"gate/matrix-passed": "head0"})
        self.assertEqual((gh.added, gh.removed, code), (("gate/matrix-not-needed",), ["gate/matrix-passed"], 0))

    def test_a_matrix_label_applied_in_this_event_supersedes(self):
        gh, _, out, _ = self.gate(["gate/matrix-passed", "gate/matrix-not-needed"], state={mg.AUTO_NA: "head0"},
                                  env={"EVENT": "labeled", "EVENT_LABEL": "gate/matrix-passed"})
        self.assertEqual(gh.removed, ["gate/matrix-not-needed"])
        self.assertIn("`gate/matrix-passed` holds on this head", out)

    def test_a_label_applied_by_hand_over_an_old_record_is_theirs(self):
        gh, _, _, _ = self.gate(["gate/matrix-not-needed"], files=("src/a.ts",), state={mg.AUTO_NA: "head0"},
                                na_actor="Nemo")
        self.assertEqual((gh.removed, gh.written), ([], [{mg.HAND_NA: "head1"}]))  # the gate's record is dropped, the label kept and bound

    def test_a_replayed_hand_labeled_event_does_not_disown_the_gates_label(self):
        # a re-run replays a person's old `labeled` payload; the timeline says the label on the PR is the gate's
        gh, code, _, _ = self.gate(["gate/matrix-not-needed", "gate/review-passed"], files=("src/App.tsx",),
                                   state={mg.AUTO_NA: "head1"}, env={"EVENT": "labeled", "EVENT_LABEL": "gate/matrix-not-needed"})
        self.assertEqual((gh.removed, code), (["gate/matrix-not-needed"], 1))

    def test_a_lagging_timeline_is_read_again(self):
        p = pull(["gate/matrix-not-needed"])
        gh = Recorder(p, events=[labeled("gate/matrix-not-needed", actor="Nemo")], state={mg.AUTO_NA: "head0"})
        gh.files = lambda: ["src/App.tsx"]
        later = [labeled("gate/matrix-not-needed", actor="Nemo", at="2026-10-20T09:00:00Z"), labeled("gate/matrix-not-needed")]
        reads = iter([gh._events, gh._events, later])  # the gate's event shows up only on the third re-read
        gh.events_again = lambda: next(reads, later)
        verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual(gh.removed, ["gate/matrix-not-needed"])

    def test_an_unlabeled_last_is_read_again_before_the_label_is_taken(self):
        # a person removed the gate's label and applied it again; the list does not show their `labeled` yet
        un = {**labeled("gate/matrix-not-needed", actor="Nemo", at="2026-10-20T11:00:00Z"), "event": "unlabeled"}
        p = pull(["gate/matrix-not-needed", "gate/review-passed"])
        gh = Recorder(p, events=REVIEW_OK + [labeled("gate/matrix-not-needed"), un], state={mg.AUTO_NA: "head0"})
        gh.files = lambda: ["src/App.tsx"]
        gh.events_again = lambda: gh._events + [labeled("gate/matrix-not-needed", actor="Nemo", at="2026-10-20T11:00:05Z")]
        code, _ = verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual((gh.removed, gh.written[-1], code), ([], {mg.HAND_NA: "head1"}, 0))

    def test_events_of_one_second_keep_their_order_by_id(self):
        at = "2026-10-20T11:00:00Z"
        un = {**labeled("gate/matrix-not-needed", actor="Nemo", at=at), "event": "unlabeled", "id": 1}
        again = {**labeled("gate/matrix-not-needed", actor="Nemo", at=at), "id": 2}
        gh, code = self.ui_push_over_record([labeled("gate/matrix-not-needed", at="2026-10-20T09:00:00Z"), again, un])
        self.assertEqual((gh.removed, code), ([], 0))  # the person's `labeled` (id 2) is the last one

    def ui_push_over_record(self, na_events):
        p = pull(["gate/matrix-not-needed", "gate/review-passed"])
        gh = Recorder(p, events=REVIEW_OK + na_events, state={mg.AUTO_NA: "head0"})
        gh.files = lambda: ["src/App.tsx"]
        code, _ = verdict(gh, lambda: mg.run(gh, gh.pull()))
        return gh, code

    def test_a_timeline_without_the_gates_event_yet_still_counts_it_as_the_gates(self):
        gh, code = self.ui_push_over_record([])  # the run right after the one that applied it: the list lags
        self.assertEqual((gh.removed, code), (["gate/matrix-not-needed"], 1))

    def test_an_unlabeled_last_means_the_newer_labeled_is_the_gates(self):
        nemo = "Nemo"
        un = {**labeled("gate/matrix-not-needed", actor=nemo, at="2026-10-20T11:00:00Z"), "event": "unlabeled"}
        gh, code = self.ui_push_over_record([labeled("gate/matrix-not-needed", actor=nemo), un])
        self.assertEqual((gh.removed, code), (["gate/matrix-not-needed"], 1))

    def test_a_person_labeling_after_the_gate_owns_the_label(self):
        gh, code = self.ui_push_over_record([labeled("gate/matrix-not-needed", at="2026-10-20T09:00:00Z"),
                                             labeled("gate/matrix-not-needed", actor="Nemo")])
        self.assertEqual((gh.removed, gh.written[-1], code), ([], {mg.HAND_NA: "head1"}, 0))

    def test_a_matrix_label_without_a_recorded_head_waits_for_its_own_run(self):
        # the swap from matrix_run.sh: the `unlabeled` run may come before the `labeled` one
        gh, _, _, _ = self.gate(["gate/matrix-passed"])
        self.assertEqual((gh.added, gh.removed), ((), []))

    def test_a_matrix_label_applied_on_an_older_head_does_not_take_the_gates_label(self):
        gh, _, out, _ = self.gate(["gate/matrix-passed", "gate/matrix-not-needed"], state={mg.AUTO_NA: "head0"},
                                  env={"EVENT": "labeled", "EVENT_LABEL": "gate/matrix-passed", "EVENT_HEAD_SHA": "head0"})
        self.assertEqual(gh.removed, ["gate/matrix-passed"])  # evaluate drops the stale one, the gate keeps its own
        self.assertNotIn("holds on this head", out)

    def test_an_incomplete_file_list_sets_nothing_and_takes_back_its_own(self):
        gh, _, out, _ = self.gate(changed=3001)
        self.assertEqual(gh.added, ())
        self.assertIn("GitHub lists 1 of 3001 changed files", out)
        gh, _, _, _ = self.gate(["gate/matrix-not-needed"], changed=2, state={mg.AUTO_NA: "head0"})
        self.assertEqual(gh.removed, ["gate/matrix-not-needed"])
        gh, _, _, _ = self.gate(files=[f"{i}.md" for i in range(mg.FILES_CAP)], changed=mg.FILES_CAP)
        self.assertEqual(gh.added, ())
        gh, _, _, _ = self.gate(files=[f"{i}.md" for i in range(mg.FILES_CAP - 1)], changed=mg.FILES_CAP - 1)
        self.assertEqual(gh.added, ("gate/matrix-not-needed",))

    def test_trailing_comments_and_a_bom_are_not_part_of_a_pattern(self):
        gh, _, _, _ = self.gate(listed="\ufeff" + r"[^/]+\.md  # docs" + "\n" + r"x#y" + "\n")
        self.assertEqual(gh.added, ("gate/matrix-not-needed",))
        self.assertTrue(mg.matrix_free(["x#y"], r"x#y"))  # a `#` inside a pattern stays

    def test_no_base_sha_or_an_odd_file_is_a_note(self):
        _, _, out, seen = self.gate(base_sha="")
        self.assertEqual(seen, [])  # never read at the default branch instead
        self.assertIn("ValueError: the PR has no base sha", out)
        for err in (TypeError("list indices"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad"), KeyError("content")):
            gh = Recorder(pull(["gate/review-passed"]), events=REVIEW_OK)
            gh.file_text = lambda *a, err=err, **k: (_ for _ in ()).throw(err)
            code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
            self.assertIn(f"not applied ({type(err).__name__}", out)


class HandMatrixLabel(unittest.TestCase):
    """#89: a hand-set `gate/matrix-not-needed` is bound to its head and watched; the gate's own label is not (above)."""
    NA = "gate/matrix-not-needed"
    LIST = r"[^/]+\.md" + "\n"

    def gate(self, state=None, own=(), env=None, listed=LIST, head="head2", events=None, labels=None):
        p = pull(labels or [self.NA, "gate/review-passed"], sha=head)
        p["base"]["ref"] = "dev"
        gh = Recorder(p, events=REVIEW_OK + [labeled(self.NA, actor="Nemo")] if events is None else events, state=state)
        gh.matrix_free_list, gh.own = listed, own
        with mock.patch.dict(os.environ, env or {}):
            code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
        return gh, code, out

    def test_it_is_bound_to_the_payload_head_on_its_labeled_event(self):
        gh, code, _ = self.gate(env={"EVENT": "labeled", "EVENT_LABEL": self.NA, "EVENT_HEAD_SHA": "head1"},
                                state={mg.HAND_NA: "older"}, own=["src/a.ts"])
        self.assertEqual(gh.removed, [self.NA])  # the stale record "older" was replaced by head1, and own_paths was asked from there
        self.assertEqual(gh.owned, ("head1", "head2", "dev"))  # bound to what the person saw, then checked against the live head

    def test_it_is_bound_to_the_live_head_on_a_labeled_run_of_that_head(self):
        gh, code, _ = self.gate(head="head1", env={"EVENT": "labeled", "EVENT_LABEL": self.NA})
        self.assertEqual((gh.written[-1], gh.removed, code), ({mg.HAND_NA: "head1"}, [], 0))

    def test_a_push_outside_the_list_removes_it_and_names_the_paths(self):
        gh, code, out = self.gate(state={mg.HAND_NA: "head1"}, own=["README.md", "package.json", "src/a.ts"])
        self.assertEqual((gh.removed, code), ([self.NA], 1))
        self.assertEqual(gh.owned, ("head1", "head2", "dev"))
        self.assertIn("removed by the gate", out)
        self.assertIn("'package.json', 'src/a.ts'", out)
        self.assertNotIn("'README.md'", out)
        self.assertNotIn(mg.HAND_NA, gh.written[-1])

    def test_a_push_inside_the_list_keeps_it_and_rebinds(self):
        gh, code, _ = self.gate(state={mg.HAND_NA: "head1"}, own=["README.md", "CHANGES.md"])
        self.assertEqual((gh.removed, gh.written[-1], code), ([], {mg.HAND_NA: "head2"}, 0))

    def test_a_base_merge_without_own_paths_keeps_it(self):
        gh, code, _ = self.gate(state={mg.HAND_NA: "head1"}, own=[])  # own_paths leaves out what the base brought
        self.assertEqual((gh.removed, gh.written[-1], code), ([], {mg.HAND_NA: "head2"}, 0))

    def test_an_unknown_bound_head_is_taken_from_the_timeline_then_checked(self):
        for state in (None, {}, {mg.HAND_NA: ""}, {mg.HAND_NA: None}):
            gh, code, _ = self.gate(state=state, own=["README.md"])
            self.assertEqual((gh.removed, gh.written[-1], gh.owned, code), ([], {mg.HAND_NA: "head2"}, ("head1", "head2", "dev"), 0))

    def test_the_same_head_is_not_compared(self):
        gh, code, _ = self.gate(state={mg.HAND_NA: "head2"}, own=["src/a.ts"])
        self.assertEqual((gh.removed, gh.owned, code), ([], None, 0))
        self.assertTrue(all(w == {mg.HAND_NA: "head2"} for w in gh.written))  # nothing new to record

    def test_the_gates_own_label_keeps_its_rule_and_leaves_no_hand_record(self):
        gh, code, _ = self.gate(state={mg.AUTO_NA: "head1", mg.HAND_NA: "head0"}, own=[], events=REVIEW_OK + [labeled(self.NA)])
        self.assertEqual((gh.removed, gh.owned, code), ([self.NA], None, 1))  # the diff (src/a.ts) left the list: removed as before
        self.assertEqual(gh.written[-1], {})

    def test_a_person_label_over_the_gates_one_is_hand_set_from_then_on(self):
        gh, code, _ = self.gate(state={mg.AUTO_NA: "head1"}, own=["src/a.ts"])
        self.assertEqual(gh.removed, [self.NA])  # the gate's record is dropped; the label is checked from the timeline's commit

    def test_the_record_goes_with_the_label(self):
        gh, _, _ = self.gate(state={mg.HAND_NA: "head1"}, labels=["gate/review-passed"])
        self.assertNotIn(mg.HAND_NA, gh.written[-1] if gh.written else {})
        self.assertEqual(gh.written[-1], {})

    def test_an_unreadable_list_or_an_api_error_keeps_it_with_a_note(self):
        gh, code, out = self.gate(state={mg.HAND_NA: "head1"}, own=RuntimeError("gh api 502"))
        self.assertEqual((gh.removed, code), ([], 1))  # red (waiting): the head is not checked
        self.assertIn("(set by hand) not re-checked on this head (RuntimeError: gh api 502) — re-run the gate.", out)
        self.assertIn("Merge gate: waiting", out)
        self.assertTrue(all(w == {mg.HAND_NA: "head1"} for w in gh.written))  # still bound to head1
        for err in (ValueError("Expecting value: line 1 column 1 (char 0)"), TypeError("x"), KeyError("sha")):
            gh, code, out = self.gate(state={mg.HAND_NA: "head1"}, own=err)  # a non-JSON body, an odd answer
            self.assertEqual((gh.removed, code), ([], 1))
            self.assertIn(f"not re-checked on this head ({type(err).__name__}", out)
            self.assertIn("— re-run the gate.", out)
        gh, code, out = self.gate(state={mg.HAND_NA: "head1"}, own=["src/a.ts"], listed="src/(\n")
        self.assertEqual((gh.removed, code), ([], 1))
        self.assertIn("unreadable", out)
        self.assertIn("fix `.github/matrix-free-paths` on the base, or set the label again on this head", out)
        self.assertNotIn("re-run the gate", out)
        self.assertTrue(all(w == {mg.HAND_NA: "head1"} for w in gh.written))

    def test_a_history_that_cannot_be_listed_removes_it(self):
        gh, code, out = self.gate(state={mg.HAND_NA: "head1"}, own=None)
        self.assertEqual((gh.removed, code), ([self.NA], 1))
        self.assertIn("cannot be compared", out)
        self.assertIn(f"{mg.COMPARE_CAP} or more own commits", out)
        self.assertIn(f"{mg.FILES_CAP} or more files in one commit", out)
        self.assertIn(f"{mg.COMPARE_CAP} or more files in a merge's diff against the base, or a part of it is unreadable", out)

    def test_the_removal_names_five_paths_and_counts_the_rest(self):
        gh, _, out = self.gate(state={mg.HAND_NA: "head1"}, own=[f"src/{i}.ts" for i in range(7)])
        self.assertEqual(gh.removed, [self.NA])
        self.assertIn("'src/4.ts' and 2 more", out)
        self.assertNotIn("'src/5.ts'", out)

    def test_no_list_at_the_base_means_nothing_is_free(self):
        gh, _, out = self.gate(state={mg.HAND_NA: "head1"}, own=["README.md"], listed=None)
        self.assertEqual(gh.removed, [self.NA])
        self.assertIn("`.github/matrix-free-paths` is missing at the base", out)
        gh, _, out = self.gate(state={mg.HAND_NA: "head1"}, own=["src/a.ts"])
        self.assertNotIn("is missing", out)

    def test_a_rebase_onto_the_same_tree_keeps_it_and_rebinds(self):
        p = pull([self.NA, "gate/review-passed"], sha="head2")
        gh = Recorder(p, events=REVIEW_OK + [labeled(self.NA, actor="Nemo")], state={mg.HAND_NA: "head1"})
        gh.matrix_free_list, gh.own = self.LIST, ["src/a.ts"]
        gh.trees = {"head1": "t1", "head2": "t1"}
        code, _ = verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual((gh.removed, gh.owned, gh.written[-1], code), ([], None, {mg.HAND_NA: "head2"}, 0))
        gh.trees = {"head1": "t1", "head2": "t2"}  # another tree: compared
        gh._state = {mg.HAND_NA: "head1"}
        verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual(gh.removed, [self.NA])
        gh = Recorder(pull([self.NA, "gate/review-passed"], sha="head2"), events=REVIEW_OK + [labeled(self.NA, actor="Nemo")],
                      state={mg.HAND_NA: "head1"})
        gh.matrix_free_list, gh.own, gh.trees = self.LIST, ["src/a.ts"], {}  # unknown trees never equal
        verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual(gh.removed, [self.NA])

    def no_record(self, timeline, author="Nemo", own=("src/a.ts",), seen=None):
        p = pull([self.NA, "gate/review-passed"], sha="head2", author=author)
        gh = Recorder(p, events=REVIEW_OK + [labeled(self.NA, actor="Nemo")], state={})
        gh.matrix_free_list, gh.own, gh.timeline_events = self.LIST, own, timeline
        gh.seen = seen or {}
        code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
        return gh, code, out

    LABELED = {"event": "labeled", "label": {"name": "gate/matrix-not-needed"}, "created_at": "2026-10-20T10:00:00Z"}

    @staticmethod
    def commit(sha, at):
        return {"event": "committed", "sha": sha, "committer": {"date": f"2026-10-20T{at}Z"}}

    def test_a_label_without_a_record_is_checked_from_the_commit_it_was_set_on(self):
        tl = [self.LABELED, self.commit("c0", "09:00:00"), self.commit("c1", "10:05:00")]
        gh, code, out = self.no_record(tl, own=["src/a.ts"])  # a push to src/ after the label
        self.assertEqual((gh.removed, gh.owned, code), ([self.NA], ("c0", "head2", "dev"), 1))
        self.assertIn("'src/a.ts'", out)
        gh, code, _ = self.no_record(tl, own=["README.md"])  # a docs push
        self.assertEqual((gh.removed, gh.written[-1], code), ([], {mg.HAND_NA: "head2"}, 0))
        gh, code, _ = self.no_record(tl, own=[])  # a merge of the base: own_paths leaves its files out
        self.assertEqual((gh.removed, gh.written[-1], code), ([], {mg.HAND_NA: "head2"}, 0))

    def test_the_commit_of_the_label_is_the_last_one_seen_before_it(self):
        tl = [self.commit("old", "08:00:00"), self.commit("same", "10:00:00"), self.LABELED, self.commit("late", "10:00:01")]
        gh, _, _ = self.no_record(tl)
        self.assertEqual(gh.owned[0], "old")  # the same second counts as after: the owner cannot have looked at it
        gh, _, _ = self.no_record([self.LABELED, self.commit("old", "08:00:00"), {"event": "committed", "committer": {"date": "2026-10-20T09:59:00Z"}}])
        self.assertEqual(gh.owned[0], "old")  # an event without a sha cannot be a bound head
        # a later `labeled` of ANOTHER label does not move the label's time
        other = {"event": "labeled", "label": {"name": "gate/review-passed"}, "created_at": "2026-10-20T10:10:00Z"}
        gh, _, _ = self.no_record([self.LABELED, self.commit("c0", "09:00:00"), self.commit("c1", "10:05:00"), other])
        self.assertEqual(gh.owned[0], "c0")
        # of this label twice: the newest decides
        again = {**self.LABELED, "created_at": "2026-10-20T10:07:00Z"}
        gh, _, _ = self.no_record([self.LABELED, again, self.commit("c0", "09:00:00"), self.commit("c1", "10:05:00")])
        self.assertEqual(gh.owned[0], "c1")

    def test_a_label_without_a_record_and_a_commit_as_old_as_itself_is_removed(self):
        gh, code, out = self.no_record([self.LABELED, self.commit("late", "10:05:00")])  # force-push after, nothing older usable
        self.assertEqual((gh.removed, gh.owned, code), ([self.NA], None, 1))
        self.assertIn("is unknown", out)
        gh, _, _ = self.no_record([self.LABELED, {"event": "head_ref_force_pushed", "created_at": "2026-10-20T10:05:00Z"}])
        self.assertEqual(gh.removed, [self.NA])  # a force-push only: the commit the label was set on is gone

    def test_a_date_tie_goes_to_the_later_event_not_to_the_sha(self):
        # a rebase: the head's sha sorts lower than its parent's, both dated in the same second
        gh, _, _ = self.no_record([self.LABELED, self.commit("zzz-parent", "09:00:00"), self.commit("aaa-head", "09:00:00")])
        self.assertEqual(gh.owned[0], "aaa-head")

    def test_the_server_clock_decides_not_the_commits_own_date(self):  # F1: made before the label, pushed after it
        tl = [self.LABELED, self.commit("c0", "09:00:00"), self.commit("c1", "09:30:00")]  # c1 is dated BEFORE the label
        seen = {"c0": "2026-10-20T09:01:00Z", "c1": "2026-10-20T10:20:00Z"}  # but GitHub saw it after the label
        gh, code, out = self.no_record(tl, own=["src/a.ts"], seen=seen)
        self.assertEqual((gh.owned[0], gh.removed, code), ("c0", [self.NA], 1))  # bound to what the owner saw: c0
        self.assertIn("'src/a.ts'", out)

    def test_a_commit_in_the_middle_of_a_push_is_never_the_bound_head(self):
        tl = [self.LABELED, self.commit("c0", "09:00:00"), self.commit("mid", "09:10:00"), self.commit("tip", "09:20:00")]
        late, early = "2026-10-20T10:20:00Z", "2026-10-20T09:21:00Z"
        gh, _, _ = self.no_record(tl, seen={"c0": "2026-10-20T09:01:00Z", "mid": None, "tip": late})
        self.assertEqual(gh.owned[0], "c0")  # the push (mid, tip) came after the label: both are after it
        gh, _, _ = self.no_record(tl, seen={"c0": "2026-10-20T09:01:00Z", "mid": None, "tip": early})
        self.assertEqual(gh.owned[0], "tip")

    def test_the_live_head_without_a_check_suite_waits(self):
        tl = [self.LABELED, self.commit("c0", "09:00:00"), self.commit("head2", "09:30:00")]
        gh, code, out = self.no_record(tl, seen={"head2": None})
        self.assertEqual((gh.removed, gh.owned, code), ([], None, 1))
        self.assertIn("head2 has no check suite yet", out)
        self.assertTrue(all(mg.HAND_NA not in w for w in gh.written))

    def test_a_commit_without_a_suite_that_is_not_the_head_is_passed_over(self):  # the thread: [labeled, head1, tip, mid] in one second
        tl = [self.LABELED, self.commit("c0", "09:00:00"), self.commit("head2", "09:30:00"), self.commit("mid", "09:30:00")]
        gh, code, _ = self.no_record(tl, seen={"head2": "2026-10-20T10:20:00Z", "mid": None})
        self.assertEqual((gh.owned[0], code), ("c0", 1))

    def test_a_suite_of_another_branch_is_not_the_push_of_this_pr(self):
        tl = [self.LABELED, self.commit("c0", "09:00:00"), self.commit("c1", "09:30:00")]
        seen = {"c0": "2026-10-20T09:01:00Z", "c1": {"b-other": "2026-10-20T09:30:00Z", "feat/x": "2026-10-20T10:20:00Z"}}
        gh, code, out = self.no_record(tl, own=["src/a.ts"], seen=seen)
        self.assertEqual((gh.owned[0], gh.removed, gh.seen_ref, code), ("c0", [self.NA], "feat/x", 1))

    FP = {"event": "head_ref_force_pushed", "created_at": "2026-10-20T09:40:00Z"}

    def test_a_force_push_before_the_label_after_the_commit_was_pushed_removes_it(self):  # the thread: W, X(baseline), reset to W, label on W
        tl = [self.commit("w", "09:00:00"), self.commit("head2", "09:30:00"), self.FP, self.LABELED]
        gh, code, out = self.no_record(tl, own=[])
        self.assertEqual((gh.removed, gh.owned, code), ([self.NA], None, 1))
        self.assertIn("force-pushed after head2 was pushed", out)
        tl = [self.commit("w", "09:00:00"), self.commit("x", "09:30:00"), self.FP, self.LABELED, self.commit("head2", "10:31:00")]
        gh, code, out = self.no_record(tl, own=[])  # a later non-baseline commit on top does not hide it
        self.assertEqual((gh.removed, gh.owned, code), ([self.NA], None, 1))
        self.assertIn("force-pushed after x was pushed", out)

    def test_a_rebase_whose_suite_shares_the_second_of_its_force_push_is_kept(self):
        fp = {"event": "head_ref_force_pushed", "created_at": "2026-10-20T09:40:00Z"}
        gh, code, _ = self.no_record([self.commit("w", "09:00:00"), fp, self.commit("r", "09:40:00"), self.LABELED], own=[],
                                     seen={"w": "2026-10-20T09:00:10Z", "r": "2026-10-20T09:40:00Z"})
        self.assertEqual((gh.removed, gh.owned[0], code), ([], "r", 0))

    def test_a_force_push_in_the_second_of_the_label_counts_as_after_it(self):
        fp = {"event": "head_ref_force_pushed", "created_at": "2026-10-20T10:00:00Z"}
        gh, code, out = self.no_record([self.commit("c0", "09:00:00"), self.LABELED, fp], own=[])
        self.assertEqual((gh.removed, gh.owned, code), ([self.NA], None, 1))
        self.assertIn("force-pushed after the label", out)

    def test_a_force_push_after_the_label_removes_it(self):
        fp = {"event": "head_ref_force_pushed", "created_at": "2026-10-20T10:01:00Z"}
        gh, code, out = self.no_record([self.LABELED, self.commit("c0", "09:00:00"), fp, self.commit("c1", "10:01:00")],
                                       seen={"c1": "2026-10-20T10:01:00Z"})
        self.assertEqual((gh.removed, gh.owned, code), ([self.NA], None, 1))
        self.assertIn("force-pushed after the label", out)
        fp0 = {**fp, "created_at": "2026-10-20T08:00:00Z"}
        gh, code, _ = self.no_record([fp0, self.LABELED, self.commit("c0", "09:00:00")], own=["README.md"])
        self.assertEqual((gh.removed, gh.owned[0], code), ([], "c0", 0))

    def test_unreadable_check_suites_wait(self):
        gh, code, out = self.no_record([self.LABELED, self.commit("c0", "09:00:00")], seen={"c0": RuntimeError("HTTP 502")})
        self.assertEqual((gh.removed, gh.owned, code), ([], None, 1))
        self.assertIn("check suites of c0 unreadable, RuntimeError: HTTP 502", out)

    def test_the_real_first_seen_is_the_earliest_check_suite(self):
        gh = mg.GitHub("o/r", "1")
        pages = [{"check_suites": [{"created_at": "2026-10-20T10:00:00Z", "head_branch": "feat/x"}]},
                 {"check_suites": [{"created_at": "2026-10-20T09:00:00Z", "head_branch": "feat/x"}, {},
                                   {"created_at": "2026-10-20T08:00:00Z", "head_branch": "other"}]}]  # another branch's suite does not count
        with mock.patch.object(mg, "gh_json", return_value=pages) as call:
            self.assertEqual(gh.first_seen("abc", "feat/x"), "2026-10-20T09:00:00Z")
        self.assertEqual(call.call_args.args, ("repos/o/r/commits/abc/check-suites", "--paginate"))
        with mock.patch.object(mg, "gh_json", return_value=[{"check_suites": []}]):
            self.assertIsNone(gh.first_seen("abc", "feat/x"))

    def test_a_lagging_timeline_without_the_labeled_event_waits(self):
        gh, code, out = self.no_record([self.commit("c0", "09:00:00")])
        self.assertEqual((gh.removed, code), ([], 1))
        self.assertIn("its `labeled` event is not on the timeline yet", out)
        self.assertTrue(all(mg.HAND_NA not in w for w in gh.written))

    def test_an_unreadable_timeline_waits_unbound(self):
        gh, code, out = self.no_record(RuntimeError("HTTP 502"))
        self.assertEqual((gh.removed, code), ([], 1))
        self.assertIn("timeline unreadable, RuntimeError: HTTP 502", out)
        self.assertTrue(all(mg.HAND_NA not in w for w in gh.written))
        gh, code, out = self.no_record(ValueError("Expecting value"))  # a body that is not JSON
        self.assertEqual((gh.removed, code), ([], 1))
        self.assertIn("timeline unreadable, ValueError: Expecting value", out)
        self.assertIn("— re-run the gate.", out)

    def test_the_real_timeline_reads_the_timeline_endpoint_and_flattens_its_pages(self):
        gh = mg.GitHub("o/r", "1")
        with mock.patch.object(mg, "gh_json", return_value=[[{"event": "committed"}], [{"event": "labeled"}]]) as call:
            self.assertEqual(gh.timeline(), [{"event": "committed"}, {"event": "labeled"}])
        self.assertTrue(call.call_args.args[0].endswith("/issues/1/timeline"))
        self.assertIn("--paginate", call.call_args.args)

    def test_dependabots_label_is_not_watched(self):
        p = pull([self.NA, "gate/review-passed"], sha="head2", author="dependabot[bot]")
        gh = Recorder(p, events=REVIEW_OK + [labeled(self.NA, actor="dependabot[bot]")], state={mg.HAND_NA: "head1"})
        gh.matrix_free_list, gh.own = self.LIST, ["src/a.ts"]
        code, _ = verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual((gh.removed, gh.owned, code), ([], None, 0))
        gh, code, _ = self.no_record([self.LABELED, {"event": "head_ref_force_pushed", "created_at": "2026-10-21T10:00:00Z"}],
                                     author="app/dependabot")
        self.assertEqual(gh.removed, [])

    def test_a_pr_without_a_base_sha_is_a_note_and_keeps_it(self):
        p = pull([self.NA, "gate/review-passed"], sha="head2")
        p["base"]["sha"] = ""
        gh = Recorder(p, events=REVIEW_OK + [labeled(self.NA, actor="Nemo")], state={mg.HAND_NA: "head1"})
        gh.own = ["src/a.ts"]
        code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual((gh.removed, gh.owned, code), ([], None, 1))  # red: nothing could be checked
        self.assertIn("(the PR has no base sha) — set the label again on this head.", out)

    def test_the_list_is_read_at_the_base_sha(self):
        p = pull([self.NA, "gate/review-passed"], sha="head2")
        gh = Recorder(p, events=REVIEW_OK + [labeled(self.NA, actor="Nemo")], state={mg.HAND_NA: "head1"})
        gh.matrix_free_list, gh.own = self.LIST, ["README.md"]
        seen = []
        real = gh.file_text
        gh.file_text = lambda repo, path, ref, token=None: (seen.append(ref), real(repo, path, ref))[1]
        verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual(seen, ["base1"])

    def test_template_copies_are_not_bound(self):
        p = pull([self.NA], head="sync/templates-1", sha="head2")
        gh = Recorder(p, events=[labeled(self.NA, actor="Nemo")], state={mg.HAND_NA: "head1"})
        gh.own = ["src/a.ts"]
        verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual(gh.removed, [])


class OwnPaths(unittest.TestCase):
    """GitHub.own_paths over a fake REST graph that pages like the real API (100 files / commits a page)."""
    PAGE = 100

    @staticmethod
    def entry(f):
        """A file as a name or as (name, patch) or as a dict."""
        if isinstance(f, dict): return f
        if isinstance(f, tuple): return {"filename": f[0], "patch": f[1]}
        return {"filename": f, "patch": "+x"}

    def chunks(self, items):
        return [items[i:i + self.PAGE] for i in range(0, len(items), self.PAGE)] or [[]]

    def api(self, commits, files, compares):
        """commits: {sha: [parents]}, files: {sha: [file]}, compares: {"a...b": (status, [file], [commit shas])}."""
        def fake(path, *args, **kw):
            path = path.split("/", 3)[3]
            if path.startswith("commits/"):
                sha = path[8:]
                fs = [self.entry(f) for f in files[sha]]
                return [{"sha": sha, "parents": [{"sha": p} for p in commits[sha]], "files": ch} for ch in self.chunks(fs)]
            if path.startswith("compare/"):
                key = path[8:]
                if key not in compares:
                    raise RuntimeError("HTTP 404")
                st, fs, shas = compares[key]
                fch, cch = self.chunks([self.entry(f) for f in fs]), self.chunks(shas)
                return [{"status": st, "files": fch[i] if i < len(fch) else [],
                         "commits": [{"sha": s, "parents": [{"sha": p} for p in commits[s]]} for s in (cch[i] if i < len(cch) else [])]}
                        for i in range(max(len(fch), len(cch)))]
            raise AssertionError(path)
        return fake

    def run_it(self, commits, files, compares, base_tip="tip"):
        compares = {"B...tip": ("ahead", [], []), **compares}
        gh = mg.GitHub("o/r", "1")
        gh.base_tip = lambda ref: base_tip
        with mock.patch.object(mg, "gh_json", self.api(commits, files, compares)):
            return gh.own_paths("B", "H", "dev")

    def test_own_commits_count_with_their_files(self):
        c = {"c1": ["B"], "c2": ["c1"]}
        out = self.run_it(c, {"c1": ["a.ts"], "c2": ["b.md", "a.ts"]}, {"B...H": ("ahead", [], ["c1", "c2"])})
        self.assertEqual(out, ["a.ts", "b.md"])

    def test_a_rename_counts_with_both_names(self):
        f = {"filename": "docs/a.md", "previous_filename": "src/a.ts", "patch": "+x"}
        self.assertEqual(self.run_it({"c1": ["B"]}, {"c1": [f]}, {"B...H": ("ahead", [], ["c1"])}), ["docs/a.md", "src/a.ts"])

    def test_the_files_of_every_page_count(self):
        many = [f"d{i}.md" for i in range(150)] + ["package.json"]  # the non-free one is on page 2
        out = self.run_it({"c1": ["B"]}, {"c1": many}, {"B...H": ("ahead", [], ["c1"])})
        self.assertIn("package.json", out)
        self.assertEqual(len(out), 151)

    def test_the_commits_of_every_page_count(self):
        shas = [f"c{i}" for i in range(120)]  # the PR's last commit is on page 2 of the compare
        c = {s: ["B"] for s in shas}
        out = self.run_it(c, {s: ["a.md"] for s in shas[:-1]} | {"c119": ["package.json"]}, {"B...H": ("ahead", [], shas)})
        self.assertIn("package.json", out)
        base = [f"b{i}" for i in range(120)]  # and the base's commits of the tip compare span two pages as well
        c2 = {"m": ["B"], **{b: ["B"] for b in base}}
        out = self.run_it(c2, {"m": ["a.md"], **{b: ["src/x.ts"] for b in base}},
                          {"B...H": ("ahead", [], ["m", *base]), "B...tip": ("ahead", [], base)})
        self.assertEqual(out, ["a.md"])  # b119 is on the second page of `theirs`

    def merge(self, merge_files, diff, incoming, **extra):
        c = {"m": ["B", "x"]}
        compares = {"B...H": ("ahead", [], ["m"]), "tip...x": ("behind", [], []), "x...m": ("ahead", diff, []),
                    "B...x": ("ahead", incoming, []), **extra}
        return self.run_it(c, {"m": merge_files}, compares)

    def test_a_merge_of_the_base_counts_only_what_the_base_did_not_bring(self):
        out = self.merge(["from-base.ts", "conflict.ts", "own.md"], diff=["conflict.ts", "own.md"],
                         incoming=[("from-base.ts", "+b"), ("conflict.ts", "+b")])
        self.assertEqual(out, ["conflict.ts", "own.md"])  # from-base.ts equals the base's content at m

    def test_a_clean_base_merge_has_no_own_paths(self):
        self.assertEqual(self.merge(["a.ts", "b.ts"], diff=["old-pr-file.ts"], incoming=["a.ts"]), [])

    def test_a_file_both_sides_edited_merged_cleanly_is_the_bases(self):
        patch = "@@ -1,3 +1,4 @@\n ctx\n+\"dep\": \"2\"\n ctx"
        shifted = "@@ -7,3 +7,4 @@\n other ctx\n+\"dep\": \"2\"\n more ctx"  # the same change, other hunk header and context
        out = self.merge([("package.json", shifted)], diff=["package.json"], incoming=[("package.json", patch)])
        self.assertEqual(out, [])
        out = self.merge([("package.json", shifted + "\n+\"evil\": 1")], diff=["package.json"], incoming=[("package.json", patch)])
        self.assertEqual(out, ["package.json"])  # a resolution adds a line
        out = self.merge([("package.json", None)], diff=["package.json"], incoming=[("package.json", patch)])
        self.assertEqual(out, ["package.json"])  # no patch to compare (binary, too large): the PR's

    def test_a_cap_on_a_merge_compare_is_unknown(self):
        big = [f"f{i}.md" for i in range(mg.COMPARE_CAP)]
        self.assertIsNone(self.merge(["a.md"], diff=big, incoming=["a.md"]))  # a cut list would let `&=` keep what the base brought

    def test_an_unreadable_base_change_of_a_merge_is_unknown(self):
        out = self.run_it({"m": ["B", "x"]}, {"m": ["a.md"]},
                          {"B...H": ("ahead", [], ["m"]), "tip...x": ("behind", [], []), "x...m": ("ahead", ["a.md"], [])})
        self.assertIsNone(out)  # `compare B...x` is a 404

    def test_an_unreadable_diff_against_the_base_parent_is_unknown(self):
        out = self.run_it({"m": ["B", "x"]}, {"m": ["a.md"]},
                          {"B...H": ("ahead", [], ["m"]), "tip...x": ("behind", [], []), "B...x": ("ahead", ["a.md"], [])})
        self.assertIsNone(out)  # `compare x...m` is a 404: an empty list would empty the merge's files

    def test_an_unreadable_commit_is_unknown(self):
        real = self.api({"c1": ["B"]}, {"c1": ["a.md"]}, {"B...H": ("ahead", [], ["c1"]), "B...tip": ("ahead", [], [])})
        def fake(path, *args, **kw):
            if "/commits/" in path:
                raise RuntimeError("gh api: HTTP 404")
            return real(path, *args, **kw)
        gh = mg.GitHub("o/r", "1"); gh.base_tip = lambda ref: "tip"
        with mock.patch.object(mg, "gh_json", fake):
            self.assertIsNone(gh.own_paths("B", "H", "dev"))

    def test_a_clean_merge_of_a_base_that_brought_many_files_is_not_unknown(self):
        big = [f"f{i}.md" for i in range(260)]
        self.assertEqual(self.merge(big, diff=["old.md"], incoming=big), [])  # the merge lists them all as changed vs P1; the base's list only takes files away

    def test_a_binary_file_edited_on_both_sides_is_the_prs(self):
        self.assertEqual(self.merge([("blob.bin", None)], diff=["blob.bin"], incoming=[("blob.bin", None)]), ["blob.bin"])
    def test_an_octopus_merge_checks_every_extra_parent(self):
        c = {"m": ["B", "x", "y"]}
        compares = {"B...H": ("ahead", [], ["m"]), "tip...x": ("behind", [], []), "tip...y": ("identical", [], []),
                    "x...m": ("ahead", ["a.md", "z.ts"], []), "y...m": ("ahead", ["z.ts"], []),
                    "B...x": ("ahead", [], []), "B...y": ("ahead", [], [])}
        self.assertEqual(self.run_it(c, {"m": ["a.md", "z.ts"]}, compares), ["z.ts"])  # a.md equals y's content: brought by y

    def test_a_merge_of_something_else_counts_whole(self):
        c = {"m": ["B", "x"]}
        out = self.run_it(c, {"m": ["f.ts"]}, {"B...H": ("ahead", [], ["m"]), "tip...x": ("diverged", [], [])})
        self.assertEqual(out, ["f.ts"])

    def test_an_unavailable_base_side_counts_the_merge_whole(self):
        c = {"m": ["B", "x"]}  # `compare tip...x` is a 404: unreadable is not the base
        self.assertEqual(self.run_it(c, {"m": ["f.ts"]}, {"B...H": ("ahead", [], ["m"])}), ["f.ts"])

    def test_a_base_merge_between_own_commits(self):
        c = {"c1": ["B"], "m": ["c1", "x"], "c2": ["m"]}
        out = self.run_it(c, {"c1": ["a.md"], "m": ["base.ts"], "c2": ["b.md"]},
                          {"B...H": ("ahead", [], ["c1", "m", "c2"]), "tip...x": ("identical", [], []),
                           "x...m": ("ahead", ["a.md"], []), "c1...x": ("ahead", ["base.ts"], [])})
        self.assertEqual(out, ["a.md", "b.md"])

    def test_the_bases_own_commits_in_the_range_are_not_the_prs(self):
        c = {"b1": ["B"], "m": ["B", "b1"], "c2": ["m"]}
        compares = {"B...H": ("ahead", [], ["b1", "m", "c2"]), "B...tip": ("ahead", [], ["b1"]),
                    "tip...b1": ("behind", [], []), "b1...m": ("ahead", [], []), "B...b1": ("ahead", ["src/x.ts"], [])}
        self.assertEqual(self.run_it(c, {"b1": ["src/x.ts"], "m": ["src/x.ts"], "c2": ["a.md"]}, compares), ["a.md"])
        many = [f"b{i}" for i in range(mg.COMPARE_CAP)]  # the base's commits are not capped, the PR's own are
        c3 = {"m1": ["B"], **{b: ["B"] for b in many}}
        self.assertEqual(self.run_it(c3, {"m1": ["README.md"], **{b: [] for b in many}},
                                     {"B...H": ("ahead", [], ["m1", *many]), "B...tip": ("ahead", [], many)}), ["README.md"])
        gh = mg.GitHub("o/r", "1"); gh.base_tip = lambda ref: "tip"
        del compares["B...tip"]
        with mock.patch.object(mg, "gh_json", self.api(c, {"b1": ["src/x.ts"], "m": [], "c2": ["a.md"]}, compares)):
            self.assertIsNone(gh.own_paths("B", "H", "dev"))  # the base's list unavailable: unknown

    def test_an_unrelated_history_or_a_gone_commit_is_unknown(self):
        for compares in ({"B...H": ("diverged", [], [])}, {"B...H": ("behind", [], [])}, {}):
            self.assertIsNone(self.run_it({}, {}, compares))

    def test_too_many_commits_or_files_is_unknown(self):
        shas = [f"c{i}" for i in range(mg.COMPARE_CAP)]
        c = {s: ["B"] for s in shas}
        self.assertIsNone(self.run_it(c, {s: [] for s in shas}, {"B...H": ("ahead", [], shas)}))
        self.assertIsNone(self.run_it({"c1": ["B"]}, {"c1": [f"{i}.md" for i in range(mg.FILES_CAP)]},
                                      {"B...H": ("ahead", [], ["c1"])}))  # GitHub's own limit for one commit
        out = self.run_it({"c1": ["B"]}, {"c1": [f"{i}.md" for i in range(mg.FILES_CAP - 1)]}, {"B...H": ("ahead", [], ["c1"])})
        self.assertEqual(len(out), mg.FILES_CAP - 1)  # a big own commit below it is listed whole

    def test_an_api_error_propagates(self):
        gh = mg.GitHub("o/r", "1")
        with mock.patch.object(mg, "gh_json", side_effect=RuntimeError("HTTP 502")):
            with self.assertRaises(RuntimeError):
                gh.own_paths("B", "H", "dev")


class GitHubFiles(unittest.TestCase):
    """The real `pulls/{pr}/files` readers."""

    def test_one_read_serves_names_renames_and_statuses(self):
        pages = [[{"filename": "README.md", "previous_filename": "src/app.ts", "status": "renamed"}, {"filename": "b.md"}]]
        with mock.patch.object(mg, "gh_json", return_value=pages) as api:
            gh = mg.GitHub("o/r", "1")
            self.assertEqual(gh.touched_paths(), ["README.md", "src/app.ts", "b.md"])
            self.assertEqual(gh.files(), ["README.md", "b.md"])
            self.assertEqual(gh.file_status(), {"README.md": "renamed", "b.md": ""})
        self.assertEqual(api.call_count, 1)

    def test_write_state_returns_the_comment_id(self):
        with mock.patch.object(mg, "gh_json", return_value={"id": 9}):
            self.assertEqual(mg.GitHub("o/r", "1").write_state(None, {"a": "b"}), 9)
            self.assertEqual(mg.GitHub("o/r", "1").write_state(5, {"a": "b"}), 5)


class CallerArgv(unittest.TestCase):
    def test_argv_is_accepted_by_run_pr_checks_parser(self):
        """The argv merge_gate builds must parse under run_pr_checks.py's argparse: an unknown flag is exit 2 there."""
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        path = next((p for p in (os.path.join(here, "..", "..", "plugins", "omnisgm", "scripts", "checks", "run_pr_checks.py"),
                                 os.path.join(here, "run_pr_checks.py")) if os.path.isfile(p)), None)
        if path is None:
            self.skipTest("run_pr_checks.py is not next to this repo copy")
        spec = importlib.util.spec_from_file_location("run_pr_checks_under_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        calls = []
        d = tempfile.mkdtemp(prefix="gate-argv-")
        try:
            script = os.path.join(d, "run_pr_checks.py")
            touch(script)
            touch(os.path.join(d, mg.PR_CHECKS_LIB))
            env = {"GITHUB_STEP_SUMMARY": os.path.join(d, "s.md"), "REPO": "o/r", "PR": "7"}
            with mock.patch.dict(os.environ, env):
                mg.pr_checks_report(script, lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""))
        finally:
            shutil.rmtree(d)
        self.assertEqual(len(calls), len(mg.PR_CHECKS_GROUPS))
        self.assertEqual(set().union(*(mod.GROUPS.get(g, (g,)) for g in mg.PR_CHECKS_GROUPS)), set(mod.ALL))   # no check left out
        self.assertLessEqual(mod.FILES_TIMEOUT + 2 * mod.GH_TIMEOUT, mg.PR_CHECKS_TIMEOUT)   # hygiene's worst case: the files list once, a read per other check
        for argv in (c[2:] for c in calls):   # [python, script, *argv]
            reached = []

            def stop(*a, **kw):
                reached.append(a)
                raise RuntimeError("no network in this test")

            with self.subTest(argv=argv), contextlib.redirect_stdout(io.StringIO()):
                try:
                    code = mod.main(argv, gh=stop)
                except SystemExit as e:
                    self.fail(f"run_pr_checks.py rejected merge_gate's argv {argv} (exit {e.code})")
                self.assertEqual(code, 0)       # --report: exit 0 once the argv is accepted; 2 = parsed but never reached a check
                self.assertTrue(reached, f"{argv} parsed but no check reached gh")   # the checks catch the stop themselves


class WorkflowContract(unittest.TestCase):
    """merge-gate.yml next to this file: the job IS the required context — nothing else reports a verdict."""

    def _text(self, name="merge-gate.yml", here=None, optional_in_copy=False):
        here = here or os.path.dirname(os.path.abspath(__file__))
        for candidate in (os.path.join(here, name), os.path.join(here, "..", "workflows", name)):
            if os.path.exists(candidate):
                with open(candidate) as f:
                    return f.read()
        # A repo copy (.github/scripts) may run this test before the sync PR that adds the workflow is merged:
        # a skip there, a failure in templates/workflows, where a renamed workflow must not turn the only check into a skip.
        if optional_in_copy and os.path.basename(os.path.normpath(here)) == "scripts":
            self.skipTest(f"{name} is not rolled out in this repo yet")
        self.fail(f"{name} not found next to the script or in ../workflows")

    @staticmethod
    def _types(text):
        on = text.split("\non:\n", 1)[1].split("\n\n", 1)[0]
        types = [l.split("#")[0].strip() for l in on.splitlines() if l.strip().startswith("types:")]
        assert len(types) == 1, types
        return on, {x.strip() for x in types[0].split("[", 1)[1].split("]", 1)[0].split(",")}   # a set: "labeled" is not in "unlabeled"

    def test_a_missing_report_workflow_skips_in_a_copy_and_fails_in_the_template(self):
        d = tempfile.mkdtemp(prefix="gate-copy-")
        try:
            copy, tmpl = os.path.join(d, ".github", "scripts"), os.path.join(d, "templates", "workflows")
            os.makedirs(copy)
            os.makedirs(tmpl)
            with self.assertRaises(unittest.SkipTest):
                self._text("pr-checks-report.yml", here=copy, optional_in_copy=True)
            with self.assertRaises(self.failureException):
                self._text("pr-checks-report.yml", here=tmpl, optional_in_copy=True)
            with self.assertRaises(self.failureException):
                self._text("merge-gate.yml", here=copy)                  # the verdict's own workflow is never optional
        finally:
            shutil.rmtree(d)

    def test_the_job_is_named_merge_gate_and_only_runs_the_script(self):
        text = self._text()
        jobs = text.split("\njobs:\n", 1)[1]  # the job's own `name:` (4 spaces), not the workflow's on line 1
        self.assertEqual([l.split("#")[0].rstrip() for l in jobs.splitlines() if l.startswith("    name: ")],
                         ["    name: Merge gate"])  # the ruleset's required context (authoring-workflows 12b); the report is another workflow
        on, types = self._types(text)
        self.assertLessEqual({"opened", "reopened", "ready_for_review", "synchronize", "labeled", "unlabeled"}, types)
        self.assertNotIn("workflow_dispatch", on)  # a dispatch run is attached to no PR: never a verdict (Table#1251)
        self.assertNotIn("--fail", text)
        self.assertNotIn("checks: write", text)
        self.assertIn("      checks: read", text)  # first_seen reads commits/{sha}/check-suites: a 403 would wait forever
        self.assertEqual(text.count("run: python3 .github/scripts/merge_gate.py"), 1)
        self.assertNotIn("--pr-checks-report", text)   # no report job in the verdict's workflow: it would hold `merge-gate-<PR>`

    def test_the_report_is_a_workflow_of_its_own_with_its_own_group(self):
        text, gate = self._text("pr-checks-report.yml", optional_in_copy=True), self._text()
        group = lambda s: re.search(r"\nconcurrency:\n  group: (.+)\n  cancel-in-progress: (\w+)", s).groups()
        self.assertNotEqual(group(text)[0], group(gate)[0])               # the verdict's group is never held by a report
        self.assertEqual(group(text), ("pr-checks-${{ github.event.pull_request.number }}", "true"))
        on, types = self._types(text)
        self.assertEqual(types, {"opened", "reopened", "ready_for_review", "synchronize"})   # no label events: a label changes nothing the checks read
        self.assertNotIn("workflow_dispatch", on)
        jobs = text.split("\njobs:\n", 1)[1]
        self.assertEqual([l.split("#")[0].rstrip() for l in jobs.splitlines() if l.startswith("    name: ")], ["    name: PR checks report"])
        self.assertIn("grep -q -- '--pr-checks-report' .github/scripts/merge_gate.py", jobs)   # an old copy would compute the verdict
        self.assertLess(jobs.index("grep -q -- '--pr-checks-report'"), jobs.index("python3 .github/scripts/merge_gate.py --pr-checks-report"))
        self.assertIn("python3 .github/scripts/merge_gate.py --pr-checks-report", jobs)
        self.assertNotIn("name: Merge gate", jobs)                        # not the required context's name
        self.assertNotIn("needs:", jobs)
        minutes = int(re.search(r"\n    timeout-minutes: (\d+)", jobs).group(1))
        self.assertGreater(minutes * 60, len(mg.PR_CHECKS_GROUPS) * mg.PR_CHECKS_TIMEOUT + 180)   # the groups + the gh bootstrap
        perms = re.search(r"\n    permissions:\n((?:      \S.*\n)+)", jobs)
        self.assertIsNotNone(perms)                                       # no block = the repo's default token rights
        self.assertEqual(sorted(l.split("#")[0].strip() for l in perms.group(1).splitlines()),
                         ["contents: read", "issues: read", "pull-requests: read"])   # a report reads


class Gate(unittest.TestCase):
    def test_bound_labels_on_the_live_head_pass(self):
        rm, fail, st = mg.evaluate(Fake(), pull(["gate/matrix-passed", "gate/review-passed"]), ["src/a.ts"], REVIEW_OK,
                                   {"gate/matrix-passed": "head1"})
        self.assertEqual((rm, fail), ([], []))
        self.assertEqual(st, {"gate/matrix-passed": {"sha": "head1", "tree": None}})  # an old string entry reads as tree None

    def test_labeled_event_records_the_payload_head(self):
        rm, fail, st = mg.evaluate(Fake(), pull(["gate/matrix-passed", "gate/review-passed"]), ["src/a.ts"], REVIEW_OK, {},
                                   event="labeled", event_label="gate/matrix-passed", event_head="head1")
        self.assertEqual((rm, fail), ([], []))
        self.assertEqual(st["gate/matrix-passed"]["sha"], "head1")

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
        fake = Fake(own=[], trees={"head1": "t1"})  # came from dev: own_paths leaves the base's files out
        rm, fail, st = mg.evaluate(fake, pull(["gate/snapshots-approved", "gate/matrix-not-needed", "gate/review-passed"]),
                                   [SNAP], REVIEW_OK, {"gate/snapshots-approved": "head0"})
        self.assertEqual((rm, fail), ([], []))
        self.assertEqual(fake.owned, ("head0", "head1", "dev"))
        self.assertEqual(st["gate/snapshots-approved"], {"sha": "head1", "tree": "t1"})  # re-bound WITH the live tree

    def test_snapshot_approval_dies_when_own_baselines_differ_between_the_heads(self):
        fake = Fake(own=[SNAP])
        rm, fail, st = mg.evaluate(fake, pull(["gate/snapshots-approved", "gate/matrix-not-needed", "gate/review-passed"]),
                                   [SNAP], REVIEW_OK, {"gate/snapshots-approved": "head0"})
        self.assertEqual(rm, ["gate/snapshots-approved"])
        self.assertEqual(len(fail), 1)
        self.assertNotIn("gate/snapshots-approved", st)

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
            self.assertEqual(mg.GitHub("r", "1").state(), (2, {"gate/matrix-passed": {"sha": "real", "tree": None}}))

    def test_compare_unknown_is_conservative(self):
        rm, _, _ = mg.evaluate(Fake(own=None), pull(["gate/snapshots-approved"]), [SNAP], [],
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
        wf = ".github/workflows/sync-recheck.yml"
        cases = [(".claude/rules/b.md", st) for st in ("added", "renamed", "removed", "copied", "")]
        cases += [(wf, st) for st in ("renamed", "removed", "copied", "")]  # a workflow copy: only `added` joins `modified`
        for path, status in cases:
            files = [".claude/rules/a.md", path]
            gh = SyncFake(([], [], []), {files[0]: "modified", path: status})
            _, fail, _ = mg.evaluate(gh, pull(head="sync/templates-abc1234"), files, [], {})
            waiting, errors = mg.split_outcome(fail)
            self.assertTrue(any("only modified copies, and added workflow copies" in e and path in e
                                and "outside `sync/templates-*`" in e for e in errors), (path, status, fail))
            self.assertEqual(waiting, [], status)
            self.assertEqual(gh.asked, [], status)  # blobs are not even compared

    def test_template_sync_exempts_an_added_workflow_copy(self):
        for path in sorted(mg.WORKFLOW_COPIES):
            files = [".claude/rules/a.md", path]
            gh = SyncFake(([], [], []), {files[0]: "modified", path: "added"})
            _, fail, _ = mg.evaluate(gh, pull(head="sync/templates-abc1234"), files, [], {})
            self.assertEqual(fail, [], path)
            self.assertEqual([a[0] for a in gh.asked], [tuple(files)], path)  # its text is still compared
            gh = SyncFake(([], [], [path]), {files[0]: "modified", path: "added"})  # settings unlike the repo's gate
            _, fail, _ = mg.evaluate(gh, pull(head="sync/templates-abc1234"), files, [], {})
            self.assertTrue(fail, path)

    def test_new_copy_takes_the_settings_lines_of_the_repos_gate(self):
        tpl = ("jobs:\n  a:\n    runs-on: self-hosted   # note\n  b:\n    runs-on: self-hosted\n"
               "      - uses: actions/setup-node@v4\n        with:\n          node-version: 22\nend\n")
        donor = "jobs:\n  g:\n    runs-on: ubuntu-latest\n  h:\n    runs-on: ubuntu-latest\n"
        self.assertEqual(mg.new_copy("a.yml", tpl, donor),
                         tpl.replace("self-hosted   # note", "ubuntu-latest").replace("runs-on: self-hosted", "runs-on: ubuntu-latest"))
        for other in ("jobs:\n  g:\n    runs-on: ubuntu-latest\n  h:\n    runs-on: self-hosted\n",  # two texts: no choice
                      "", None, "jobs:\n  g:\n    steps: []\n"):  # no gate, no runs-on line
            with self.subTest(donor=other):
                self.assertEqual(mg.new_copy("a.yml", tpl, other), tpl)
        donor24 = donor + "          node-version: 24\n"
        self.assertIn("          node-version: 24\n", mg.new_copy("a.yml", tpl, donor24))  # each setting by its own name
        self.assertNotIn("node-version: 22", mg.new_copy("a.yml", tpl, donor24))
        self.assertEqual(mg.new_copy("a.py", "    runs-on: self-hosted\n", donor), "    runs-on: self-hosted\n")  # a script

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

    def test_a_settings_key_only_one_side_has(self):
        # claude-plugins#23: claude-review.yml v2.60 adds the `publish` job, so the template has a `runs-on` key no copy has
        tpl = "jobs:\n  a:\n    runs-on: self-hosted\n  b:\n    runs-on: self-hosted\n  n:\n    runs-on: self-hosted\n"
        cases = [  # (copy, the line job n gets)
            ("jobs:\n  a:\n    runs-on: ubuntu-latest\n  b:\n    runs-on: ubuntu-latest\n", "ubuntu-latest"),  # the repo's mapping
            ("jobs:\n  a:\n    runs-on: self-hosted\n  b:\n    runs-on: self-hosted\n", "self-hosted"),
            ("jobs:\n  a:\n    runs-on: ubuntu-latest\n  b:\n    runs-on: self-hosted\n", "self-hosted"),   # no agreement: the template's
            # no agreement, and neither copy line is the template's: a set pick cannot pass by luck (hash order)
            ("jobs:\n  a:\n    runs-on: ubuntu-latest\n  b:\n    runs-on: macos-latest\n", "self-hosted"),
            ("jobs:\n  z:\n    runs-on: ubuntu-latest\n", "self-hosted"),  # no shared key at all: the template's
        ]
        for copy, want in cases:
            with self.subTest(copy=copy):
                out = mg.split_settings("w.yml", mg.with_settings("w.yml", tpl, copy))[1]
                self.assertEqual(out[("n", "runs-on:", 0)], f"    runs-on: {want}")
                self.assertEqual(sorted(out), sorted(mg.split_settings("w.yml", tpl)[1]))  # a key only the copy has goes
        # the mapping reads the template LINE: a different template line (a comment) is another setting value
        tpl2 = tpl.replace("  n:\n    runs-on: self-hosted\n", "  n:\n    runs-on: self-hosted   # x\n")
        out = mg.with_settings("w.yml", tpl2, cases[0][0])
        self.assertIn("  n:\n    runs-on: self-hosted   # x", out)
        # a template line no copy key shares (a new setting in a new job) stays the template's
        tpl3 = "  CI_CHECK: 'V'\njobs:\n  a:\n    runs-on: self-hosted\n  n:\n    node-version: 24\n"
        out = mg.with_settings("w.yml", tpl3, "  CI_CHECK: 'X'\njobs:\n  a:\n    runs-on: ubuntu-latest\n")
        self.assertIn("  n:\n    node-version: 24", out)
        self.assertIn("  CI_CHECK: 'X'", out)
        # a copy key the template dropped is gone, the rest keep the copy's lines
        out = mg.with_settings("w.yml", "jobs:\n  a:\n    runs-on: self-hosted\n",
                               "jobs:\n  a:\n    runs-on: ubuntu-latest\n  gone:\n    runs-on: ubuntu-latest\n")
        self.assertEqual(out, "jobs:\n  a:\n    runs-on: ubuntu-latest\n")

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
        # a job added with a settings line: the copy's a/b disagree on the template line `self-hosted` → the template's
        self.assertTrue(mg.with_settings("w.yml", tpl + "  c:\n    runs-on: self-hosted\n", copy).endswith("  c:\n    runs-on: self-hosted\n"))

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
            # a job the template adds (claude-plugins#23): the merge must carry the sync's line for it, no other
            texts[(T, "templates/workflows/merge-gate.yml", R)] = "jobs:\n  a:\n    runs-on: self-hosted\n  p:\n    runs-on: self-hosted\n"
            texts[("o/r", wf, "t")] = "jobs:\n  a:\n    runs-on: ubuntu-latest\n  old:\n    runs-on: ubuntu-latest\n"
            for p_line, bad in (("ubuntu-latest", []), ("self-hosted", [wf])):
                merged = f"jobs:\n  a:\n    runs-on: ubuntu-latest\n  p:\n    runs-on: {p_line}\n"
                texts[("o/r", wf, "h")] = texts[("o/r", wf, "m")] = merged
                with self.subTest(p=p_line):
                    self.assertEqual(gh.template_mismatches([wf], "h", "m", "t"), ([], [], bad))
            texts[("o/r", wf, "h")] = texts[("o/r", wf, "m")] = "jobs:\n  a:\n    runs-on: self-hosted\n  p:\n    runs-on: ubuntu-latest\n"
            self.assertEqual(gh.template_mismatches([wf], "h", "m", "t"), ([], [], [wf]))  # an old key still keeps the base's
            # an added copy (claude-plugins#71): no copy at the base, the settings come from the base's merge-gate.yml
            rc = ".github/workflows/sync-recheck.yml"
            texts[(T, "templates/workflows/sync-recheck.yml", R)] = "jobs:\n  r:\n    runs-on: self-hosted\n"
            texts[("o/r", rc, "t")] = None
            texts[("o/r", wf, "t")] = "jobs:\n  a:\n    runs-on: ubuntu-latest\n"
            for line, bad in (("ubuntu-latest", []), ("self-hosted", [rc])):
                texts[("o/r", rc, "h")] = texts[("o/r", rc, "m")] = f"jobs:\n  r:\n    runs-on: {line}\n"
                with self.subTest(added=line):
                    self.assertEqual(gh.template_mismatches([rc], "h", "m", "t"), ([], [], bad))
            texts[("o/r", wf, "t")] = None  # no gate at the base: the template's lines
            texts[("o/r", rc, "h")] = texts[("o/r", rc, "m")] = "jobs:\n  r:\n    runs-on: ubuntu-latest\n"
            self.assertEqual(gh.template_mismatches([rc], "h", "m", "t"), ([], [], [rc]))
            texts[("o/r", rc, "h")] = texts[("o/r", rc, "m")] = "jobs:\n  r:\n    runs-on: self-hosted\n"
            self.assertEqual(gh.template_mismatches([rc], "h", "m", "t"), ([], [], []))
            # a copy the base carries keeps its OWN line, not the gate's: Rules' merge-gate.yml runs on ubuntu-latest,
            # its sync-recheck.yml on self-hosted (the claude-review.yml of Table/Rules/News is the real case: CI_CHECK)
            texts[("o/r", wf, "t")] = "jobs:\n  a:\n    runs-on: ubuntu-latest\n"
            texts[("o/r", rc, "t")] = "old\njobs:\n  r:\n    runs-on: self-hosted\n"
            for line, bad in (("self-hosted", []), ("ubuntu-latest", [rc])):
                texts[("o/r", rc, "h")] = texts[("o/r", rc, "m")] = f"jobs:\n  r:\n    runs-on: {line}\n"
                with self.subTest(carried=line):
                    self.assertEqual(gh.template_mismatches([rc], "h", "m", "t"), ([], [], bad))
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
        st = {"gate/matrix-passed": {"sha": "abc", "tree": "t1"}, "gate/snapshots-approved": {"sha": "def", "tree": None}}
        self.assertEqual(mg.parse_state(mg.render_state(st)), st)
        old = {"gate/matrix-passed": "abc", mg.AUTO_NA: "h"}  # the string form of before the tree binding; other keys stay as they are
        self.assertEqual(mg.parse_state(mg.render_state(old)),
                         {"gate/matrix-passed": {"sha": "abc", "tree": None}, mg.AUTO_NA: "h"})
        self.assertEqual(mg.parse_state("<!-- merge-gate-state garbage -->"), {})

    def test_unlabeled_drops_the_state_entry(self):
        _, _, st = mg.evaluate(Fake(), pull(["gate/matrix-not-needed", "gate/review-passed"]), ["src/a.ts"], REVIEW_OK,
                               {"gate/matrix-passed": "head1"}, event="unlabeled", event_label="gate/matrix-passed")
        self.assertEqual(st, {})


class SnapshotApproval(unittest.TestCase):
    """#91: `gate/snapshots-approved` survives commits that leave the PR's own baselines alone (bound from the timeline when
    its `labeled` run left no record) and `gate/snapshots-review-needed` says the owner has to look."""
    S, RN, M = "gate/snapshots-approved", "gate/snapshots-review-needed", "gate/matrix-passed"
    LABELED = {"event": "labeled", "label": {"name": "gate/snapshots-approved"}, "created_at": "2026-10-20T10:00:00Z"}
    TIMELINE = [LABELED, {"event": "committed", "sha": "head1", "committer": {"date": "2026-10-20T09:00:00Z"}}]
    BASE = {"gate/matrix-passed": {"sha": "head2", "tree": None}}

    class Rec(Recorder):
        snaps, add_error, remove_error = [SNAP], None, None
        def files(self): return list(self.snaps)
        def add_label(self, name):
            if self.add_error: raise self.add_error
            super().add_label(name)
        def remove_label(self, name):
            if self.remove_error and name == "gate/snapshots-review-needed": raise self.remove_error
            super().remove_label(name)

    def gate(self, labels, state=None, own=("src/a.ts",), timeline=TIMELINE, snaps=(SNAP,), head="head2", base="dev",
             head_ref="feat/x", add_error=None, remove_error=None, seen=None, trees=None):
        p = pull(labels, sha=head, base=base, head=head_ref)
        gh = self.Rec(p, events=REVIEW_OK + [labeled(self.S, actor="Nemo")], state={**self.BASE, **(state or {})})
        gh.own, gh.timeline_events, gh.snaps, gh.add_error, gh.remove_error = own, timeline, list(snaps), add_error, remove_error
        gh.seen, gh.trees = seen or {}, dict(trees or {})
        code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
        return gh, code, out

    ON = ["gate/snapshots-approved", "gate/matrix-passed", "gate/review-passed"]

    def test_no_record_and_a_push_without_baselines_keeps_it_and_rebinds(self):
        gh, code, _ = self.gate(self.ON)
        self.assertEqual((gh.removed, gh.added, code), ([], (), 0))
        self.assertEqual(gh.owned, ("head1", "head2", "dev"))  # bound to the last commit dated at or before the label
        self.assertEqual(gh.written[-1][self.S], {"sha": "head2", "tree": None})

    def test_no_record_and_an_own_baseline_change_removes_it(self):
        gh, code, _ = self.gate(self.ON, own=[SNAP])
        self.assertEqual((gh.removed, gh.added, code), ([self.S], (self.RN,), 1))  # and the owner is asked to look again
        self.assertNotIn(self.S, gh.written[-1])

    def test_a_recorded_head_and_an_own_baseline_change_removes_it(self):
        gh, code, out = self.gate(self.ON, state={self.S: {"sha": "head1", "tree": None}}, own=["src/a.ts", SNAP])
        self.assertEqual((gh.removed, gh.added, gh.owned, code), ([self.S], (self.RN,), ("head1", "head2", "dev"), 1))
        self.assertIn("::notice::removed gate/snapshots-approved by the gate", out)  # neutral: the reason is printed where it is decided
        self.assertIn("::notice::`gate/snapshots-approved` removed by the gate: the PR's own commits since head1 changed baselines: "
                      "'tests/e2e/a.spec.ts-snapshots/x.png'.", out)
        self.assertNotIn("applied on another head", out)

    def test_a_recorded_head_and_a_push_without_baselines_keeps_it(self):
        gh, code, _ = self.gate(self.ON, state={self.S: {"sha": "head1", "tree": None}})
        self.assertEqual((gh.removed, gh.added, code, gh.written[-1][self.S]["sha"]), ([], (), 0, "head2"))

    def test_a_base_merge_that_brought_baselines_keeps_it(self):
        for state in ({self.S: {"sha": "head1", "tree": None}}, {}):
            gh, code, _ = self.gate(self.ON, state=state, own=[])  # own_paths leaves out what the base brought
            self.assertEqual((gh.removed, gh.added, code), ([], (), 0))

    def test_history_that_cannot_be_compared_removes_it(self):
        for state in ({self.S: {"sha": "head1", "tree": None}}, {}):
            gh, code, out = self.gate(self.ON, state=state, own=None)
            self.assertEqual((gh.removed, gh.added, code), ([self.S], (self.RN,), 1))
            self.assertIn("the commits since head1 cannot be compared", out)

    def test_a_matrix_label_of_another_head_says_which_heads_in_the_log(self):
        gh, code, out = self.gate(self.ON, state={self.M: {"sha": "headOld", "tree": None}, self.S: {"sha": "head2", "tree": None}})
        self.assertEqual((gh.removed, code), ([self.M], 1))
        self.assertIn("::notice::`gate/matrix-passed` removed by the gate: it was applied on headOld, the live head is head2.", out)

    def test_an_approval_stays_when_the_pr_has_no_baselines_left(self):
        gh, code, _ = self.gate(self.ON, snaps=["src/a.ts"], state={self.S: {"sha": "head1", "tree": None}}, own=["src/a.ts"])
        self.assertEqual((gh.removed, code, gh.written[-1][self.S]["sha"]), ([], 0, "head2"))

    def test_other_exceptions_of_the_bound_head_checks_wait_too(self):
        gh, code, out = self.gate(self.ON, state={self.S: {"sha": "head1", "tree": None}}, own=ValueError("not json"))
        self.assertEqual((gh.removed, code), ([], 1))
        self.assertIn("not re-checked on this head (ValueError: not json)", out)
        gh, code, out = self.gate(self.ON, trees={"head1": ValueError("not json")})
        self.assertEqual((gh.removed, code), ([], 1))
        self.assertIn("not re-checked on this head (ValueError: not json)", out)
        gh, code, out = self.gate(self.ON, seen={"head1": KeyError("check_suites")})
        self.assertEqual(code, 1)
        self.assertIn("check suites of head1 unreadable, KeyError", out)

    def test_a_rebase_whose_suite_shares_the_second_of_its_force_push_is_kept(self):  # the candidate is the commit the force-push made
        c = lambda sha, at: {"event": "committed", "sha": sha, "committer": {"date": f"2026-10-20T{at}Z"}}
        fp = {"event": "head_ref_force_pushed", "created_at": "2026-10-20T09:40:00Z"}
        gh, code, _ = self.gate(self.ON, head="r", state={self.M: {"sha": "r", "tree": None}}, own=[],
                                timeline=[c("w", "09:00:00"), fp, c("r", "09:40:00"), self.LABELED],
                                seen={"w": "2026-10-20T09:00:10Z", "r": "2026-10-20T09:40:00Z"})
        self.assertEqual((gh.removed, gh.written[-1][self.S]["sha"], code), ([], "r", 0))

    def test_an_api_error_keeps_it_and_waits(self):
        for state in ({self.S: {"sha": "head1", "tree": None}}, {}):
            gh, code, out = self.gate(self.ON, state=state, own=RuntimeError("HTTP 502"))
            self.assertEqual((gh.removed, gh.added, code), ([], (), 1))
            self.assertIn("waiting: `gate/snapshots-approved` not re-checked on this head (RuntimeError: HTTP 502)", out)
            self.assertEqual(gh.written[-1].get(self.S, {}).get("sha"), "head1" if state else None)  # not re-bound

    def test_no_record_and_a_lagging_or_unreadable_timeline_waits_with_the_label_kept(self):
        for tl, why in (([self.TIMELINE[1]],"`labeled` event is not on the timeline yet"), (RuntimeError("HTTP 502"), "timeline unreadable")):
            gh, code, out = self.gate(self.ON, timeline=tl)
            self.assertEqual((gh.removed, gh.owned, code), ([], None, 1))
            self.assertIn(why, out)
            self.assertNotIn(self.S, gh.written[-1] if gh.written else {})

    def test_no_record_and_no_commit_as_old_as_the_label_removes_it_with_a_note(self):
        gh, code, out = self.gate(self.ON, timeline=[self.LABELED, {"event": "committed", "sha": "late",
                                                                    "committer": {"date": "2026-10-20T10:05:00Z"}}])
        self.assertEqual((gh.removed, gh.owned, code), ([self.S], None, 1))
        self.assertIn("::notice::`gate/snapshots-approved` removed by the gate: no commit on the timeline is as old as the label", out)

    def test_a_commit_made_before_the_label_but_pushed_after_it_is_not_the_head_the_owner_saw(self):  # F1
        tl = [self.LABELED, {"event": "committed", "sha": "head1", "committer": {"date": "2026-10-20T09:00:00Z"}},
              {"event": "committed", "sha": "head1b", "committer": {"date": "2026-10-20T09:30:00Z"}}]  # head1b dated before the label
        seen = {"head1": "2026-10-20T09:01:00Z", "head1b": "2026-10-20T10:20:00Z"}  # GitHub saw it after the label
        gh, code, _ = self.gate(self.ON, timeline=tl, seen=seen, own=[SNAP])  # its baseline change must not ride on the approval
        self.assertEqual((gh.owned[0], gh.removed, code), ("head1", [self.S], 1))

    def test_no_record_and_the_live_head_without_a_check_suite_waits(self):
        tl = [*self.TIMELINE, {"event": "committed", "sha": "head2", "committer": {"date": "2026-10-20T09:30:00Z"}}]
        gh, code, out = self.gate(self.ON, timeline=tl, seen={"head2": None})
        self.assertEqual((gh.removed, gh.owned, code), ([], None, 1))
        self.assertIn("head2 has no check suite yet", out)

    def test_a_commit_without_a_suite_that_is_not_the_head_is_passed_over(self):  # the thread's timeline
        tl = [*self.TIMELINE, {"event": "committed", "sha": "head2", "committer": {"date": "2026-10-20T09:30:00Z"}},
              {"event": "committed", "sha": "mid", "committer": {"date": "2026-10-20T09:30:00Z"}}]
        gh, code, _ = self.gate(self.ON, timeline=tl, seen={"head2": "2026-10-20T10:20:00Z", "mid": None}, own=[SNAP])
        self.assertEqual((gh.owned[0], gh.removed, code), ("head1", [self.S], 1))

    def test_a_suite_of_another_branch_does_not_make_a_commit_seen(self):  # a stack: B1 was pushed to branch b before the label
        tl = [self.LABELED, {"event": "committed", "sha": "head1", "committer": {"date": "2026-10-20T09:00:00Z"}},
              {"event": "committed", "sha": "head2", "committer": {"date": "2026-10-20T09:30:00Z"}}]
        seen = {"head1": "2026-10-20T09:01:00Z", "head2": {"b": "2026-10-20T09:30:00Z", "feat/x": "2026-10-20T10:01:00Z"}}
        gh, code, _ = self.gate(self.ON, timeline=tl, seen=seen, own=[SNAP])
        self.assertEqual((gh.owned[0], gh.removed, gh.seen_ref, code), ("head1", [self.S], "feat/x", 1))

    def test_a_force_push_before_the_label_after_the_commit_was_pushed_removes_it(self):  # the thread: W, X(baseline), reset to W, label on W
        c = lambda sha, at: {"event": "committed", "sha": sha, "committer": {"date": f"2026-10-20T{at}Z"}}
        fp = {"event": "head_ref_force_pushed", "created_at": "2026-10-20T09:40:00Z"}
        seen = {"w": "2026-10-20T09:00:10Z", "head2": "2026-10-20T09:30:00Z"}
        gh, code, out = self.gate(self.ON, timeline=[c("w", "09:00:00"), c("head2", "09:30:00"), fp, self.LABELED], seen=seen, own=[SNAP])
        self.assertEqual((gh.removed, gh.owned, code), ([self.S], None, 1))
        self.assertIn("force-pushed after head2 was pushed", out)
        gh, code, out = self.gate(self.ON, head="z", state={self.M: {"sha": "z", "tree": None}}, own=[],
                                  timeline=[c("w", "09:00:00"), c("head2", "09:30:00"), fp, self.LABELED, c("z", "10:31:00")],
                                  seen={**seen, "z": "2026-10-20T10:31:00Z"})  # a later non-baseline commit on top does not hide it
        self.assertEqual((gh.removed, gh.owned, code), ([self.S], None, 1))
        self.assertIn("force-pushed after head2 was pushed", out)

    def test_a_force_push_in_the_second_of_the_label_counts_as_after_it(self):
        fp = {"event": "head_ref_force_pushed", "created_at": "2026-10-20T10:00:00Z"}
        gh, code, out = self.gate(self.ON, timeline=[self.TIMELINE[1], self.LABELED, fp], seen={"head1": "2026-10-20T09:00:10Z"}, own=[])
        self.assertEqual((gh.removed, gh.owned, code), ([self.S], None, 1))
        self.assertIn("force-pushed after the label", out)

    def test_an_unreadable_tree_of_the_bound_head_waits_with_the_label_kept(self):
        gh, code, out = self.gate(self.ON, trees={"head1": RuntimeError("HTTP 502")})
        self.assertEqual((gh.removed, gh.owned, code), ([], None, 1))
        self.assertIn("not re-checked on this head (RuntimeError: HTTP 502)", out)

    def test_check_suites_that_are_not_json_wait(self):
        gh, code, out = self.gate(self.ON, seen={"head1": ValueError("not json")})
        self.assertEqual((gh.removed, gh.owned, code), ([], None, 1))
        self.assertIn("check suites of head1 unreadable, ValueError: not json", out)

    def test_a_force_push_after_the_label_removes_a_recordless_approval(self):
        fp = {"event": "head_ref_force_pushed", "created_at": "2026-10-20T10:01:00Z"}
        gh, code, out = self.gate(self.ON, timeline=[*self.TIMELINE, fp], own=[])
        self.assertEqual((gh.removed, gh.owned, code), ([self.S], None, 1))
        self.assertIn("force-pushed after the label", out)

    def test_a_suite_in_the_second_of_the_label_counts_as_after_it(self):
        gh, _, _ = self.gate(self.ON, seen={"head1": "2026-10-20T10:00:00Z"}, own=[])
        self.assertEqual((gh.removed, gh.owned), ([self.S], None))  # nothing seen strictly before the label: removed

    def test_bound_to_the_live_head_from_the_timeline_is_recorded_without_a_walk(self):
        gh, code, _ = self.gate(self.ON, head="head1", state={self.M: {"sha": "head1", "tree": None}}, own=[SNAP])
        self.assertEqual((gh.removed, gh.owned, code, gh.written[-1][self.S]["sha"]), ([], None, 0, "head1"))

    def test_the_same_tree_after_a_recordless_binding_keeps_and_rebinds_with_the_tree(self):
        gh, code, _ = self.gate(self.ON, own=[SNAP], trees={"head1": "t1", "head2": "t1"})
        self.assertEqual((gh.removed, gh.owned, code, gh.written[-1][self.S]), ([], None, 0, {"sha": "head2", "tree": "t1"}))

    def test_review_needed_is_added_while_baselines_wait_for_the_approval(self):
        gh, code, out = self.gate(["gate/matrix-passed", "gate/review-passed"])
        self.assertEqual((gh.added, gh.removed, code), ((self.RN,), [], 1))
        self.assertIn("waiting for `gate/snapshots-approved`", out)  # the WAIT line stays the only failure

    def test_review_needed_is_left_on_while_it_is_still_wanted(self):
        gh, _, _ = self.gate(["gate/matrix-passed", "gate/review-passed", self.RN])
        self.assertEqual((gh.added, gh.removed), ((), []))  # a `labeled`/`unlabeled` re-run writes nothing: no loop

    def test_review_needed_goes_when_the_approval_is_on(self):
        gh, code, _ = self.gate(self.ON + [self.RN], state={self.S: {"sha": "head2", "tree": None}})
        self.assertEqual((gh.removed, gh.added, code), ([self.RN], (), 0))

    def test_review_needed_goes_when_the_pr_no_longer_changes_baselines(self):
        gh, _, _ = self.gate(["gate/matrix-passed", "gate/review-passed", self.RN], snaps=["src/a.ts"])
        self.assertEqual((gh.removed, gh.added), ([self.RN], ()))
        gh, _, _ = self.gate(["gate/matrix-passed", "gate/review-passed"], snaps=["src/a.ts"])
        self.assertEqual((gh.removed, gh.added), ([], ()))

    def test_a_release_pr_gets_no_review_needed(self):
        gh, _, _ = self.gate(["gate/matrix-passed"], base="master", head_ref="release/2026-11-15")
        self.assertEqual(gh.added, ())

    def test_only_a_release_branch_into_master_is_a_release(self):
        for base, head_ref in (("master", "feat/x"), ("dev", "release/2026-11-15")):
            gh, _, _ = self.gate(["gate/matrix-passed", "gate/review-passed"], base=base, head_ref=head_ref)
            self.assertEqual(gh.added, (self.RN,), (base, head_ref))

    def test_the_wait_line_and_the_label_share_one_rule(self):
        pl = pull(base="master", head="release/x")
        self.assertEqual((mg.awaited_snapshots(pl, [SNAP, "src/a.ts"]), mg.awaited_snapshots(pull(), [SNAP, "src/a.ts"])), (0, 1))
        _, fail, _ = mg.evaluate(Fake(), pl, [SNAP], [], {})
        self.assertFalse(any("screenshot baseline" in f for f in fail))

    def test_a_label_the_repo_does_not_have_is_a_notice_not_a_crash(self):
        err = subprocess.CalledProcessError(1, ["gh", "pr", "edit"])
        gh, code, out = self.gate(["gate/matrix-passed", "gate/review-passed"], add_error=err)
        self.assertEqual(code, 1)  # still only the WAIT line
        self.assertIn("::notice::`gate/snapshots-review-needed` not added", out)
        gh, code, out = self.gate(self.ON + [self.RN], state={self.S: {"sha": "head2", "tree": None}}, remove_error=err)
        self.assertEqual(code, 0)
        self.assertIn("::notice::`gate/snapshots-review-needed` not removed", out)

    def test_the_label_name_has_an_env_override(self):
        import importlib
        self.addCleanup(importlib.reload, mg)  # the module goes back to its default constants, whatever happens below
        with mock.patch.dict(os.environ, {"LABEL_SNAP_REVIEW": "x/look"}):
            self.assertEqual(importlib.reload(mg).LABEL_SNAP_REVIEW, "x/look")
            gh = self.Rec(pull(["gate/matrix-passed"]))
            mg.snap_review_label(gh, gh.pull(), [SNAP], [])
            self.assertEqual(gh.added, ("x/look",))  # the function reads the constant, not a literal


class StackedPrs(unittest.TestCase):
    """Stacked PRs (a base that is another PR's branch) and the tree binding of the head-bound labels."""
    M, S, R = "gate/matrix-passed", "gate/snapshots-approved", "gate/review-passed"

    def test_a_lower_pr_with_its_label_on_its_own_head_stays_green(self):  # (1)
        rm, fail, _ = mg.evaluate(Fake(), pull([self.M, self.R], base="feat/lower-base", default="dev"), ["src/a.ts"],
                                  REVIEW_OK, {self.M: {"sha": "head1", "tree": "t1"}})
        self.assertEqual((rm, fail), ([], []))

    def test_head_moved_with_the_same_tree_keeps_and_rebinds_both_labels(self):  # (2)
        for name in (self.M, self.S):
            fake = Fake(trees={"head1": "t1"})
            rm, fail, st = mg.evaluate(fake, pull([name, "gate/matrix-not-needed", self.R] if name == self.S else [name, self.R]),
                                       [SNAP] if name == self.S else ["src/a.ts"], REVIEW_OK,
                                       {name: {"sha": "head0", "tree": "t1"}})
            self.assertEqual((rm, fail, st[name]), ([], [], {"sha": "head1", "tree": "t1"}), name)
            self.assertIsNone(fake.owned, name)  # no own_paths walk is needed when the trees are equal

    def test_head_moved_with_another_tree_removes_the_label(self):  # (3)
        rm, _, st = mg.evaluate(Fake(trees={"head1": "t2"}), pull([self.M]), ["src/a.ts"], [],
                                {self.M: {"sha": "head0", "tree": "t1"}})
        self.assertEqual(rm, [self.M])
        self.assertNotIn(self.M, st)

    def test_an_old_string_entry_has_no_tree_and_none_never_equals_none(self):  # (4)
        # the live head's tree cannot be read either: None == None must not keep the label
        for name in (self.M, self.S):
            fake = Fake(own=None)
            labels = [name] if name == self.M else [name, "gate/matrix-not-needed"]
            rm, _, st = mg.evaluate(fake, pull(labels), [SNAP], [], {name: "head0"})
            self.assertEqual(rm, [name], name)
            self.assertNotIn(name, st)
            self.assertEqual(fake.tree_reads, [], name)  # an unknown tree is not even looked up for the live head
        rm, _, _ = mg.evaluate(Fake(trees={}), pull([self.M]), ["src/a.ts"], [], {self.M: {"sha": "head0", "tree": None}})
        self.assertEqual(rm, [self.M])

    def test_the_labeled_event_records_the_tree_of_the_event_head_not_the_live_one(self):  # (5)
        # applied on head0 (tree A), live head is head1 (tree B): the recorded tree is A, so the label does not survive
        fake = Fake(trees={"head0": "A", "head1": "B"})
        rm, _, st = mg.evaluate(fake, pull([self.M, self.R]), ["src/a.ts"], REVIEW_OK, {},
                                event="labeled", event_label=self.M, event_head="head0")
        self.assertEqual(rm, [self.M])
        self.assertEqual(fake.tree_reads[0], "head0")
        # applied on the live head: the entry carries the live head's tree
        _, _, st = mg.evaluate(fake, pull([self.M, self.R]), ["src/a.ts"], REVIEW_OK, {}, event="labeled", event_label=self.M,
                               event_head="head1")
        self.assertEqual(st[self.M], {"sha": "head1", "tree": "B"})

    def test_snapshots_approved_is_kept_on_an_equal_tree_even_when_compare_is_unknown(self):  # (6)
        rm, fail, st = mg.evaluate(Fake(own=None, trees={"head1": "t1"}),
                                   pull([self.S, "gate/matrix-not-needed", self.R]), [SNAP], REVIEW_OK,
                                   {self.S: {"sha": "head0", "tree": "t1"}})
        self.assertEqual((rm, fail, st[self.S]), ([], [], {"sha": "head1", "tree": "t1"}))

    def test_the_messages_no_longer_mention_workflow_dispatch_or_the_default_branch(self):  # (7)
        _, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-not-needed"], base="feat/lower"), ["src/a.ts"], [], {})
        text = " ".join(fail)
        self.assertIn("gate/review-passed", text)
        self.assertNotIn("workflow_dispatch", text)
        self.assertNotIn("default branch", text)

    def test_a_stacked_pr_without_the_review_label_waits_it_is_not_an_error(self):  # (8)
        _, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-not-needed"], base="feat/lower", default="dev"), ["src/a.ts"], [], {})
        waiting, errors = mg.split_outcome(fail)
        self.assertEqual(errors, [])
        self.assertEqual(len(waiting), 1)
        self.assertTrue(waiting[0].startswith("waiting for `gate/review-passed`"))
        gh = Recorder(pull(["gate/matrix-not-needed"], base="feat/lower"))
        code, out = verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual(code, 1)
        self.assertIn("::error::waiting: waiting for `gate/review-passed`", out)
        self.assertNotIn("## Merge gate: blocked", out)

    def test_github_tree_reads_the_commit_and_an_unreadable_one_is_none(self):
        with mock.patch.object(mg, "gh_json", return_value={"sha": "c", "tree": {"sha": "t9"}}) as call:
            self.assertEqual(mg.GitHub("o/r", "1").tree("c"), "t9")
        call.assert_called_once_with("repos/o/r/git/commits/c")
        with mock.patch.object(mg, "gh_json", side_effect=RuntimeError("HTTP 404")):
            self.assertIsNone(mg.GitHub("o/r", "1").tree("c"))

    def test_the_run_binds_the_tree_and_keeps_the_label_through_a_retarget(self):
        gh = Recorder(pull([self.M, self.R], base="dev", sha="head2"), events=REVIEW_OK,
                      state={self.M: {"sha": "head1", "tree": "t1"}})
        gh.tree = lambda sha: {"head2": "t1"}.get(sha)
        code, _ = verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual((code, gh.removed, gh.written), (0, [], [{self.M: {"sha": "head2", "tree": "t1"}}]))

    def test_github_tree_swallows_only_a_missing_commit_and_other_errors_propagate(self):
        for err, ok in (("HTTP 404", True), ("HTTP 422", True), ("HTTP 502", False), ("rate limit exceeded", False)):
            with mock.patch.object(mg, "gh_json", side_effect=RuntimeError(err)):
                if ok:
                    self.assertIsNone(mg.GitHub("o/r", "1").tree("c"), err)
                else:
                    with self.assertRaises(RuntimeError, msg=err):
                        mg.GitHub("o/r", "1").tree("c")

    def test_a_tree_read_error_turns_the_run_red_and_keeps_the_label(self):
        gh = Recorder(pull([self.M, self.R], sha="head2"), events=REVIEW_OK, state={self.M: {"sha": "head1", "tree": "t1"}})
        def boom(sha): raise RuntimeError("HTTP 502")
        gh.tree = boom
        with self.assertRaises(RuntimeError):
            verdict(gh, lambda: mg.run(gh, gh.pull()))
        self.assertEqual((gh.removed, gh.written), ([], []))

    def test_a_malformed_state_comment_is_no_state_and_a_malformed_entry_no_head(self):
        self.assertEqual(mg.parse_state(mg.render_state([1])), {})  # valid JSON, not an object
        self.assertEqual(mg.parse_state(mg.render_state("x")), {})
        for bad in (None, {"tree": "t"}, 7):
            rm, fail, _ = mg.evaluate(Fake(), pull([self.M, self.R]), ["src/a.ts"], REVIEW_OK, {self.M: bad})
            self.assertEqual(rm, [], bad)
            self.assertEqual(len(fail), 1, bad)
            self.assertIn("no head is recorded", fail[0], bad)

    def test_the_resolve_release_skip_holds_for_release_into_master_only(self):
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.normpath(os.path.join(here, "..", "..", ".github", "workflows", "claude-review.yml"))
        if not os.path.exists(path):
            self.skipTest("a repo copy: claude-review.yml is checked in claude-plugins")
        line = next(l.strip() for l in open(path) if 'skip="release PR' in l)
        def skipped(base, head):
            out = subprocess.run(["bash", "-c", f'skip=""; base="{base}"; head="{head}"; {line}; echo "$skip"'],
                                 capture_output=True, text=True, check=True).stdout.strip()
            return out
        self.assertEqual(skipped("master", "release/2026-11-13"), "release PR (exempt from gate/review-passed)")
        self.assertEqual(skipped("master", "dev"), "")            # dev -> master gets a round
        self.assertEqual(skipped("feat/lower", "release/x"), "")  # a release-looking head into another base is an ordinary PR
        self.assertEqual(skipped("dev", "feat/x"), "")

    def test_the_review_workflow_does_not_skip_a_stacked_pr(self):
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.normpath(os.path.join(here, "..", "..", ".github", "workflows", "claude-review.yml"))
        if not os.path.exists(path):
            self.skipTest("a repo copy: claude-review.yml is checked in claude-plugins")
        text = open(path).read()
        self.assertNotIn("base is not the default branch", text)
        # the Resolve step: no default-branch input, and exactly this set of skip reasons (a skip on the base would add one)
        start = text.index("      - name: Resolve PR")
        step = text[start:text.index("\n      - name:", start + 10)]
        self.assertNotIn("DEFAULT_BRANCH", step)
        self.assertNotIn("default_branch", step)
        self.assertEqual(set(re.findall(r'skip="([^"]*)"', step)), {
            "review is paused (REVIEW_PAUSED)",
            "", "draft", "dependabot", "template sync (merge gate checks the copies)",
            "plugin-copy (merge gate checks the copies)", "release PR (exempt from gate/review-passed)", "PR is not open",
            "gate/review-passed is set — remove the label to request a round",
            "CI check '$CI_CHECK' on the head is '$c', not success"})
        self.assertIn('[ "$draft" = "false" ] || skip="draft"', step)  # a draft still gets no round
        # the base may only matter together with a release head (merge_gate.py: base master + release/*); never alone
        for line in step.splitlines():
            if 'skip=' in line and '$base' in line:
                self.assertIn('release/', line)
                self.assertIn('"$base" != "master"', line)


if __name__ == "__main__":
    unittest.main()
