# Merge gate: labels, who sets them, how to merge

Copy of the template from OmnisGM-App/claude-plugins/templates/merge-gate.md — edit there, roll out
as copies. The ruleset of the default branch requires the `Merge gate` check
(`.github/workflows/merge-gate.yml`), which turns four `gate/*` labels into a merge condition
(owner's decision 2026-10-20). This file says who may set each label and how a PR is merged.

## The labels

| Label | Meaning | Who sets it | Who removes it |
|---|---|---|---|
| `gate/snapshots-approved` | the owner has looked at every changed screenshot baseline in the PR | **the owner only, by hand** | the gate once the PR's own baselines differ from the approved head; the owner |
| `gate/matrix-passed` | the full Playwright matrix is green on the current head (`EXIT=0`, numbers in the PR body) | the agent or the owner, after the run on that head, with the head already pushed | the gate once the head differs from the one it was applied on |
| `gate/matrix-not-needed` | the diff does not touch UI; the PR body says so in one line | the agent or the owner | whoever adds UI to the diff |
| `gate/review-passed` | the last auto-review round ended with 0 ❗ | **claude-review.yml only** | claude-review.yml on a round with ❗; anyone who wants another round (removing it starts one after a green CI) |

Required: the matrix pair (exactly one of the two) always; `gate/review-passed` unless the author is
dependabot or the PR is a release (`dev` or `release/*` → `master`); `gate/snapshots-approved` when
the PR changes any `*-snapshots/` file (release PRs excepted: their baselines were approved in the
feature PRs). Dependabot gets `gate/matrix-not-needed` from `dependabot.yml`. Head-bound labels are bound to the
head they were applied on (the gate keeps a state comment on the PR): `gate/matrix-passed` applied on
another head is removed, and so is `gate/snapshots-approved` when the PR's own baselines differ
between that head and the live one. `gate/review-passed` counts only when the review workflow applied
it — a hand-applied one is reported and ignored.

## Rules for an agent (Claude Code and anything acting with the owner's token)

1. **Never set `gate/snapshots-approved`.** The token cannot tell the agent from the owner, so the
   rule is procedural: new or changed baselines are reviewed by a human eye, and the agent's job ends
   at "baselines regenerated, here is what changed" in the PR body. The gate's message says the
   same: it waits for a human.
2. **Never set `gate/review-passed`** — the review workflow owns it. To ask for another round, remove
   the label (a round starts after a green CI) or push: a push without the label starts a round after CI by itself.
3. `gate/matrix-passed` only after the full matrix on the exact head you label, with the numbers
   in the PR body, and only under "Failed and flaky tests" below; a partial or targeted run is not the matrix. `gate/matrix-not-needed` only when
   no UI file is in the diff and the PR body says so.
4. The gate is a status check, not a reviewer: a green gate still needs the owner's merge command.
   Its colours: **yellow (in progress)** = something is still awaited — a review round, a label, a label
   event the API has not listed yet; **red** = a contradiction to fix by hand (two matrix labels, a label
   applied by the wrong actor, a label without a recorded head) or an error of the gate run itself; **green**
   = every required label holds on this head. CI is not part of the gate — it is its own required check.
   The workflow run is green unless it errors, so a waiting PR sends no failure mail.

## Failed and flaky tests (owner's decision 2026-10-22)

- **A failed test blocks the merge. No exceptions**, whether or not the test is in the diff. Fix it
  (or the run) and run the matrix again.
- **A flaky test (failed, then passed on retry) does not block the merge** once all three hold:
  1. **An issue.** The flake is filed as an issue, or an occurrence is added to the existing one. A
     test that passed on retry is a discovered race, not a re-taken exam.
  2. **A link in the code, in the same PR.** Above the test: `// FIXME(#N): flaky — <one-line
     symptom>`, so whoever edits the test sees that the race is known.
  3. **A note in the PR body.** The flaky count and the issue numbers go next to the matrix numbers.
- **The line comes out with the fix.** The PR that fixes the race removes its `FIXME`.
- **A flake that cannot be reproduced** gets its issue closed as not planned, with the evidence, and
  its `FIXME` line removed. A stale link misleads more than none.

## How to merge

- **Squash, never `--admin`.** `gh pr merge N --squash --delete-branch`, or `--auto --squash` so the
  PR merges itself when the required checks (CI + `Merge gate`) go green. `--auto` is armed only on
  the owner's merge command and only once every review thread is answered and resolved and no round
  is running (`review-response.md`, merge readiness): the checks do not know about threads. An admin
  merge bypasses the gate and is reserved for the owner's own hand in an emergency.
- **`master` is the only branch merged without squash** (Table: the release PR `dev` → `master`, see
  CLAUDE.md "Release flow", is `--merge` so the history of `dev` is kept); everything else — squash.
  A repo without a release branch (Rules, News) squashes every PR.
- **A PR that edits the gate itself** (`merge-gate.yml`, `merge_gate.py`, `claude-review.yml`) runs its
  own version of the check, so the gate cannot vouch for it: the owner reads that diff and merges by
  explicit command only.
- A green check on an old head is not a green check: after a push wait for CI and the gate on the
  new head before merging.
