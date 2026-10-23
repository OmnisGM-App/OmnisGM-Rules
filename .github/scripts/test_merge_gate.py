"""Tests for merge_gate: evaluate (table), the check-run lifecycle of run()/main(), --fail.
Run: python3 .github/scripts/test_merge_gate.py (in a repo copy) / python3 templates/workflows/test_merge_gate.py."""
import io
import os
import tempfile
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
        self.suite = None
        self.closed, self.removed, self.written = [], [], []

    def pull(self): return self._pull
    def open_check(self, head): return 7
    def suite_branch(self, check_id): return self.suite or self._pull["head"]["ref"]
    def state(self):
        if self.boom: raise self.boom
        return (None, self._state)
    def files(self): return ["src/a.ts"]
    def events(self): return self._events
    def events_again(self): return self._events
    def write_state(self, comment_id, state): self.written.append(state)
    def remove_label(self, name): self.removed.append(name)
    def close_check(self, *a): self.closed.append(a)


def lifecycle(gh, call):
    """Runs `call` with GITHUB_OUTPUT on a temp file and the summary on stdout captured; returns the output file text."""
    with tempfile.NamedTemporaryFile("w+", suffix=".out") as out, \
            mock.patch.dict(os.environ, {"GITHUB_OUTPUT": out.name, "GITHUB_STEP_SUMMARY": "", "REPO": "o/r", "PR": "1"}), \
            mock.patch("sys.stdout", new_callable=io.StringIO):
        call()
        out.seek(0)
        return out.read()


class CheckRunLifecycle(unittest.TestCase):
    """What the `Merge gate` check run ends as — the behaviour the ruleset reads (review of Rules#443 / News#165)."""

    def test_waiting_leaves_the_check_in_progress_and_marks_closed(self):
        gh = Recorder(pull())  # no labels at all: matrix pair and review label still awaited
        out = lifecycle(gh, lambda: mg.run(gh, gh.pull(), 7))
        (cid, status, conclusion, title, _), = gh.closed
        self.assertEqual((cid, status, conclusion), (7, "in_progress", None))
        self.assertTrue(title.startswith("waiting: "))
        self.assertIn("closed=true", out)

    def test_a_contradiction_closes_the_check_as_failure(self):
        gh = Recorder(pull(["gate/matrix-passed", "gate/matrix-not-needed", "gate/review-passed"]), events=REVIEW_OK,
                      state={"gate/matrix-passed": "head1"})
        lifecycle(gh, lambda: mg.run(gh, gh.pull(), 7))
        (cid, status, conclusion, title, _), = gh.closed
        self.assertEqual((cid, status, conclusion), (7, "completed", "failure"))
        self.assertTrue(title.startswith("blocked: "))

    def test_every_label_holding_closes_the_check_as_success(self):
        gh = Recorder(pull(["gate/matrix-passed", "gate/review-passed"]), events=REVIEW_OK, state={"gate/matrix-passed": "head1"})
        lifecycle(gh, lambda: mg.run(gh, gh.pull(), 7))
        self.assertEqual(gh.closed, [(7, "completed", "success", "labels ok", "every required label holds on this head")])

    def test_a_label_bound_to_another_head_is_removed_and_the_rest_is_still_awaited(self):
        gh = Recorder(pull(["gate/matrix-passed"]), state={"gate/matrix-passed": "head0"})  # bound to another head
        lifecycle(gh, lambda: mg.run(gh, gh.pull(), 7))
        self.assertEqual(gh.removed, ["gate/matrix-passed"])
        self.assertEqual(gh.closed[0][1:3], ("in_progress", None))

    def test_a_suite_without_a_branch_does_not_block(self):
        gh = Recorder(pull(["gate/matrix-passed", "gate/review-passed"]), events=REVIEW_OK, state={"gate/matrix-passed": "head1"})
        with mock.patch.object(gh, "suite_branch", lambda check_id: None), mock.patch.object(mg, "GitHub", lambda repo, pr: gh):
            lifecycle(gh, mg.main)
        self.assertEqual(gh.closed[0][1:3], ("completed", "success"))

    def test_a_close_that_fails_on_the_error_path_leaves_no_closed_marker(self):
        gh = Recorder(pull(), boom=OSError("api down"))
        gh.close_check = lambda *a: (_ for _ in ()).throw(OSError("cannot close"))
        with mock.patch.object(mg, "GitHub", lambda repo, pr: gh), \
                tempfile.NamedTemporaryFile("w+", suffix=".out") as outf, \
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": outf.name, "REPO": "o/r", "PR": "1"}), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaises(OSError):
                mg.main()
            outf.seek(0)
            self.assertNotIn("closed=true", outf.read())

    def test_a_head_shared_with_another_branch_fails_the_job_with_the_cut_advice(self):
        gh = Recorder(pull(["gate/matrix-passed"], head="release/2026-10-23", base="master", sha="f0ba9722"),
                      state={"gate/matrix-passed": "f0ba9722"})
        gh.suite = "dev"  # the suite the API put the check run into
        with mock.patch.object(mg, "GitHub", lambda repo, pr: gh), \
                tempfile.NamedTemporaryFile("w+", suffix=".out") as outf, \
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": outf.name, "REPO": "o/r", "PR": "1"}), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(mg.main(), 1)
            outf.seek(0)
            self.assertIn("closed=true", outf.read())
        (cid, status, conclusion, title, summary), = gh.closed
        self.assertEqual((status, conclusion), ("completed", "cancelled"))  # dev's suite: not a pass, not its verdict
        self.assertIn("head of `dev`", summary)
        self.assertIn("own commit", summary)
        self.assertIn("re-apply the gate labels", summary)

    def test_a_shared_head_close_that_fails_is_not_retried_as_failure(self):
        gh = Recorder(pull(["gate/matrix-passed"], head="release/2026-10-23", base="master", sha="f0ba9722"))
        gh.suite = "dev"
        calls = []

        def close(*a):
            calls.append(a)
            raise OSError("5xx")
        gh.close_check = close
        with mock.patch.object(mg, "GitHub", lambda repo, pr: gh), \
                tempfile.NamedTemporaryFile("w+", suffix=".out") as outf, \
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": outf.name, "REPO": "o/r", "PR": "1"}), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(mg.main(), 1)  # the job still blocks; the error is not re-raised into the handler
            outf.seek(0)
            self.assertNotIn("closed=true", outf.read())
        self.assertEqual([c[2] for c in calls], ["cancelled"])  # no second close as `failure` in dev's suite

    def test_an_error_after_the_open_closes_the_check_as_failure_marks_closed_and_re_raises(self):
        gh = Recorder(pull(), boom=OSError("api down"))
        with mock.patch.object(mg, "GitHub", lambda repo, pr: gh), \
                tempfile.NamedTemporaryFile("w+", suffix=".out") as outf, \
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": outf.name, "REPO": "o/r", "PR": "1"}), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaises(OSError):
                mg.main()
            outf.seek(0)
            self.assertIn("closed=true", outf.read())
        (cid, status, conclusion, title, summary), = gh.closed
        self.assertEqual((cid, status, conclusion, title), (7, "completed", "failure", "gate run failed"))
        self.assertIn("api down", summary)


