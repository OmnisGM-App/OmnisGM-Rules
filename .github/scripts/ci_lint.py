#!/usr/bin/env python3
"""ci-lint: mechanical checks for `.github/workflows/*.yml` and shell scripts (claude-plugins#57).

Every check is a function with a positive and a negative fixture (fixtures/ci_lint/<check>.{pos,neg}.{yml,sh},
run by test_ci_lint.py). No YAML library: workflows are read line by line (jobs at indent 2, job keys at indent 4,
`run:` blocks by indentation), which is how every workflow of the repos is laid out.

Checks (each hit is `path:line: [check] message`):
  permissions  a `gh` call whose API scope the job's `permissions:` block does not grant (authoring-workflows.md 5)
  timeout      a job without `timeout-minutes`
  list-limit   `gh pr|run|issue list` without `--limit`/`-L` (the default is 30 rows, silently)
  paginate     `gh api --paginate` with an aggregating `--jq` (it runs once per page), or `--slurp` with `--jq` (gh refuses)
  fallback     `x=$(cmd) || x=value` with a value a real result can also have (empty, 0, none, pending…): "the call failed"
               becomes "nothing yet" (authoring-pitfalls.md 6); a distinct sentinel (ERR, 000) passes; allow with `# fallback-ok: <why>`

Usage: ci_lint.py FILE...   (exit 1 when there are findings)
"""
import re
import shlex
import sys
from typing import List, NamedTuple, Optional


class Finding(NamedTuple):
    path: str
    line: int
    check: str
    message: str

    def __str__(self):
        return f"{self.path}:{self.line}: [{self.check}] {self.message}"


class Unit(NamedTuple):
    """A piece of shell: one `run:` block or a whole `.sh` file."""
    path: str
    line: int            # file line of the first script line
    text: str
    custom_token: bool   # GH_TOKEN/GITHUB_TOKEN comes from a secret: the job's permissions do not apply
    job: Optional[str]
    perms: Optional[dict]  # effective permissions of the job; None = no block anywhere (repo default, unknown)


class Job(NamedTuple):
    id: str
    line: int
    has_timeout: bool
    is_call: bool        # `uses:` — a reusable workflow call takes no timeout-minutes
    units: list
    end: int = 0         # last file line of the job (1-based, inclusive)


# ---------------------------------------------------------------------------------------------------------------
# parsing

def _indent(s):
    return len(s) - len(s.lstrip(" "))


def _blank(s):
    t = s.strip()
    return not t or t.startswith("#")


def parse_perms(lines, start, key_indent):
    """`permissions:` at lines[start]; returns (dict | 'read-all' | 'write-all' | {} , next index)."""
    head = lines[start].split("permissions:", 1)[1].strip()
    if head and not head.startswith("#"):
        v = head.split("#")[0].strip()
        if v in ("read-all", "write-all"):
            return v, start + 1
        if v == "{}":
            return {}, start + 1
        return {}, start + 1
    out, i = {}, start + 1
    while i < len(lines) and (_blank(lines[i]) or _indent(lines[i]) > key_indent):
        m = re.match(r"\s+([\w-]+):\s*(read|write|none)\b", lines[i])
        if m:
            out[m.group(1)] = m.group(2)
        i += 1
    return out, i


def run_blocks(lines, lo, hi):
    """Yield (first_line_number_1based, text) for each `run:` in lines[lo:hi]."""
    i = lo
    while i < hi:
        m = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key_col = len(m.group(1)) + (2 if re.match(r"^\s*-\s+run:", lines[i]) else 0)
        val = m.group(2).rstrip()
        if val[:1] in ("|", ">"):
            j, body = i + 1, []
            while j < hi and (not lines[j].strip() or _indent(lines[j]) > key_col):
                body.append(lines[j])
                j += 1
            yield i + 2, "\n".join(body)
            i = j
        else:
            yield i + 1, val.strip("'\"")
            i += 1


_TOKEN_ASSIGN = re.compile(r"(?<![A-Za-z0-9_])(?:GH_TOKEN|GITHUB_TOKEN)\s*[:=]\s*(.+)")


