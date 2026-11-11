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
LABEL_MATRIX_OK = os.environ.get("LABEL_MATRIX_OK", "gate/matrix-passed")
LABEL_MATRIX_NA = os.environ.get("LABEL_MATRIX_NA", "gate/matrix-not-needed")
LABEL_REVIEW = os.environ.get("LABEL_REVIEW", "gate/review-passed")
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
    nsnap = len(pr_snaps)
    if nsnap and not release and LABEL_SNAP not in labels:
        fail.append(f"{WAIT}{nsnap} screenshot baseline(s) changed in this PR — waiting for `{LABEL_SNAP}`. "
                    "Only a human (the owner) sets it after looking at the new images; an agent never does.")
    n_matrix = (LABEL_MATRIX_OK in labels) + (LABEL_MATRIX_NA in labels)
    if n_matrix != 1 and not (copy_pr and n_matrix == 0):  # template copies: no UI, no matrix; a failed copy is blocked above
        fail.append(f"{WAIT if n_matrix == 0 else ''}exactly one of `{LABEL_MATRIX_OK}` (full Playwright matrix green on "
                    f"head {head[:7]}) or `{LABEL_MATRIX_NA}` (diff does not touch UI — say so in the PR body) is required; "
                    f"found {n_matrix}.")
    if not bot and not release and not copy_pr and not review_ok and not any(LABEL_REVIEW in f for f in fail):
        fail.append(f"{WAIT}waiting for `{LABEL_REVIEW}` — claude-review.yml sets it when a round ends with zero ❗; "
                    "it runs after CI on every push while the label is absent (removing the label starts a round too); "
                    "a PR whose base is not the default branch gets a round only by workflow_dispatch.")
    return remove, fail, state


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
