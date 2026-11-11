# Responding to review: close the round, don't open the next one

<!-- template: claude-plugins/templates/review-response.md -->

Complements `authoring-pitfalls.md` (error classes in the PR itself); here —
behaviour AFTER the review has arrived. A round starts by itself after a green CI on every push while the
PR has no `gate/review-passed` label; a round that ends with 0 ❗ sets
the label and later pushes start nothing until someone removes it (`merge-gate.md` rule 2 says when the
author removes it before a push). workflow_dispatch
stays for replays and `force`. Each round is a full auto-review round (6–8 agents), so the price of every
push before the label is a whole round, not "a minute": batch the fixes, push once.

The original defects run out by round three or four; after that review picks apart fix prose and promises in comments.

## Order of responding to a round

1. **Decision list first, code second.** For every finding — one of three: «чиню» (fixing), «не чиню:
   причина в одну строку» (not fixing: one-line reason), «отдельной ишьёй #N» (separate issue #N). The list goes to the PR thread as ONE comment before
   the edits. «Не чиню» is legitimate for remarks, for medium ones, and for a ❗ too when the argument is
   substantive and stands in the thread (a grep, a run, the producer that does not exist).
   A ❗ left unfixed is confirmed by the next round, not by the author: that round reads the thread
   and either drops the finding (0 ❗ sets the label) or repeats it, and a repeated ❗ is fixed or put to the
   owner. The next round comes with the round's other fixes in the one push, or by a replay
   (`workflow_dispatch` of claude-review.yml with `force`: without it the run finds no new commits and
   re-checks nothing) when there is nothing to push.
2. **One push per round — without asking.** All edits of the round go into one push: the round's commit, plus a
   fix commit when the self-check of `authoring-pitfalls.md` rule 26 finds a problem. A second push
   for "also fixed a comment" is another full round (every push without `gate/review-passed` is reviewed).
   Fix-round commits, the push, the PR body update and the thread replies need no confirmation («пуш сразу как пофиксил, не жди одобрения»). New work does not ask either: the first commit of a
   feature, the branch and the PR are the agent's own. Confirmation stays for the owner's
   `gate/snapshots-approved` on a PR with changed baselines (`merge-gate.md`, "How to merge"), a push to the
   default branch outside a PR (in a repo with a release branch the release starts on the owner's word), a
   deploy run by hand where the repo's CLAUDE.md does not grant it, and any external post. Merging a ready PR
   per `merge-gate.md`, with the deploy that merge triggers, is the agent's own.
2a. **Re-walk the scenario ledger before the push** (`authoring-pitfalls.md` rule 22) and fix the twin of
   every fix (rule 21): a round that repairs only the named place and breaks a previous round's scenario is
   the most expensive round of all.
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
   for the gate; the mediums and remarks taken as «чиню» go into one push, each as its thread describes
   it, pushed with the label kept (`merge-gate.md` rule 2 lists the only exceptions; removing the label for
   an ordinary fix starts the next round and the next mediums). Push nothing
   "just in case"; take the matrix label (`merge-gate.md` rules 2b and 3: the matrix where the diff needs one,
   `gate/matrix-not-needed` otherwise) and merge (`merge-gate.md`, "How to merge").
7. **Instrumental code** (gates, scripts, tests, CI) is fixed in the scope of ❗. The mutation
   bar for product code does not apply to gate tests; no "guards for the guards" are built.
   Anything disputable — a question to the owner in the thread, not a commit.
8. **Do not argue with review in code.** Arguments — only in the thread, with a grep or a run.
9. **A remark about an unreachable input is closed with a word, not a commit.** «Писателя у поля сегодня нет» (nothing writes this field today), «такой вход не производится» (no such input is produced) — a thread reply with a grep of the producer; no test or guard for a hypothetical input is written and no round is spawned. This holds when the default for remarks is «чиню» (step 6) and for a medium too: a finding that review itself marks «вход сегодня не производится» (input not produced today) is answered with the producer grep or the corpus count of `authoring-pitfalls.md` rule 29, not with code. If review itself calls a finding a consequence of its own recipe from a previous round — that is the reviewer's self-correction; it goes into the decision list as the line «принято, ревью» (accepted, review), with no edit.

## Resolving threads

- A thread is resolved with proof: commit hash + one line "what changed", or
  «не чиню: причина» (not fixing: reason), or «➡️ #N». «Поправил» (fixed) without a hash is not a closure.
- **Only after the fix is pushed.** The reply that says what changed and how, and the
  resolve click, come after the commit with the fix exists on the PR branch and the hash in the reply is
  that commit's. Never "will fix in the next commit" + resolve, never a reply written from the planned diff:
  the reader of a resolved thread must be able to open the hash and see the change. The decision list
  (step 1) stays before the edits; thread replies are the receipt, not the promise.
- A thread without a reply is not resolved. A thread with a reviewer's question is closed by answering the question.
- Open threads after the fix commit — only those where the decision is the owner's; in the round
  comment they are listed by name.

## Merge readiness

The readiness conditions and who merges are `merge-gate.md`, "How to merge" (CI and gate green on the final head,
every thread answered and resolved, no round in flight). Two additions: the author replies to and resolves the
threads of the CI auto-review themselves, per "Resolving threads" above — they are not left for the owner; the only
threads that may stay open are those where the decision is the owner's, listed by name in the round comment. A merge
cancels the running auto-review: wait for it to post and close its threads first.

## Sign of a loop — stop

`gate/review-passed` removed by the author for a fix that stays within what its thread names is the loop
itself; the round it started is let finish: with 0 ❗ the label returns and step 6 applies, a ❗ goes by
step 1. Also: three consecutive rounds without ❗ while the number of remarks does not decrease, or two
consecutive rounds where all findings are about comments and the PR body, or two consecutive rounds without ❗ where all findings are new spellings of a parser's input or pins of branches that already work. In that case do not push: list the remaining remarks by name in the
round comment, then take the matrix label and merge (`merge-gate.md`, "How to merge"). The owner's word is needed only where a remark
raises a decision that `owner-decisions.md` reserves for them; further rounds — only on their word.
