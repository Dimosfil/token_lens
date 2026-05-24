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

### Dashboard Tabs For OpenCode Expansion

Goal: add a tab switcher that preserves the current Codex dashboard as the
default working view and creates a separate OpenCode expansion surface.

Planned changes:

- [x] Wrap the existing dashboard in a Codex tab without changing its controls.
- [x] Add an OpenCode tab placeholder for the upcoming orchestrator analytics.
- [x] Preserve the selected tab across refreshes.
- [x] Verify frontend syntax and start the local desktop/browser app.

### OpenCode Usage Ingest

Goal: connect the current OpenCode setup to Token Lens so OpenCode usage events
can be collected into the analytics database without changing the Codex import
path.

Planned changes:

- [x] Add a Token Lens ingest endpoint for OpenCode plugin events.
- [x] Normalize OpenCode usage payloads into existing turn rows.
- [x] Add a local OpenCode plugin under the explicit OpenCode config path.
- [x] Enable the plugin in the current OpenCode config without removing existing plugins.
- [x] Verify with a sample event, tests, and a backend restart.

### Query Support Helper Split

Goal: move range/bucket/task-mode and detail payload helpers out of
`app/storage/queries.py` while preserving public query behavior.

Planned changes:

- [x] Add `app/storage/query_params.py` for range, bucket, and task mode helpers.
- [x] Add `app/storage/payloads.py` for JSON decoding and raw event compaction.
- [x] Update `app/storage/queries.py` to import the extracted helpers.
- [x] Verify backend syntax and API contract tests.

### Table Resize Module Split

Goal: split `web/js/table-resize.js` by responsibility while preserving the
stable `initResizableTables()` API.

Planned changes:

- [x] Extract table settings storage/key helpers.
- [x] Extract column identity/order helpers.
- [x] Extract scroll sync helpers.
- [x] Verify JavaScript syntax and static module serving.

### Dashboard UI State Split

Goal: move dashboard state/range/query rules out of `web/app.js` while
preserving current dashboard behavior.

Planned changes:

- [x] Add a dedicated dashboard state module for page settings, range/bucket
      rules, task mode rules, and dashboard query building.
- [x] Keep `web/app.js` focused on event binding, refresh, and rendering.
- [x] Verify changed JavaScript modules and smoke-check dashboard state paths.

### Project Refactor Analysis 2026-05-22

Goal: review current backend/frontend module boundaries and identify the
smallest safe refactor steps for future work.

Planned changes:

- [x] Map current entry points, module sizes, and compatibility shims.
- [x] Review backend service, storage, source, and API boundaries for atomic
      extraction opportunities.
- [x] Review frontend entrypoint, renderers, and table utilities for atomic
      extraction opportunities.
- [x] Summarize recommended refactor order with verification checks.

### Frontend Shared Render Helpers

Goal: remove duplicated task/HTML helper logic from task and turn renderers
without changing dashboard behavior.

Planned changes:

- [x] Add a small shared render helper module.
- [x] Use shared helpers in task and turn table renderers.
- [x] Verify changed JavaScript modules.

### Table Settings Persistence

Goal: stop saved table widths and column order from being applied to the wrong
columns after reordering, refreshing, or opening detail dialogs.

Planned changes:

- [x] Fix column resize to use the header's current position instead of the
      position captured during initial page load.
- [x] Give unrelated dialog tables separate persisted settings keys.
- [x] Persist page-level controls such as range, bucket, chart mode, task mode,
      and custom dates across page refresh.
- [x] Save resized columns by stable column key instead of any visual index.
- [x] Persist full table-width snapshots and horizontal scroll positions.
- [x] Let resizable tables use user-defined widths beyond the default cell
      max-width.
- [x] Verify frontend syntax and restart/smoke-check the app.

### Desktop Dotnet Merge And Task Time

Goal: merge two desktop .NET projects into one .NET Core desktop app, use the
root logo asset, and add task time to the task table.

Planned changes:

- [x] Add elapsed task time to the existing Token Lens task tables.
- [x] Add elapsed task time to the Python mini desktop client.
- [x] Verify backend contracts, frontend syntax, and restart/smoke-check the app.

### Dashboard Task Display Mode

Goal: add a dashboard switch between bucket-aggregated task rows and individual
task rows, with individual rows available only for the one-hour and one-day
ranges.

Planned changes:

- [x] Add dashboard API support for a safe `task_mode` parameter.
- [x] Add UI controls and table rendering for aggregate vs individual task rows.
- [x] Verify backend contracts, frontend syntax, and restart/smoke-check the app.

