# Git hygiene in a shared clone — rules for the agent

Copy of the template from OmnisGM-App/claude-plugins/templates/git-hygiene.md — edit there, roll out
as copies. Every rule below has already destroyed work at least once. The clone is shared with the owner
and with parallel sessions (worktrees under `.claude/worktrees/`), so a command that is harmless alone is
not harmless here.

1. **Undo a test commit with `git reset --soft HEAD~1`, never `--hard`.** `--hard` resets the working tree
   too and silently drops every uncommitted edit in tracked files, including ones unrelated to the test commit
   (untracked files survive, so `git status` looks clean). After any history rewind compare
   `git diff <base> --stat` with the list of files you expect.
2. **No `git checkout -- .`, `git restore .` or `checkout -- <dir>` without an explicit single path.** A
   bare dot reverts the whole repository, including another session's uncommitted edits and the owner's.
   Revert one file as `git checkout HEAD -- <file>`; synced (untracked) copies come back from their sync
   script, not from git.
3. **Mutations only after a commit, and in a sandbox.** Before a mutation sweep commit the work (locally is
   enough), check "the mutant applied" with `git diff --quiet HEAD -- <file>`, revert with
   `git checkout HEAD -- <file>`, and end with an empty `git status`. Sandboxes come from
   `git archive HEAD | tar -x -C <dir>`, never from the working tree.
4. **Bare `git stash` / `git stash pop` is forbidden.** The stash stack is shared by all worktrees of a clone
   and by other sessions: a `pop` may apply someone else's entry or drop yours. If you must:
   `git stash push -u -m "<unique-tag>"`, read its SHA from `git stash list --format='%H %gs'`,
   `git stash apply <sha>`, then drop the entry found by its tag. For a baseline comparison prefer a
   separate worktree from `origin/<base>` or `git diff > patch` + `git apply`.
5. **No `git add -A` / `git add .`.** The repo's `.claude/` is tracked and other sessions keep their worktrees
   under `.claude/worktrees/`; `-A` commits them as gitlinks (News#163, 2026-10-23). Add files by name from
   your diff and read `git status --short` before every commit. A gitlink that slipped in is removed with
   `git rm --cached` in a new commit, not an amend. Keep `.claude/worktrees/` in `.gitignore`.
6. **A sandbox under `/tmp` loses files overnight.** macOS purges long-untouched files from `/tmp`, tracked
   ones included (hundreds of files and part of `node_modules` in one night). Before EVERY unit or e2e run in a
   long-lived sandbox: `git ls-files -d | wc -l` must be 0. If it is not and the commits are pushed:
   `git checkout -- .` (allowed only here, in the sandbox, where nothing uncommitted lives) → `npm ci` →
   build the shared package. Never `git add -A` over mass ` D` lines.
7. **The shared local clone itself is read-only.** No checkout, no commit, no build, no run in it; the only
   write is `git fetch`. Work happens in a worktree (`git worktree add .claude/worktrees/<name> origin/<base>`)
   or a sandbox, with absolute paths.
