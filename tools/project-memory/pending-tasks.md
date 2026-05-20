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

### Dashboard Time Range And Chart Modes

Goal: add global time-window controls and a chart mode switch for token dynamics.

Planned changes:

- [x] Add task plan and inspect current dashboard query/render flow.
- [x] Add backend time range and bucket filtering for dashboard summaries,
      charts, task/model tables, and top lists.
- [x] Add a second chart mode for average total tokens per model call.
- [x] Add UI controls for time range and grouping granularity.
- [x] Verify Python and JavaScript syntax.

Risks or dependencies:

- [x] Preserve existing response shapes where possible for current renderers.
- [x] Keep model filtering behavior compatible with the existing calls table.

Verification:

- [x] `python -m compileall app`
- [x] JavaScript syntax checks for changed web modules.
- [x] API smoke checks for dashboard, state, and bad-limit fallback.

### Modular Refactor Sprint

Goal: move Token Lens from prototype layout to a clearer modular backend and
frontend structure while preserving current behavior.

Planned changes:

- [x] Draft dedicated refactor plan in `tools/project-memory/refactor-plan.md`.
- [x] Configure project-local task manager endpoint.
- [x] Start WorkNest sprint through manager API.
- [x] Baseline current API contracts and syntax checks.
- [x] Refactor backend into core, storage, sources, services, and API modules.
- [x] Split frontend JavaScript into small static modules.
- [x] Update documentation and architecture memory.

Risks or dependencies:

- [x] Manager lifecycle confirmed through raw intake read/start/complete
      endpoints.
- [ ] Preserve existing API response contracts for the current web UI.

Verification:

- [x] `python -m compileall app`
- [x] JavaScript syntax checks for changed web modules.
- [x] `git diff --check`

### Refactor Follow-Up: Stability And Extensibility

Goal: make the new modular boundaries safer to change and cheaper to extend.

Planned changes:

- [x] Rework browser auto-refresh to poll `GET /api/state` and reload dashboard
      data only when the state version changes.
- [x] Add API contract or smoke tests around current response shapes using
      project-owned sample data.
- [x] Harden API query parsing, especially invalid or out-of-range `limit`
      values.
- [x] Add background import observability for last run time, stats, status, and
      captured error summaries.
- [x] Reduce parser row-building duplication after parser fixtures are in
      place.
- [x] Introduce a source adapter interface when a second source or importer
      cleanup makes that abstraction useful.

Risks or dependencies:

- [x] Preserve existing API response contracts for the current web UI.
- [ ] Keep verification on sample or project-owned data unless the user gives a
      concrete external path/action.

Verification:

- [x] `python -m compileall app`
- [x] JavaScript syntax checks for changed web modules.
- [x] API smoke checks for changed endpoints.
- [x] `python -m unittest tests.test_api_contracts`

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
