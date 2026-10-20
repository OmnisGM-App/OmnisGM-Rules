# Responding to review: close the round, don't open the next one

Copy of the template from OmnisGM-App/claude-plugins/templates/review-response.md — edit there,
roll out as copies. Complements `authoring-pitfalls.md` (error classes in the PR itself); here —
behaviour AFTER the review has arrived. The first round starts by itself once per PR (`opened` /
`ready_for_review`); no repo runs the review on `synchronize` (dropped in v2.34, 2026-09-22), so a push starts nothing
and every further round is requested by the owner via workflow_dispatch. Each round is a full auto-review round
(6–8 agents), so the price of an extra fix-and-request cycle is a whole round, not "a minute".

Origin: Table#574 (11 rounds in a day) and Table#576 (9 rounds) — the original defects ran out
by round three or four, after that review was picking apart fix prose and promises in comments.

## Order of responding to a round

1. **Decision list first, code second.** For every finding — one of three: «чиню» (fixing), «не чиню:
   причина в одну строку» (not fixing: one-line reason), «отдельной ишьёй #N» (separate issue #N). The list goes to the PR thread as ONE comment before
   the edits. «Не чиню» is legitimate for remarks, and for medium ones too if the argument is substantive.
2. **One commit per round, one push.** All edits of the round go into one commit. Another
   fix-and-request cycle for "also fixed a comment" is another full round.
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
   deferred with a word in the thread. A round with no ❗ and no medium findings = PR ready for the gate: push nothing
   "just in case", write to the owner.
7. **Instrumental code** (gates, scripts, tests, CI) is fixed in the scope of ❗. The mutation
   bar for product code does not apply to gate tests; no "guards for the guards" are built.
   Anything disputable — a question to the owner in the thread, not a commit.
8. **Do not argue with review in code.** Arguments — only in the thread, with a grep or a run.
9. **A remark about an unreachable input is closed with a word, not a commit.** «Писателя у поля сегодня нет» (nothing writes this field today), «такой вход не производится» (no such input is produced) — a thread reply with a grep of the producer; no test or guard for a hypothetical input is written and no round is spawned (six such remarks in the week of 22–28.09, each one dragged a round). If review itself calls a finding a consequence of its own recipe from a previous round — that is the reviewer's self-correction; it goes into the decision list as the line «принято, ревью» (accepted, review), with no edit.

## Resolving threads

- A thread is resolved with proof: commit hash + one line "what changed", or
  «не чиню: причина» (not fixing: reason), or «➡️ #N». «Поправил» (fixed) without a hash is not a closure.
- A thread without a reply is not resolved. A thread with a reviewer's question is closed by answering the question.
- Open threads after the fix commit — only those where the decision is the owner's; in the round
  comment they are listed by name.

## Merge readiness

A PR is ready to merge when all three hold, and only then the owner's explicit command merges it:

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

Three consecutive rounds without ❗ while the number of remarks does not decrease, or two consecutive rounds where all
findings are about comments and the PR body. In that case do not push: write to the owner «готов к
гейту, остались ремарки: …» (ready for the gate, remaining remarks: …) and wait for a decision. Further rounds — only on their word.
