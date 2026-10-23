#!/usr/bin/env python3
"""Merge gate — PR labels as a merge condition (owner's decision 2026-10-20).

A COPY of OmnisGM-App/claude-plugins templates/workflows/merge_gate.py lives in every repo at
.github/scripts/merge_gate.py next to merge-gate.yml; edit the template, roll out as copies.
Tests: .github/scripts/test_merge_gate.py next to it in every repo, wired into that repo's CI
(`python3 .github/scripts/test_merge_gate.py`); the template copy is templates/workflows/test_merge_gate.py.

Environment: REPO, PR, EVENT (the pull_request action), EVENT_LABEL and EVENT_HEAD_SHA (the label and
the head from a labeled/unlabeled payload), plus optional SNAPSHOT_RE, LABEL_* and DEFAULT_BRANCH.
The verdict is a check run named `Merge gate` on the PR head (the ruleset requires that name). The run opens
it as `in_progress` first and closes that same run at the end: `in_progress` stays while something is awaited
(a review round, a label, a lagging label event), `failure` on a contradiction (two matrix labels, a label by
the wrong actor, a label without a recorded head) or on any error of the run itself, `success` when everything
holds. The job ends green except on an error — a waiting PR is not a failed run and sends no mail (owner, 2026-10-23).
The ruleset requires BOTH contexts, `Merge gate` and the job `Merge gate run`: a queued, cancelled or failed
job is not green, so a run that never reached its first write cannot leave a stale verdict standing (review of
Table#1222, round 2). `--fail` is the workflow's last resort on `failure() || cancelled()`: a fresh `failure`
check run on the live head, posted with urllib (gh may be missing when the bootstrap died). It is skipped when
this script closed its own check (step output `closed=true`, written by `mark_closed`), so a real error keeps
its real reason on top instead of the generic "died before the script" one (review of Rules#443).

Head-bound labels are bound to a HEAD SHA, not to a time (review of Table#1179, 3 rounds: committer
dates are the author's clock, event lists lag, queued runs get superseded). The run of the `labeled`
event records the head from its payload in a state comment on the PR; every later run compares that
head with the live one: `gate/matrix-passed` goes on any difference, `gate/snapshots-approved` when the
PR's own `*-snapshots/` files differ between the two heads (a base merge with foreign baselines re-binds
it). A label without a recorded head is reported, never guessed — fail-closed: if the `labeled` run
itself was superseded in the concurrency queue, the label has to be removed and re-applied.
`gate/review-passed` counts only when its latest `labeled` event was made by github-actions[bot] (the
review workflow), not by a hand; the events list can lag behind the label, so it is re-read with a backoff.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

LABEL_SNAP = os.environ.get("LABEL_SNAP", "gate/snapshots-approved")
LABEL_MATRIX_OK = os.environ.get("LABEL_MATRIX_OK", "gate/matrix-passed")
LABEL_MATRIX_NA = os.environ.get("LABEL_MATRIX_NA", "gate/matrix-not-needed")
LABEL_REVIEW = os.environ.get("LABEL_REVIEW", "gate/review-passed")
SNAPSHOT_RE = re.compile(os.environ.get("SNAPSHOT_RE", r"(^|/)[^/]+-snapshots/"))
BOT_LOGINS = {"dependabot[bot]", "app/dependabot"}  # REST gives the first, `gh pr view` the second
WORKFLOW_ACTOR = "github-actions[bot]"  # labels applied with GITHUB_TOKEN carry this actor
CHECK_NAME = os.environ.get("CHECK_NAME", "Merge gate")
WAIT = "⏳ "  # prefix of a "still awaited" message — reported as in_progress, not as a failure
STATE_MARK = "<!-- merge-gate-state "
STATE_END = " -->"


def gh_json(*args: str):
    """`gh api` output as JSON; with --paginate gh concatenates one JSON document per page —
    they are decoded one after another (no `--slurp`: it needs gh ≥ 2.48, a preinstalled gh may be older)."""
    r = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"gh api {' '.join(args)}: {r.stderr.strip()[:300]}")
    dec, out, pos, text = json.JSONDecoder(), [], 0, r.stdout
    while True:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            break
        obj, pos = dec.raw_decode(text, pos)
        out.append(obj)
    return out if "--paginate" in args else out[0]


class GitHub:
    """The reads and the two writes the gate needs; replaced by a fake in tests."""

    def __init__(self, repo: str, pr: str):
        self.repo, self.pr = repo, pr

    def pull(self) -> dict:
        return gh_json(f"repos/{self.repo}/pulls/{self.pr}")

    def files(self) -> list[str]:
        pages = gh_json(f"repos/{self.repo}/pulls/{self.pr}/files", "--paginate")
        return [f["filename"] for page in pages for f in page]

    def events(self) -> list[dict]:
        pages = gh_json(f"repos/{self.repo}/issues/{self.pr}/events", "--paginate")
        return [e for page in pages for e in page]

    def events_again(self) -> list[dict]:
        import time
        time.sleep(4)
        return self.events()

    def compare_files(self, base: str, head: str) -> list[str] | None:
        try:
            pages = gh_json(f"repos/{self.repo}/compare/{base}...{head}", "--paginate")
        except RuntimeError as e:
            if "HTTP 404" in str(e) or "HTTP 422" in str(e):
                return None  # base gone (force-push) — caller treats as "everything changed"
            raise  # 5xx / rate limit / network: the run goes red, the labels stay
        # compare is three-dot (merge-base...head): when the head went BACK (force-push to an ancestor
        # or a sibling) the list is empty or partial although the tree differs — only a plain fast-forward
        # (`ahead`) or the same commit (`identical`) describes the real difference.
        if pages[0].get("status") not in ("ahead", "identical"):
            return None
        files = [f["filename"] for page in pages for f in page.get("files", [])]
        return None if len(files) >= 300 else files  # compare lists at most 300 files — unknown beyond

    def state(self) -> tuple[int | None, dict]:
        """The gate's state comment on the PR: {label: head sha}."""
        pages = gh_json(f"repos/{self.repo}/issues/{self.pr}/comments", "--paginate")
        for page in pages:
            for c in page:
                body = c.get("body") or ""
                # only the gate's own comment (GITHUB_TOKEN actor): a hand-written marker must not bind a label
                if body.startswith(STATE_MARK) and (c.get("user") or {}).get("login") == WORKFLOW_ACTOR:
                    return c["id"], parse_state(body)
        return None, {}

    def write_state(self, comment_id: int | None, state: dict) -> None:
        body = render_state(state)
        if comment_id is None:
            gh_json(f"repos/{self.repo}/issues/{self.pr}/comments", "-X", "POST", "-f", f"body={body}")
        else:
            gh_json(f"repos/{self.repo}/issues/comments/{comment_id}", "-X", "PATCH", "-f", f"body={body}")

    def remove_label(self, name: str) -> None:
        subprocess.run(["gh", "pr", "edit", self.pr, "--repo", self.repo, "--remove-label", name], check=True)

    def open_check(self, head: str) -> int:
        """A fresh `in_progress` check run on the head — the first write of the run, so the ruleset never sees
        a stale verdict while this run is working or after it dies (review of Table#1222)."""
        r = gh_json(f"repos/{self.repo}/check-runs", "-X", "POST", "-f", f"name={CHECK_NAME}", "-f", f"head_sha={head}",
                    "-f", "status=in_progress", "-f", "output[title]=evaluating", "-f", "output[summary]=the gate run is working")
        return int(r["id"])

    def suite_branch(self, check_id: int) -> str | None:
        """The branch of the check suite the run landed in. The API puts a check run into the app's existing
        suite for that SHA, and the PR merge box reads only suites of its own head branch: a release branch cut
        on the very commit of `dev` writes its verdict into `dev`'s suite and the PR shows "Expected — waiting"
        forever (Table#1227)."""
        suite = gh_json(f"repos/{self.repo}/check-runs/{check_id}").get("check_suite") or {}
        if not suite.get("id"):
            return None
        return gh_json(f"repos/{self.repo}/check-suites/{suite['id']}").get("head_branch")

    def close_check(self, check_id: int, status: str, conclusion: str | None, title: str, summary: str) -> None:
        args = [f"repos/{self.repo}/check-runs/{check_id}", "-X", "PATCH", "-f", f"status={status}",
                "-f", f"output[title]={title[:200]}", "-f", f"output[summary]={summary[:60000]}"]
        if conclusion:
            args += ["-f", f"conclusion={conclusion}"]
        gh_json(*args)


