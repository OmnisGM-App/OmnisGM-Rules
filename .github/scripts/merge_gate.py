#!/usr/bin/env python3
"""Merge gate — PR labels as a merge condition (owner's decision 2026-10-20).

A COPY of OmnisGM-App/claude-plugins templates/workflows/merge_gate.py lives in every repo at
.github/scripts/merge_gate.py next to merge-gate.yml; edit the template, roll out as copies.
Tests: .github/scripts/test_merge_gate.py next to it in every repo, wired into that repo's CI
(`python3 .github/scripts/test_merge_gate.py`); the template copy is templates/workflows/test_merge_gate.py.

Environment: REPO, PR, EVENT (the pull_request action), EVENT_LABEL and EVENT_HEAD_SHA (the label and
the head from a labeled/unlabeled payload), plus optional SNAPSHOT_RE and LABEL_*.
The verdict is the status of the job itself (`Merge gate`, the context the ruleset requires): green when every
label holds on the head, red otherwise — a message that starts with "waiting:" names what is still awaited (a review
round, a label, a lagging label event), the others are contradictions to fix by hand (two matrix labels, a label by
the wrong actor, a label without a recorded head) or an error of the run. A label event re-runs the job (a hand's
label through `labeled`/`unlabeled`; the review workflow's label — set with GITHUB_TOKEN, which fires no event —
through `gh run rerun` of every `pull_request` gate run on the head, claude-review.yml v2.51); a lagging events list is
the one case that needs "Re-run jobs" on the gate run by hand. A waiting PR is a red run that mails a failure on
every push: the owner's decision of 2026-10-24 (after Table#1241), replacing the 2026-10-23 "a waiting PR sends no
mail" that the API check run bought. No check run is written through the API (v3, 2026-10-24): GitHub puts an API check run into the OLDEST check suite of the app on that SHA, and when the same
workflow re-runs on a label the newer run supersedes that suite in the merge box together with the verdict in it
(Table#1241: "Merge gate — Expected, waiting" with a green record in the API); a shared head (Table#1227) hid it the
same way. The job's own status lives in its own run and is never hidden.

Head-bound labels are bound to a HEAD SHA, not to a time (review of Table#1179, 3 rounds: committer
dates are the author's clock, event lists lag, queued runs get superseded). The run of the `labeled`
event records the head from its payload in a state comment on the PR; every later run compares that
head with the live one: `gate/matrix-passed` goes on any difference, `gate/snapshots-approved` when the
PR's own `*-snapshots/` files differ between the two heads (a base merge with foreign baselines re-binds
it). A label without a recorded head is reported, never guessed — fail-closed: if the `labeled` run
itself was superseded in the concurrency queue, the label has to be removed and re-applied.
`gate/review-passed` counts only when its latest `labeled` event was made by github-actions[bot] (the
review workflow), not by a hand; the events list can lag behind the label, so it is re-read with a backoff.

Template sync (owner's decision 2026-11-08, instead of an admin bypass): a PR from a `sync/templates-*` branch
needs neither `gate/review-passed` nor a matrix label when it targets the default branch and the gate itself confirms
that every changed file is `.claude/rules/<name>.md` and its blob at the head and at GitHub's test merge commit
(sync-recheck.yml re-runs the gate after the base moves) is the blob of `templates/<name>.md` on the live master of
TEMPLATES_REPO (claude-plugins, read with TEMPLATES_TOKEN — the org secret TEMPLATES_READ_TOKEN), and every file's
status is `modified` (an added copy is a new rule for the repo, a rename hides a removal: ordinary PRs). The branch
name only asks for the check; the blobs decide it. A sync branch that fails it (a foreign file, a blob that
differs, a token that cannot read TEMPLATES_REPO, another base) is blocked with the reason and the way out, and no
review round or matrix is awaited for it: claude-review.yml skips the branch by name, and labels do not lift the block.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import re
import subprocess
import sys

LABEL_SNAP = os.environ.get("LABEL_SNAP", "gate/snapshots-approved")
LABEL_MATRIX_OK = os.environ.get("LABEL_MATRIX_OK", "gate/matrix-passed")
LABEL_MATRIX_NA = os.environ.get("LABEL_MATRIX_NA", "gate/matrix-not-needed")
LABEL_REVIEW = os.environ.get("LABEL_REVIEW", "gate/review-passed")
SNAPSHOT_RE = re.compile(os.environ.get("SNAPSHOT_RE", r"(^|/)[^/]+-snapshots/"))
SYNC_PREFIX = "sync/templates-"
# a plain rule file name only: `?`, `&`, `#`, `%` or a newline would reshape the contents-API URL (review of #37)
SYNC_PATH = re.compile(r"\.claude/rules/[A-Za-z0-9][A-Za-z0-9._-]*\.md")
TEMPLATES_REPO = os.environ.get("TEMPLATES_REPO", "OmnisGM-App/claude-plugins")
TEMPLATES_REF = os.environ.get("TEMPLATES_REF", "master")
BOT_LOGINS = {"dependabot[bot]", "app/dependabot"}  # REST gives the first, `gh pr view` the second
WORKFLOW_ACTOR = "github-actions[bot]"  # labels applied with GITHUB_TOKEN carry this actor
WAIT = "⏳ "  # prefix of a "still awaited" message — reported as "waiting:", not as a contradiction
STATE_MARK = "<!-- merge-gate-state "
STATE_END = " -->"


def gh_json(*args: str, token: str | None = None):
    """`gh api` output as JSON; with --paginate gh concatenates one JSON document per page —
    they are decoded one after another (no `--slurp`: it needs gh ≥ 2.48, a preinstalled gh may be older)."""
    env = dict(os.environ, GH_TOKEN=token) if token else None
    r = subprocess.run(["gh", "api", *args], capture_output=True, text=True, env=env)
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
    """The reads and the two writes (label removal, state comment) the gate needs; replaced by a fake in tests."""

    def __init__(self, repo: str, pr: str):
        self.repo, self.pr = repo, pr

    def pull(self) -> dict:
        return gh_json(f"repos/{self.repo}/pulls/{self.pr}")

    def files(self) -> list[str]:
        pages = gh_json(f"repos/{self.repo}/pulls/{self.pr}/files", "--paginate")
        return [f["filename"] for page in pages for f in page]

    def file_status(self) -> dict[str, str]:
        """{filename: status} of the PR's files (added / modified / removed / renamed …) — the sync exemption needs it."""
        pages = gh_json(f"repos/{self.repo}/pulls/{self.pr}/files", "--paginate")
        return {f["filename"]: f.get("status", "") for page in pages for f in page}

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

    def blob_sha(self, repo: str, path: str, ref: str, token: str | None = None) -> str | None:
        """The git blob sha of `path` at `ref`; None when the file is not there (removed by the PR, no template)."""
        try:
            q = urllib.parse.quote
            return gh_json(f"repos/{repo}/contents/{q(path, safe='/')}?ref={q(ref, safe='')}", token=token)["sha"]
        except RuntimeError as e:
            if "HTTP 404" in str(e):
                return None
            raise  # 5xx / rate limit / a bad token: the run goes red, nothing is exempted

    def templates_unreadable(self) -> str | None:
        """Why the copies cannot be compared (no token, or the token does not see TEMPLATES_REPO); None when they can."""
        token = os.environ.get("TEMPLATES_TOKEN")
        if not token:
            return f"TEMPLATES_TOKEN is empty — the copies cannot be compared with {TEMPLATES_REPO}@{TEMPLATES_REF} (org secret TEMPLATES_READ_TOKEN)."
        try:
            gh_json(f"repos/{TEMPLATES_REPO}", token=token)
        except RuntimeError as e:
            # a private repo answers 404 to a token that cannot see it, so 404 is an access problem here, not a missing file
            if "rate limit" not in str(e).lower() and any(code in str(e) for code in ("HTTP 401", "HTTP 403", "HTTP 404")):
                return (f"TEMPLATES_TOKEN cannot read {TEMPLATES_REPO} ({str(e).split(': ', 1)[-1].strip()[:80]}) — fix the org secret "
                        "TEMPLATES_READ_TOKEN (its repository access), not the templates.")
            raise
        return None

    def template_mismatches(self, files: list[str], head: str, merge: str) -> tuple[list[str], list[str]]:
        """Changed files whose blob is not the template's on TEMPLATES_REF: (at the head, at the test merge commit only)."""
        token = os.environ.get("TEMPLATES_TOKEN")
        at_head, at_merge = [], []
        for f in files:
            want = self.blob_sha(TEMPLATES_REPO, "templates/" + f.rsplit("/", 1)[-1], TEMPLATES_REF, token)
            if want is None or self.blob_sha(self.repo, f, head) != want:
                at_head.append(f)
            elif self.blob_sha(self.repo, f, merge) != want:
                at_merge.append(f)
        return at_head, at_merge

    def merge_parent(self, sha: str) -> str | None:
        parents = gh_json(f"repos/{self.repo}/commits/{sha}").get("parents") or []
        return parents[0]["sha"] if parents else None

    def base_tip(self, ref: str) -> str:
        return gh_json(f"repos/{self.repo}/branches/{urllib.parse.quote(ref, safe='')}")["commit"]["sha"]

    def merge_commit(self, pull: dict) -> str | None:
        """GitHub's test merge commit of the PR when it is built on the live tip of the base, None on a conflict or when
        it does not settle. `mergeable: null` means GitHub is recomputing it (REST "Get a pull request"), and right after
        a push to the base an older merge_commit_sha can still read as mergeable, so the PR is re-read with a backoff."""
        import time
        base = (pull.get("base") or {}).get("ref", "")
        for delay in (5, 10, 20, None):
            if pull.get("mergeable") is False:
                return None
            sha = pull.get("merge_commit_sha")
            if pull.get("mergeable") is True and sha and self.merge_parent(sha) == self.base_tip(base):
                return sha
            if delay is None:
                return None
            time.sleep(delay)
            pull = self.pull()

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
             event: str = "", event_label: str = "",
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
            fail.append(f"{WAIT}`{LABEL_REVIEW}` is set but its `labeled` event is not on record yet — press \"Re-run jobs\" on this gate run (Checks tab).")
        else:
            fail.append(f"`{LABEL_REVIEW}` was applied by `{actor}`, not by the review workflow — it does not count; "
                        "remove it and let a review round set it.")

    release = base_ref == "master" and head_ref.startswith("release/")  # dev -> master is not a release since 2026-10-23
    bot = author in BOT_LOGINS
    sync_branch = head_ref.startswith(SYNC_PREFIX)
    if sync_branch:
        default = (pull["base"].get("repo") or {}).get("default_branch")
        way_out = (" This branch is never merged as an ordinary PR: a change beyond the template copies goes in a PR from "
                   "a branch outside `sync/templates-*`; the next sync run opens a new PR and closes this one.")
        foreign = [f for f in files if not SYNC_PATH.fullmatch(f)]
        if base_ref != default:
            fail.append(f"`{head_ref}` targets `{base_ref}`, not the default branch `{default}` — the template-sync "
                        "exemption holds only there." + way_out)
        elif not files or foreign:
            fail.append(f"`{head_ref}` is a template-sync branch but changes {', '.join(map(repr, foreign[:5])) or 'nothing'} — "
                        "only `.claude/rules/*.md` copies of claude-plugins templates are exempt." + way_out)
        elif (not_mod := sorted(f"{f} ({st or '?'})" for f, st in gh.file_status().items() if st != "modified")):
            # an added copy is a new rule for the repo (a decision, an ordinary PR); a rename hides the removal of its source
            fail.append(f"template-sync branch: {', '.join(not_mod[:5])} — only modified copies are exempt." + way_out)
        elif (why := gh.templates_unreadable()):
            fail.append(f"template-sync branch: {why}")
        elif not (merge := gh.merge_commit(pull)):
            fail.append("template-sync branch: GitHub has no test merge of this PR with the live base (not computed "
                        "yet, not rebuilt after a push to the base, or a conflict) — press \"Re-run jobs\" on this gate run; on a conflict run sync-templates.yml "
                        "(workflow_dispatch, dry_run: false), it clones the current base and replaces this PR." + way_out)
        else:
            at_head, at_merge = gh.template_mismatches(files, head, merge)
            if at_head:
                fail.append(f"template-sync branch: {', '.join(at_head[:5])} differ from {TEMPLATES_REPO} "
                            f"templates@{TEMPLATES_REF} at the head — edit the template, not the copy." + way_out)
            if at_merge:
                fail.append(f"template-sync branch: {', '.join(at_merge[:5])} match the template at the head but not in the "
                            "merge with the base (the base changed the copy) — run sync-templates.yml (workflow_dispatch, "
                            "dry_run: false): it clones the current base and replaces this PR." + way_out)
    nsnap = len(pr_snaps)
    if nsnap and not release and LABEL_SNAP not in labels:
        fail.append(f"{WAIT}{nsnap} screenshot baseline(s) changed in this PR — waiting for `{LABEL_SNAP}`. "
                    "Only a human (the owner) sets it after looking at the new images; an agent never does.")
    n_matrix = (LABEL_MATRIX_OK in labels) + (LABEL_MATRIX_NA in labels)
    if n_matrix != 1 and not (sync_branch and n_matrix == 0):  # rule files only: no UI, no matrix; a failed sync is blocked above
        fail.append(f"{WAIT if n_matrix == 0 else ''}exactly one of `{LABEL_MATRIX_OK}` (full Playwright matrix green on "
                    f"head {head[:7]}) or `{LABEL_MATRIX_NA}` (diff does not touch UI — say so in the PR body) is required; "
                    f"found {n_matrix}.")
    if not bot and not release and not sync_branch and not review_ok and not any(LABEL_REVIEW in f for f in fail):
        fail.append(f"{WAIT}waiting for `{LABEL_REVIEW}` — claude-review.yml sets it when a round ends with zero ❗; "
                    "it runs after CI on every push while the label is absent (removing the label starts a round too); "
                    "a PR whose base is not the default branch gets a round only by workflow_dispatch.")
    return remove, fail, state


def split_outcome(fail: list[str]) -> tuple[list[str], list[str]]:
    """(still awaited, contradictions): both make the job red; the first group is reported as "waiting"."""
    waiting = [f[len(WAIT):] for f in fail if f.startswith(WAIT)]
    errors = [f for f in fail if not f.startswith(WAIT)]
    return waiting, errors


def main() -> int:
    gh = GitHub(os.environ["REPO"], os.environ["PR"])
    return run(gh, gh.pull())


def run(gh: GitHub, pull: dict) -> int:
    """0 when every label holds on the live head, 1 otherwise; an API error propagates (the job is red with it)."""
    env = os.environ.get
    comment_id, state = gh.state()
    remove, fail, new_state = evaluate(gh, pull, gh.files(), gh.events(), state,
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
    for f in errors:
        print(f"::error::{f}")
    for f in waiting:
        print(f"::error::waiting: {f}")
    if errors:
        print("## Merge gate: blocked\n" + "\n".join(f"- {f}" for f in errors + waiting), file=out)
        return 1
    if waiting:
        print("## Merge gate: waiting\n" + "\n".join(f"- {f}" for f in waiting), file=out)
        return 1
    print("## Merge gate: ok", file=out)
    print("labels ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
