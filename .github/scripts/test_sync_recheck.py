"""Tests for sync_recheck. Run: python3 .github/scripts/test_sync_recheck.py (in a repo copy) /
python3 templates/workflows/test_sync_recheck.py."""
import io
import os
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest import mock

import sync_recheck as sr

HERE = os.path.dirname(os.path.abspath(__file__))


def pr(num, ref, sha):
    return {"number": num, "head": {"ref": ref, "sha": sha}}


def run(rid, at, status="completed", event="pull_request"):
    return {"id": rid, "created_at": at, "status": status, "event": event}


class Fake:
    def __init__(self, pulls, runs, statuses=(), fail_rerun=(), attempts=()):
        """fail_rerun: one refused `gh run rerun` per occurrence of a run id."""
        self.pulls, self.runs, self.statuses, self.fail_rerun = pulls, runs, list(statuses), list(fail_rerun)
        self.attempts = list(attempts)
        self.reran, self.asked_base, self.asked_runs = [], None, []

    def open_pulls(self, base):
        self.asked_base = base
        return self.pulls

    def gate_runs(self, sha, branch):
        self.asked_runs.append((sha, branch))
        return self.runs.get(sha, [])

    def run_state(self, run_id):
        self.polls = getattr(self, "polls", 0) + 1
        if self.polls > 100:
            raise AssertionError("polled past any deadline")
        status = self.statuses.pop(0) if self.statuses else "in_progress"
        return status, self.attempts.pop(0) if self.attempts else 1

    def rerun(self, run_id):
        if run_id in self.fail_rerun:
            self.fail_rerun.remove(run_id)
            raise subprocess.CalledProcessError(1, ["gh", "run", "rerun", str(run_id)])
        self.reran.append(run_id)


class Clock:
    """Each wait advances the clock by the waited seconds."""
    def __init__(self):
        self.t, self.waited = 0.0, 0

    def __call__(self):
        return self.t

    def wait(self, s):
        self.t += s
        self.waited += 1


def recheck(fake, budget=300):
    out, clock = io.StringIO(), Clock()
    with redirect_stdout(out):
        rc = sr.recheck(fake, "dev", wait=clock.wait, clock=clock, budget=budget)
    return rc, out.getvalue(), clock.waited