class WorkflowContract(unittest.TestCase):
    """merge-gate.yml next to this file: the `--fail` step must read the marker the script writes."""

    def test_the_fail_step_is_guarded_by_the_closed_marker(self):
        here = os.path.dirname(os.path.abspath(__file__))
        for candidate in (os.path.join(here, "merge-gate.yml"), os.path.join(here, "..", "workflows", "merge-gate.yml")):
            if os.path.exists(candidate):
                with open(candidate) as f:
                    text = f.read()
                break
        else:
            self.fail("merge-gate.yml not found next to the script or in ../workflows")
        steps = text.split("\n      - ")
        gate = [s for s in steps if "run: python3 .github/scripts/merge_gate.py\n" in s]
        fail = [s for s in steps if "merge_gate.py --fail" in s]
        self.assertEqual((len(gate), len(fail)), (1, 1))
        self.assertIn("id: gate", [l.split("#")[0].strip() for l in gate[0].splitlines()])
        if_line = [l for l in fail[0].splitlines() if l.strip().startswith("if:")]
        self.assertEqual(len(if_line), 1)
        self.assertEqual(" ".join(if_line[0].split("#")[0].split()),
                         "if: (failure() || cancelled()) && steps.gate.outputs.closed != 'true'")


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

    def test_suite_branch_reads_the_check_run_then_its_suite(self):
        with mock.patch.object(mg, "gh_json", side_effect=[{"check_suite": {"id": 5}}, {"head_branch": "dev"}]) as api:
            self.assertEqual(mg.GitHub("o/r", "1").suite_branch(7), "dev")
        self.assertEqual([c.args[0] for c in api.call_args_list], ["repos/o/r/check-runs/7", "repos/o/r/check-suites/5"])
        with mock.patch.object(mg, "gh_json", side_effect=[{"check_suite": None}]):
            self.assertIsNone(mg.GitHub("o/r", "1").suite_branch(7))

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
        self.assertEqual(mg.split_outcome(fail)[1], [])  # an event lag is awaited, not a contradiction
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

    def test_fail_mode_posts_a_fresh_failure_on_the_live_head(self):
        calls = []

        def post(path, payload=None):
            calls.append((path, payload))
            return {"head": {"sha": "live9"}} if path == "pulls/7" else {"id": 1}
        p = mg.report_dead_run("o/r", "7", "t", "died", post=post)
        self.assertEqual([c[0] for c in calls], ["pulls/7", "check-runs"])
        self.assertEqual((p["head_sha"], p["status"], p["conclusion"], p["name"]), ("live9", "completed", "failure", mg.CHECK_NAME))

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
