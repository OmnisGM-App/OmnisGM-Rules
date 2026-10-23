"""Table tests for merge_gate.evaluate — run: python3 -m unittest templates/workflows/test_merge_gate.py"""
import unittest

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
        self.assertEqual(mg.split_outcome(fail)[1], [])  # an event lag is awaited, not a contradiction
        # a later hand-applied event beats an older bot one; the newest event decides
        ev = [labeled("gate/review-passed", at="2026-10-20T09:00:00Z"), labeled("gate/review-passed", actor="Nemo", at="2026-10-20T11:00:00Z")]
        _, fail, _ = mg.evaluate(Fake(), pull(["gate/review-passed", "gate/matrix-not-needed"]), ["src/a.ts"], ev, {})
        self.assertEqual(len(fail), 1)

    def test_dependabot_needs_only_the_matrix_label(self):
        for login in ("dependabot[bot]", "app/dependabot"):
            _, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-not-needed"], author=login), ["package.json"], [], {})
            self.assertEqual(fail, [], login)

    def test_release_pr_from_dev_needs_only_the_matrix_label(self):
        files = [SNAP, "src/a.ts"]
        for head in ("dev", "release/2026-10-20-1"):
            _, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-not-needed"], head=head, base="master"), files, [], {})
            self.assertEqual(fail, [], head)
        _, fail, _ = mg.evaluate(Fake(), pull(["gate/matrix-not-needed"], head="feat/x", base="master"), files, [], {})
        self.assertEqual(len(fail), 2)

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
