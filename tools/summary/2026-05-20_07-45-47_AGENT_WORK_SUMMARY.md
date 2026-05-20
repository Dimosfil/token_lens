# Agent Work Summary

Created: 2026-05-20 07:45:47 Europe/Moscow

## Current State

- Token Lens was started successfully with `.\start.ps1`.
- Local URL: `http://127.0.0.1:8765`.
- Current branch: `main` tracking `origin/main`.

## Completed

- Bootstrapped the local `gi` instruction kit from `D:\AI\general-instructions`.
- Added local agent instructions, runbook, working agreements, startup script,
  update checker, project memory files, and summary folder.
- Recorded instruction-kit baseline `2026.05.19.8` in
  `tools/project-memory/instruction-kit.json`.
- Added generated agent-memory ignore rules to `.gitignore`.
- Documented the Token Lens stack and architecture in
  `tools/project-memory/architecture.md`.
- Initialized local agent-memory SQLite at
  `tools/project-memory/project_memory.sqlite`.
- Added `tools/project-memory/index_project.py` for `init`, `rebuild`, `stats`,
  `search`, `note`, and `export-notes`.
- Exported reviewable memory notes to `tools/project-memory/NOTES.md`.

## Checks Run

- `git diff --check`
- `.\tools\check-instruction-kit-updates.ps1`
- `.\tools\agent-start.ps1 -MaxLines 20`
- `python .\tools\project-memory\index_project.py init`
- `python .\tools\project-memory\index_project.py rebuild`
- `python .\tools\project-memory\index_project.py stats`
- `python .\tools\project-memory\index_project.py search SQLite --limit 8`

## Important Boundaries

- `data/analytics.sqlite` is the product database.
- `tools/project-memory/project_memory.sqlite` is generated local agent memory
  and should stay uncommitted.
- Existing modified app files were present during instruction-kit work:
  `app/db.py`, `app/importer.py`, `app/server.py`, `web/app.js`,
  `web/index.html`.
- Those app/web changes should not be mixed into a `gi` instruction-memory
  commit unless the user explicitly wants them included.

## Next Useful Commands

```powershell
.\tools\agent-start.ps1
python .\tools\project-memory\index_project.py stats
python .\tools\project-memory\index_project.py search "query" --limit 10
```