def _secret_token(text):
    """Does the text give `GH_TOKEN`/`GITHUB_TOKEN` a credential of its own (another secret, not the job's)? `secrets.GITHUB_TOKEN`
    is the job's token, and `secrets.X || github.token` falls back to it: both stay under the job's `permissions:`.
    None when the text sets no token at all (the level does not decide)."""
    found = False
    for m in _TOKEN_ASSIGN.finditer(text):
        found = True
        v = m.group(1)
        if re.search(r"\bgithub\.token\b", v):
            continue
        names = re.findall(r"\bsecrets\.(\w+)", v)
        if not names or any(name != "GITHUB_TOKEN" for name in names):
            return True
    return False if found else None


def _own_credential(*levels):
    """The innermost level that sets a token decides (the step's `env:` over the job's over the workflow's): a `github.token` in the
    job's `env:` overrides a secret at the top. A one-shot `GH_TOKEN=… gh …` prefix is the call's own business (`_own_token`)."""
    for text in levels:
        r = _secret_token(text)
        if r is not None:
            return r
    return False


def _step_env(step):
    """The text of the step's own `env:` block (its key sits where the step's first key does, past the list dash)."""
    lines = step.split("\n")
    lines[0] = re.sub(r"^(\s*)-\s", lambda m: m.group(1) + "  ", lines[0])
    out = ""
    for k, l in enumerate(lines):
        m = re.match(r"^ {8}env:\s*(.*)$", l)
        if not m:
            continue
        out += m.group(1) + "\n"
        for x in lines[k + 1:]:
            if not _blank(x) and _indent(x) <= 8:
                break
            out += x + "\n"
        break
    return out


def parse_workflow(path, text) -> List[Job]:
    lines = text.split("\n")
    top_perms = None
    top_env = ""
    jobs_at = None
    for i, l in enumerate(lines):
        if re.match(r"^permissions:", l):
            top_perms, _ = parse_perms(lines, i, 0)
        elif re.match(r"^env:\s*(#.*)?$", l):
            j = i + 1
            while j < len(lines) and (_blank(lines[j]) or _indent(lines[j]) > 0):
                top_env += lines[j] + "\n"
                j += 1
        elif re.match(r"^jobs:\s*$", l):
            jobs_at = i
    if jobs_at is None:
        return []
    jobs_end = next((i for i in range(jobs_at + 1, len(lines)) if lines[i] and not lines[i][0].isspace() and not lines[i].startswith("#")), len(lines))
    starts = [i for i in range(jobs_at + 1, jobs_end) if re.match(r"^  [\w-]+:\s*(#.*)?$", lines[i])]
    ends = starts[1:] + [jobs_end]
    jobs = []
    for s, e in zip(starts, ends):
        seg = lines[s:e]
        jid = re.match(r"^  ([\w-]+):", lines[s]).group(1)
        perms = top_perms
        has_timeout, is_call = False, False
        job_env = ""
        k = 1
        while k < len(seg):
            l = seg[k]
            if _indent(l) == 4 and not _blank(l):
                if l.strip().startswith("permissions:"):
                    perms, k = parse_perms(seg, k, 4)
                    continue
                if l.strip().startswith("timeout-minutes:"):
                    has_timeout = True
                if l.strip().startswith("uses:"):
                    is_call = True
                if l.strip().startswith("env:"):
                    j = k + 1
                    while j < len(seg) and (_blank(seg[j]) or _indent(seg[j]) > 4):
                        job_env += seg[j] + "\n"
                        j += 1
            k += 1
        # steps: split by the list dash of `steps:` so a step's own env is found
        step_at = [i for i, l in enumerate(seg) if re.match(r"^\s{6}-\s", l)]
        bounds = list(zip(step_at, step_at[1:] + [len(seg)]))
        units = []
        for a, b in bounds:
            step = "\n".join(seg[a:b])
            custom = _own_credential(_step_env(step), job_env, top_env)
            for ln, body in run_blocks(seg, a, b):
                units.append(Unit(path, s + ln, body, custom, jid, perms))
        jobs.append(Job(jid, s + 1, has_timeout, is_call, units, e))
    return jobs


PERM_HEAD = re.compile(r"^\s*permissions:")
TIMEOUT_LINE = re.compile(r"^\s*timeout-minutes:")
TOKEN_LINE = re.compile(r"^\s*(?:export\s+)?(?:GH_TOKEN|GITHUB_TOKEN)\s*[:=]")


