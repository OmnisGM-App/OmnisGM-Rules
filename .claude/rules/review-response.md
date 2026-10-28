# Responding to review: close the round, don't open the next one

Copy of the template from OmnisGM-App/claude-plugins/templates/review-response.md — edit there,
roll out as copies. Complements `authoring-pitfalls.md` (error classes in the PR itself); here —
behaviour AFTER the review has arrived. A round starts by itself after a green CI on every push while the
PR has no `gate/review-passed` label (claude-review.yml v2.48, 2026-10-20); a round that ends with 0 ❗ sets
the label and later pushes start nothing until someone removes it (`merge-gate.md` rule 2 says when the
author removes it before a push: behaviour changes after a clean round are reviewed again). workflow_dispatch
stays for replays and `force`. Each round is a full auto-review round (6–8 agents), so the price of every
push before the label is a whole round, not "a minute": batch the fixes, push once.

Origin: Table#574 (11 rounds in a day) and Table#576 (9 rounds) — the original defects ran out
by round three or four, after that review was picking apart fix prose and promises in comments.

## Order of responding to a round

1. **Decision list first, code second.** For every finding — one of three: «чиню» (fixing), «не чиню:
   причина в одну строку» (not fixing: one-line reason), «отдельной ишьёй #N» (separate issue #N). The list goes to the PR thread as ONE comment before
   the edits. «Не чиню» is legitimate for remarks, for medium ones, and for a ❗ too when the argument is
   substantive and stands in the thread (a grep, a run, the producer that does not exist) — owner's decision
   2026-10-28. A ❗ left unfixed is confirmed by the next round, not by the author: that round reads the thread
   and either drops the finding (0 ❗ sets the label) or repeats it, and a repeated ❗ is fixed or put to the
   owner. The next round comes with the round's other fixes in the one commit, or by a replay
   (`workflow_dispatch` of claude-review.yml) when there is nothing to push. After a round that set
   `gate/review-passed`, «не чиню» is the default for a medium, not the exception (step 6).