def parse_state(body: str) -> dict:
    try:
        return json.loads(body[len(STATE_MARK):body.index(STATE_END)])
    except (ValueError, KeyError):
        return {}


def render_state(state: dict) -> str:
    return (STATE_MARK + json.dumps(state, sort_keys=True) + STATE_END +
            "\nMerge gate state: the head each `gate/*` label was applied on (written by the workflow; do not edit).")


def last_labeled_actor(events: list[dict], name: str) -> str | None:
    acts = [(e["created_at"], (e.get("actor") or {}).get("login", "")) for e in events
            if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == name]
    return max(acts)[1] if acts else None


def evaluate(gh: GitHub, pull: dict, files: list[str], events: list[dict], state: dict,
             default_branch: str = "dev", event: str = "", event_label: str = "",
             event_head: str = "") -> tuple[list[str], list[str], dict]:
    """Returns (labels to remove, failure messages, new state)."""
    labels = {l["name"] for l in pull.get("labels", [])}
    head_ref, head = pull["head"]["ref"], pull["head"]["sha"]
    base_ref, author = pull["base"]["ref"], pull["user"]["login"]
    pr_snaps = {f for f in files if SNAPSHOT_RE.search(f)}
    state = dict(state)
    remove: list[str] = []
    fail: list[str] = []

    for name in (LABEL_MATRIX_OK, LABEL_SNAP):
        if name not in labels:
            state.pop(name, None)
            continue
        if event == "labeled" and event_label == name:
            state[name] = event_head or head  # the head the person saw when applying it
        bound = state.get(name)
        if bound is None:
            fail.append(f"`{name}` is set but no head is recorded for it (its `labeled` run was skipped or superseded) — "
                        "remove and re-apply the label.")
        elif bound != head:
            if name == LABEL_MATRIX_OK:
                remove.append(name)
            else:
                changed = gh.compare_files(bound, head)
                if changed is None or pr_snaps.intersection(changed) or not pr_snaps:
                    remove.append(name)
                else:
                    state[name] = head  # only foreign files (a base merge) between the two heads — still approved
    for name in remove:
        state.pop(name, None)
    labels -= set(remove)

    review_ok = False
    if LABEL_REVIEW in labels:
        actor = last_labeled_actor(events, LABEL_REVIEW)
        for _ in range(5):  # the events list lags behind a just-applied label (and may still show a human's older one)
            if actor == WORKFLOW_ACTOR or not hasattr(gh, "events_again"):
                break
            events = gh.events_again()
            actor = last_labeled_actor(events, LABEL_REVIEW)
        if actor == WORKFLOW_ACTOR:
            review_ok = True
        elif actor is None:
            fail.append(f"{WAIT}`{LABEL_REVIEW}` is set but its `labeled` event is not on record yet — re-run the gate.")
        else:
            fail.append(f"`{LABEL_REVIEW}` was applied by `{actor}`, not by the review workflow — it does not count; "
                        "remove it and let a review round set it.")

    release = base_ref == "master" and (head_ref == default_branch or head_ref.startswith("release/"))
    bot = author in BOT_LOGINS
    nsnap = len(pr_snaps)
    if nsnap and not release and LABEL_SNAP not in labels:
        fail.append(f"{WAIT}{nsnap} screenshot baseline(s) changed in this PR — waiting for `{LABEL_SNAP}`. "
                    "Only a human (the owner) sets it after looking at the new images; an agent never does.")
    n_matrix = (LABEL_MATRIX_OK in labels) + (LABEL_MATRIX_NA in labels)
    if n_matrix != 1:
        fail.append(f"{WAIT if n_matrix == 0 else ''}exactly one of `{LABEL_MATRIX_OK}` (full Playwright matrix green on "
                    f"head {head[:7]}) or `{LABEL_MATRIX_NA}` (diff does not touch UI — say so in the PR body) is required; "
                    f"found {n_matrix}.")
    if not bot and not release and not review_ok and not any(LABEL_REVIEW in f for f in fail):
        fail.append(f"{WAIT}waiting for `{LABEL_REVIEW}` — claude-review.yml sets it when a round ends with zero ❗; "
                    "it runs after CI on every push while the label is absent (removing the label starts a round too).")
    return remove, fail, state


