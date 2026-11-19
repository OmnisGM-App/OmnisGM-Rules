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
dates are the author's clock, event lists lag, queued runs get superseded; no committer date is compared anywhere). The run of the `labeled`
event records the head from its payload in a state comment on the PR; every later run compares that
head with the live one: `gate/matrix-passed` goes on any difference, `gate/snapshots-approved` only when the
PR's OWN commits since the bound head touched a `*-snapshots/` path (`GitHub.own_paths`: a base merge's baselines do not
count, a conflict resolution in a baseline does; a push that leaves the baselines alone keeps the approval and re-binds
it; history that cannot be compared removes it as before; an API error keeps it and the run waits). Each entry is `{"sha": head, "tree": the head's tree}` (an old entry that is a bare sha string reads as
`{"sha": s, "tree": None}`): when the head moved but its TREE equals the recorded one (a retarget or a rebase that only
drops commits already in the base, the stacked-PR case), both labels are kept and the sha is re-bound — the code
the matrix ran on, and the baselines the owner looked at, are byte-for-byte the same; an unknown tree (an old entry,
a failed read) never counts as equal, so the old rules apply. The base of the PR does not matter to any of this: a PR
into another PR's branch (a stack) is held to the same labels as a PR into the default branch. A `gate/matrix-passed` without a recorded head is reported, never guessed — fail-closed: if its `labeled` run
itself was superseded in the concurrency queue, the label has to be removed and re-applied. A `gate/snapshots-approved`
without a record (#91, Table#1759) is bound like a hand-set `gate/matrix-not-needed` (`timeline_bound`): to the last
`committed` event of the timeline that GitHub had seen strictly before its last `labeled` event — the server's times on both sides:
the earliest check suite of the commit on the PR's branch (made by the push) against the event's `created_at`; then checked as above.
No commit seen that early, or a force-push at or after the label, removes the approval (a notice with the reason); an unreadable or
lagging timeline, unreadable check suites or a live head with no suite yet keep it and turn the run red (waiting).
`gate/snapshots-review-needed` (#91; LABEL_SNAP_REVIEW) is the gate's own marker: on while the PR changes `*-snapshots/` files,
is not a release and has no `gate/snapshots-approved` (also right after the gate removed it), off otherwise. It is only a navigation aid for the
owner (to find PRs whose screenshots await a look) and strictly informational: never a failure, a WAIT or a block (the "waiting for
`gate/snapshots-approved`" line is the gate's); a failure to add or remove it is a notice only.
`gate/review-passed` counts only when its latest `labeled` event was made by github-actions[bot] (the
review workflow), not by a hand; the events list can lag behind the label, so it is re-read with a backoff.

Review pause (owner's switch, the Actions variable REVIEW_PAUSED = `true`, skill omnisgm-review-pause): no round runs and the
gate stops waiting for `gate/review-passed`. `gate/review-skipped` is only the trace of that on the PR: the gate keeps it on
while the pause holds for a PR without `gate/review-passed` and takes it off otherwise, and the verdict never reads it, so a
hand-set one opens nothing. A `gate/review-passed` set by a hand is still a contradiction during a pause.

Template copies (owner's decisions 2026-11-08 for rule files, 2026-11-10 for workflow copies, claude-plugins#45): a PR
from a `sync/templates-*` branch or labelled `plugin-copy` (sync-templates.yml sets both) needs neither
`gate/review-passed` nor a matrix label when it targets the default branch and the gate itself confirms that every
changed file is a copy named by `template_of` (`.claude/rules/<name>.md` or a WORKFLOW_COPIES path), its status is
`modified`, or `added` for a WORKFLOW_COPIES path (sync-templates adds a workflow copy the repo does not carry yet, with
the settings lines of the repo's own merge-gate.yml, `new_copy`; a new rule file stays a decision for the repo and a
rename hides a removal: ordinary PRs), and its text at the
head and at GitHub's test merge commit (sync-recheck.yml re-runs the gate after the base moves) equals its template on
the live master of TEMPLATES_REPO (claude-plugins, read with TEMPLATES_TOKEN — the org secret TEMPLATES_READ_TOKEN)
outside the repo's settings lines (SETTING_LINE in a workflow copy), while those lines in the test merge are what
`with_settings` makes of the template and the base's copy. The branch name and the label only ask for the check; the texts decide it. A PR that fails it is blocked
with the reason and the way out, and no review round or matrix is awaited for it: claude-review.yml skips both.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.parse
import re
import subprocess
import sys

LABEL_SNAP = os.environ.get("LABEL_SNAP", "gate/snapshots-approved")
LABEL_SNAP_REVIEW = os.environ.get("LABEL_SNAP_REVIEW", "gate/snapshots-review-needed")
LABEL_MATRIX_OK = os.environ.get("LABEL_MATRIX_OK", "gate/matrix-passed")
LABEL_MATRIX_NA = os.environ.get("LABEL_MATRIX_NA", "gate/matrix-not-needed")
LABEL_REVIEW = os.environ.get("LABEL_REVIEW", "gate/review-passed")
LABEL_REVIEW_SKIPPED = os.environ.get("LABEL_REVIEW_SKIPPED", "gate/review-skipped")
SNAPSHOT_RE = re.compile(os.environ.get("SNAPSHOT_RE", r"(^|/)[^/]+-snapshots/"))
SYNC_PREFIX = "sync/templates-"
LABEL_COPY = os.environ.get("LABEL_COPY", "plugin-copy")
# a workflow copy in a product repo -> its template in TEMPLATES_REPO; sync_templates.sh rolls out the same map
WORKFLOW_COPIES = {
    ".github/workflows/merge-gate.yml": "templates/workflows/merge-gate.yml",
    ".github/workflows/sync-recheck.yml": "templates/workflows/sync-recheck.yml",
    ".github/workflows/claude-review.yml": ".github/workflows/claude-review.yml",
    ".github/scripts/merge_gate.py": "templates/workflows/merge_gate.py",
    ".github/scripts/test_merge_gate.py": "templates/workflows/test_merge_gate.py",
    ".github/scripts/sync_recheck.py": "templates/workflows/sync_recheck.py",
    ".github/scripts/test_sync_recheck.py": "templates/workflows/test_sync_recheck.py",
    # the PR checks report (claude-plugins#57, #71): its own workflow, run by merge_gate.py --pr-checks-report, over the two machine-gate
    # scripts (their tests stay in claude-plugins)
    ".github/workflows/pr-checks-report.yml": "templates/workflows/pr-checks-report.yml",
    ".github/scripts/run_pr_checks.py": "plugins/omnisgm/scripts/checks/run_pr_checks.py",
    ".github/scripts/ci_lint.py": "plugins/omnisgm/scripts/checks/ci_lint.py",
}
# the repo's own settings in a workflow copy (runner, CI check name, Node version): a sync keeps them, the gate
# compares them with the base's copy instead of the template
SETTING_LINE = re.compile(r"^\s*(runs-on:|CI_CHECK:|node-version:|- name: Setup Node\b|# Self-sufficiency on self-hosted: Node\b)")
SETTING_MARK = "\0setting"
# a plain rule file name only: `?`, `&`, `#`, `%` or a newline would reshape the contents-API URL (review of #37)
SYNC_PATH = re.compile(r"\.claude/rules/[A-Za-z0-9][A-Za-z0-9._-]*\.md")
TEMPLATES_REPO = os.environ.get("TEMPLATES_REPO", "OmnisGM-App/claude-plugins")
TEMPLATES_REF = os.environ.get("TEMPLATES_REF", "master")
BOT_LOGINS = {"dependabot[bot]", "app/dependabot"}  # REST gives the first, `gh pr view` the second
WORKFLOW_ACTOR = "github-actions[bot]"  # labels applied with GITHUB_TOKEN carry this actor
WAIT = "⏳ "  # prefix of a "still awaited" message — reported as "waiting:", not as a contradiction
STATE_MARK = "<!-- merge-gate-state "
STATE_END = " -->"


def template_of(path: str) -> str | None:
    """The template path in TEMPLATES_REPO of a copy in a product repo; None for any other file."""
    if SYNC_PATH.fullmatch(path):
        return "templates/" + path.rsplit("/", 1)[-1]
    return WORKFLOW_COPIES.get(path)


JOB_LINE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*(#.*)?$")


def split_settings(path: str, text: str) -> tuple[list[str], dict[tuple[str, str, int], str]]:
    """(the lines with each settings line replaced by a mark, the settings lines by key); only a `.yml` copy has them.
    A key is (the job id under `jobs:`, "" above it; the setting; its order among that setting's lines in the job), so a
    template that reorders jobs keeps each job's own value and no value moves to another job."""
    lines = text.split("\n")
    if not path.endswith(".yml"):
        return lines, {}
    body, settings, job, jobs, seen = [], {}, "", False, {}
    for l in lines:
        if l.startswith("jobs:"):
            jobs = True
        elif jobs and JOB_LINE.match(l):
            job = JOB_LINE.match(l).group(1)
        m = SETTING_LINE.match(l)
        if m:
            n = seen.get((job, m.group(1)), 0)
            seen[(job, m.group(1))] = n + 1
            settings[(job, m.group(1), n)] = l
            body.append(SETTING_MARK)
        else:
            body.append(l)
    return body, settings


def with_settings(path: str, template: str, copy: str) -> str:
    """The template with the copy's settings lines in their places, matched by key: what sync_templates.sh writes.
    A key only the copy has (a job or step the template dropped) goes. A key only the template has (a new job) takes
    the copy's line of the template keys with the same template line when the copy agrees on them (a new
    `runs-on: self-hosted` job runs where the repo's other self-hosted jobs run), else the template's line."""
    body, want = split_settings(path, template)
    _, have = split_settings(path, copy)

    def line(key):
        if key in have:
            return have[key]
        same = {have[k] for k in want if k in have and want[k] == want[key]}  # an equal line is the same setting
        return same.pop() if len(same) == 1 else want[key]
    it = iter(want)  # dicts keep the template's order: the n-th mark is the n-th key
    return "\n".join(line(next(it)) if l == SETTING_MARK else l for l in body)


SETTINGS_DONOR = ".github/workflows/merge-gate.yml"   # where a copy the repo does not carry yet takes its settings lines


def new_copy(path: str, template: str, donor: str | None) -> str:
    """A workflow copy the repo does not carry yet, as sync_templates.sh adds it: the template, each settings line of it
    replaced by the line of the same setting in the repo's merge-gate.yml (`donor`) when that file has exactly one such
    line text (Rules runs its gate jobs on `ubuntu-latest`); otherwise, and for a script, the template's line."""
    if not path.endswith(".yml"):
        return template
    by_name: dict[str, set[str]] = {}
    for (_, name, _), l in split_settings(SETTINGS_DONOR, donor or "")[1].items():
        by_name.setdefault(name, set()).add(l.strip())
    out = []
    for l in template.split("\n"):
        m = SETTING_LINE.match(l)
        own = by_name.get(m.group(1), set()) if m else set()
        out.append(l[: len(l) - len(l.lstrip())] + next(iter(own)) if len(own) == 1 else l)
    return "\n".join(out)


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

    def _files(self) -> list[dict]:
        """`pulls/{pr}/files`, read once per run (the head does not move under a run; GitHub caps the list at 3000)."""
        if getattr(self, "_pages", None) is None:
            self._pages = [f for page in gh_json(f"repos/{self.repo}/pulls/{self.pr}/files", "--paginate") for f in page]
        return self._pages

    def files(self) -> list[str]:
        return [f["filename"] for f in self._files()]

    def touched_paths(self) -> list[str]:
        """Every path the PR touches: each file's name and, for a rename, the name it had (a move out of `src/` is a change there)."""
        return [p for f in self._files() for p in (f["filename"], f.get("previous_filename")) if p]

    def file_status(self) -> dict[str, str]:
        """{filename: status} of the PR's files (added / modified / removed / renamed …) — the sync exemption needs it."""
        return {f["filename"]: f.get("status", "") for f in self._files()}

    def events(self) -> list[dict]:
        pages = gh_json(f"repos/{self.repo}/issues/{self.pr}/events", "--paginate")
        return [e for page in pages for e in page]

    def events_again(self) -> list[dict]:
        import time
        time.sleep(4)
        return self.events()

    def own_paths(self, bound: str, head: str, base_ref: str) -> list[str] | None:
        """The paths the PR's OWN commits touched between `bound` and `head`; None when that cannot be told (the head is not
        a descendant of `bound`; COMPARE_CAP or more own commits, FILES_CAP or more files in one commit, COMPARE_CAP or more
        files in a merge's diff against its base parent). Walks the commits `bound..head` without
        those the base has and `bound` has not. A commit with one parent counts with all its files (a rename with both
        names). A merge whose second parent is in the base's history (`compare tip...parent` is `behind`/`identical`) counts
        only with the files that (1) the merge changed against its first parent, (2) differ from the base parent's content
        (`compare second-parent...merge`: what the base brought equals it there) and (3) when the base changed the file too
        (`compare first-parent...second-parent`), whose +/- lines of the merge's own patch differ from the base's patch: a
        clean merge of a file both sides edited shows the base's change again and is not the PR's, a resolution adds a line
        and is. A patch that is missing (binary, too large) counts as the PR's. A merge of anything else, or whose base
        side cannot be read, counts with all its files. A `get` lists every page (GitHub pages files and commits by 100);
        an API error other than 404/422 propagates."""
        def get(path: str):
            try:
                return gh_json(f"repos/{self.repo}/{path}", "--paginate")
            except RuntimeError as e:
                if "HTTP 404" in str(e) or "HTTP 422" in str(e):
                    return None
                raise
        def files_of(pages, cap: int = COMPARE_CAP) -> list[dict] | None:
            files = [f for page in pages for f in page.get("files", [])]
            return None if len(files) >= cap else files
        def names(files: list[dict]) -> set[str]:
            return {p for f in files for p in (f["filename"], f.get("previous_filename")) if p}
        def change(patch: str | None) -> list[str] | None:
            # only the +/- lines, not where they sit: it survives a shift of the @@ headers, and a merge crafted to relocate
            # the base's lines gives no new right (whoever can do that can set the label by hand)
            return None if patch is None else [l for l in patch.splitlines() if l[:1] in ("+", "-")]
        pages = get(f"compare/{bound}...{head}")
        if not pages or pages[0].get("status") not in ("ahead", "identical"):
            return None
        commits = [c for page in pages for c in page.get("commits", [])]
        tip = self.base_tip(base_ref)
        # after a merge of the base `bound..head` also lists the base's own commits: `compare bound...tip` names those the
        # base has and `bound` has not — they are the base's, not the PR's, and contribute nothing
        theirs = get(f"compare/{bound}...{tip}")
        if not theirs:
            return None
        # no cap on what is skipped, nor on the base's files below: they only take files away, a partial list is stricter
        skip = {c["sha"] for page in theirs for c in page.get("commits", [])}
        commits = [c for c in commits if c["sha"] not in skip]
        if len(commits) >= COMPARE_CAP:
            return None
        out: set[str] = set()
        for c in commits:
            detail = get(f"commits/{c['sha']}")  # one document per page: the parents on each, the files split between them
            own_files = files_of(detail or [], FILES_CAP)  # GitHub's own limit for a commit; a cut list would lose the PR's files
            if own_files is None or not detail:
                return None
            parents = [p["sha"] for p in detail[0].get("parents", [])]
            mine = names(own_files)
            for p in parents[1:]:
                side = get(f"compare/{tip}...{p}")
                if not side or side[0].get("status") not in ("behind", "identical"):
                    continue  # not the base's history (or unreadable): the merge's files are the PR's
                diff = get(f"compare/{p}...{c['sha']}")
                incoming = get(f"compare/{parents[0]}...{p}")
                diff_files = files_of(diff or [])  # capped: a cut list would let `&=` keep files the base brought
                if diff_files is None or not diff or not incoming:
                    return None
                in_files = [f for page in incoming for f in page.get("files", [])]
                mine &= names(diff_files)
                base_patch = {f["filename"]: f.get("patch") for f in in_files}
                for f in own_files:
                    theirs_change = change(base_patch.get(f["filename"])) if f["filename"] in base_patch else None
                    if theirs_change is not None and theirs_change == change(f.get("patch")):
                        mine.discard(f["filename"])  # the base's own edit of the file, merged cleanly
            out |= mine
        return sorted(out)

    def first_seen(self, sha: str, ref: str) -> str | None:
        """When GitHub first saw a commit as a pushed head OF THE BRANCH `ref`: the earliest `created_at` of its check suites
        with `head_branch == ref` (the server's clock, a suite is created by the push; one made by a push of the same sha to
        another branch is not this PR's push); None when it has none (a commit in the middle of a push has no suite of its own)."""
        pages = gh_json(f"repos/{self.repo}/commits/{sha}/check-suites", "--paginate")
        return min((c["created_at"] for page in pages for c in page.get("check_suites", [])
                    if c.get("created_at") and c.get("head_branch") == ref), default=None)

    def timeline(self) -> list[dict]:
        """The PR's timeline events (labeled, committed, head_ref_force_pushed …)."""
        return [e for page in gh_json(f"repos/{self.repo}/issues/{self.pr}/timeline", "--paginate") for e in page]

    def file_text(self, repo: str, path: str, ref: str, token: str | None = None) -> str | None:
        """The text of `path` at `ref`; None when the file is not there (removed by the PR, no template)."""
        try:
            q = urllib.parse.quote
            got = gh_json(f"repos/{repo}/contents/{q(path, safe='/')}?ref={q(ref, safe='')}", token=token)
            return base64.b64decode(got["content"]).decode("utf-8")
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

    def template_mismatches(self, files: list[str], head: str, merge: str,
                            base: str) -> tuple[list[str], list[str], list[str]]:
        """Changed copies that are not their template on TEMPLATES_REF outside the settings lines (at the head; at the
        test merge commit only), and those whose settings lines in the test merge are not what the sync makes of the
        template and the base's copy (`with_settings`: the base's lines, a new key from the template)."""
        token = os.environ.get("TEMPLATES_TOKEN")
        at_head, at_merge, settings = [], [], []
        for f in files:
            want = self.file_text(TEMPLATES_REPO, template_of(f), TEMPLATES_REF, token)
            body = None if want is None else split_settings(f, want)[0]
            got = self.file_text(self.repo, f, head)
            if body is None or got is None or split_settings(f, got)[0] != body:
                at_head.append(f)
                continue
            merged = self.file_text(self.repo, f, merge)
            if merged is None or split_settings(f, merged)[0] != body:
                at_merge.append(f)
            else:
                old = self.file_text(self.repo, f, base)
                sync = (with_settings(f, want, old) if old is not None   # an added copy: the settings of the repo's gate
                        else new_copy(f, want, self.file_text(self.repo, SETTINGS_DONOR, base)))
                if split_settings(f, merged)[1] != split_settings(f, sync)[1]:
                    settings.append(f)
        return at_head, at_merge, settings

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
        """The gate's state comment on the PR: {label: {"sha", "tree"}} (plus the gate's own markers)."""
        pages = gh_json(f"repos/{self.repo}/issues/{self.pr}/comments", "--paginate")
        for page in pages:
            for c in page:
                body = c.get("body") or ""
                # only the gate's own comment (GITHUB_TOKEN actor): a hand-written marker must not bind a label
                if body.startswith(STATE_MARK) and (c.get("user") or {}).get("login") == WORKFLOW_ACTOR:
                    return c["id"], parse_state(body)
        return None, {}

    def write_state(self, comment_id: int | None, state: dict) -> int | None:
        """Writes the state comment; returns its id (a new one when it is created)."""
        body = render_state(state)
        if comment_id is None:
            return gh_json(f"repos/{self.repo}/issues/{self.pr}/comments", "-X", "POST", "-f", f"body={body}").get("id")
        gh_json(f"repos/{self.repo}/issues/comments/{comment_id}", "-X", "PATCH", "-f", f"body={body}")
        return comment_id

    def tree(self, sha: str) -> str | None:
        """The tree of a commit; None when the commit is gone (404/422: the caller then treats the tree as unknown). Any
        other error (5xx, rate limit, network) propagates: the run goes red and the labels stay, as in `own_paths`."""
        try:
            return gh_json(f"repos/{self.repo}/git/commits/{sha}").get("tree", {}).get("sha")
        except RuntimeError as e:
            if "HTTP 404" in str(e) or "HTTP 422" in str(e):
                return None
            raise

    def remove_label(self, name: str) -> None:
        subprocess.run(["gh", "pr", "edit", self.pr, "--repo", self.repo, "--remove-label", name], check=True)

    def add_label(self, name: str) -> None:
        subprocess.run(["gh", "pr", "edit", self.pr, "--repo", self.repo, "--add-label", name], check=True)


def bound_entry(value) -> dict | None:
    """A head-bound label's state entry as {"sha", "tree"}: the old form was the bare sha string (tree unknown)."""
    if isinstance(value, dict):
        return {"sha": value.get("sha"), "tree": value.get("tree")}
    if isinstance(value, str):
        return {"sha": value, "tree": None}
    return None


def normalize_state(state: dict) -> dict:
    """Head-bound entries (matrix-passed, snapshots-approved) as dicts; every other key (the gate's own markers) as is."""
    out = dict(state)
    for name in (LABEL_MATRIX_OK, LABEL_SNAP):
        if name in out:
            entry = bound_entry(out[name])
            if entry is None:
                del out[name]
            else:
                out[name] = entry
    return out


def parse_state(body: str) -> dict:
    try:
        parsed = json.loads(body[len(STATE_MARK):body.index(STATE_END)])
    except (ValueError, KeyError):
        return {}
    return normalize_state(parsed) if isinstance(parsed, dict) else {}


def render_state(state: dict) -> str:
    return (STATE_MARK + json.dumps(state, sort_keys=True) + STATE_END +
            "\nMerge gate state: the head each `gate/*` label was applied on (written by the workflow; do not edit).")


def last_labeled_actor(events: list[dict], name: str) -> str | None:
    acts = [(e["created_at"], (e.get("actor") or {}).get("login", "")) for e in events
            if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == name]
    return max(acts)[1] if acts else None


MATRIX_FREE = ".github/matrix-free-paths"   # per repo, not a template copy: one regex per line, `#` starts a comment
AUTO_NA = "auto:" + LABEL_MATRIX_NA          # state key: the gate applied the label itself (a hand-set one is only watched: hand_matrix)
HAND_NA = "hand:" + LABEL_MATRIX_NA          # state key: the head a hand-set label is bound to (its `labeled` run; with no record, the last commit of the timeline pushed before its `labeled`, see timeline_bound)
COMPARE_CAP = 250                            # own_paths: unknown at this many own commits, or at this many files in a merge's diff against its base parent (FILES_CAP: in one commit)
FILES_CAP = 3000                             # `pulls/{pr}/files` lists at most this many; `commits/{sha}` too (own_paths: unknown at this many files in one commit)


def matrix_free(paths: list[str], spec: str | None) -> bool:
    """True when the repo lists its matrix-free paths and every touched path fully matches one of them. A `#` at the
    start of a line or after whitespace starts a comment; a BOM is dropped."""
    lines = [re.split(r"(?:^|\s)#", l, maxsplit=1)[0].strip() for l in (spec or "").lstrip("\ufeff").splitlines()]
    pats = [re.compile(l) for l in lines if l]
    return bool(pats) and bool(paths) and all(any(p.fullmatch(f) for p in pats) for f in paths)


def gate_set_label(gh: GitHub, events: list[dict], name: str) -> bool:
    """Whether `name`, on the PR now, is the workflow's own, read from the timeline (not the run's payload: a re-run
    replays its original `labeled` event long after the label changed hands). The LAST labeled/unlabeled event of the
    label decides: the workflow's `labeled` makes it the gate's, a person's or an agent's `labeled` makes it theirs.
    Anything else (no event, `unlabeled` last while the label is on the PR, a person's `labeled` that may hide a newer
    one) means the list lags: it is re-read like for `gate/review-passed`. When the re-reads run out, the doubt goes to
    the gate, which takes its label back (red), never to a person (a label nobody would ever remove)."""
    def last(evs: list[dict]) -> tuple[str, str] | None:
        # events of one second keep their order by id, not by the event's name or the actor's login
        acts = [((e["created_at"], e.get("id", 0)), e["event"], (e.get("actor") or {}).get("login", "")) for e in evs
                if e.get("event") in ("labeled", "unlabeled") and (e.get("label") or {}).get("name") == name]
        return max(acts, key=lambda a: a[0])[1:] if acts else None
    gates = ("labeled", WORKFLOW_ACTOR)
    got = last(events)
    for _ in range(5):
        if got == gates or not hasattr(gh, "events_again"):
            break
        got = last(gh.events_again())
    return got is None or got[0] == "unlabeled" or got[1] == WORKFLOW_ACTOR


def timeline_bound(gh: GitHub, label: str, ref: str, head: str) -> tuple[str | None, str | None, str | None]:
    """The head a head-bound label with no record was set on: the last `committed` event of the timeline (timeline order) that
    GitHub had seen as a push to the PR's branch `ref` strictly before the label's last `labeled` event, both on the SERVER's
    clock — `first_seen` of the commit (its earliest check suite of that branch, created by the push) against the `created_at`
    of the event (never a commit's own date: that is the author's clock, and a commit made before the label but pushed after
    it must not read as the head the owner saw; a suite of another branch is not this PR's push). Walks the commits from the
    newest; one without a suite of its own (the middle of a push) is passed over, except the live `head` itself, which cannot be
    timed yet. Returns (sha, None, None); (None, why, None) when it cannot be told yet (timeline or check suites unreadable,
    the `labeled` event not on the timeline, the live head has no suite yet: the caller waits, never guesses); (None, None, why)
    when the label has to go: a `head_ref_force_pushed` at or after the label, or after the candidate's own push (a rebase's suite and its force-push event share a time: not after) (the history it
    saw was rewritten), or no commit was seen that early."""
    try:
        events = gh.timeline()
    except (RuntimeError, ValueError) as e:  # ValueError: a body that is not JSON
        return None, f"timeline unreadable, {type(e).__name__}: {str(e)[:120]}", None
    at = max((e.get("created_at", "") for e in events if e.get("event") == "labeled"
              and (e.get("label") or {}).get("name") == label), default="")
    if not at:
        return None, "its `labeled` event is not on the timeline yet", None
    fps = [e.get("created_at", "") for e in events if e.get("event") == "head_ref_force_pushed"]
    if any(f >= at for f in fps):
        return None, None, "the branch was force-pushed after the label, so the head it was set on is unknown"
    for sha in [e["sha"] for e in events if e.get("event") == "committed" and e.get("sha")][::-1]:
        try:
            seen = gh.first_seen(sha, ref)
        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            return None, f"check suites of {sha[:7]} unreadable, {type(e).__name__}: {str(e)[:120]}", None
        if seen is None:
            if sha == head:
                return None, f"{sha[:7]} has no check suite yet, so the time it was pushed is unknown", None
            continue  # the middle of a push: pushed with a newer commit that has a suite, never the head anyone saw
        if seen < at:
            if any(seen < f for f in fps):  # reset after it was pushed (and the sha pushed again): not what the owner looked at
                return None, None, f"the branch was force-pushed after {sha[:7]} was pushed, so the head it was set on is unknown"
            return sha, None, None
    return None, None, "no commit on the timeline is as old as the label, so the head it was set on is unknown"


def hand_matrix(gh: GitHub, pull: dict, state: dict, comment_id: int | None, event: str, event_label: str,
                event_head: str) -> tuple[dict, int | None, bool, str | None]:
    """A `gate/matrix-not-needed` a person or an agent set (#89): bound to the head it was set on (HAND_NA in the state
    comment: the payload head of its `labeled` run; with no record — a superseded `labeled` run, a label from before
    the record — the last commit of the timeline that GitHub had seen before the label's last `labeled` event (server times,
    branch suites, timeline_bound), then the usual check from there; no such commit, or a force-push after the label, removes it; a lagging timeline or unreadable check suites: the head is not checked, the run
    is red (waiting) until it can be). On a new head the label is removed when the PR's own commits since the bound head
    touched a path outside MATRIX_FREE (read at the base, own_paths leaves out what a merge of the base brought), the paths
    named in the note; when they touched only listed paths the label stays and is bound to the new head. Unreadable list
    or an API error: the label and the binding stay and the run is red ("waiting": the head is not checked); a history
    that cannot be compared (a force-push) removes it, as a matrix label bound to another head goes. Returns the shape of auto_matrix; the state is written by run()."""
    head = pull["head"]["sha"]
    if event == "labeled" and event_label == LABEL_MATRIX_NA:
        state[HAND_NA] = event_head or head  # the head the person saw
    bound = state.get(HAND_NA)
    def waiting(why: str, way_out: str = "re-run the gate") -> tuple[dict, int | None, bool, str]:
        return state, comment_id, False, (f"{WAIT}`{LABEL_MATRIX_NA}` (set by hand) not re-checked on this head ({why}) "
                                          f"— {way_out}.")
    def removed(why: str) -> tuple[dict, int | None, bool, str]:
        gh.remove_label(LABEL_MATRIX_NA)
        pull["labels"] = [l for l in pull.get("labels", []) if l["name"] != LABEL_MATRIX_NA]
        state.pop(HAND_NA, None)
        return state, comment_id, False, f"`{LABEL_MATRIX_NA}` (set by hand) removed by the gate: {why}. Run the matrix or set it again."
    if not isinstance(bound, str) or not bound:
        bound, why, gone = timeline_bound(gh, LABEL_MATRIX_NA, pull["head"]["ref"], head)
        if why:
            return waiting(why)
        if gone:
            return removed(gone)
        state[HAND_NA] = bound
    if bound == head:
        return state, comment_id, False, None
    base = pull.get("base") or {}
    if not base.get("sha"):
        return waiting("the PR has no base sha", "set the label again on this head")
    try:
        spec = gh.file_text(gh.repo, MATRIX_FREE, base["sha"])
        tree = gh.tree(head)
        if tree is not None and gh.tree(bound) == tree:  # a rebase onto the same files: nothing new, as for matrix-passed
            state[HAND_NA] = head
            return state, comment_id, False, None
        own = gh.own_paths(bound, head, base.get("ref", ""))
    except (RuntimeError, ValueError, TypeError, KeyError, re.error) as e:  # ValueError: a body that is not JSON
        return waiting(f"{type(e).__name__}: {str(e)[:120]}")
    if own is None:
        return removed(f"the commits since {bound[:7]} cannot be compared (history rewritten, {COMPARE_CAP} or more own commits, "
                       f"{FILES_CAP} or more files in one commit, or {COMPARE_CAP} or more files in a merge's diff against the base, or a part of it is unreadable)")
    try:
        outside = [p for p in own if not matrix_free([p], spec)]
    except re.error as e:
        return waiting(f"`{MATRIX_FREE}` unreadable: {e}", f"fix `{MATRIX_FREE}` on the base, or set the label again on this head")
    if not outside:
        state[HAND_NA] = head
        return state, comment_id, False, None
    return removed((f"`{MATRIX_FREE}` is missing at the base, so no path counts as free; " if spec is None else "")
                   + f"the commits since {bound[:7]} touch paths outside `{MATRIX_FREE}`: {', '.join(map(repr, outside[:5]))}"
                   + (f" and {len(outside) - 5} more" if len(outside) > 5 else ""))


def auto_matrix(gh: GitHub, pull: dict, files: list[str], paths: list[str], events: list[dict], state: dict,
                comment_id: int | None, event: str = "", event_label: str = "",
                event_head: str = "") -> tuple[dict, int | None, bool, str | None]:
    """Sets `gate/matrix-not-needed` itself when every path the PR touches is in MATRIX_FREE, read at the PR's BASE
    (a PR cannot widen its own list), and removes the label it set once the diff leaves the list, the list cannot be
    read for a new head, or a `gate/matrix-passed` bound to this head replaces it; a label a person or an agent set is
    theirs (its last `labeled` event is not the workflow's) — it is only watched, see hand_matrix. Labels the gate applies with GITHUB_TOKEN start no workflow
    run, so `pull` is updated in place for this run's verdict. Returns (new state, state comment id, whether the state
    was already written, a line for the summary or None)."""
    labels = {l["name"] for l in pull.get("labels", [])}
    state, head = dict(state), pull["head"]["sha"]
    if pull["head"]["ref"].startswith(SYNC_PREFIX) or LABEL_COPY in labels:
        return state, comment_id, False, None  # template copies need no matrix label at all
    auto = (state.get(AUTO_NA) is not None and LABEL_MATRIX_NA in labels
            and gate_set_label(gh, events, LABEL_MATRIX_NA))
    if not auto:
        state.pop(AUTO_NA, None)
    if LABEL_MATRIX_NA not in labels or auto:
        state.pop(HAND_NA, None)  # a record of a label that is gone or became the gate's
    if LABEL_MATRIX_NA in labels and not auto:
        if (pull.get("user") or {}).get("login") in BOT_LOGINS:
            return state, comment_id, False, None  # Dependabot's label comes from dependabot.yml: nothing to bind
        return hand_matrix(gh, pull, state, comment_id, event, event_label, event_head)
    matrix_ok = False
    if LABEL_MATRIX_OK in labels:  # bound the way evaluate() binds it
        seen = event_head or head  # a `labeled` run binds the payload head with its tree, as evaluate() records it
        entry = {"sha": seen, "tree": gh.tree(seen) if seen != head else None} \
            if (event == "labeled" and event_label == LABEL_MATRIX_OK) \
            else (bound_entry(state.get(LABEL_MATRIX_OK)) or {"sha": None, "tree": None})
        if entry["sha"] is None:
            return state, comment_id, False, None  # its `labeled` run has not recorded a head yet: that run decides
        # same tree on a moved head holds the label in evaluate() too, so it holds here (no second matrix label)
        matrix_ok = entry["sha"] == head or (entry["tree"] is not None and gh.tree(head) == entry["tree"])
    free, note = False, None
    if matrix_ok:
        if auto:
            note = f"`{LABEL_MATRIX_NA}` removed by the gate: `{LABEL_MATRIX_OK}` holds on this head."
    elif len(files) >= FILES_CAP or pull.get("changed_files", len(files)) != len(files):
        note = f"`{MATRIX_FREE}` not applied: GitHub lists {len(files)} of {pull.get('changed_files')} changed files."
    else:
        base = (pull.get("base") or {}).get("sha")
        try:
            if not base:
                raise ValueError("the PR has no base sha")
            free = matrix_free(paths, gh.file_text(gh.repo, MATRIX_FREE, base))
        except (RuntimeError, ValueError, TypeError, KeyError, re.error) as e:
            # the list is a convenience: an API hiccup or a bad file never turns the gate red by itself; the gate's
            # label survives it only on the head it was decided for (a re-run), a new head waits for a matrix label
            note = f"`{MATRIX_FREE}` not applied ({type(e).__name__}: {str(e)[:120]}) — set the matrix label by hand."
            if not auto or state.get(AUTO_NA) == head:
                return state, comment_id, False, note
    if free and not auto:
        state[AUTO_NA] = head
        # the record goes first: a failure after it leaves a record without its label, which the next run drops;
        # a label without its record would pass for a hand-set one and never be removed
        comment_id = gh.write_state(comment_id, state)
        gh.add_label(LABEL_MATRIX_NA)
        pull["labels"] = pull.get("labels", []) + [{"name": LABEL_MATRIX_NA}]
        return state, comment_id, True, (f"`{LABEL_MATRIX_NA}` set by the gate: all {len(paths)} touched path(s) match "
                                         f"`{MATRIX_FREE}` of the base.")
    if auto and not free:
        gh.remove_label(LABEL_MATRIX_NA)  # the label goes first, the record with this run's state
        pull["labels"] = [l for l in pull.get("labels", []) if l["name"] != LABEL_MATRIX_NA]
        state.pop(AUTO_NA, None)
        return state, comment_id, False, note or (f"`{LABEL_MATRIX_NA}` removed by the gate: the diff now touches paths "
                                                  f"outside `{MATRIX_FREE}`.")
    if auto:
        state[AUTO_NA] = head
    return state, comment_id, False, note


def is_release(pull: dict) -> bool:
    """`release/*` -> `master`; dev -> master is not a release since 2026-10-23."""
    return pull["base"]["ref"] == "master" and pull["head"]["ref"].startswith("release/")


def review_paused() -> bool:
    """The owner's repo switch: only the exact value `true` pauses the review, so a typo keeps the gate closed."""
    return os.environ.get("REVIEW_PAUSED", "") == "true"


def review_exempt(pull: dict) -> bool:
    """Dependabot, a release PR and a template copy never wait for a review round."""
    labels = {l["name"] for l in pull.get("labels", [])}
    return (pull["user"]["login"] in BOT_LOGINS or is_release(pull) or pull["head"]["ref"].startswith(SYNC_PREFIX)
            or LABEL_COPY in labels)


def awaited_snapshots(pull: dict, files: list[str]) -> int:
    """How many screenshot baselines of the PR wait for the owner's `gate/snapshots-approved`: those the PR changes, none for a
    release (approved in the feature PRs). The one place of this rule: the WAIT line of evaluate() and the label
    `gate/snapshots-review-needed` both read it."""
    return 0 if is_release(pull) else sum(1 for f in files if SNAPSHOT_RE.search(f))


def evaluate(gh: GitHub, pull: dict, files: list[str], events: list[dict], state: dict,
             event: str = "", event_label: str = "",
             event_head: str = "") -> tuple[list[str], list[str], dict]:
    """Returns (labels to remove, failure messages, new state)."""
    labels = {l["name"] for l in pull.get("labels", [])}
    head_ref, head = pull["head"]["ref"], pull["head"]["sha"]
    base_ref = pull["base"]["ref"]
    state = normalize_state(state)
    remove: list[str] = []
    fail: list[str] = []

    for name in (LABEL_MATRIX_OK, LABEL_SNAP):
        if name not in labels:
            state.pop(name, None)
            continue
        if event == "labeled" and event_label == name:
            seen = event_head or head  # the head the person saw when applying it, and the tree of THAT head
            state[name] = {"sha": seen, "tree": gh.tree(seen)}
        entry = state.get(name)
        if (entry is None or entry["sha"] is None) and name == LABEL_SNAP:
            # no record (its `labeled` run was superseded): bound from the timeline like a hand-set matrix label, then checked
            bound, why, gone = timeline_bound(gh, name, head_ref, head)
            if why:
                fail.append(f"{WAIT}`{name}` not re-checked on this head ({why}) — re-run the gate.")
                continue
            if gone:
                print(f"::notice::`{name}` removed by the gate: {gone}. The owner sets it again.")
                remove.append(name)
                continue
            try:
                entry = {"sha": bound, "tree": gh.tree(bound)}
            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                fail.append(f"{WAIT}`{name}` not re-checked on this head ({type(e).__name__}: {str(e)[:120]}) — re-run the gate.")
                continue
        if entry is None or entry["sha"] is None:
            fail.append(f"`{name}` is set but no head is recorded for it (its `labeled` run was skipped or superseded) — "
                        "remove and re-apply the label.")
        elif entry["sha"] != head:
            try:
                # same tree = the very files the matrix ran on / the owner looked at (a retarget or a rebase that only drops
                # commits already in the base); an unknown tree (None) is never equal to anything
                if entry["tree"] is not None and gh.tree(head) == entry["tree"]:
                    state[name] = {"sha": head, "tree": entry["tree"]}
                elif name == LABEL_MATRIX_OK:
                    print(f"::notice::`{name}` removed by the gate: it was applied on {entry['sha'][:7]}, the live head is {head[:7]}.")
                    remove.append(name)
                else:
                    # the approval covers the PR's own baselines: it goes only when the PR's OWN commits since the bound head
                    # touched a `*-snapshots/` path (a base merge's baselines are not the PR's); history not comparable: goes
                    own = gh.own_paths(entry["sha"], head, base_ref)
                    if own is None:
                        print(f"::notice::`{name}` removed by the gate: the commits since {entry['sha'][:7]} cannot be compared "
                              "(history rewritten, or too many commits or files to list). The owner sets it again.")
                        remove.append(name)
                    elif (hit := [f for f in own if SNAPSHOT_RE.search(f)]):
                        print(f"::notice::`{name}` removed by the gate: the PR's own commits since {entry['sha'][:7]} changed "
                              f"baselines: {', '.join(map(repr, hit[:5]))}{f' and {len(hit) - 5} more' if len(hit) > 5 else ''}. The owner looks again.")
                        remove.append(name)
                    else:
                        state[name] = {"sha": head, "tree": gh.tree(head)}
            except (RuntimeError, ValueError, TypeError, KeyError) as e:  # an API error: the label and its binding stay, red
                if name == LABEL_MATRIX_OK:
                    raise
                fail.append(f"{WAIT}`{name}` not re-checked on this head ({type(e).__name__}: {str(e)[:120]}) — re-run the gate.")
        elif entry != state.get(name):
            state[name] = entry  # bound from the timeline to the live head
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

    sync_branch = head_ref.startswith(SYNC_PREFIX)
    copy_pr = sync_branch or LABEL_COPY in labels
    if copy_pr:
        default = (pull["base"].get("repo") or {}).get("default_branch")
        if sync_branch:
            tag, claim = "template-sync branch", f"`{head_ref}` is a template-sync branch but changes"
            way_out = (" This branch is never merged as an ordinary PR: a change beyond the template copies goes in a PR from "
                       "a branch outside `sync/templates-*`; the next sync run opens a new PR and closes this one.")
        else:
            tag, claim = f"`{LABEL_COPY}` PR", f"`{LABEL_COPY}` is set but the PR changes"
            way_out = f" Remove `{LABEL_COPY}` to send this PR through an ordinary review round."
        foreign = [f for f in files if template_of(f) is None]
        if base_ref != default:
            fail.append(f"{tag} into `{base_ref}`, not the default branch `{default}` — the template-copy "
                        "exemption holds only there." + way_out)
        elif not files or foreign:
            fail.append(f"{claim} {', '.join(map(repr, foreign[:5])) or 'nothing'} — only copies of claude-plugins "
                        "templates (`.claude/rules/*.md` and the workflow copies) are exempt." + way_out)
        elif (not_mod := sorted(f"{f} ({st or '?'})" for f, st in gh.file_status().items()
                                if not (st == "modified" or (st == "added" and f in WORKFLOW_COPIES)))):
            # a new rule file is a decision for the repo (an ordinary PR); a rename hides the removal of its source
            fail.append(f"{tag}: {', '.join(not_mod[:5])} — only modified copies, and added workflow copies, are exempt." + way_out)
        elif (why := gh.templates_unreadable()):
            fail.append(f"{tag}: {why}")
        elif not (merge := gh.merge_commit(pull)):
            fail.append(f"{tag}: GitHub has no test merge of this PR with the live base (not computed "
                        "yet, not rebuilt after a push to the base, or a conflict) — press \"Re-run jobs\" on this gate run; on a conflict run sync-templates.yml "
                        "(workflow_dispatch, dry_run: false), it clones the current base and replaces this PR." + way_out)
        else:
            at_head, at_merge, settings = gh.template_mismatches(files, head, merge, gh.merge_parent(merge))
            if at_head:
                fail.append(f"{tag}: {', '.join(at_head[:5])} differ from {TEMPLATES_REPO} "
                            f"templates@{TEMPLATES_REF} at the head — edit the template, not the copy." + way_out)
            if at_merge:
                fail.append(f"{tag}: {', '.join(at_merge[:5])} match the template at the head but not in the "
                            "merge with the base (the base changed the copy) — run sync-templates.yml (workflow_dispatch, "
                            "dry_run: false): it clones the current base and replaces this PR." + way_out)
            if settings:
                fail.append(f"{tag}: {', '.join(settings[:5])} change the repo's settings lines (runs-on, CI_CHECK, the "
                            "Node version) — a copy keeps the base's; change them in an ordinary PR." + way_out)
    nsnap = awaited_snapshots(pull, files)
    if nsnap and LABEL_SNAP not in labels:
        fail.append(f"{WAIT}{nsnap} screenshot baseline(s) changed in this PR — waiting for `{LABEL_SNAP}`. "
                    "Only a human (the owner) sets it after looking at the new images; an agent never does.")
    n_matrix = (LABEL_MATRIX_OK in labels) + (LABEL_MATRIX_NA in labels)
    if n_matrix != 1 and not (copy_pr and n_matrix == 0):  # template copies: no UI, no matrix; a failed copy is blocked above
        fail.append(f"{WAIT if n_matrix == 0 else ''}exactly one of `{LABEL_MATRIX_OK}` (full Playwright matrix green on "
                    f"head {head[:7]}) or `{LABEL_MATRIX_NA}` (diff does not touch UI — say so in the PR body) is required; "
                    f"found {n_matrix}.")
    if not review_exempt(pull) and not review_ok and not review_paused() and not any(LABEL_REVIEW in f for f in fail):
        fail.append(f"{WAIT}waiting for `{LABEL_REVIEW}` — claude-review.yml sets it when a round ends with zero ❗; "
                    "it runs after CI on every push of a non-draft PR while the label is absent (removing the label starts a round too).")
    return remove, fail, state


def snap_review_label(gh: GitHub, pull: dict, files: list[str], removed: list[str]) -> None:
    """`gate/snapshots-review-needed` (#91): on while the PR changes `*-snapshots/` files, is not a release and has no
    `gate/snapshots-approved` (`removed` — the labels evaluate() took off in this run — counts as absent), off otherwise. It
    only says "the owner has to look"; the failure is the WAIT line of evaluate(). A label the repo does not have makes the
    add fail: a notice, never a crash (nor a red run). Labels written with GITHUB_TOKEN fire no event, so this cannot loop."""
    labels = {l["name"] for l in pull.get("labels", [])} - set(removed)
    want = awaited_snapshots(pull, files) > 0 and LABEL_SNAP not in labels
    have = LABEL_SNAP_REVIEW in labels
    if want == have:
        return
    try:
        (gh.add_label if want else gh.remove_label)(LABEL_SNAP_REVIEW)
    except subprocess.CalledProcessError as e:  # e.g. the label does not exist in this repo
        print(f"::notice::`{LABEL_SNAP_REVIEW}` not {'added' if want else 'removed'} (exit {e.returncode}) — does the label exist in this repo?")


def review_skip_label(gh: GitHub, pull: dict) -> None:
    """`gate/review-skipped`: on while the review is paused and this PR would otherwise wait for a round, off otherwise. A trace
    for the reader, never part of the verdict; a label the repo does not have is a notice, not a red run."""
    labels = {l["name"] for l in pull.get("labels", [])}
    want = review_paused() and LABEL_REVIEW not in labels and not review_exempt(pull)
    if want == (LABEL_REVIEW_SKIPPED in labels):
        return
    try:
        (gh.add_label if want else gh.remove_label)(LABEL_REVIEW_SKIPPED)
    except subprocess.CalledProcessError as e:
        print(f"::notice::`{LABEL_REVIEW_SKIPPED}` not {'added' if want else 'removed'} (exit {e.returncode}) — does the label exist in this repo?")


def split_outcome(fail: list[str]) -> tuple[list[str], list[str]]:
    """(still awaited, contradictions): both make the job red; the first group is reported as "waiting"."""
    waiting = [f[len(WAIT):] for f in fail if f.startswith(WAIT)]
    errors = [f for f in fail if not f.startswith(WAIT)]
    return waiting, errors


PR_CHECKS = "run_pr_checks.py"
PR_CHECKS_LIB = "ci_lint.py"   # run_pr_checks.py imports it at load time: a repo with one of the two copies cannot run the report
NOT_ROLLED_OUT = ("### PR checks: not rolled out in this repo\n\n`.github/scripts/run_pr_checks.py` and `.github/scripts/ci_lint.py` are not both here, "
                  "so the report did not run. The next sync-templates PR adds both (from claude-plugins `plugins/omnisgm/scripts/checks/`) "
                  "in a repo that carries `.github/scripts/merge_gate.py`.")
# One run_pr_checks.py process per group, not one for all: the script prints once, after its last check, so one hang under a single
# outer timeout would throw away the findings of the checks that did finish. Its `gh` calls time out after GH_TIMEOUT (30 s), well
# inside PR_CHECKS_TIMEOUT, so a hung call is that check's `skipped` line and the group still prints; each group's part goes to the
# summary as soon as it ends, so a cancelled job keeps what finished.
PR_CHECKS_GROUPS = ("closes", "bot-threads", "hygiene", "ci-lint")
PR_CHECKS_NOTHING = "PR checks: nothing found."   # run_pr_checks.render() for an empty result
PR_CHECKS_TIMEOUT = 120


def pr_checks_report(script: str | None = None, run_cmd=subprocess.run) -> None:
    """REPORT, not a gate (owner's decision 2026-11-11, claude-plugins#57: turning it into a failure waits for the false-positive
    rate): run the PR machine gates (closes-with-open-items, unanswered bot threads, hygiene, ci-lint) and put what they find in the
    step summary. Runs from `pr-checks-report.yml`, a workflow of its own (claude-plugins#71: inside merge-gate.yml it held the
    verdict's concurrency group), so no verdict ever waits for it. Never raises. A repo that lacks either of the two copies
    (before the sync adds them) gets a visible line instead of a silent skip."""
    try:
        _pr_checks_report(script, run_cmd)
    except Exception as e:  # noqa: BLE001 - a report must not fail the job, not even through an unwritable summary
        print(f"::warning::PR checks report failed: {type(e).__name__}: {str(e)[:200]}")


def _fence(text: str) -> str:
    """A code fence longer than any backtick run in `text` (bot comments and issue checklist items are foreign text)."""
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}\n{text}\n{ticks}"


def _pr_checks_report(script, run_cmd) -> None:
    script = script or os.path.join(os.path.dirname(os.path.abspath(__file__)), PR_CHECKS)
    if not (os.path.isfile(script) and os.path.isfile(os.path.join(os.path.dirname(script), PR_CHECKS_LIB))):
        _summary_write(NOT_ROLLED_OUT)
        return
    found = False
    for group in PR_CHECKS_GROUPS:
        try:
            r = run_cmd([sys.executable, script, "--repo", os.environ["REPO"], "--pr", os.environ["PR"], "--only", group, "--report"],
                        capture_output=True, text=True, timeout=PR_CHECKS_TIMEOUT)
            out = (r.stdout or "").strip() if r.returncode == 0 else f"[{group}] did not run (exit {r.returncode}): {(r.stderr or '')[-300:].strip()}"
        except Exception as e:  # noqa: BLE001 - one group's hang or crash is that group's line; the others keep their findings
            out = f"[{group}] did not run: {type(e).__name__}: {str(e)[:200]}"
        if out and out != PR_CHECKS_NOTHING:
            _summary_write(_fence(out))
            found = True
    if not found:
        _summary_write(PR_CHECKS_NOTHING)


def _summary_write(text: str) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    out = open(summary, "a") if summary else sys.stdout
    print(text, file=out)
    if summary:
        out.close()


def main(argv: list[str] | None = None) -> int:
    """`merge_gate.py` evaluates the labels (the verdict job); `merge_gate.py --pr-checks-report` writes the PR checks report
    (its own workflow, never a verdict: exit 0 always)."""
    if "--pr-checks-report" in (sys.argv[1:] if argv is None else argv):
        pr_checks_report()
        return 0
    gh = GitHub(os.environ["REPO"], os.environ["PR"])
    return run(gh, gh.pull())


def run(gh: GitHub, pull: dict) -> int:
    """0 when every label holds on the live head, 1 otherwise; an API error propagates (the job is red with it)."""
    env = os.environ.get
    event, event_label = env("EVENT", ""), env("EVENT_LABEL", "")
    comment_id, state = gh.state()
    files, events, event_head = gh.files(), gh.events(), env("EVENT_HEAD_SHA", "")
    auto_state, comment_id, saved, auto_note = auto_matrix(gh, pull, files, gh.touched_paths(), events, state, comment_id,
                                                           event=event, event_label=event_label, event_head=event_head)
    if saved:
        state = auto_state  # already in the state comment
    remove, fail, new_state = evaluate(gh, pull, files, events, auto_state, event=event, event_label=event_label,
                                       event_head=event_head)
    for name in remove:
        gh.remove_label(name)
        print(f"::notice::removed {name} by the gate")
    snap_review_label(gh, pull, files, remove)
    review_skip_label(gh, pull)
    if new_state != state or (comment_id is None and new_state):
        gh.write_state(comment_id, new_state)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    out = open(summary, "a") if summary else sys.stdout
    if auto_note and auto_note.startswith(WAIT):
        fail.append(auto_note)  # a hand label that could not be checked on this head: red until a run can
    elif auto_note:
        print(f"::notice::{auto_note}")
        print(auto_note + "\n", file=out)
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