def token_line(t):
    """Does the line set the token for what runs after it (`GH_TOKEN: …`, `GH_TOKEN=…`, `export GH_TOKEN=…`)? A line where a command
    follows the assignment (`GH_TOKEN=$APP gh pr comment …`) sets it for that one call only."""
    if not TOKEN_LINE.match(t):
        return False
    m = re.match(r"^\s*(?:export\s+)?(?:GH_TOKEN|GITHUB_TOKEN)=(.*)$", t)
    if not m:
        return True
    try:
        rest = shlex.split(re.sub(r"\$\{\{.*?\}\}", "X", _strip_comment(m.group(1))))
    except ValueError:
        return True
    return len(rest) <= 1


def _perm_blocks(text):
    """[(first line, last line, job id | None for the workflow's block)] of every `permissions:` block, 1-based."""
    lines = text.split("\n")
    jobs = parse_workflow("", text)
    out = []
    for i, l in enumerate(lines):
        indent = 0 if re.match(r"^permissions:", l) else 4 if re.match(r"^    permissions:", l) else None
        if indent is None:
            continue
        _, nxt = parse_perms(lines, i, indent)
        job = next((j.id for j in jobs if j.line <= i + 1 <= j.end), None) if indent else None
        out.append((i + 1, nxt, job))
    return out


def edit_scopes(text, edits):
    """{job id: {"permissions" | "timeout"}}: the findings an edit of the file caused although the finding's own line is untouched.
    A change inside a `permissions:` block (a line of the block that was removed or added: a line after the block is not one) moves
    the grants of its job (of every job without a block of its own for the workflow's block), a changed token line moves which token
    the call runs under: both `permissions`. A removed `timeout-minutes:` leaves its job without: `timeout`.
    `edits` = [(line, removed, text)]: for an added line its number in the new file, for a removed one the number of the new-file
    line that follows the removal."""
    jobs = parse_workflow("", text)
    if not jobs:
        return {}
    first = min(j.line for j in jobs)
    blocks = _perm_blocks(text)
    every = {j.id for j in jobs}
    inherit = every - {b[2] for b in blocks if b[2]}      # a job with a block of its own does not read the workflow's
    out = {}

    def blame(ids, kind):
        for i in ids:
            out.setdefault(i, set()).add(kind)

    prev, left = None, False
    for pos, removed, t in edits:
        ref = pos - 1 if removed else pos      # a line that is still in the file, inside the same block
        in_job = {j.id for j in jobs if j.line <= ref <= j.end}
        block = next((b for b in blocks if b[0] <= ref <= b[1]), None)
        if not (removed and prev == pos):
            left = False                       # removed lines of one place come in a run: after a line outside the block the rest is outside too
        prev = pos if removed else None
        belongs = False
        if block:
            if removed:
                key = 0 if block[2] is None else 4
                if t.strip() and not (PERM_HEAD.match(t) or _indent(t) > key):
                    left = True
                belongs = not left and bool(t.strip())
            else:
                belongs = not _blank(t)
        if belongs:                            # a removal at the block's end still has `ref` in it
            blame(inherit if block[2] is None else {block[2]}, "permissions")
        elif removed and PERM_HEAD.match(t):   # the whole block, header included, was removed: the job has the workflow's grants now
            blame(inherit if ref < first else in_job, "permissions")
        elif token_line(t):
            blame(every if ref < first else in_job, "permissions")
        elif removed and TIMEOUT_LINE.match(t):
            blame(in_job, "timeout")
    return out


# ---------------------------------------------------------------------------------------------------------------
# shell helpers

def logical_lines(text, first_line):
    """(line_number, joined text) for each logical line: a trailing `\\`, `||`, `&&` or `|` joins the next line. Comment-only
    lines are dropped; the comment tail of a code line is kept (checks look at `# fallback-ok:`)."""
    raw = text.split("\n")
    out, i = [], 0
    while i < len(raw):
        l = raw[i]
        if not l.strip() or l.strip().startswith("#"):
            i += 1
            continue
        start, cur = i, l
        while True:
            code = re.sub(r"\s+#.*$", "", cur).rstrip()
            if code.endswith("\\"):
                cur = code[:-1] + " "
            elif re.search(r"(\|\||&&|(?<!\|)\|)$", code):
                cur = code + " "
            else:
                break
            i += 1
            if i >= len(raw):
                break
            cur += raw[i].strip()
        out.append((first_line + start, cur))
        i += 1
    return out


