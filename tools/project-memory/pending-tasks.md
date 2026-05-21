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

### Dashboard Human Task Labels

Goal: reduce visible hash/id noise in dashboard tables and keep one useful project/task identifier.

Planned changes:

- [x] Replace visible technical id columns with one human task/project column.
- [x] Keep full ids available in hover details for troubleshooting.
- [x] Verify JavaScript syntax.

Risks or dependencies:

- [x] Use only data already imported into the analytics database.
- [x] Preserve API compatibility by changing renderers only.

Verification:

- [x] JavaScript syntax checks for changed render modules.

### Dashboard Horizontal Table Scroll

Goal: keep wide dashboard tables usable when source/id fields exceed the viewport.

Planned changes:

- [x] Make resizable tables expose a real horizontal overflow width.
- [x] Add a synchronized top horizontal scrollbar.
- [x] Verify JavaScript syntax.

Risks or dependencies:

- [x] Preserve current column resize behavior and stored widths.
- [x] Keep top and bottom scroll positions synchronized.

Verification:

- [x] JavaScript syntax checks for changed table resize module.

### Dashboard Resizable Source Fields

Goal: make dashboard tables easier to inspect by resizing columns and exposing
additional source identifiers already stored in the analytics database.

Planned changes:

- [x] Add table column resize handles to the web UI.
- [x] Add extra source/id fields to task and call tables.
- [x] Verify Python and JavaScript syntax.

Risks or dependencies:

- [x] Preserve current API compatibility by adding fields instead of removing
  existing ones.
- [x] Do not inspect external Codex logs for this UI-only pass.

Verification:

- [x] `python -m compileall app`
- [x] JavaScript syntax checks for changed modules.
- [x] `python -m unittest discover tests`

### Desktop Mini Taskbar Icon

Goal: make the desktop mini client show the project logo in the Windows title
bar and taskbar.

Planned changes:

- [x] Add a Windows-friendly `.ico` asset derived from `Logo.png`.
- [x] Configure Tk to use the `.ico` before falling back to `Logo.png`.
- [x] Restart the mini client and verify the app still launches.

Risks or dependencies:

- [x] Preserve the existing PNG logo path for the web UI.
- [x] Keep the launcher behavior unchanged.

Verification:

- [x] `python -m py_compile desktop\mini_client.py`
- [x] Relaunch `desktop-mini.ps1`.

### Attach Logo Asset

Goal: use the root `Logo.png` in the web dashboard and desktop mini client.

Planned changes:

- [x] Expose the root logo through the local static server.
- [x] Add the logo to the web page chrome and favicon.
- [x] Use the logo as the desktop mini client window icon.
- [x] Verify Python syntax and static asset serving.

Risks or dependencies:

- [x] Reuse the existing root asset instead of duplicating it.
- [x] Preserve current UI behavior and existing user changes.

Verification:

- [x] `python -m compileall app desktop`
- [x] Smoke-check `GET /Logo.png`.

### Dashboard Full Empty Buckets

Goal: make hourly/week chart data include empty periods so week + hour renders
168 bars instead of only non-empty hours.

Planned changes:

- [x] Inspect current bucket aggregation and trimming behavior.
- [x] Fill missing chart buckets with zero-valued rows.
- [x] Keep hourly chart labels readable with horizontal scrolling.
- [x] Verify backend syntax and API output count.

Risks or dependencies:

- [x] Preserve existing dashboard response fields.
- [x] Keep analytics database reads read-only.

Verification:

- [x] `python -m compileall app`
- [x] Smoke-check `/api/dashboard?range=7d&bucket=hour` returns 168 daily rows.

### Desktop Mini Client

Goal: add a minimal desktop window that shows recent token usage rows without
opening the browser.

Planned changes:

- [x] Inspect existing API fields for the mini table.
- [x] Add a dependency-free Tkinter mini client.
- [x] Add a PowerShell launcher that starts the backend if needed.
- [x] Verify Python syntax and basic launcher behavior.

Risks or dependencies:

- [x] Preserve the existing web UI and API contracts.
- [x] Keep the client read-only except for using the existing backend startup.

Verification:

- [x] `python -m py_compile desktop\mini_client.py`
- [x] Smoke-check `GET /api/tasks?limit=4`.

Follow-up:

- [x] Launch the mini client without leaving a PowerShell window open.

### Dashboard Date Range Defaults And Bucket Guard

Goal: make the dashboard use a global date range by default and keep chart
bucket choices compatible with the selected range.

Planned changes:

- [x] Inspect current range and bucket implementation.
- [x] Add a one-hour range and make week/day the default API and UI selection.
- [x] Prevent chart bucket selections that are larger than the selected range.
- [x] Render all buckets for the selected range instead of only the last 24.
- [x] Verify Python and JavaScript syntax.

Risks or dependencies:

- [x] Preserve existing dashboard response shapes.
- [x] Keep all filtering read-only against the analytics database.

Verification:

- [x] `python -m compileall app`
- [x] JavaScript syntax checks for changed web modules.
- [x] Restart local server and smoke-check default, `1h/month`, and
      `365d/month` dashboard queries.

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
### Daily Bar Tooltips

Goal: show detailed bucket data when hovering chart bars.

Planned changes:

- [x] Inspect daily chart rendering and available aggregate fields.
- [x] Add hover/focus tooltip markup for each daily bar.
- [x] Style tooltip without shifting the chart layout.
- [x] Verify JavaScript syntax and whitespace.

Risks or dependencies:

- [x] Preserve the existing chart mode toggle and compact chart layout.
- [x] Keep tooltip data derived from existing dashboard payload fields.

Verification:

- [x] `node --check web\js\render\daily.js`
- [x] `git diff --check`
