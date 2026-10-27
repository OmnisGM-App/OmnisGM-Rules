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
dependabot or the PR is a release (`release/*` → `master` only; `dev` → `master`, the form of #1219 and
earlier, needs `gate/review-passed` since 2026-10-23, and claude-review.yml skips a PR whose base is not the
default branch — such a PR gets its round only by `workflow_dispatch`; whether a `release/*`
head is an empty commit whose parent is a `dev` commit is not checked yet, #1226); `gate/snapshots-approved` when
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
   **When to remove it yourself** (owner's decision 2026-10-23, OmnisGM-App/OmnisGM-News#163): the label was earned by the head
   the clean round read; a push that changes behaviour after it would merge unreviewed. Remove the label
   BEFORE that push and say why in the round comment when at least one holds:
   - product code changes behaviour — a new branch, condition, data shape, query, API call or effect, in
     any file, including files the clean round never saw;
   - a medium finding was fixed by a different approach than the one named in the thread, not by the
     reviewer's own line;
   - gate, review, CI, deploy or security logic changed (workflows, the gate script, access rules) in anything
     but a comment;
   - a base merge had conflicts resolved by hand;
   - the diff since the labelled head is over ~50 lines of non-test, non-doc code (a guideline, not a gate).
   Keep the label and push without a round when the push is only: tests, comments, docs, the PR body,
   a rename with no logic change, a clean base merge, or a one-line fix exactly as the reviewer wrote it.
   In doubt — remove: a wasted round costs minutes, an unreviewed change costs a release.
2b. **Matrix after review, not before.** The full matrix (and targeted e2e re-runs) wait until the auto-review
   and its fix rounds are done: one matrix on the final head. Before review — unit tests and the local CI script;
   an early matrix is machine time thrown away by the first fix commit (owner, 2026-10-19, Table#1146,
   #1163). A PR with changed `*-snapshots/` baselines waits for the owner's `gate/snapshots-approved` as well
   before the matrix (proposed by the agent, accepted by the owner, 2026-10-27): a rejected frame is re-shot and
   re-run, so a matrix taken before the owner's look is the same thrown-away machine time. Re-shooting the
   baselines the PR itself touches is part of the change, not of the matrix: `authoring-e2e.md` rule 6.
3. `gate/matrix-passed` only after the full matrix on the exact head you label, with the numbers
   in the PR body, and only under "Failed and flaky tests" below; a partial or targeted run is not the matrix. `gate/matrix-not-needed` only when
   no UI file is in the diff and the PR body says so. Two release-only exceptions (Table, owner's decision
   2026-10-23), both because the labelled head has the very TREE the matrix ran on: (a) the matrix of the
   last feature PR counts for the `dev` head when that PR's head contained the `dev` it was squash-merged
   on and nothing matrix-relevant landed after it; (b) a release cut as an empty commit on top of a `dev`
   head carries that head's matrix. The PR body names the head the matrix ran on and why it carries over.
   A third carry-over, for flaky tests (proposed by the agent, accepted by the owner, 2026-10-27): the
   `// FIXME(#N)` lines of "Failed and flaky tests" are written after the run, so they land in a commit the
   matrix never saw. When `git diff <matrix head> <live head>` consists only of comment lines inside
   `tests/e2e/**` (no spec logic, no baseline, no product file), the matrix of `<matrix head>` counts for the
   live head; the PR body names both SHAs. Anything else in that diff means a new matrix.
4. The gate is a status check, not a reviewer: a green gate is the condition, "How to merge" below says who
   merges (the agent itself; the owner's hand is only `gate/snapshots-approved` on changed baselines).
   Its colours: **green** = every required label holds on this head; **red** = either something is still
   awaited (the job log says `waiting: …` — a review round, a label, a label event the API has not listed yet)
   or a contradiction to fix by hand (two matrix labels, a label applied by the wrong actor, a label without a
   recorded head) or an error of the gate run itself. A label event re-runs the job (the review workflow's
   label re-runs it through `gh run rerun`), so a waiting PR goes green once the label lands; a lagging events
   list is the one case for "Re-run jobs" on the gate run by hand. A waiting PR is a red run and mails a
   failure on every push — the owner's decision of 2026-10-24, replacing the 2026-10-23 "no mail" that the API
   check run bought. CI is not part of the gate — it is its own required check. The verdict is the status of
   the job `Merge gate` itself (v3, 2026-10-24): an API check run lands in the oldest check suite of that SHA
   and is hidden from the merge box as soon as the gate re-runs on a label (Table#1241) or the head is shared
   with another branch (Table#1227); a `workflow_dispatch` run is attached to no PR and never counts (Table#1251).
   The ruleset requires `Merge gate` (the job) next to the CI check.

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

- **Who merges (owner's decisions 2026-10-21 and 2026-10-24).** The agent merges its own PR itself once it
  is ready: CI and `Merge gate` green on the final head, `gate/review-passed` set by the workflow, an honest
  matrix label (the full matrix on this head, or `gate/matrix-not-needed` with the one-line reason in the
  body), every review thread answered and resolved, no round in flight. That covers PRs that edit the gate,
  the review workflow or the rules, and the release PR once the release skill's checklist holds (the release
  itself still STARTS on the owner's word — that is scheduling, not approval). The owner's hand is exactly one
  thing: `gate/snapshots-approved` on a PR with changed `*-snapshots/` baselines — a human looks at the frames
  and confirms them in GitHub; with that label on the final head the agent merges that PR too. In
  `claude-plugins` the same readiness criteria apply (owner, 2026-10-19).
- **A merge command, when the owner does give one, covers one PR**: the PR it was said about — not a stack
  whose order the reviewer suggested, not "the next one" after "merge and take the next task" (that permits
  starting the task, not merging its PR), not an "if it goes green — merge" from an earlier exchange. A PR
  that is not ready is reported as not ready, never merged on a command alone (`--admin` is never used).
- **Squash, never `--admin`.** `gh pr merge N --squash --delete-branch`, or `--auto --squash` so the
  PR merges itself when the required checks (CI + `Merge gate`) go green. `--auto` is armed only once
  every review thread is answered and resolved and no round is running (`review-response.md`, merge
  readiness): the checks do not know about threads. An admin merge bypasses the gate and is reserved
  for the owner's own hand in an emergency.
- **A stacked PR (base is another PR's branch, not `dev`/`master`) is opened as a draft** and marked ready
  only after the lower PR is merged and this one is retargeted (owner, 2026-10-14). Merge order of a stack:
  `gh pr edit <upper> --base dev` FIRST, then `gh pr merge <lower> --delete-branch` — deleting the base
  branch closes the upper PR instead of retargeting it (News#162→#163, 2026-10-23). If it did close:
  push the old SHA back to the base branch name, `gh pr reopen`, `gh pr edit --base`, delete the branch again.
- **`master` is the only branch merged without squash** (Table: the release PR `release/YYYY-MM-DD` →
  `master`, cut from the `dev` head, see CLAUDE.md "Release flow", is `--merge` so the history of `dev`
  is kept); everything else — squash.
  A repo without a release branch (Rules, News) squashes every PR.
- **A PR that edits the gate itself** (`merge-gate.yml`, `merge_gate.py`, `claude-review.yml`) runs its
  own version of the check, so the gate cannot vouch for it. It is merged under the ordinary readiness
  criteria above (the agent itself) — the author reads its own diff with the knowledge that the gate's
  verdict on it is self-reported.
- A green check on an old head is not a green check: after a push wait for CI and the gate on the
  new head before merging.