def _strip_comment(line):
    """The line without its trailing comment: the first `#` outside quotes that follows whitespace (or starts the line)."""
    quote, i = None, 0
    while i < len(line):
        c = line[i]
        if c == "\\" and quote != "'":
            i += 2
            continue
        if quote:
            quote = None if c == quote else quote
        elif c in "'\"":
            quote = c
        elif c == "#" and (i == 0 or line[i - 1].isspace()):
            return line[:i]
        i += 1
    return line


def commands(line):
    """Split a logical line into commands (token lists) at | || && ; ( ) — quotes respected; on an unbalanced quote
    the whole line is one command split on whitespace. A trailing comment is not shell."""
    line = _strip_comment(line)
    try:
        lx = shlex.shlex(line, posix=True, punctuation_chars="|&;()")
        lx.whitespace_split = True
        lx.commenters = ""
        toks = list(lx)
    except ValueError:
        toks = line.split()
        return [toks]
    cmds, cur = [], []
    for t in toks:
        if t and set(t) <= set("|&;()"):
            if cur:
                cmds.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        cmds.append(cur)
    # a substitution inside double quotes is ONE token (`n="$(gh pr list …)"`): its inside is a command line of its own;
    # inside single quotes `$(…)` is text and is never looked at
    for inner in _quoted_substitutions(line):
        cmds += commands(inner)
    return cmds


def _quoted_substitutions(line):
    """The text inside each balanced `$( … )` that sits in double quotes of a raw line (single-quoted ones are literals)."""
    out, quote, i = [], None, 0
    while i < len(line):
        c = line[i]
        if quote == "'":
            quote = None if c == "'" else quote
        elif c == "\\" and i + 1 < len(line):
            i += 1
        elif c in "'\"" and quote in (None, c):
            quote = None if quote else c
        elif c == "$" and line.startswith("$(", i) and quote == '"':
            depth, j = 0, i + 1
            while j < len(line):
                depth += {"(": 1, ")": -1}.get(line[j], 0)
                if depth == 0:
                    break
                j += 1
            out.append(line[i + 2:j])
            i = j
        i += 1
    return out


_SKIP = {"env", "command", "exec", "time", "if", "then", "elif", "else", "while", "until", "do", "!", "{", "}", "sudo"}


_WRAPPERS = {"timeout": ("-k", "-s", "--kill-after", "--signal"), "nice": ("-n", "--adjustment"), "stdbuf": ("-i", "-o", "-e", "--input", "--output", "--error")}


def skip_wrappers(toks, i):
    """Index past `timeout [options] DURATION`, `nice [-n N]` and `stdbuf [-oL …]` at toks[i] (the wrapped command follows);
    i itself when toks[i] is none of them. Shared with run_pr_checks._head."""
    while i < len(toks) and toks[i] in _WRAPPERS:
        w = toks[i]
        i += 1
        while i < len(toks) and toks[i].startswith("-") and toks[i] != "--":
            takes_value = toks[i] in _WRAPPERS[w]
            i += 2 if takes_value else 1
        if w == "timeout":
            i += 1                      # the duration
    return i


def gh_command(toks):
    """If the command is a `gh` call, return its tokens after `gh`, else None."""
    i = 0
    while i < len(toks):
        j = skip_wrappers(toks, i)
        if j != i:
            i = j
        elif toks[i] in _SKIP or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[i]):
            i += 1
        else:
            break
    # `gh`, a path to it, or the variable a workflow keeps it in (`"$GH_BIN" pr list`, `${GH}`)
    if i < len(toks) and (toks[i] == "gh" or toks[i].endswith("/gh") or re.fullmatch(r"\$\{?GH(?:_BIN)?\}?", toks[i])):
        return toks[i + 1:]
    return None


# ---------------------------------------------------------------------------------------------------------------
# permissions

LEVEL = {"none": 0, "read": 1, "write": 2}