class Recheck(unittest.TestCase):
    def test_reruns_the_newest_pull_request_run_of_each_sync_pr_only(self):
        f = Fake([pr(1, "sync/templates-abc-1-1", "s1"), pr(2, "feat/x", "s2"), pr(3, "sync/templates-def-2-1", "s3")],
                 {"s1": [run(10, "2026-11-10T09:00:00Z"), run(11, "2026-11-10T09:05:00Z"), run(12, "2026-11-10T09:09:00Z", event="workflow_dispatch")],
                  "s2": [run(20, "2026-11-10T09:00:00Z")],
                  "s3": [run(30, "2026-11-10T09:00:00Z")]})
        rc, out, _ = recheck(f)
        self.assertEqual((rc, f.reran, f.asked_base), (0, [11, 30], "dev"))
        self.assertEqual(f.asked_runs, [("s1", "sync/templates-abc-1-1"), ("s3", "sync/templates-def-2-1")])
        self.assertIn("#1: re-ran Merge gate run 11 on s1", out)

    def test_same_timestamp_picks_the_higher_id(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(40, "2026-11-10T09:00:00Z"), run(41, "2026-11-10T09:00:00Z")]})
        self.assertEqual((recheck(f)[0], f.reran), (0, [41]))

    def test_a_run_in_progress_is_waited_for_then_rerun(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(10, "2026-11-10T09:00:00Z", status="in_progress")]},
                 statuses=["in_progress", "completed"])
        self.assertEqual((recheck(f)[0], f.reran, f.statuses), (0, [10], []))

    def test_a_run_not_started_is_left_alone_without_waiting(self):
        for status in ("queued", "pending", "waiting", "requested"):
            f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(10, "2026-11-10T09:00:00Z", status=status)]})
            rc, out, waited = recheck(f)
            self.assertEqual((rc, f.reran, waited), (0, [], 0), status)
            self.assertIn(f"#1: Merge gate run 10 is {status} — it reads the live base", out)

    def test_a_run_that_never_ends_is_not_rerun_and_fails_the_job(self):
        f = Fake([pr(1, "sync/templates-a", "s1"), pr(2, "sync/templates-b", "s2")],
                 {"s1": [run(10, "2026-11-10T09:00:00Z", status="in_progress")], "s2": [run(20, "2026-11-10T09:00:00Z")]},
                 statuses=["in_progress"] * 3)
        rc, out, waited = recheck(f, budget=30)
        self.assertEqual((rc, f.reran, waited), (1, [20], 3))
        self.assertIn("#1: Merge gate run 10 is still in_progress", out)

    def test_one_deadline_for_the_whole_loop(self):
        f = Fake([pr(1, "sync/templates-a", "s1"), pr(2, "sync/templates-b", "s2")],
                 {"s1": [run(10, "2026-11-10T09:00:00Z", status="in_progress")],
                  "s2": [run(20, "2026-11-10T09:00:00Z", status="in_progress")]},
                 statuses=["in_progress"] * 3)
        rc, out, waited = recheck(f, budget=30)
        self.assertEqual((rc, f.reran, waited), (1, [], 3))
        self.assertIn("#2: Merge gate run 20 is still in_progress", out)

    def test_a_failure_on_one_pr_is_named_and_the_next_pr_is_still_rerun(self):
        f = Fake([pr(1, "sync/templates-a", "s1"), pr(2, "sync/templates-b", "s2")],
                 {"s1": [run(10, "2026-11-10T09:00:00Z")], "s2": [run(20, "2026-11-10T09:00:00Z")]},
                 statuses=["completed"] * 13, fail_rerun={10})
        rc, out, _ = recheck(f)
        self.assertEqual((rc, f.reran), (1, [20]))
        self.assertRegex(out, r"#1: Command .*rerun', '10'.* returned non-zero")

    def test_a_rerun_refused_because_the_run_was_re_run_meanwhile_is_not_a_failure(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(10, "2026-11-10T09:00:00Z")]}, statuses=["queued"], fail_rerun={10})
        rc, out, _ = recheck(f)
        self.assertEqual((rc, f.reran, f.statuses), (0, [], []))
        self.assertIn("#1: Merge gate run 10 is queued — it reads the live base", out)

    def test_a_refused_rerun_waits_out_the_stale_completed_window(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(10, "2026-11-10T09:00:00Z")]},
                 statuses=["completed", "completed", "queued"], fail_rerun={10})
        rc, out, waited = recheck(f)
        self.assertEqual((rc, f.reran, waited), (0, [], 2))
        self.assertIn("is queued", out)

    def test_a_refused_rerun_counts_a_new_attempt_even_while_completed(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [dict(run(10, "2026-11-10T09:00:00Z"), run_attempt=2)]},
                 statuses=["completed"] * 20, attempts=[2, 2, 3], fail_rerun={10})
        self.assertEqual((recheck(f)[::2], f.reran), ((0, 2), [10]))

    def test_a_refused_rerun_that_reveals_a_run_in_progress_waits_for_it_and_reruns(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(10, "2026-11-10T09:00:00Z")]},
                 statuses=["in_progress", "in_progress", "completed"], attempts=[2, 2, 2], fail_rerun={10})
        rc, out, waited = recheck(f)
        self.assertEqual((rc, f.reran, waited), (0, [10], 2))
        self.assertIn("#1: re-ran Merge gate run 10 on s1", out)

    def test_a_second_refusal_on_the_grown_attempt_waits_for_that_attempt_to_move(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(10, "2026-11-10T09:00:00Z")]},
                 statuses=["completed"] * 20, attempts=[2] * 20, fail_rerun=[10, 10])
        self.assertEqual((recheck(f)[0], f.reran), (1, []))

    def test_the_attempt_seen_while_waiting_in_progress_is_the_baseline_of_a_refusal(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(10, "2026-11-10T09:00:00Z", status="in_progress")]},
                 statuses=["in_progress"] + ["completed"] * 20, attempts=[2] * 21, fail_rerun=[10])
        self.assertEqual((recheck(f)[0], f.reran), (1, []))

    def test_a_refused_rerun_waits_no_longer_than_the_shared_deadline(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(10, "2026-11-10T09:00:00Z")]},
                 statuses=["completed"] * 20, fail_rerun={10})
        self.assertEqual(recheck(f, budget=20)[::2], (1, 4))

    def test_a_refused_rerun_still_completed_after_60_s_is_a_failure(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(10, "2026-11-10T09:00:00Z")]},
                 statuses=["completed"] * 20, fail_rerun={10})
        rc, out, waited = recheck(f)
        self.assertEqual((rc, waited), (1, 12))
        self.assertRegex(out, r"#1: Command .*rerun', '10'.* returned non-zero")

    def test_an_api_error_on_one_pr_is_named_and_the_next_pr_is_still_rerun(self):
        class Broken(Fake):
            def gate_runs(self, sha, branch):
                if sha == "s1":
                    raise RuntimeError("gh api …: HTTP 502")
                return super().gate_runs(sha, branch)
        f = Broken([pr(1, "sync/templates-a", "s1"), pr(2, "sync/templates-b", "s2")], {"s2": [run(20, "2026-11-10T09:00:00Z")]})
        rc, out, _ = recheck(f)
        self.assertEqual((rc, f.reran), (1, [20]))
        self.assertIn("#1: gh api …: HTTP 502", out)

    def test_a_sync_pr_without_a_gate_run_fails_the_job(self):
        f = Fake([pr(1, "sync/templates-a", "s1")], {"s1": [run(10, "2026-11-10T09:00:00Z", event="workflow_dispatch")]})
        rc, out, _ = recheck(f)
        self.assertEqual((rc, f.reran), (1, []))
        self.assertIn("#1: no Merge gate run on s1", out)

    def test_a_plugin_copy_pr_on_any_branch_is_re_checked_too(self):
        labelled = dict(pr(4, "ci/copies", "s4"), labels=[{"name": "plugin-copy"}])
        f = Fake([labelled, dict(pr(5, "ci/other", "s5"), labels=[{"name": "area/ci"}])],
                 {"s4": [run(40, "2026-11-10T09:00:00Z")], "s5": [run(50, "2026-11-10T09:00:00Z")]})
        self.assertEqual((recheck(f)[0], f.reran), (0, [40]))

    def test_no_open_sync_pr_does_nothing(self):
        f = Fake([pr(2, "feat/sync/templates-x", "s2")], {"s2": [run(20, "2026-11-10T09:00:00Z")]})
        self.assertEqual((recheck(f)[0], f.reran), (0, []))


