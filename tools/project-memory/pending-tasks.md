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

### Average Model Usage Table

Goal: add a separate UI table with average token usage per model.

Planned changes:

- [x] Inspect the existing models API and dashboard rendering.
- [x] Add average usage fields to the model summary data.
- [x] Render a dedicated average-by-model table in the web UI.
- [x] Verify Python and JavaScript syntax.

Risks or dependencies:

- [x] Keep the existing model filter behavior intact.
- [x] Avoid changing the analytics database schema for a derived summary.

Verification:

- [x] `python -m compileall app`
- [x] `node --check web\app.js`

### Auto Refresh Web Data

Goal: refresh the web UI automatically when imported analytics data changes.

Planned changes:

- [x] Add a small data-state API endpoint.
- [x] Poll the state endpoint from the browser and refresh views on change.
- [x] Verify Python compilation and instruction-kit status.

Risks or dependencies:

- [x] Preserve existing user changes in app and web files.
- [x] Avoid reading external Codex logs directly for verification.

Verification:

- [x] `python -m compileall app`
- [x] `node --check web\app.js`
- [x] Direct `AnalyticsHandler.data_state` check against the project analytics DB
- [x] `git diff --check`
- [x] `.\tools\check-instruction-kit-updates.ps1`

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
