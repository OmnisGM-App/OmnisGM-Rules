"""Tests for merge_gate: evaluate (table), the job verdict of run()/main(), the workflow contract.
Run: python3 .github/scripts/test_merge_gate.py (in a repo copy) / python3 templates/workflows/test_merge_gate.py."""
import io
import os
import unittest
from unittest import mock

import merge_gate as mg

BOT = mg.WORKFLOW_ACTOR
SNAP = "tests/e2e/a.spec.ts-snapshots/x.png"


def pull(labels=(), head="feat/x", base="dev", author="Nemo", sha="head1"):
    return {"labels": [{"name": l} for l in labels], "head": {"ref": head, "sha": sha},
            "base": {"ref": base}, "user": {"login": author}}


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
