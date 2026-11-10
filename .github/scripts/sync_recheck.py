"""Re-run the merge gate of open template-sync PRs after the default branch moves (claude-plugins#42).

The gate compares a `sync/templates-*` PR's copies at its head and in GitHub's test merge as of its run; the
rulesets do not require an up-to-date branch, so a later push to the base would otherwise merge on a stale verdict.
Env: REPO, BASE (the default branch). A copy of templates/workflows/sync_recheck.py in claude-plugins.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

from merge_gate import SYNC_PREFIX, gh_json

GATE_WORKFLOW = "merge-gate.yml"
# A run that has not started reads the PR and its test merge live when it starts (merge_gate.merge_commit).
NOT_STARTED = {"queued", "pending", "waiting", "requested"}


def sync_pulls(pulls: list[dict]) -> list[dict]:
    return [p for p in pulls if p["head"]["ref"].startswith(SYNC_PREFIX)]


def latest_run(runs: list[dict]) -> dict | None:
    """The newest `pull_request` run of the gate on one head; a re-run keeps its id and bumps run_attempt."""
    runs = [r for r in runs if r.get("event") == "pull_request"]
    return max(runs, key=lambda r: (r["created_at"], r["id"])) if runs else None


class GitHub:
    def __init__(self, repo: str):
        self.repo = repo

    def open_pulls(self, base: str) -> list[dict]:
        pages = gh_json(f"repos/{self.repo}/pulls?state=open&base={base}&per_page=100", "--paginate")
        return [p for page in pages for p in page]

    def gate_runs(self, sha: str, branch: str) -> list[dict]:
        return gh_json("-X", "GET", f"repos/{self.repo}/actions/workflows/{GATE_WORKFLOW}/runs",
                       "-f", f"head_sha={sha}", "-f", f"branch={branch}", "-f", "event=pull_request")["workflow_runs"]

    def run_state(self, run_id: int) -> tuple[str, int]:
        r = gh_json(f"repos/{self.repo}/actions/runs/{run_id}")
        return r["status"], r.get("run_attempt", 1)

    def rerun(self, run_id: int) -> None:
        subprocess.run(["gh", "run", "rerun", str(run_id), "--repo", self.repo], check=True)


def recheck_one(gh, p: dict, wait, clock, deadline: float) -> int:
    num, sha = p["number"], p["head"]["sha"]
    run = latest_run(gh.gate_runs(sha, p["head"]["ref"]))
    if run is None:
        print(f"#{num}: no Merge gate run on {sha[:8]} — nothing to re-run; the PR waits for its gate")
        return 1
    status, attempt = run["status"], run.get("run_attempt", 1)
    while True:
        if status in NOT_STARTED:
            print(f"#{num}: Merge gate run {run['id']} is {status} — it reads the live base when it starts")
            return 0
        if status == "in_progress" and clock() < deadline:
            wait(10)
            status, attempt = gh.run_state(run["id"])
            continue
        if status != "completed":
            print(f"#{num}: Merge gate run {run['id']} is still {status} — re-run it by hand once it ends")
            return 1
        try:
            gh.rerun(run["id"])
        except subprocess.CalledProcessError:
            # right after another job's rerun the run still reads `completed` for a while (claude-review.yml): wait for
            # its status or attempt to move, every 5 s for up to 60 s within the shared deadline, then decide again
            until = min(deadline, clock() + 60)
            while True:
                now_status, now_attempt = gh.run_state(run["id"])
                if now_status != "completed" or now_attempt > attempt:
                    break
                if clock() >= until:
                    raise
                wait(5)
            status, attempt = now_status, now_attempt
            continue
        print(f"#{num}: re-ran Merge gate run {run['id']} on {sha[:8]}")
        return 0


def recheck(gh, base: str, wait=time.sleep, clock=time.monotonic, budget: float = 300) -> int:
    """Re-runs the latest gate run of each open sync PR into `base`; a run in progress may have read the base before
    the push, so it is waited for (one deadline for the whole loop). 1 when any PR could not be re-checked."""
    deadline, rc = clock() + budget, 0
    for p in sync_pulls(gh.open_pulls(base)):
        try:
            rc |= recheck_one(gh, p, wait, clock, deadline)
        except (RuntimeError, subprocess.CalledProcessError) as e:
            print(f"#{p['number']}: {e}")
            rc = 1
    return rc


def main() -> int:
    return recheck(GitHub(os.environ["REPO"]), os.environ["BASE"])


if __name__ == "__main__":
    sys.exit(main())