class ProdGitHub(unittest.TestCase):
    def test_the_api_calls_and_their_arguments(self):
        calls = []

        def fake_gh_json(*args, **kw):
            calls.append(args)
            if args[0].startswith("repos/o/r/pulls"):
                return [[{"n": 1}], [{"n": 2}]]
            if args[:2] == ("-X", "GET"):
                return {"workflow_runs": ["r"]}
            return {"status": "completed", "run_attempt": 3}

        gh = sr.GitHub("o/r")
        with mock.patch.object(sr, "gh_json", side_effect=fake_gh_json), mock.patch.object(sr.subprocess, "run") as srun:
            self.assertEqual(gh.open_pulls("dev"), [{"n": 1}, {"n": 2}])
            self.assertEqual(gh.gate_runs("abc", "sync/templates-x"), ["r"])
            self.assertEqual(gh.run_state(7), ("completed", 3))
            gh.rerun(7)
        self.assertEqual(calls, [
            ("repos/o/r/pulls?state=open&base=dev&per_page=100", "--paginate"),
            ("-X", "GET", "repos/o/r/actions/workflows/merge-gate.yml/runs",
             "-f", "head_sha=abc", "-f", "branch=sync/templates-x", "-f", "event=pull_request"),
            ("repos/o/r/actions/runs/7",),
        ])
        srun.assert_called_once_with(["gh", "run", "rerun", "7", "--repo", "o/r"], check=True)


def workflow(name):
    for candidate in (os.path.join(HERE, name), os.path.join(HERE, "..", "workflows", name)):
        if os.path.exists(candidate):
            with open(candidate, encoding="utf-8") as f:
                return f.read()
    raise AssertionError(f"{name} not found next to the script or in ../workflows")


class WorkflowContract(unittest.TestCase):
    def test_push_trigger_job_level_guard_and_concurrency_and_the_rights_it_uses(self):
        yml = workflow("sync-recheck.yml")
        self.assertRegex(yml, r"(?m)^on:\n  push:\n\njobs:\n")
        self.assertNotRegex(yml, r"(?m)^concurrency:")
        job = yml.split("\n  recheck:\n", 1)[1]
        self.assertTrue(job.startswith("    if: github.ref == format('refs/heads/{0}', github.event.repository.default_branch)\n"))
        self.assertRegex(job, r"\n    concurrency:\n      group: sync-recheck\n      cancel-in-progress: false\n")
        self.assertRegex(job, r"(?m)^      actions: write\b")
        self.assertIn("python3 .github/scripts/sync_recheck.py", job)

    def test_the_gate_workflow_it_reruns_exists(self):
        self.assertEqual(sr.GATE_WORKFLOW, "merge-gate.yml")
        self.assertIn("name: Merge gate", workflow(sr.GATE_WORKFLOW))


if __name__ == "__main__":
    unittest.main()