2. **One commit per round, one push — without asking.** All edits of the round go into one commit. A second push
   for "also fixed a comment" is another full round (every push without `gate/review-passed` is reviewed).
   Fix-round commits, the push, the PR body update and the thread replies need no confirmation (owner,
   2026-09-15: «пуш сразу как пофиксил, не жди одобрения»). New work does not ask either: the first commit of a
   feature, the branch and the PR are the agent's own (owner, 2026-10-27). Confirmation stays for the owner's
   `gate/snapshots-approved` on a PR with changed baselines (`merge-gate.md`, "How to merge"), a push to the
   default branch outside a PR (in a repo with a release branch the release starts on the owner's word), a
   deploy run by hand where the repo's CLAUDE.md does not grant it, and any external post. Merging a ready PR
   per `merge-gate.md`, with the deploy that merge triggers, is the agent's own.
2a. **Re-walk the scenario ledger before the push** (`authoring-pitfalls.md` rule 22) and fix the twin of
   every fix (rule 21): a round that repairs only the named place and breaks a previous round's scenario is
   the most expensive round of all (Table#1179: four rounds with ❗).
3. **Fix code, not prose.** The response to a finding is a code or test edit, or an argument in the thread.
   Do not add an explanatory comment to the code: every promise phrase ("a test guards this",
   "the only place", "guarantees", "cannot happen") is a candidate finding
   for the next round. A promise that no code or test holds is removed, not wrapped in
   a caveat.
4. **A test per review's recipe — only after running it both ways**: green on clean code,
   red on the mutant. Fails on clean code or the input is unreachable — the recipe does not fit; say so
   in the thread, do not commit the test.
5. **PR body and the «Проверено» (Verified) block — from the final head, once.** Strict order: code →
   run → body. Any code push after the snapshot makes the block stale (`authoring-pitfalls`
   item 4), and review will catch it. Do not re-snapshot while there are no new commits.
6. **Remarks do not spawn a round.** They are fixed in the same commit as ❗ and medium ones, or
   deferred with a word in the thread. A round with no ❗ sets `gate/review-passed` and that is the PR ready
   for the gate, whatever mediums and remarks came with it: they are not fixed in this PR but answered in
   the thread «не чиню: причина» or filed «➡️ #N» with the reviewer's recipe as the issue's checklist. The
   only pushes after the label are those `merge-gate.md` rule 2 allows with it (tests, comments, docs, the
   PR body, a one-line fix exactly as the reviewer wrote it); a push that removes the label for a medium
   starts the next round and the next mediums (Table#1315: six such rounds in one night). Push nothing
   "just in case"; take the matrix label (`merge-gate.md` rules 2b and 3: the matrix where the diff needs one,
   `gate/matrix-not-needed` otherwise) and merge (`merge-gate.md`, "How to merge").
7. **Instrumental code** (gates, scripts, tests, CI) is fixed in the scope of ❗. The mutation
   bar for product code does not apply to gate tests; no "guards for the guards" are built.
   Anything disputable — a question to the owner in the thread, not a commit.
8. **Do not argue with review in code.** Arguments — only in the thread, with a grep or a run.
9. **A remark about an unreachable input is closed with a word, not a commit.** «Писателя у поля сегодня нет» (nothing writes this field today), «такой вход не производится» (no such input is produced) — a thread reply with a grep of the producer; no test or guard for a hypothetical input is written and no round is spawned (six such remarks in the week of 22–28.09, each one dragged a round). If review itself calls a finding a consequence of its own recipe from a previous round — that is the reviewer's self-correction; it goes into the decision list as the line «принято, ревью» (accepted, review), with no edit.

## Resolving threads

- A thread is resolved with proof: commit hash + one line "what changed", or
  «не чиню: причина» (not fixing: reason), or «➡️ #N». «Поправил» (fixed) without a hash is not a closure.
- **Only after the fix is pushed** (owner, 2026-10-23). The reply that says what changed and how, and the
  resolve click, come after the commit with the fix exists on the PR branch and the hash in the reply is
  that commit's. Never "will fix in the next commit" + resolve, never a reply written from the planned diff:
  the reader of a resolved thread must be able to open the hash and see the change. The decision list
  (step 1) stays before the edits; thread replies are the receipt, not the promise.
- A thread without a reply is not resolved. A thread with a reviewer's question is closed by answering the question.
- Open threads after the fix commit — only those where the decision is the owner's; in the round
  comment they are listed by name.

## Merge readiness

A PR is ready to merge when all three hold; who merges it then is `merge-gate.md`, "How to merge" (the agent
itself; a PR with changed baselines needs the owner's `gate/snapshots-approved` first):

1. **CI is green** — the required check of the ruleset has passed on the final head (plus the full
   e2e matrix where the repo's gate demands it).
2. **Every review thread is answered and resolved** — including the threads of the CI auto-review.
   The author replies to and resolves auto-review threads themselves, per "Resolving threads" above
   (hash + one line / «не чиню: причина» / «➡️ #N»); they are not left for the owner. The only
   threads that may stay open are those where the decision is the owner's, listed by name in the
   round comment.
3. **No review round is in flight** — a merge cancels the running auto-review; wait for it to post
   and close its threads first.

## Sign of a loop — stop

`gate/review-passed` removed by the author for anything but a ❗ or the owner's new work is the loop itself: the
round it starts can only bring more mediums. Also: three consecutive rounds without ❗ while the number of
remarks does not decrease, or two consecutive rounds where all findings are about comments and the PR body.
In that case do not push: list the remaining remarks by name in the
round comment, then take the matrix label and merge as in step 6. The owner's word is needed only where a remark
raises a decision that `owner-decisions.md` reserves for them; further rounds — only on their word.