def split_outcome(fail: list[str]) -> tuple[list[str], list[str]]:
    """(still awaited, contradictions): the first group keeps the check run in_progress, the second fails it."""
    waiting = [f[len(WAIT):] for f in fail if f.startswith(WAIT)]
    errors = [f for f in fail if not f.startswith(WAIT)]
    return waiting, errors


def report_dead_run(repo: str, pr: str, token: str, reason: str, post=None) -> dict:
    """`--fail`: a new `completed/failure` check run on the PR's live head. `post(path, payload)` is the REST
    call (urllib by default) — replaced in tests."""
    import urllib.request

    def rest(path: str, payload: dict | None = None) -> dict:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/{path}", method="POST" if payload else "GET",
                                     data=json.dumps(payload).encode() if payload else None,
                                     headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    post = post or rest
    head = post(f"pulls/{pr}")["head"]["sha"]
    payload = {"name": CHECK_NAME, "head_sha": head, "status": "completed", "conclusion": "failure",
               "output": {"title": "gate run failed", "summary": reason[:60000]}}
    post("check-runs", payload)
    return payload


def mark_closed() -> None:
    """Tell the workflow the check run is closed (verdict or error), so the `--fail` step stays out."""
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as out:
        out.write("closed=true\n")


def main() -> int:
    repo, pr = os.environ["REPO"], os.environ["PR"]
    if "--fail" in sys.argv[1:]:
        p = report_dead_run(repo, pr, os.environ["GH_TOKEN"],
                            "the gate run died before the script reported a verdict (cancelled, timed out or failed on "
                            "bootstrap) — see the workflow log; re-run the gate")
        print(f"::notice::{CHECK_NAME} closed as failure on {p['head_sha'][:8]}")
        return 0
    gh = GitHub(repo, pr)
    pull = gh.pull()
    check_id = gh.open_check(pull["head"]["sha"])
    try:
        branch = gh.suite_branch(check_id)
        if branch and branch != pull["head"]["ref"]:
            why = (f"the head {pull['head']['sha'][:8]} is also the head of `{branch}`, so the verdict lands in that "
                   f"branch's check suite and this PR never sees it — give the branch its own commit "
                   f"(an empty one on top is enough) and push again")
            gh.close_check(check_id, "completed", "failure", "blocked: head shared with another branch", why)
            mark_closed()
            print(f"::error::{why}")
            return 1
        return run(gh, pull, check_id)
    except BaseException as e:  # noqa: BLE001 — the verdict must never stay stale: close the run as failed, then re-raise
        try:
            gh.close_check(check_id, "completed", "failure", "gate run failed", f"the gate run died before a verdict: {e}"[:60000])
            mark_closed()
        except Exception as e2:  # noqa: BLE001
            print(f"::warning::could not close the check run after the error: {e2}")
        raise


