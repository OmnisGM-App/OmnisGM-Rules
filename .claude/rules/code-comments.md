# Code comments: hard rules

<!-- template: claude-plugins/templates/code-comments.md -->

There is NO separate review lens for comments: comment cleanliness is the author's duty, the pass below is
mandatory before every push. Review catches only comments that lie about behaviour or a contract, and
offers one thing — delete or fix the code, never add more text.

Every extra phrase is a candidate review finding "the comment promises what the code does not hold", and that is how
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
7. **By grep, not by eye** (a grep that gives a false zero is the usual miss: it must use `-H`
   so a single file is named, ignore case, and cover JSX comments, `it.each(`/`test.describe(`,
   threshold numbers, quantifiers, PR links and the comment share in a new file). Over
   the changed files run ALL five scripts of the omnisgm plugin's `scripts/checks/` (`CHECK <name> <base>` from the repo root, the launcher form of `authoring-pitfalls.md`;
   no output and exit 0 is clean, exit 1 prints `path:line:text`, exit 2 means the script itself broke — never a pass; the
   scripts pick a UTF-8 locale themselves, a bare `\b` over Cyrillic matches nothing in the POSIX one) and go through every
   hit — remove it or state in the decision line why it is not a violation:

   - `comment-stopwords.sh` (a): forbidden classes 2–4 and 8, quantifiers, references to a PR or a review — case-insensitive, JSX comments too.
   - `comment-numbers.sh` (b): a number with a unit in a comment (px, ms, %, KB, мс, строк, раз…) — each needs an executable source (a constant, a mixin, `useMediaQuery`), otherwise the number lies.
   - `comment-test-rationale.sh` (c): a comment block above a test case, across a blank line and a decorator, for `it.each`/`test.describe`/`describe.skip` and `def test_`; `CASE_FNS` adds test-case function names (the default covers vitest/playwright and the Rules helpers `check`/`eq`/`recognizes`).
   - `comment-share.sh` (d): the share of comment lines in each changed source file (budget ≤10 %, `rules` ≤15 %) — counted, not estimated.
   - `docblock-wedge.sh <base>` (e): prints `file:line: under a docblock that is not its own` for each added declaration (indented too) that, walking up past the docblock and blank lines you added to the nearest UNCHANGED line, meets someone else's closing `*/` (a removed line in between resets it, so editing a documented signature is not flagged) — move your declaration above the old docblock or below the code it describes.

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