def _api_info(args):
    """(path, mutating) of a `gh api` call; path is None for graphql or a fully dynamic path."""
    path, method, has_field = None, None, False
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-X", "--method") and i + 1 < len(args):
            method = args[i + 1].upper()
            i += 2
            continue
        if a.startswith("--method="):
            method = a.split("=", 1)[1].upper()
        elif a in ("-f", "-F", "--field", "--raw-field", "--input"):
            has_field = True
            i += 2
            continue
        elif a in ("--jq", "-q", "-H", "--header", "--hostname", "-t", "--template", "--cache", "--preview", "-p"):
            i += 2
            continue
        elif a.startswith("-"):
            i += 1
            continue
        elif path is None:
            path = a
        i += 1
    mutating = method in ("POST", "PUT", "PATCH", "DELETE") or (method is None and has_field)
    if path in (None, "graphql") or re.fullmatch(r"\$\{?\w+\}?", path or ""):
        path = None
    return path, mutating


def needs_of(args):
    """List of requirement alternatives for a `gh` call: each is a list of (scope, level) any of which is enough, or
    None when the call needs nothing the block can lack."""
    if not args:
        return []
    top = args[0]
    sub = args[1] if len(args) > 1 else ""
    n = []
    if top == "run":
        n.append(([("actions", "write" if sub in ("rerun", "cancel", "delete") else "read")], f"gh run {sub}"))
    elif top == "workflow":
        n.append(([("actions", "write" if sub in ("run", "enable", "disable") else "read")], f"gh workflow {sub}"))
    elif top == "pr":
        if sub in ("view", "list", "diff", "checks", "status"):
            n.append(([("pull-requests", "read")], f"gh pr {sub}"))
        elif sub in ("comment", "edit"):
            n.append(([("pull-requests", "write"), ("issues", "write")], f"gh pr {sub}"))
        elif sub == "merge":   # PUT /pulls/{n}/merge also writes the base branch
            n.append(([("pull-requests", "write")], "gh pr merge"))
            n.append(([("contents", "write")], "gh pr merge"))
        elif sub in ("close", "reopen", "ready", "review", "create", "update-branch"):
            n.append(([("pull-requests", "write")], f"gh pr {sub}"))
    elif top == "issue":
        if sub in ("view", "list", "status"):
            n.append(([("issues", "read")], f"gh issue {sub}"))
        elif sub == "comment":
            n.append(([("issues", "write"), ("pull-requests", "write")], "gh issue comment"))
        elif sub in ("create", "edit", "close", "reopen", "delete", "lock", "unlock", "transfer", "pin", "unpin"):
            n.append(([("issues", "write")], f"gh issue {sub}"))
    elif top == "label" and sub in ("create", "edit", "delete", "clone"):
        n.append(([("issues", "write"), ("pull-requests", "write")], f"gh label {sub}"))
    elif top == "release" and sub in ("create", "edit", "delete", "upload"):
        n.append(([("contents", "write")], f"gh release {sub}"))
    elif top == "api":
        path, mut = _api_info(args[1:])
        if path:
            p = "/" + path.lstrip("/")
            w = "write" if mut else "read"
            if re.search(r"/actions/", p):
                n.append(([("actions", w)], f"gh api {path}"))
            if re.search(r"/(check-runs|check-suites)\b", p):
                n.append(([("checks", w)], f"gh api {path}"))
            if re.search(r"/commits/[^/]+/status(es)?\b|/statuses/", p):
                n.append(([("statuses", w)], f"gh api {path}"))
            if re.search(r"/pulls(/|$|\?)", p):
                n.append(([("pull-requests", w)], f"gh api {path}"))
            elif re.search(r"/(issues|labels)(/|$|\?)", p):
                alt = [("issues", w), ("pull-requests", w)] if w == "write" else [("issues", "read"), ("pull-requests", "read")]
                n.append((alt, f"gh api {path}"))
            if mut and re.search(r"/(contents|git/refs|git/commits|git/trees)(/|$)", p):
                n.append(([("contents", "write")], f"gh api {path}"))
    return n


def _own_token(toks):
    """`GH_TOKEN=… gh …`: the call carries its own credentials, the job's permissions do not apply to it."""
    for t in toks:
        if re.match(r"^(?:GH|GITHUB)_TOKEN=", t):
            return True
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t) and t not in _SKIP:
            return False
    return False