def run(gh: GitHub, pull: dict, check_id: int) -> int:
    env = os.environ.get
    comment_id, state = gh.state()
    remove, fail, new_state = evaluate(gh, pull, gh.files(), gh.events(), state, env("DEFAULT_BRANCH") or "dev",
                                       event=env("EVENT", ""), event_label=env("EVENT_LABEL", ""),
                                       event_head=env("EVENT_HEAD_SHA", ""))
    for name in remove:
        gh.remove_label(name)
        print(f"::notice::removed {name} — it was applied on another head")
    if new_state != state or (comment_id is None and new_state):
        gh.write_state(comment_id, new_state)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    out = open(summary, "a") if summary else sys.stdout
    waiting, errors = split_outcome(fail)
    if errors:
        for f in errors:
            print(f"::error::{f}")
        for f in waiting:
            print(f"::notice::{f}")
        text = "\n".join(f"- {f}" for f in errors + waiting)
        gh.close_check(check_id, "completed", "failure", "blocked: " + errors[0], text)
        print("## Merge gate: blocked\n" + text, file=out)
    elif waiting:
        for f in waiting:
            print(f"::notice::{f}")
        text = "\n".join(f"- {f}" for f in waiting)
        gh.close_check(check_id, "in_progress", None, "waiting: " + waiting[0], text)
        print("## Merge gate: waiting\n" + text, file=out)
    else:
        gh.close_check(check_id, "completed", "success", "labels ok", "every required label holds on this head")
        print("## Merge gate: ok", file=out)
        print("labels ok")
    mark_closed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
