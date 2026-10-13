# Code comments: hard rules

Copy of the template from OmnisGM-App/claude-plugins/templates/code-comments.md — edit there,
roll out as copies. Since 2026-09-16 there is NO separate review lens for comments (owner
decision, confirmed 2026-09-28: instead of a lens — a stricter author pass): comment
cleanliness is the author's duty, the pass below is mandatory before every push. Review catches only comments that lie about behaviour or a contract, and
offers one thing — delete or fix the code, never add more text.

Measurement 2026-09-16 (Table): code written by sessions over the last months carries 24–36%
comment lines (`sheet domain` 24%, `shared/lib` 33%, the new map-pins slice 26%,
`firestore.rules` 36%) versus 5% in the old `game-items`. Every extra phrase is a candidate
review finding "the comment promises what the code does not hold", and that is how
endless fix rounds are born.

## What a comment may say

A comment answers one question: **why the non-obvious decision here**. If the answer
is obvious from the code, the name or the type — there is no comment.

Allowed (and only this):

- **A non-obvious constraint with a source**: issue number, § of a doc, link to a library bug,
  a system rule (`Rules/…#L…`). One–two lines: "`x` in fractions 0..1 — survives an image
  swap (#375)".
- **A workaround for an external bug**: which bug, link, under what condition the workaround can be removed.
- **Why not the obvious path**: "not `useEffect` — recreates the map on language change".
- **Public API contract** — one docblock per export: what it takes, what it returns, what it
  throws. No retelling of the signature.
- **TODO/FIXME only with an issue number**: `// TODO(#577): …`. Without a number — do not commit.

## What is forbidden

1. **Retelling the code** ("increment the counter", "if empty — return null", "import
   the helper"). The reader sees the code.
2. **Promises and guarantees**: "the only place", "guarantees", "cannot happen",
   "a test guards this", "tsc/the gate catches it", "always/never". If it is true, a test
   or a gate holds it — name it, do not promise. If no test/gate holds it — the promise is a lie.
3. **History and review**: "after review", "used to be", "in round five", "fixed per
   finding", "unlike the previous version". The code reader does not see the PR history.
   History lives in git and in the PR.
4. **Numbers duplicated from code or tests**: "three tests hold this", "17 scenarios",
   "~1.5 min", "452 files". A number goes stale with the very next commit. Exception — the number
   is itself the reason (threshold, limit, buffer size) — then with a source.
5. **Retelling game rules or a document** in prose next to the code that implements them.
   One link to the source.
6. **Explaining the language or framework** (how `useMemo` works, what `Record` is).
7. **A docstring repeating the signature** ("takes an id and returns a document").
8. **A comment arguing with review or justifying** ("it is this way here because otherwise review
   finds…"). Arguments go in the PR thread.
9. **A comment instead of a name**: if a comment is needed to understand a variable —
  rename the variable.

## Budget

- A line comment — one line. A block above a function — up to three lines. A block longer
  than three lines is allowed only for a public API contract or an external-bug workaround with
  a link; anything longer moves to `plans/`, to an issue or to a doc, and the code keeps
  one link.
- File header — at most five lines: module purpose and its link (issue/doc). Not a changelog,
  not a list of "what we do NOT do here".
- Guideline for a product code file: comments ≤10% of lines. `firestore.rules` ≤15%.
  Exceeding it when adding a new file is a reason to reread and cut, not a reason
  to justify.
- Tests: the case's motive goes in the test name (`it('…')`), not in a block above it. A comment in a test
  is allowed only for non-obvious data setup.

## How to fix per review

Review found a false or forbidden comment → **delete** the comment or **fix the
code** so the statement becomes true. Never add a caveat, a clarification,
a second "actually" paragraph. Two versions of one explanation in one place are worse than
none.

## Comment pass — a mandatory step before EVERY push

Done after code and tests, before the PR body and the decision list. For every file from
`git diff --name-only <base>...HEAD`:

1. **List** all comments in the file's diff AND the file header (the diff may not have touched it,
   but the edit may have made it stale).
2. **Remove** every comment of a forbidden class (list above). Do not rewrite —
   delete.
3. **Verify the facts** of every remaining one: names and signatures exist, numbers match the
   code, the source (issue/doc/rules line) is named and correct, the trigger condition in an
   error text equals the condition in the code.
4. **Find twins**: grep the phrase you changed across the file and its neighbours — a surviving
   second version of the explanation is removed in the same commit.
5. **Update** comments this edit turned into lies (the docstring above a
   changed function, the module header listing consumers, "until step N lands"),
   — usually a deletion, more rarely one line with a fact instead of a promise.
6. **Budget**: a new or rewritten file has a comment-line share ≤10% (`rules`
   ≤15%) — count, do not estimate; above — cut to the threshold.
7. **By grep, not by eye** (owner decision 2026-09-28; revised 2026-09-29: in one week,
   62 review findings under this rule despite the mandatory step — the previous grep gave a false zero
   on a single file without `-H`, ignored case, JSX comments, `it.each(`/`test.describe(`,
   missed threshold numbers, quantifiers, PR links and the comment share in a new file). Over
   the changed files run ALL four commands and go through every hit — remove it or
   state in the decision line why it is not a violation:

   ```bash
   F=$(git diff --name-only --diff-filter=d <base>...HEAD | grep -vE '\.(png|jpg|webp|svg|lock)$')   # excluding deleted files; commands verified on mawk/gawk/BSD awk and under C.UTF-8
   # the exit code is checked INSIDE xargs (outside you see xargs' code): clean → 0, grep error → non-zero code and the error text
   # CASE_FNS — test-case function names for (c); the default covers vitest/playwright and Rules helpers (check/eq/recognizes): an extra name does not produce a false zero
   # (a) forbidden classes 2–4 and 8 + quantifiers + references to PR/review — case-insensitive, JSX comments too
   RE_A='^[[:space:]]*(//|#|\*|/\*|<!--|\{/\*).*(ревью|раунд|раньше было|поправлен|в отличие от прежн|после правк|исправлен[оа] по|единственн|гарантир|не может произойти|тест сторожит|ловит (tsc|гейт)|\bвсегда\b|\bникогда\b|\bвсе[хм]?\b|\bкажд(ый|ая|ое|ого)\b|\bтолько\b|\breview\b|\bround\b|previously|used to|\bonly\b|\bevery\b|\balways\b|\bnever\b|PR #|#[0-9]{2,4}\b.*(ревью|review))'
   echo "$F" | xargs sh -c 'grep -HinE "$0" "$@" || [ $? -eq 1 ]' "$RE_A"
   # (b) numbers with units in comments — each must have an executable source (constant, mixin, useMediaQuery), otherwise the number lies
   RE_B='^[[:space:]]*(//|#|\*|/\*|\{/\*|<!--).*[0-9]+([.,][0-9]+)?[[:space:]]*((px|ms|s|%|KB|MB)|(мс|КБ|мин|сек|строк|тест|файл|сценари)[[:alpha:]]*|раз(а|ов)?)([^[:alnum:]]|$)'
   echo "$F" | xargs sh -c 'grep -HnE "$0" "$@" || [ $? -eq 1 ]' "$RE_B"
   # (c) test rationale as a block above the case, including across a blank line and for it.each/test.describe/describe.skip
   echo "$F" | grep -E '(\.(test|spec)\.[jt]sx?|/test_[^/]+\.(mjs|py))$' | xargs -r awk -v C="${CASE_FNS:-it|test|describe|check|eq|recognizes}" 'BEGIN{n=0; re="^[[:space:]]*((" C ")(\\.[a-zA-Z]+)*(\\(|`)|def test_)"} /^[[:space:]]*(\/\/|\/\*|\*|#)/{n++; next} /^[[:space:]]*$/{next} $0 ~ re {if(n) print FILENAME":"FNR; n=0; next} {n=0}'
   # (d) share of comment lines in each new/rewritten file (budget ≤10 %, rules ≤15 %) — counted, not estimated
   for f in $(echo "$F" | grep -E '\.(ts|tsx|mts|mjs|js|py|astro|scss|rules)$'); do awk -v f="$f" '/^[[:space:]]*(\/\/|\*|\/\*|\{\/\*|#[^!]|<!--)/{c++} END{if(NR>40 && c*10>NR) printf "%s: %d/%d строк = %d%%\n", f, c, NR, c*100/NR}' "$f"; done
   ```

   Plus one pass by eye over a ±20-line window around every hunk (`git diff -U20`):
   a comment that became a lie from SOMEONE ELSE's edit in the same diff or from your edit on
   a neighbouring line contains no stop-words and grep does not catch it. A new block of code does not land
   between someone else's docblock and what it describes: after inserting, reread the neighbour above
   and below.

   Zero hits is the norm; a hit with the excuse "but it is true" is no excuse: the truth
   is held by a test or a gate — name it and remove the comment.
8. **One line in the decision list** in the PR thread: «комментарии: проход по N файлам, снято
   K, актуализировано M, греп-попаданий а/б/в = X/Y/Z (разобраны: …), доля в новых файлах:
   <файл> P %» (comments: pass over N files, removed K, updated M, grep hits a/b/c = X/Y/Z (triaged: …), share in new files: <file> P %). Without this line and without the numbers the push is not ready.

Before pushing, read your diff as a reader with no PR history: every phrase in a
comment is either verifiable against the code next to it, or gets deleted.