def check_permissions(unit: Unit) -> List[Finding]:
    out = []
    if unit.perms is None or unit.custom_token:
        return out
    perms = unit.perms
    for ln, line in logical_lines(unit.text, unit.line):
        for toks in commands(line):
            args = gh_command(toks)
            if args is None or _own_token(toks):
                continue
            for alts, what in needs_of(args):
                if perms == "write-all":
                    continue
                if perms == "read-all":
                    granted = lambda s, lv: lv == "read"
                else:
                    granted = lambda s, lv, p=perms: LEVEL[p.get(s, "none")] >= LEVEL[lv]
                if not any(granted(s, lv) for s, lv in alts):
                    want = " or ".join(f"{s}: {lv}" for s, lv in alts)
                    have = perms if isinstance(perms, str) else (", ".join(f"{k}: {v}" for k, v in perms.items()) or "none")
                    out.append(Finding(unit.path, ln, "permissions",
                                       f"`{what}` needs `{want}`, the job's permissions block has: {have} (a 403 on the first real run)"))
    return out


# ---------------------------------------------------------------------------------------------------------------
# the other script checks

def check_list_limit(unit: Unit) -> List[Finding]:
    out = []
    for ln, line in logical_lines(unit.text, unit.line):
        for toks in commands(line):
            args = gh_command(toks)
            if args and len(args) > 1 and args[0] in ("pr", "run", "issue") and args[1] == "list":
                if not any(re.fullmatch(r"--limit(=.*)?|-L\d*", t) for t in args):
                    out.append(Finding(unit.path, ln, "list-limit", f"`gh {args[0]} list` without --limit returns at most 30 rows, silently"))
    return out


AGG = {"length", "add", "unique", "unique_by", "sort", "sort_by", "group_by", "join", "min", "max", "min_by", "max_by", "first", "last", "reduce", "limit", "any", "all"}