### Auto Refresh Fetch Errors Under Load

Goal: prevent transient `Failed to fetch` errors when auto refresh overlaps
with heavier dashboard or bucket/detail queries.

Planned changes:

- [x] Add UI request tracking so `/api/state` polling skips while the app is
      already loading user-requested data.
- [x] Tune SQLite connections for friendlier concurrent reads/writes.
- [x] Verify syntax, tests, restart, and smoke-check the affected endpoints.

### Call Detail Payload Size

Goal: make the call detail modal open reliably for rows whose captured raw
response event contains very large instructions/tools metadata.

Planned changes:

- [x] Compact task-detail raw event payloads before returning them to the UI.
- [x] Add a regression test for oversized event metadata.
- [x] Verify backend tests and restart/smoke-check the local server.

### Auto Refresh Missing Model Filter

Goal: stop dashboard auto refresh from failing when the model filter control is
not present in the current header layout.

Planned changes:

- [x] Make model option rendering tolerate the removed optional filter element.
- [x] Verify JavaScript syntax for the affected modules.

### Dashboard Task Column Order

Goal: let the dashboard task table keep `Status` at the end for now, support
manual column ordering, and prevent long text from visually overlapping the next
field.

Planned changes:

- [x] Move the task status column to the end.
- [x] Add persisted manual column ordering for the task table.
- [x] Clamp overflowing cell text inside its own column.
- [x] Verify frontend syntax and restart/smoke check if needed.

### All-Time Dashboard Tasks Table

Goal: make the dashboard's "Задачи целиком" table show tasks from every imported
day while keeping charts, summary cards, model calls, and model averages tied to
the selected time range.

Planned changes:

- [x] Let task queries opt into an all-time range.
- [x] Use the all-time task query in the dashboard payload.
- [x] Add a regression test for older tasks outside the selected range.

Verification:

- [x] `python -m compileall app`
- [x] `python -m unittest discover -s tests`

### Raw Event Capture And Token Suspects

Goal: make raw Codex response events a reliable source of truth for call details
and later token-waste analysis.

Planned changes:

- [x] Backfill or reimport older rows so existing calls can populate
      `event_json` when a raw Codex event exists.
- [x] Add an explicit raw event captured/missing indicator in the call detail
      modal.
- [x] Keep raw JSON visible in the UI instead of trying to normalize every
      request field upfront.
- [ ] Add a `Token suspects` table or endpoint that highlights likely waste:
      high input vs average, mostly cached input, many in-progress or zero-token
      calls, large instructions/tools/schema/metadata, previous-response chains,
      and repeated system context.
- [ ] Add an `Analyze token waste` action for a selected call that sends the
      full raw event plus computed measurements to the analyzer.

Risks or dependencies:

- [x] Confirm `event_json` is populated from Codex raw events before trusting AI
      analysis.
- [ ] Use the whole request/event object for analysis, not only visible
      request/response text.
- [ ] Preserve read-only access to external Codex logs and store analysis data
      only in Token Lens' own database.

Verification:

- [x] Reimport/backfill fills `event_json` for rows whose source log contains a
      response event.
- [x] Detail modal clearly distinguishes captured raw event data from missing
      raw event data.
- [ ] Suspect detection can be smoke-checked with database rows containing
      known large instructions/tools or previous-response context.

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

### Bucketed Dashboard Tasks

Goal: keep dashboard loading fast by showing task records only for the selected
range, grouped by the selected candle size, with a detail list per bucket.

Planned changes:

- [x] Add custom dashboard date range parameters.
- [x] Replace all-time dashboard tasks with bucketed task aggregates.
- [x] Move effort into the main task table and remove the duplicate model-calls UI.
- [x] Add a bucket detail modal listing tasks inside the selected candle.
- [x] Verify API contract tests and syntax checks.

Risks or dependencies:

- [x] Preserve existing task-detail behavior for individual task rows.
- [x] Avoid reading external Codex logs for verification.

Verification:

- [x] `python -m compileall app`
- [x] `node --check web\app.js`
- [x] `node --check web\js\render\tasks.js`
- [x] `python -m unittest discover -s tests`
- [x] Restarted with `.\start.ps1 -Restart`
- [x] HTTP smoke: `/api/state`, `/api/dashboard?range=1h&bucket=hour`,
      `/api/bucket-tasks?...`, and custom date dashboard query
