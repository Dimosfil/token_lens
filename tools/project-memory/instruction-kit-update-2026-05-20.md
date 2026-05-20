# Instruction Kit Update 2026-05-20

Goal: apply pending shared instruction-kit migrations from 2026.05.20.2 to
2026.05.20.5 without mixing unrelated app or web refactor changes.

Planned changes:
- Add bug-evidence analysis posture to local agent instructions.
- Add separate agent working-language preferences and selector.
- Add or refresh task-manager plan skill guidance if the local kit includes it.
- Record applied migration metadata after verification.

Execution order:
1. Apply instruction and helper file changes.
2. Validate JSON and PowerShell parsing.
3. Run `git diff --check` and instruction update check.
4. Commit and push only scoped instruction-kit update files if not blocked by
   unrelated changes.

Risk: the worktree already has unrelated app/web refactor changes, so staging
must be explicit and scoped.

Status: complete. Commit/push was not attempted because unrelated app/web and
project-memory changes were already present in the worktree.