def aggregates_pages(expr: str) -> bool:
    """Does the jq program apply an aggregate to a whole page (not to each streamed item)? Depth-0 scan: `.[]` marks the
    pipeline as streaming until a `[...]` collect closes; an aggregate seen while not streaming works on the page."""
    streaming = False
    depth_p = depth_b = 0
    i, n = 0, len(expr)
    in_str = False
    while i < n:
        c = expr[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth_p += 1
        elif c == ")":
            depth_p = max(0, depth_p - 1)
        elif c == "[":
            if depth_p == 0 and depth_b == 0 and expr.startswith("[]", i) and i > 0 and expr[i - 1] in ".":
                streaming = True
            elif depth_p == 0 and depth_b == 0 and not streaming and re.match(r"\[-?\d+\]", expr[i:]):
                return True      # `.[0]`, `.workflow_runs[-1]`: one value of EACH page
            depth_b += 1
        elif c == "]":
            depth_b = max(0, depth_b - 1)
            if depth_b == 0 and depth_p == 0 and not (i > 0 and expr[i - 1] == "["):
                streaming = False  # a collected array is one value again
        elif depth_p == 0 and depth_b == 0 and (c.isalpha() or c == "_") and (i == 0 or not (expr[i - 1].isalnum() or expr[i - 1] in "_.$")):
            m = re.match(r"[A-Za-z_]+", expr[i:])
            w = m.group(0)
            if w in AGG and not streaming:
                return True
            i += len(w)
            continue
        i += 1
    return False


def _jq_expr(args):
    for i, a in enumerate(args):
        if a in ("--jq", "-q") and i + 1 < len(args):
            return args[i + 1]
        if a.startswith("--jq="):
            return a[len("--jq="):]
    return None


def check_paginate(unit: Unit) -> List[Finding]:
    out = []
    for ln, line in logical_lines(unit.text, unit.line):
        for toks in commands(line):
            args = gh_command(toks)
            if not args or args[0] != "api" or "--paginate" not in args:
                continue
            expr = _jq_expr(args)
            if expr is None:
                continue
            if "--slurp" in args:
                out.append(Finding(unit.path, ln, "paginate", "gh refuses `--slurp` together with `--jq`; pipe `--paginate --slurp` into `jq`"))
            elif aggregates_pages(expr):
                out.append(Finding(unit.path, ln, "paginate",
                                   "`--paginate --jq` runs the program once per page, so this aggregate is per page; use `--paginate --slurp | jq …` (gh >= 2.48) or aggregate after `--jq '.[]'`"))
    return out


# `x=$(cmd) || x=value` where the value is one the SUCCESS path can also produce (authoring-pitfalls.md 6): "the call failed"
# then reads as "nothing there yet" / "still pending" and the next branch acts on it. A plain conditional
# (`[ -z "$a" ] || skip=...`), a status capture (`cmd || rc=$?`) and a distinct sentinel the next branch tests
# (`|| code=000`, `|| live=ERR`, `|| line="unknown "`) are not findings.
FALLBACK_RE = re.compile(
    r"(?:^\s*|[;&|{(]\s*|\b(?:then|do|else)\s+)(?:(?:local|export|declare|readonly)\s+)?[A-Za-z_]\w*=[\"']?(?:\$\(.*\)|`[^`]*`)[\"']?\s*"
    r"\|\|\s*(?:\{\s*)?[A-Za-z_]\w*=(?!=|\$\?)(?P<val>\"[^\"]*\"|'[^']*'|\{\}|\[\]|[^\s;&|})]*)")
# values a real result can equal: empty, zero, empty JSON, and the state words of a run/check/PR
INDISTINGUISHABLE = {"", "0", "[]", "{}", "null", "none", "false", "pending", "queued", "waiting", "in_progress"}


def check_fallback(unit: Unit) -> List[Finding]:
    out = []
    raw = unit.text.split("\n")
    for ln, line in logical_lines(unit.text, unit.line):
        code = re.sub(r"\s+#.*$", "", line)
        m = FALLBACK_RE.search(code)
        if not m or m.group("val").strip("\"' \t").lower() not in INDISTINGUISHABLE:
            continue
        idx = ln - unit.line
        # the allowance covers the line itself and a line right above it that is a comment of its own (a `# fallback-ok:` at
        # the tail of another code line belongs to that line)
        allow = re.compile(r"#\s*fallback-ok:\s*\S")
        above = raw[idx - 1] if idx > 0 else ""
        if allow.search(raw[idx]) or allow.search(line) or (above.lstrip().startswith("#") and allow.search(above)):
            continue
        out.append(Finding(unit.path, ln, "fallback",
                           "`|| x=…` turns a failed call into a value a real result can also have (empty, 0, none, pending…); fail loudly, use a distinct sentinel the next branch tests, or add `# fallback-ok: <why>`"))
    return out


def check_timeout(job: Job, path: str) -> List[Finding]:
    if job.has_timeout or job.is_call:
        return []
    return [Finding(path, job.line, "timeout", f"job `{job.id}` has no `timeout-minutes` (a hung step holds the runner for 6 hours)")]


UNIT_CHECKS = {
    "permissions": check_permissions,
    "list-limit": check_list_limit,
    "paginate": check_paginate,
    "fallback": check_fallback,
}
SH_CHECKS = ("list-limit", "paginate", "fallback")   # permissions and timeout are workflow-only
ALL_CHECKS = ("permissions", "timeout") + tuple(k for k in UNIT_CHECKS if k != "permissions")


def lint_workflow(path, text, only=None) -> List[Finding]:
    out = []
    for job in parse_workflow(path, text):
        if only is None or "timeout" in only:
            out += check_timeout(job, path)
        for u in job.units:
            for name, fn in UNIT_CHECKS.items():
                if only is None or name in only:
                    out += fn(u)
    return sorted(out)


def lint_shell(path, text, only=None) -> List[Finding]:
    u = Unit(path, 1, text, False, None, None)
    out = []
    for name in SH_CHECKS:
        if only is None or name in only:
            out += UNIT_CHECKS[name](u)
    return sorted(out)


def lint(path, text, only=None) -> List[Finding]:
    if re.search(r"\.ya?ml$", path):
        return lint_workflow(path, text, only)
    if path.endswith(".sh"):
        return lint_shell(path, text, only)
    return []


def main(argv):
    findings = []
    for p in argv:
        findings += lint(p, open(p, encoding="utf-8").read())
    for f in findings:
        print(f)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
