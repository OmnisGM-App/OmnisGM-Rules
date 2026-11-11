#!/usr/bin/env python3
"""Machine gates for a PR (claude-plugins#57): one entry point for the pre-push hook (#56).

Checks (name — what fails):
  closes       the PR body has `Closes|Fixes|Resolves #N` and issue N still has unchecked `- [ ]` items (an item
               `~~…~~ ➡️ #M` or `-> #M` counts as done; a bare struck item does not) — use `Refs #N`                        (authoring-pitfalls.md 4)
  bot-threads  a review thread opened by github-actions[bot] that the PR author never answered
  plugin-version  `plugins/omnisgm/**` changed without a version change in its plugin.json
  pyc          a tracked `*.pyc` / `__pycache__`
  test-wiring  a new `test_*.py` / `test_*.mjs` / `*_test.py` / `*.test.{js,jsx,ts,tsx,mjs,cjs,mts,cts}` that no workflow or package.json runs  (authoring-pitfalls.md 7)
  (`hygiene` selects plugin-version, pyc and test-wiring together)
  ci-lint      ci_lint.py over the changed `.github/workflows/*.yml` and `*.sh`

Usage:
  run_pr_checks.py --repo R --pr N [--only a,b] [--report]      remote: the PR through the GitHub API (read-only)
  run_pr_checks.py --local [--base B] [--repo R --pr N]         local: the diff of HEAD against B (default origin/HEAD)
  --report: print the findings and exit 0
  --body-file F: the PR body from a file (a PR that does not exist yet)
  --include-resolved: count resolved bot threads too
Exit: 0 clean (or --report), 1 findings, 2 a check could not read what it needs (shown as `skipped`, never as a pass).
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ci_lint  # noqa: E402

PLUGIN_DIR = "plugins/omnisgm/"
PLUGIN_JSON = "plugins/omnisgm/.claude-plugin/plugin.json"
BOT_LOGINS = {"github-actions", "github-actions[bot]"}
TEST_FILE_RE = re.compile(r"(^|/)(test_[^/]+\.(?:py|mjs)|[^/]+_test\.py|[^/]+\.test\.[cm]?[jt]sx?)$")
ALL = ("closes", "bot-threads", "plugin-version", "pyc", "test-wiring", "ci-lint")
GROUPS = {"hygiene": ("plugin-version", "pyc", "test-wiring")}


class Finding:
    def __init__(self, check, message, details=()):
        self.check, self.message, self.details = check, message, list(details)

    def __repr__(self):
        return f"Finding({self.check!r}, {self.message!r})"


class Skipped(Exception):
    """A check could not read its input; reported, never silently green."""


# ---------------------------------------------------------------------------------------------------------------
# gh access (injectable for tests)

GH_TIMEOUT = 30      # one gh call, well under merge_gate.py's PR_CHECKS_TIMEOUT: a hung call is this check's `skipped`
FILES_TIMEOUT = 40   # the paginated files list (up to 30 pages); fetched once and its failure cached, so a group pays it once


def run_gh(args, input_text=None, timeout=GH_TIMEOUT):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, input=input_text, timeout=timeout)
    if r.returncode != 0:
        raise Skipped(f"gh {' '.join(args[:3])}: {r.stderr.strip()[:200]}")
    return r.stdout


def decode_documents(text):
    """`gh api --paginate` prints one JSON document per page, concatenated. Lists are merged, objects collected."""
    dec, i, out = json.JSONDecoder(), 0, []
    text = text.strip()
    while i < len(text):
        doc, j = dec.raw_decode(text, i)
        out.extend(doc) if isinstance(doc, list) else out.append(doc)
        i = j
        while i < len(text) and text[i].isspace():
            i += 1
    return out


class Remote:
    def __init__(self, repo, pr, gh=run_gh):
        self.repo, self.pr, self.gh = repo, pr, gh
        self._pr = None
        self._files = None
        self._files_error = None

    def pull(self):
        if self._pr is None:
            self._pr = json.loads(self.gh(["api", f"repos/{self.repo}/pulls/{self.pr}"]))
        return self._pr

    def files(self):
        """[{path, status, patch}] of the PR (removed files included, status 'removed')."""
        if self._files_error is not None:   # the checks that read the files do not each wait for the same timeout again
            raise self._files_error
        if self._files is None:
            try:
                raw = decode_documents(self.gh(["api", f"repos/{self.repo}/pulls/{self.pr}/files?per_page=100", "--paginate"],
                                               timeout=FILES_TIMEOUT))
            except Exception as e:  # noqa: BLE001 - cached and re-raised: each caller still reports its own `skipped`
                self._files_error = e
                raise
            self._files = [{"path": f["filename"], "status": f["status"], "patch": f.get("patch")} for f in raw]
        return self._files

    def read(self, path):
        """Text of `path` at the PR head, or None when it does not exist there."""
        try:
            return self.gh(["api", "-H", "Accept: application/vnd.github.raw", f"repos/{self.repo}/contents/{path}?ref={self.pull()['head']['sha']}"])
        except Skipped as e:
            if "404" in str(e) or "Not Found" in str(e):
                return None
            raise

    def _contents(self, path):
        """The items of the directory `path` at the PR head ([] when it does not exist there)."""
        try:
            return decode_documents(self.gh(["api", f"repos/{self.repo}/contents/{path}?ref={self.pull()['head']['sha']}"]))
        except Skipped as e:
            if "404" in str(e) or "Not Found" in str(e):
                return []
            raise

    def list_dir(self, path):
        return [i["path"] for i in self._contents(path) if i.get("type") == "file"]

    def list_subdirs(self, path):
        return [i["path"] for i in self._contents(path) if i.get("type") == "dir"]

    def tracked(self):
        return None   # the whole tree is not read through the API; hygiene looks at the PR's files only

    def body(self):
        return self.pull().get("body") or ""

    def author(self):
        return self.pull()["user"]["login"]

    def issue_body(self, repo, number):
        d = json.loads(self.gh(["api", f"repos/{repo}/issues/{number}"]))
        if "pull_request" in d:
            return None, None
        return d.get("body") or "", d.get("state")

    def threads(self):
        owner, name = self.repo.split("/")
        q = ("query($o:String!,$n:String!,$p:Int!,$c:String){repository(owner:$o,name:$n){pullRequest(number:$p){"
             "reviewThreads(first:100,after:$c){pageInfo{hasNextPage endCursor} nodes{isResolved isOutdated "
             "comments(first:50){nodes{author{login} body path line url}}}}}}}")
        cursor, out = None, []
        for _ in range(50):
            args = ["api", "graphql", "-f", f"query={q}", "-f", f"o={owner}", "-f", f"n={name}", "-F", f"p={self.pr}"]
            if cursor:
                args += ["-f", f"c={cursor}"]
            d = json.loads(self.gh(args))
            if d.get("errors"):
                raise Skipped(f"graphql: {d['errors'][0].get('message', '')[:200]}")
            rt = d["data"]["repository"]["pullRequest"]["reviewThreads"]
            out += rt["nodes"]
            if not rt["pageInfo"]["hasNextPage"]:
                return out
            cursor = rt["pageInfo"]["endCursor"]
        raise Skipped("more than 5000 review threads")


class Local(Remote):
    """Files and file contents from the local checkout; PR-level data from the API when --repo/--pr are given."""

    def __init__(self, base, repo=None, pr=None, gh=run_gh, root="."):
        super().__init__(repo, pr, gh)
        self.base, self.root = base, root

    def git(self, *a):
        r = subprocess.run(["git", "-C", self.root] + list(a), capture_output=True, text=True)
        if r.returncode != 0:
            raise Skipped(f"git {' '.join(a[:3])}: {r.stderr.strip()[:200]}")
        return r.stdout

    def files(self):
        if self._files is None:
            out = self.git("diff", "--name-status", "-z", "--no-renames", f"{self.base}...HEAD").split("\0")
            files = []
            for st, p in zip(out[0::2], out[1::2]):
                status = {"A": "added", "D": "removed", "M": "modified"}.get(st[:1], "modified")
                patch = ""
                if status != "removed" and (p == PLUGIN_JSON or p.endswith((".sh", ".yml", ".yaml"))):   # the patches the checks read
                    patch = re.sub(r"(?s)^.*?\n(?=@@)", "", self.git("diff", "-U0", "--no-color", f"{self.base}...HEAD", "--", p), count=1)
                files.append({"path": p, "status": status, "patch": patch})
            self._files = files
        return self._files

    def read(self, path):
        try:
            return self.git("show", f"HEAD:{path}")
        except Skipped:
            return None

    def list_dir(self, path):
        try:
            return [l for l in self.git("ls-tree", "--name-only", "-r", "HEAD", "--", path).split("\n") if l]
        except Skipped:
            return []

    def list_subdirs(self, path):
        return []   # list_dir above is recursive

    def tracked(self):
        return [l for l in self.git("ls-files").split("\n") if l]


# ---------------------------------------------------------------------------------------------------------------
# closes

_FENCE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
CLOSE_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b:?[ \t]+(?:https://github\.com/([\w.-]+/[\w.-]+)/issues/|([\w.-]+/[\w.-]+)#|#)(\d+)", re.I)
MOVED_RE = re.compile(r"~~.*~~\s*(?:➡️?|->|→)\s*(?:[\w.-]+/[\w.-]+)?#\d+")
UNCHECKED_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:~~\s*)?\[ \]")


def closing_refs(body, default_repo):
    """[(repo, number)] closed by the PR body (code spans and fences do not close anything)."""
    seen, out = set(), []
    for m in CLOSE_RE.finditer(_FENCE_RE.sub(" ", body or "")):
        repo = m.group(1) or m.group(2) or default_repo
        key = (repo.lower(), int(m.group(3)))
        if key not in seen:
            seen.add(key)
            out.append((repo, int(m.group(3))))
    return out


def open_items(issue_body):
    """Unchecked checklist lines of an issue body that are not moved (`~~…~~ ➡️ #N` or `-> #N`), outside code fences.
    A struck item without an arrow to where it went is NOT done (omnisgm-issue: close only when every item is `[x]` or moved)."""
    text = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), issue_body or "", flags=re.S)
    return [l.strip() for l in text.split("\n") if UNCHECKED_RE.match(l) and not MOVED_RE.search(l)]


def check_closes(src, body=None, include_closed=False):
    """include_closed: also read issues that are already closed (a measurement over merged PRs; a live PR closes an open issue)."""
    body = src.body() if body is None else body
    out, unreadable = [], []
    for repo, n in closing_refs(body, src.repo or ""):
        if not repo:
            raise Skipped("the PR body closes an issue but --repo is not given")
        try:
            text, state = src.issue_body(repo, n)
        except Skipped as e:   # another repo's private issue, a typo: the next reference is still checked
            unreadable.append(f"{repo}#{n} ({str(e)[:80]})")
            continue
        if text is None or (state == "closed" and not include_closed):
            continue
        items = open_items(text)
        if items:
            out.append(Finding("closes", f"the PR closes {repo}#{n} but {len(items)} checklist item(s) there are neither `[x]` nor moved (omnisgm-issue rule: close only when every item is `[x]` or `~~…~~ ➡️ #N`; a bare struck item is not done) — use `Refs #{n}`, or fix each item: `[x]` with evidence, or an arrow to where it went", items))
    if unreadable and not out:
        raise Skipped("could not read " + ", ".join(unreadable))
    if unreadable:   # the others have findings: what was not read must not look checked
        out.append(Finding("closes", f"{len(unreadable)} closed issue(s) could not be read, so their checklists are NOT checked (a reference to another repo's issue the token cannot see?)", unreadable))
    return out


# ---------------------------------------------------------------------------------------------------------------
# bot threads

def unanswered_bot_threads(threads, pr_author, include_resolved=False):
    out = []
    for t in threads:
        if t.get("isResolved") and not include_resolved:
            continue
        cs = (t.get("comments") or {}).get("nodes") or []
        if not cs:
            continue
        first = (cs[0].get("author") or {}).get("login", "")
        if first not in BOT_LOGINS:
            continue
        if any((c.get("author") or {}).get("login", "").lower() == pr_author.lower() for c in cs[1:]):
            continue
        out.append(t)
    return out


def check_bot_threads(src, include_resolved=False):
    if not (src.repo and src.pr):
        raise Skipped("review threads need --repo and --pr")
    bad = unanswered_bot_threads(src.threads(), src.author(), include_resolved)
    if not bad:
        return []
    details = []
    for t in bad:
        c = t["comments"]["nodes"][0]
        loc = f"{c.get('path') or '?'}:{c.get('line') or '?'}"
        flag = " (resolved, no reply)" if t.get("isResolved") else (" (outdated)" if t.get("isOutdated") else "")
        details.append(f"{loc}{flag} {c.get('url') or ''} — {(c.get('body') or '').strip().splitlines()[0][:100] if (c.get('body') or '').strip() else ''}")
    return [Finding("bot-threads", f"{len(bad)} bot review thread(s) have no reply from the PR author", details)]


# ---------------------------------------------------------------------------------------------------------------
# hygiene

def check_plugin_version(files):
    changed = [f for f in files if f["path"].startswith(PLUGIN_DIR)]
    if not changed:
        return []
    pj = next((f for f in files if f["path"] == PLUGIN_JSON), None)
    patch = (pj or {}).get("patch") or ""
    bumped = bool(re.search(r'(?m)^-\s*"version"', patch)) and bool(re.search(r'(?m)^\+\s*"version"', patch))
    if pj and pj["status"] == "added":
        bumped = True
    if bumped:
        return []
    return [Finding("plugin-version", f"`{PLUGIN_DIR}**` changed ({len(changed)} file(s)) but the `version` in {PLUGIN_JSON} did not — bump the patch version",
                    [f["path"] for f in changed][:10])]


def check_no_pyc(files, tracked=None):
    pat = re.compile(r"(^|/)__pycache__(/|$)|\.py[co]$")
    bad = [f["path"] for f in files if f["status"] != "removed" and pat.search(f["path"])]
    if tracked is not None:
        bad += [p for p in tracked if pat.search(p) and p not in bad]
    return [Finding("pyc", f"{len(bad)} compiled Python file(s) tracked (`*.pyc` / `__pycache__`) — remove them and add them to .gitignore", bad[:20])] if bad else []


# Wiring means "a CI step or a package.json script really runs this file". Carriers are the workflows, the composite actions and the
# package.json files; their commands are read (comments are not), and a file is wired when a command
#   - names it (path, a suffix of it, or a file under the command's `cd` / `working-directory`),
#   - has a glob token with a literal part that matches it (a bare `*` of a `case` branch matches nothing),
#   - is `unittest discover -s <dir> -p <pattern>` / `pytest <paths>` and the file is under that directory and matches the pattern,
#   - or is a JS runner (vitest, jest, mocha, ava, playwright test, `node --test`) started with no file arguments in a directory above it.
# Only a segment that starts something (an interpreter or a runner) counts: a `paths:` filter or a docstring does not.
_RUN_HEAD = re.compile(r"(?:.*/)?(?:python[\d.]*|node|bash|sh|npm|pnpm|yarn|bun|deno|tsx|ts-node|vitest|jest|mocha|ava|pytest|py\.test|playwright)|\./.*")
_PREFIX_WORDS = {"npx", "env", "exec", "sudo", "time", "command", "nohup", "xvfb-run", "then", "do", "else", "elif", "if", "while", "until", "!", "{", "}"}
_JS_EXT = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
_JS_RUNNERS = {"vitest", "jest", "mocha", "ava"}
_NODE_TEST_NAME = re.compile(r"(\.test|-test|_test)\.[cm]?[jt]sx?$|^test[-.][^/]*$")
_FLAG_WITH_VALUE = {"-k", "-m", "-c", "-p", "-n", "--tb", "--maxfail", "--rootdir", "--junitxml", "--config", "--project", "-r", "--reporter",
                    "--environment", "--pool", "--shard", "--root", "--dir", "-t", "--testNamePattern", "--maxWorkers", "--workers", "--outputFile"}


def _norm(p):
    r = os.path.normpath(p or ".")
    return "" if r == "." else r


def _join(cwd, t):
    return _norm(os.path.join(cwd or ".", t))


def _under(path, d):
    d = _norm(d)
    return d == "" or path.startswith(d + "/")


def _glob_re(g):
    out, i = "", 0
    while i < len(g):
        if g.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif g.startswith("**", i):
            out += ".*"; i += 2
        elif g[i] == "*":
            out += "[^/]*"; i += 1
        elif g[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(g[i]); i += 1
    return re.compile(out + r"\Z")


def _strip_comments(text):
    return re.sub(r"(?m)(^|\s)#.*$", r"\1", text)


def _split_commands(line):
    """The commands of one shell line, cut at `&&`, `||`, `;` and `|` that sit outside quotes (`echo "x; pytest tests"` is one
    command, an `echo`). An unbalanced quote keeps the rest of the line in one command."""
    out, cur, quote, i = [], "", None, 0
    while i < len(line):
        c = line[i]
        if c == "\\" and quote != "'" and i + 1 < len(line):
            cur += line[i:i + 2]
            i += 2
            continue
        if quote:
            quote = None if c == quote else quote
        elif c in "'\"":
            quote = c
        elif c in ";|" or line.startswith("&&", i):
            i += 2 if line[i:i + 2] in ("&&", "||") else 1
            out.append(cur)
            cur = ""
            continue
        cur += c
        i += 1
    return out + [cur]


def _segments(text):
    """(cwd, tokens) for every command segment of a carrier text, with `cd X &&` and `working-directory:` applied. A `cd` inside
    `( … )` ends with the parenthesis; a `cd` to `$VAR`, `/…` or `~…` leaves the directory unknown (""); a `cd` carries on to the lines after it."""
    for step in re.split(r"(?m)^\s*-\s", text):
        wd = re.search(r"(?m)^\s*working-directory:\s*(\S+)", step)
        cwd = _norm(wd.group(1).strip("'\"")) if wd else ""
        joined = re.sub(r"\\\n", " ", step)
        for line in joined.split("\n"):
            line = re.sub(r"^\s*run:\s*[|>]?[-+]?\s*", "", line)
            saved = []                                    # the directory before each `(` that is still open on this line
            for seg in _split_commands(line):
                saved += [cwd] * len(re.match(r"\s*(?:\(\s*)*", seg).group(0).replace(" ", ""))
                seg = re.sub(r"\d*>&(?:\d+|-)", " ", seg)                      # 2>&1
                seg = re.sub(r"(?:\d*>>?|&>>?|\d*<)\s*[^\s;|&]+", " ", seg)     # > log, >> log, &> log, < file
                toks = re.findall(r"[^\s'\"`()]+", seg)
                if toks[:1] == ["cd"] and len(toks) > 1:
                    cwd = "" if toks[1][0] in "$/~" else _join(cwd, toks[1])
                elif toks:
                    yield cwd, toks
                for _ in range(min(len(saved), len(re.search(r"(?:\)\s*)*$", seg).group(0).replace(" ", "")))):
                    cwd = saved.pop()
            if saved:
                cwd = saved[0]


def _head(toks):
    """Index of the command a segment starts: past `NAME=value`, `npx`/`env`/`sudo`…, `npm exec`; None for a YAML key (`name: Run vitest`)."""
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.endswith(":"):
            return None
        j = ci_lint.skip_wrappers(toks, i)          # `timeout 600 npx vitest run`
        if j != i:
            i = j
            continue
        if re.match(r"^[A-Za-z_]\w*=", t) or t in _PREFIX_WORDS or (t in ("npm", "pnpm", "yarn") and toks[i + 1:i + 2] in (["exec"], ["dlx"])):
            i += 2 if t in ("npm", "pnpm", "yarn") else 1
            continue
        return i
    return None


def _flags_skipped(toks):
    """Positional tokens: no flags, no values of the flags that take one."""
    out, skip = [], False
    for t in toks:
        if skip:
            skip = False
        elif t in _FLAG_WITH_VALUE:
            skip = True
        elif not t.startswith("-"):
            out.append(t)
    return out


def _unwrapped(toks):
    """`uv run X`, `poetry run X` start X; `coverage run …` is `python …` under coverage."""
    j = 0
    while j < len(toks) and re.match(r"^[A-Za-z_]\w*=", toks[j]):
        j += 1
    if toks[j:j + 2] in (["uv", "run"], ["poetry", "run"]):
        return toks[:j] + toks[j + 2:]
    if toks[j:j + 2] == ["coverage", "run"]:
        return toks[:j] + ["python3"] + toks[j + 2:]
    return toks


def _segment_wires(path, cwd, toks):
    toks = _unwrapped(toks)
    head = _head(toks)
    if head is None or not _RUN_HEAD.fullmatch(toks[head]):
        return False
    base = os.path.basename(path)
    if "unittest" in toks and "discover" in toks:
        start, pat = ".", "test*.py"
        rest = toks[toks.index("discover") + 1:]
        for k, t in enumerate(rest):
            if t in ("-s", "--start-directory") and k + 1 < len(rest):
                start = rest[k + 1]
            elif t in ("-p", "--pattern") and k + 1 < len(rest):
                pat = rest[k + 1]
        positional = [t for k, t in enumerate(rest) if not t.startswith("-") and (k == 0 or rest[k - 1] not in ("-s", "-p", "-t", "--start-directory", "--pattern", "--top-level-directory"))]
        if positional and "-s" not in rest and "--start-directory" not in rest:
            start = positional[0]
            if len(positional) > 1 and "-p" not in rest and "--pattern" not in rest:
                pat = positional[1]
        return path.endswith(".py") and _under(path, _join(cwd, start)) and fnmatch.fnmatchcase(base, pat)
    if "unittest" in toks and path.endswith(".py"):
        # no `discover`: bare `unittest` discovers from the working directory; `unittest a.b.test_x[.Class.method]` names modules
        args = _flags_skipped(toks[toks.index("unittest") + 1:])
        if not args:
            return _under(path, cwd) and fnmatch.fnmatchcase(base, "test*.py")
        for a in args:
            parts = a.split(".")
            if any(_join(cwd, "/".join(parts[:n])) + ".py" == path for n in range(len(parts), 0, -1)):
                return True
        return False
    for k, t in enumerate(toks):
        t = t.strip()
        if not t or t.startswith("-"):
            continue
        if re.search(r"[*?\[]", t):
            if not re.search(r"[A-Za-z0-9]", re.sub(r"[*?\[\]]", "", t)):
                continue                      # `*)` of a case branch, `*`: nothing literal to match
            if "/" in t:
                if _glob_re(_join(cwd, t)).match(path):
                    return True
            elif fnmatch.fnmatchcase(base, t) and _under(path, cwd):
                return True
        elif "." in os.path.basename(t) or "/" in t:
            if path == _join(cwd, t) if cwd else (path == _norm(t) or path.endswith("/" + _norm(t))):
                return True        # after a `cd` / `working-directory` only the joined path; with no known cwd a suffix may be the same file
    # the runner is the command itself: `python -m pytest`, `yarn vitest`, `npx vitest` — a runner NAME elsewhere in the segment
    # (`pip install pytest`, `npm install -D vitest`) starts nothing
    k0 = head
    if re.fullmatch(r"(?:.*/)?python[\d.]*", toks[head]):
        m = next((k for k in range(head + 1, len(toks)) if toks[k] == "-m"), None)
        if m is not None and all(t.startswith("-") for t in toks[head + 1:m]):
            k0 = m + 1
    elif toks[head] in ("pnpm", "yarn", "bun"):
        k0 = head + 1
        while k0 < len(toks):                  # `pnpm --filter web vitest run`, `yarn workspace web vitest run`: which package, not what runs
            if toks[k0] in ("--filter", "-F", "-C", "--dir", "workspace"):
                k0 += 2
            elif re.match(r"--(?:filter|dir)=", toks[k0]):
                k0 += 1
            else:
                break
    at = toks[k0] if k0 < len(toks) else ""
    if path.endswith(".py"):
        runner = k0 if at in ("pytest", "py.test") else None
        if runner is not None:
            args = [a.split("::")[0] for a in _flags_skipped(toks[runner + 1:])]
            return any(path == _join(cwd, a) or _under(path, _join(cwd, a)) for a in args) if args else _under(path, cwd)
        return False
    js = k0 if (at in _JS_RUNNERS or (at == "playwright" and toks[k0 + 1:k0 + 2] == ["test"])) else None
    node_test = any(toks[k] == "node" and "--test" in toks[k + 1:k + 3] for k in range(len(toks)))
    if (js is not None or node_test) and path.endswith(_JS_EXT):
        start = js if js is not None else toks.index("--test")
        args = [a for a in _flags_skipped(toks[start + 1:]) if a not in ("run", "watch", "test", "related", "--test")]
        if args:
            return any(a in path and not re.search(r"[*?\[]", a) for a in args)   # a vitest/jest filter is a substring
        if not _under(path, cwd):
            return False
        return bool(_NODE_TEST_NAME.search(base) or "/test/" in "/" + path) if node_test and js is None else True
    return False


def is_wired(path, carriers):
    """Is the test file at `path` run by a command of the carriers (workflow / action / package.json texts or (name, text) pairs)?"""
    for c in carriers:
        name, text = c if isinstance(c, tuple) else ("x.yml", c)
        if name.endswith("package.json"):
            pkg_dir = _norm(os.path.dirname(name))
            try:
                scripts = (json.loads(text) or {}).get("scripts") or {}
                text = "\n".join(f"- {v}" for v in scripts.values() if isinstance(v, str))
            except ValueError:
                pass                          # not JSON: read it as plain command lines
            base_dir = pkg_dir
        else:
            base_dir = ""
        for cwd, toks in _segments(_strip_comments(text)):
            if _segment_wires(path, _join(base_dir, cwd) if base_dir else cwd, toks):
                return True
    return False


def wiring_texts(src, test_paths):
    carriers = []
    files = set(src.list_dir(".github/workflows")) | set(src.list_dir(".github/actions"))
    for d in sorted(src.list_subdirs(".github/actions")):
        files |= set(src.list_dir(d))
    for p in sorted(files):
        if re.search(r"\.ya?ml$", p):
            t = src.read(p)
            if t:
                carriers.append((p, t))
    dirs = {""}
    for p in test_paths:
        parts = p.split("/")[:-1]
        for i in range(len(parts) + 1):
            dirs.add("/".join(parts[:i]))
    for d in sorted(dirs):
        name = (d + "/" if d else "") + "package.json"
        t = src.read(name)
        if t:
            carriers.append((name, t))
    return carriers


def check_test_wiring(src, files):
    new = [f["path"] for f in files if f["status"] in ("added", "renamed", "copied") and TEST_FILE_RE.search(f["path"])
           and not re.search(r"(^|/)(node_modules|fixtures|__snapshots__)/", f["path"])]
    if not new:
        return []
    texts = wiring_texts(src, new)
    bad = [p for p in new if not is_wired(p, texts)]
    return [Finding("test-wiring", f"{len(bad)} new test file(s) that no workflow or package.json runs — a test outside CI is not a gate (pitfalls 7)", bad)] if bad else []


# ---------------------------------------------------------------------------------------------------------------
# ci-lint

def patch_edits(patch):
    """[(line, removed, text)] of a unified diff: an added line with its number in the new file, a removed line with the number
    of the new-file line that follows it. A hunk header `+N,0` (a `-U0` hunk that only removes) names the line BEFORE the removal."""
    out, n = [], 0
    for l in (patch or "").split("\n"):
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", l)
        if m:
            n = int(m.group(1)) - (0 if m.group(2) == "0" else 1)
        elif l.startswith("+"):
            n += 1
            out.append((n, False, l[1:]))
        elif l.startswith("-"):
            out.append((n + 1, True, l[1:]))
        elif l.startswith(" "):
            n += 1
    return out


def added_lines(patch):
    """Line numbers (new side) a unified-diff `patch` adds; None when there is no patch to read."""
    if not patch:
        return None
    return {n for n, removed, _ in patch_edits(patch) if not removed}


def check_ci_lint(src):
    """ci_lint over the changed workflows and scripts; in a modified file only the findings on lines the PR added (a PR is not
    blamed for what the file already had). Fixture and vendored directories are skipped: a fixture is a deliberate violation."""
    out = []
    for f in src.files():
        p = f["path"]
        if f["status"] == "removed" or not (re.match(r"^\.github/workflows/[^/]+\.ya?ml$", p) or p.endswith(".sh")):
            continue
        if re.search(r"(^|/)(fixtures|node_modules)/", p):
            continue
        text = src.read(p)
        if text is None:
            continue
        if f["status"] == "renamed" and not f.get("patch"):
            continue                          # a pure rename adds no line: nothing to blame
        if f["status"] != "added" and not f.get("patch"):
            # very large diffs and mode-only changes come without a patch: blaming the PR for every old finding of the file would be wrong
            out.append(Finding("ci-lint", f"{p}: patch not available, the file was not checked"))
            continue
        added = added_lines(f.get("patch")) if f["status"] != "added" else None
        found = ci_lint.lint(p, text)
        if added is not None:
            # a `permissions` / `timeout` finding stands on the `gh` call or the job header, which the PR did not touch when it
            # only edited the `permissions:` block or removed `timeout-minutes:`: it is still this PR's 403
            scoped = ci_lint.edit_scopes(text, patch_edits(f.get("patch"))) if p.endswith((".yml", ".yaml")) else {}
            jobs = ci_lint.parse_workflow(p, text) if scoped else []
            by_job = lambda x: next((j.id for j in jobs if j.line <= x.line <= j.end), None)
            found = [x for x in found if x.line in added or x.check in scoped.get(by_job(x), ())]
        if found:
            out.append(Finding("ci-lint", f"{p}: {len(found)} finding(s)", [str(x) for x in found]))
    return out


# ---------------------------------------------------------------------------------------------------------------

def run_checks(src, only=None, body=None, include_resolved=False):
    """-> (findings, skipped) where skipped is [(check, reason)]."""
    findings, skipped = [], []
    fns = {
        "closes": lambda: check_closes(src, body),
        "bot-threads": lambda: check_bot_threads(src, include_resolved),
        "plugin-version": lambda: check_plugin_version(src.files()),
        "pyc": lambda: check_no_pyc(src.files(), src.tracked()),
        "test-wiring": lambda: check_test_wiring(src, src.files()),
        "ci-lint": lambda: check_ci_lint(src),
    }
    for name in ALL:
        if only is not None and name not in only:
            continue
        try:
            findings += fns[name]()
        except Skipped as e:
            skipped.append((name, str(e)))
        except Exception as e:  # noqa: BLE001 - a crash of one check (a timeout, a missing gh, an unexpected reply) must not
            # take the others' findings with it (authoring-pitfalls 6): it is a skipped check, never a pass and never a traceback
            skipped.append((name, f"{type(e).__name__}: {str(e)[:200]}"))
    return findings, skipped


def render(findings, skipped):
    if not findings and not skipped:
        return "PR checks: nothing found."
    lines = []
    for f in findings:
        lines.append(f"[{f.check}] {f.message}")
        lines += [f"  - {d}" for d in f.details]
    lines += [f"[{name}] skipped: {why}" for name, why in skipped]
    return "\n".join(lines)


def main(argv=None, gh=run_gh):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo")
    ap.add_argument("--pr", type=int)
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--base")
    ap.add_argument("--only", help="comma-separated: " + ", ".join(ALL) + ", hygiene")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--body-file")
    ap.add_argument("--include-resolved", action="store_true")
    a = ap.parse_args(argv)
    only = set()
    for n in (a.only.split(",") if a.only else []):
        only |= set(GROUPS.get(n, (n,)))
    only = only or None
    if only and not only <= set(ALL):
        print(f"unknown check in --only: {sorted(only - set(ALL))}", file=sys.stderr)
        return 2
    if a.local:
        base = a.base
        if not base:
            r = subprocess.run(["git", "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"], capture_output=True, text=True)
            base = r.stdout.strip()
        if not base:
            print("no --base and no origin/HEAD", file=sys.stderr)
            return 2
        src = Local(base, a.repo, a.pr, gh)
    elif a.repo and a.pr:
        src = Remote(a.repo, a.pr, gh)
    else:
        print("give --repo and --pr, or --local", file=sys.stderr)
        return 2
    body = open(a.body_file, encoding="utf-8").read() if a.body_file else None
    if a.local and not (a.repo and a.pr):
        only = (only or set(ALL)) - {"bot-threads"} - ({"closes"} if body is None else set())
        if not only:
            print("--local without --repo/--pr cannot run bot-threads, and closes needs --body-file: give --repo and --pr", file=sys.stderr)
            return 2
    findings, skipped = run_checks(src, only, body, a.include_resolved)
    print(render(findings, skipped))
    if a.report:
        return 0
    return 1 if findings else (2 if skipped else 0)


if __name__ == "__main__":
    sys.exit(main())
