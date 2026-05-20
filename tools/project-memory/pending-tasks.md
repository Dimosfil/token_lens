# Pending Tasks

Use this file for active project-wide plans and multi-step work.

Keep entries concise and task-relevant. Do not store full diffs, large logs,
generated outputs, secrets, credentials, or private production data.

## Status Markers

- `[ ]` not started
- `[~]` in progress
- `[x]` done
- `[!]` blocked or needs attention

## Tasks

### Initialize Agent Memory SQLite

Goal: record the application stack in durable project memory and initialize the
local agent-memory SQLite layer following the copied `gi` instructions.

Planned changes:

- [x] Add a concise architecture/stack note.
- [x] Add a project-memory SQLite CLI script with schema and index commands.
- [x] Initialize the local generated SQLite database.
- [x] Export reviewable Markdown notes.

Execution order:

- [x] Read local `gi` memory instructions.
- [x] Create Markdown stack note.
- [x] Create and run `index_project.py`.
- [x] Verify targeted commands.

Risks or dependencies:

- [x] Keep agent memory separate from `data/analytics.sqlite`.
- [x] Avoid storing secrets, prompts, raw logs, or private local app data.

Verification:

- [x] `python .\tools\project-memory\index_project.py init`
- [x] `python .\tools\project-memory\index_project.py rebuild`
- [x] `python .\tools\project-memory\index_project.py stats`
- [x] `python .\tools\project-memory\index_project.py search "SQLite"`
