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

### Mini Client Server Process Leak 2026-07-27

Goal: prevent desktop recovery from accumulating parallel Token Lens servers.

Planned changes:

- [x] Stop only the leaked Token Lens Python process trees.
- [x] Reuse a still-running recovery child instead of spawning another server.
- [x] Require exclusive Windows ownership of the HTTP listening port.
- [x] Run focused tests and restart the full app set.

### Remote ai_logger Client 2026-07-15

Goal: forward Token Lens Python logging to the remote ai_logger ingest server
while preserving the existing rotating file log and local outage durability.

Planned changes:

- [x] Install the local editable ai_logger Python client package.
- [x] Load ignored project-local client environment configuration from the
      documented launchers.
- [x] Attach the optional native Python logging handler without replacing the
      existing file/stream handlers.
- [x] Configure a local fallback JSONL file and verify that a remote outage does
      not interrupt Token Lens or discard the attempted event.
- [x] Verify an accepted test event after the remote server exposes `/ingest`
      to this LAN client.
- [x] Run regression checks, restart the app set, and update the runtime
      integration contract.

### Import CPU and Launcher Diagnostics 2026-07-15

Goal: preserve enough local evidence to distinguish a CPU-heavy import from
concurrent Token Lens runtimes without logging private source contents.

Planned changes:

- [x] Add PID/thread context and per-source wall/CPU timings to runtime logs.
- [x] Record launcher process discovery and lifecycle decisions in a bounded
      project-local log.
- [x] Add focused regression coverage and document the observability contract.
- [x] Restart and verify one clean runtime through a real automatic import.

### Mini Stale Display Recovery 2026-07-13

Goal: prevent a transient limit/API error from freezing Mini on an old account
limit snapshot.

Planned changes:

- [x] Trace the stale visible values to the failed Tkinter callback queue.
- [x] Preserve worker exceptions until their main-thread callback executes.
- [x] Isolate failed UI callbacks so queue processing and scheduling continue.
- [x] Run focused tests, restart Mini, and verify current live limits.

### Mini Codex Limit Freshness 2026-07-11

Goal: keep Mini's Codex and Spark remaining limits aligned with the live Codex
account source during active agent usage.

Planned changes:

- [x] Confirm the backend returns the same live limits as the official balance.
- [x] Refresh Codex limits once per configured Mini polling cycle without
      reloading unchanged task rows.
- [x] Add focused regression coverage, restart Mini, and verify live values.

### Mini Client UI Thread Safety 2026-07-11

Goal: prevent intermittent Token Lens Mini freezes by keeping every Tkinter
operation on the main UI thread.

Planned changes:

- [x] Snapshot widget-backed request settings before starting HTTP workers.
- [x] Deliver worker results through a main-thread callback queue.
- [x] Add focused regression coverage for the thread boundary.
- [x] Run verification, restart only Mini, and confirm its window responds.

### Mini Client Poll Throttling 2026-07-11

Goal: prevent Mini from repeatedly blocking on Codex limit reads and rebuilding
limit widgets during unchanged 5-second poll cycles.

Planned changes:

- [x] Make unchanged-state polls skip source context refresh until a separate
      throttle interval elapses.
- [x] Keep manual refresh and changed data refresh behavior immediate.
- [x] Avoid worker-thread reads of active Tk/source state in stale-limit
      fallback.
- [x] Add a delayed auto-import mode so startup does not launch a heavy import
      automatically while records still update in the background.
- [x] Add focused regression coverage and restart the app set.

### Codex Terra Post-Sampling Usage 2026-07-11

Goal: show token usage for `gpt-5.6-terra` rows whose Codex logs record
post-sampling usage with a prefixed trace segment.

Planned changes:

- [x] Diagnose that Mini raw-only rows have `codex_threads` metadata but no
      matching `turns` usage rows.
- [x] Extend the Codex post-sampling parser to accept prefixed trace lines
      without parsing quoted response-output snippets.
- [x] Backfill already archived raw post-sampling usage rows into `turns`
      where parseable; current 2026-07-11 raw-only terra rows have no
      `total_usage_tokens` or parseable response usage markers in archived
      raw logs.
- [x] Run focused/full verification and restart the app set.

### API Handler Service Boundary Refactor 2026-07-01

Goal: enforce the API-to-service contract by removing legacy handler methods
that bypass the service layer and call storage queries directly.

Planned changes:

- [x] Confirm current routes use `analytics_service`.
- [x] Remove unused `AnalyticsHandler` storage-query compatibility methods.
- [x] Add a contract guard so the handler does not expose those legacy methods.
- [x] Run focused API contract tests plus compile/check verification.

### Codex Account Limit Normalizer Boundary 2026-07-01

Goal: separate Codex account-limit payload normalization and app-server process
lifecycle from cache and command-resolution orchestration.

Planned changes:

- [x] Move rate-limit payload normalization into a pure service helper module.
- [x] Keep `read_usage_limits()` behavior and existing service-level config
      controls unchanged.
- [x] Point focused normalization tests at the new module contract.
- [x] Move reusable app-server stdio client/process lifecycle into its own
      module contract.
- [x] Point process lifecycle tests at the new client module.
- [x] Run focused account/API tests plus compile/check verification.

### Codex Account Limit Stale Fallback 2026-07-01

Goal: keep visible Codex account limits stable when the local app-server
temporarily times out or returns no fresh data.

Planned changes:

- [x] Return the last successful account-limit snapshot as `stale` on transient
      read failures instead of clearing `groups`/`windows`.
- [x] Add desktop mini in-memory fallback for HTTP/backend read failures.
- [x] Show the last successful update time in desktop and browser limit widgets.
- [x] Add regression coverage for stale backend fallback and desktop helpers.
- [x] Run focused tests, syntax checks, and full test discovery.

### Codex Query State Metadata Refactor 2026-07-01

Goal: keep Codex thread-state metadata handling readable without changing
usage-log totals behavior.

Planned changes:

- [x] Extract task-detail Codex state lookup/application from the aggregate
      assembly path.
- [x] Preserve the invariant that `state_tokens_used` is reference metadata and
      never replaces usage-log `total_tokens`.
- [x] Run focused API contract tests plus compile/check verification.

### Detail Modal Request Token Comparison 2026-06-30

Goal: make the call-detail modal explain how the visible `Request` payload size
relates to the token totals shown in the table.

Planned changes:

- [x] Add an approximate request-token estimate derived from the request payload.
- [x] Compare that estimate with the row `Total` directly in the modal.
- [x] Surface short token-count labels near the payload copy buttons.

### Usage-Only Detail Accuracy 2026-07-17

Goal: make Codex post-sampling usage-only rows distinguish unavailable payloads
and token breakdowns from real zero values.

Planned changes:

- [x] Recover matching request and response payloads from archived raw events when available.
- [x] Mark usage-only rows as lacking a reliable input/cached/output/reasoning breakdown.
- [x] Render unavailable payloads and breakdown fields explicitly in the detail modal.
- [x] Clarify that Codex thread-state tokens are a session-level estimate.
- [x] Add focused regression coverage and run coherent-batch verification.

### Task Table Column Sorting 2026-07-17

Goal: let users sort task tables by any visible column while keeping the newest
task time first by default.

Planned changes:

- [x] Add stable typed sorting for task, bucket, text, time, and token columns.
- [x] Make task headers keyboard-accessible and show the active direction.
- [x] Keep the default separate-task and bucket order on finish time descending.
- [x] Preserve sorting across automatic dashboard refreshes.
- [x] Add focused verification, restart the app set, and verify the live API/UI assets.

### On-Demand Codex Transcript Payloads 2026-07-17

Goal: show Request and Response for usage-only Codex calls by reading the exact
selected local session transcript without persisting private message text in the
analytics database.

Planned changes:

- [x] Resolve only the transcript filename matching the selected analytics thread ID.
- [x] Parse user and assistant messages inside exact `task_started` turn boundaries.
- [x] Fill only missing detail payloads and keep SQLite rows unchanged.
- [x] Reject unsafe thread IDs and tolerate unknown/malformed transcript records.
- [x] Add privacy documentation and focused parser/service regression coverage.
- [x] Verify the current chat end to end, restart the app set, and inspect live API metadata without logging payload text.

### Source-Specific Analytics Separation 2026-06-30

Goal: keep Codex and OpenCode query behavior separate so source tabs cannot
break each other's task aggregation semantics.

Planned changes:

- [x] Split Codex task list and bucket-detail aggregation from OpenCode task
      aggregation.
- [x] Aggregate Codex visible task rows by chat/thread with call and token sums.
- [x] Keep OpenCode on its own session/message aggregation path.
- [x] Expand `chat:{thread_id}` detail rows to all imported calls for the chat.
- [x] Add regression tests for Codex and OpenCode per-chat aggregation.

### Codex Token Usage Parser Hardening 2026-06-30

Goal: prevent Codex response text, command output, or test fixtures that mention
`codex.turn.token_usage.*` or `post sampling token usage` from being imported
as real token usage unless they appear in the initial telemetry trace.

Planned changes:

- [x] Verify the bad 743544-token row against the archived/source log record.
- [x] Restrict token-usage parsing to real telemetry spans or standalone
      token-usage log events.
- [x] Add regression tests for quoted token-usage snippets in response output.
- [x] Remove already imported false-positive Codex usage rows from the local
      analytics database and recheck the dashboard.
- [x] Add support for Codex post-sampling `total_usage_tokens` estimates.
- [x] Track the last scanned Codex source log id separately from imported turn
      ids so skipped rows are not rescanned forever.
- [x] Remove zero-token response events and current false positives from the
      local analytics database, then backfill current-day Codex estimates.
- [x] Run focused/full verification and update durable import contract memory.

### Persistent Codex Account Limit Client 2026-06-30

Goal: query Codex account limits through one reusable local
`codex app-server --stdio` process instead of spawning a process for every
uncached HTTP request.

Planned changes:

- [x] Add a persistent stdio client with request serialization, timeout
      handling, restart-on-failure, and Windows process-tree cleanup.
- [x] Keep configuration boundaries for cache, request timeout, idle timeout,
      and optional persistent mode.
- [x] Add regression tests for process reuse, stale-client restart, and cleanup.
- [x] Update architecture memory and run focused/full verification.

### Raw-Only Codex Task Display Correction 2026-06-30

Goal: stop showing missing Codex usage as real zero-token model calls.

Planned changes:

- [x] Mark raw-only Codex task rows as missing usage data in the API contract.
- [x] Show unknown token values as `-` in the web dashboard and desktop mini.
- [x] Keep raw event counts separate from model call counts.
- [x] Run focused regression tests and restart the app set.

### Backend Freshness And Connection Indicators 2026-06-26

Goal: make stale Token Lens data and backend connectivity visible in both the
web dashboard and desktop mini client.

Planned changes:

- [x] Diagnose why the visible tables stopped at 2026-06-25 while raw logs
      continued updating on 2026-06-26.
- [x] Make Codex usage import process only new log rows after the last imported
      Codex usage source id.
- [x] Add a backend connection indicator to the web dashboard.
- [x] Add a backend connection indicator to Token Lens Mini.
- [x] Run focused tests, restart the app set, and verify live endpoints.

### Codex Raw Activity Visibility 2026-06-26

Goal: show recent Codex chats in Mini even when Codex logs contain activity but
no token-usage completion record yet.

Planned changes:

- [x] Confirm `Update ht,en` has raw Codex activity but no parsed usage turn.
- [x] Preserve safe raw-log display metadata for thread names and models.
- [x] Add raw-only Codex task fallback rows with zero tokens.
- [x] Verify Mini/API show the raw-only row after restart.

### OpenCode Spend Aggregation Correction 2026-06-25

Goal: make OpenCode spend and task totals comparable to provider billing by
summing request rows instead of using only the latest message row in a session.

Planned changes:

- [x] Verify the local OpenCode DB has per-request `message.data.tokens` rows
      and session aggregates equal the sum of those rows.
- [x] Change OpenCode summary and task queries to sum all scoped request rows.
- [x] Keep latest row metadata for display labels while using aggregate token
      and cost totals.
- [x] Add an OpenCode import rowid lookback so recently updated message rows are
      reprocessed after the cursor advances.
- [x] Run focused and full regression tests, reimport current OpenCode rows, and
      restart the app set.

### Data Refresh Freshness Module 2026-06-25

Goal: make Token Lens data freshness explicit so mini and web refreshes do not
silently show stale imported rows.

Planned changes:

- [x] Extract import/update orchestration into a dedicated data refresh module.
- [x] Route server startup, background loop, API refresh, and mini refresh
      through that module.
- [x] Add tests for every public function in the refresh module.
- [x] Verify app restart and API freshness behavior.

### Mini Agent Tabs And Per-Agent Settings 2026-06-25

Goal: replace source toggle buttons with Codex/OpenCode tabs and persist table
settings separately per agent.

Planned changes:

- [x] Add per-agent settings helpers with migration from existing shared keys.
- [x] Replace source buttons with tabs.
- [x] Load/save rows, signal, sound, threshold, and columns per agent.
- [x] Add focused tests, run verification, and restart the app set.

### Mini Table Field Configuration 2026-06-25

Goal: let Token Lens Mini users choose visible table fields and show both short
date and minute-level date/time.

Planned changes:

- [x] Add configurable mini table column metadata and persisted visibility.
- [x] Add a Columns UI menu for toggling fields.
- [x] Add date/time column and focused tests.
- [x] Run verification and restart the app set.

### Mini Codex Chat Labels 2026-06-25

Goal: restore Codex chat names in Token Lens Mini without changing the
OpenCode task-label behavior.

Planned changes:

- [x] Expand Codex session-name loading for current JSONL metadata shapes.
- [x] Add focused regression coverage.
- [x] Run focused verification and restart the app set.

### Agent Launch Config Instructions 2026-06-24

Goal: make project-local instructions unambiguous for agents preparing a clean
Token Lens checkout with missing local source config.

Planned changes:

- [x] Add an agent launch-preparation section to `AGENTS.md`.
- [x] Add a runbook checklist for writing `config.local.json` before launch.
- [x] Document Codex SQLite candidate priority and privacy limits.
- [x] Mirror the source-path contract in README and connected-project memory.

### Codex Limit Verification Instructions 2026-06-24

Goal: make agents verify Codex 5h/weekly/Spark limits through the correct local
Codex app-server path instead of confusing them with OpenAI API key usage.

Planned changes:

- [x] Document the Codex limit source of truth in `AGENTS.md`.
- [x] Add runbook commands for `/api/usage-limits`.
- [x] Explain expected `groups`/`windows` response shape and Spark bucket.
- [x] Record that OpenAI API/Admin API and SQLite analytics are separate data
      sources from Codex account limits.

### Codex Launcher Discovery Hardening 2026-06-24

Goal: prevent agents and runtime checks from misclassifying WindowsApps aliases
as missing Codex installations.

Planned changes:

- [x] Ignore WindowsApps Codex aliases during launcher discovery.
- [x] Persist a usable discovered `codex_app_server_command` to local config.
- [x] Return actionable `/api/usage-limits` errors for bad launcher overrides.
- [x] Add regression tests and update agent-facing launch/limit instructions.

### Dashboard Local Time Default 2026-06-24

Goal: make dashboard time buckets use local time by default while keeping UTC
available as an explicit switch.

Planned changes:

- [x] Add a dashboard time-mode parameter and local/UTC bucket expressions.
- [x] Add a web UI switch that defaults to local time and preserves UTC choice.
- [x] Add focused regression coverage for time-mode normalization/bucketing.
- [x] Run focused verification.

### OpenCode Cumulative Chat Rows 2026-06-24

Goal: show OpenCode cumulative usage as one chat/task row per session instead
of one row per message snapshot with repeatedly accumulated token totals.

Planned changes:

- [x] Inspect current OpenCode rows and confirm totals are cumulative per
      `thread_id`.
- [x] Add OpenCode-specific task aggregation that uses the latest chat snapshot.
- [x] Add regression coverage for OpenCode task rows.
- [x] Run focused verification and restart the app set.

### Mini OpenCode Chat Labels 2026-06-24

Goal: make Token Lens Mini show useful OpenCode chat labels after cumulative
chat rows are grouped correctly.

Planned changes:

- [x] Inspect current mini label selection and OpenCode task rows.
- [x] Preserve meaningful OpenCode chat titles and use timestamp fallback only
      when no human title is available.
- [x] Add focused helper tests.
- [x] Run focused verification.

### Local Source Path Configuration 2026-06-24

Goal: make Token Lens portable to new machines without hard-coded Codex/OpenCode
source paths in code or committed defaults.

Planned changes:

- [x] Move committed external source defaults to blank portable config values.
- [x] Add runtime Codex source validation and skip unavailable sources cleanly.
- [x] Add an interactive local source configuration script for `config.local.json`.
- [x] Document the local configuration contract and add focused tests.
- [x] Support Codex session names from a JSONL file, sessions directory, or glob.
- [x] Auto-discover standard Codex source locations when local config is blank.
- [x] Persist discovered blank or stale source paths to ignored `config.local.json`.
- [x] Auto-discover standard OpenCode DB and token-tracker source locations.
- [x] Auto-discover the Codex CLI command for live account-limit reads.

### Mini Settings Corruption Recovery 2026-06-24

Goal: keep Token Lens Mini UI settings durable even when the primary settings
file is corrupted or partially written.

Planned changes:

- [x] Inspect the current settings file and load/save behavior.
- [x] Add backup-based settings recovery and repair.
- [x] Add focused tests for corrupted primary settings recovery.
- [x] Restore a valid local settings file and verify restart behavior.

### OpenCode Pull Import 2026-06-21

Goal: bring in the friend's OpenCode/DeepSeek file-based usage import without
regressing the existing OpenCode dashboard UI or background import logging.

Planned changes:

- [x] Compare the copied OpenCode implementation with current local behavior.
- [x] Add OpenCode DB/JSONL import state, parsers, and import orchestration.
- [x] Preserve current Codex import logging while adding OpenCode background import.
- [x] Add focused tests for OpenCode parser/state behavior.
- [x] Run compile and unittest checks.

### Mini Settings Startup Guard 2026-06-20

Goal: prevent Token Lens Mini from overwriting saved settings with startup
defaults when settings cannot be loaded or the UI is still initializing.

Planned changes:

- [x] Inspect current mini settings load/save behavior.
- [x] Add a startup guard around automatic settings persistence.
- [x] Add focused tests for settings load status and overwrite protection.
- [x] Run syntax and helper tests, then restart the affected app set.

### Windows Desktop Autostart 2026-06-20

Goal: add Windows startup autostart for the Token Lens desktop app through the
standard project launcher.

Planned changes:

- [x] Inspect current autostart and desktop launch scripts.
- [x] Point the hidden Startup launcher at `start.ps1`.
- [x] Install or refresh the Windows Startup shortcut.
- [x] Verify shortcut target and app startup.

### Desktop Limit Bar Full Marker 2026-06-19

Goal: make Token Lens Mini account-limit bars clearly show which windows are
fully available.

Planned changes:

- [x] Inspect the current desktop mini limit-bar drawing.
- [x] Add a stronger full-state visual treatment and end marker.
- [x] Run focused syntax and helper tests.
- [x] Relaunch the desktop mini client.

### Limit Widget 2026-06-18

Goal: show real Codex account usage limits from `codex app-server` as a compact
web dashboard widget while keeping the desktop mini client focused on plain
usage rows.

Planned changes:

- [x] Inspect current dashboard payload, web layout, and mini-client row UI.
- [x] Confirm local analytics is the wrong data source for account limits.
- [x] Include every `rateLimitsByLimitId` bucket, including GPT-5.3-Codex-Spark.
- [x] Add a small account-limits API endpoint for desktop and browser reuse.
- [x] Render account remaining percentages and reset times in the web dashboard.
- [x] Show desktop mini limits as plain text rows.
- [x] Run focused syntax and smoke checks.

### Mini Settings Persistence 2026-05-28

Goal: persist Token Lens Mini settings across app restarts.

Planned changes:

- [x] Locate current mini UI controls and launch defaults.
- [x] Add a local settings file under ignored app data.
- [x] Save row, signal, threshold, enabled state, and window settings from the UI.
- [x] Load saved settings on startup without breaking command-line defaults.
- [x] Run focused syntax checks.

### Mini Token Signal 2026-05-28

Goal: add an optional system alert in Token Lens Mini when `Total / Call`
exceeds a user-selected threshold.

Planned changes:

- [x] Locate the desktop mini UI and refresh flow.
- [x] Add threshold, signal selection, and enable/disable controls near Refresh.
- [x] Trigger the selected system signal when refreshed rows exceed the threshold.
- [x] Preview the selected system signal when the signal dropdown changes.
- [x] Run focused syntax or smoke checks.

### Mini Signal New Rows 2026-05-29

Goal: make Token Lens Mini signal only for newly observed rows over the
threshold and visually mark rows currently over the threshold.

Planned changes:

- [x] Track per-row signal identity instead of re-alerting on old visible rows.
- [x] Highlight visible rows whose `Total / Call` exceeds the current threshold.
- [x] Run focused syntax checks for the desktop mini client.

### Windows Autostart Refresh 2026-05-27

Goal: install Token Lens Windows startup entry and launch both web server and
desktop mini client.

Planned changes:

- [x] Point autostart at the desktop launcher that also starts the web server.
- [x] Install or refresh the Windows Startup shortcut.
- [x] Start the local web server and desktop mini client.
- [x] Verify the web URL responds.

### Instruction Kit Update 2026-05-27

Goal: update the copied `general-instructions` kit from `2026.05.20.6` to
`2026.05.27.1`.

Planned changes:

- [x] Apply pending instruction migrations to local copied instruction files.
- [x] Record applied migration metadata after verification.
- [x] Run update checks and inspect scoped diffs.
- [!] Commit and push only instruction-kit update changes if safe.

### Local App Autostart 2026-05-25

Goal: start Token Lens locally and add a Windows autostart entry for the app.

Planned changes:

- [x] Start or restart the local Token Lens server.
- [x] Identify the smallest local autostart mechanism.
- [x] Add a scoped autostart helper or shortcut.
- [x] Verify the server URL and autostart target.

### OpenCode Dashboard Parity

Goal: make the OpenCode tab use the same dashboard surface as Codex while
querying OpenCode-only analytics.

Planned changes:

- [x] Reuse the Codex dashboard DOM for both source tabs.
- [x] Route dashboard, refresh, bucket detail, and polling through the active
      source.
- [x] Remove the outdated OpenCode placeholder view.
- [x] Verify frontend syntax and API smoke paths.

### Mini OpenCode Cost Surface

Goal: make Token Lens Mini switch between Codex account-limit context and
OpenCode pay-per-token cost context without showing Codex limits on OpenCode.

Planned changes:

- [x] Reuse the mini source switcher to decide which top widget to render.
- [x] Show Codex account limit bars only for the Codex source.
- [x] Show OpenCode cost, token, and call totals from source-filtered dashboard
      analytics.
- [x] Verify desktop helpers, API smoke paths, and app restart.

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

### Instruction Kit Update 2026-06-06

Goal: update the copied `general-instructions` kit from `2026.06.05.1` to
`2026.06.06.4`.

Planned changes:

- [x] Apply Windows tool setup and rule-finish guidance.
- [x] Apply task-manager active-task lifecycle guidance.
- [x] Apply task-manager add-sprint guidance.
- [x] Apply agent service guide endpoint guidance.
- [x] Verify metadata, diffs, and instruction-kit status.

### Chart Scroll To Latest

Goal: when the dashboard chart is wider than the viewport, scroll it to the
latest bucket after page load or dashboard refresh.

Planned changes:

- [x] Scroll the daily chart to its right edge after rendering non-empty data.
- [x] Verify JavaScript syntax and lightweight behavior.

### Instruction Kit Update 2026-06-08

Goal: update the copied `general-instructions` kit from `2026.06.06.4` to
`2026.06.08.2`.

Planned changes:

- [x] Apply relative/shared source path guidance.
- [x] Apply canonical GitHub source repo guidance.
- [x] Verify metadata, PowerShell parsing, diffs, and instruction-kit status.
- [!] Commit and push were blocked by pre-existing unrelated untracked files.

### Instruction Kit Update 2026-06-09

Goal: update the copied `general-instructions` kit from `2026.06.08.2` to
`2026.06.09.1`.

Planned changes:

- [x] Add configuration-boundary guidance to local agent instructions.
- [x] Run a targeted hard-coded configuration audit.
- [x] Move local Codex source paths to ignored `config.local.json`.
- [x] Replace legacy task-manager runtime URL with a service-id marker.
- [!] Defer cleanup of historical project-memory notes that mention old local
      task-manager URLs.
- [x] Record applied migration metadata.
- [x] Verify diffs and instruction-kit status.
- [!] Commit and push were blocked by pre-existing unrelated untracked files.

### Instruction Kit Update 2026-06-11

Goal: update the copied `general-instructions` kit from `2026.06.09.1` to
`2026.06.11.5`.

Planned changes:

- [x] Add repository cleanup and database classification guidance.
- [x] Add feature workflow contract and planning hierarchy guidance.
- [x] Add project-local feature workflow contract template.
- [x] Add `gi manager`/`gi tm` config-service resolution guidance.
- [x] Record applied migration metadata.
- [x] Verify diffs and instruction-kit status.

### Instruction Kit Update 2026-06-17

Goal: update the copied `general-instructions` kit from `2026.06.11.5` to
`2026.06.16.11`.

Planned changes:

- [x] Apply task-manager sync and GI command guidance.
- [x] Add portable project-memory/RAG structure and helper files.
- [x] Add semantic retrieval and local Chroma adapter guidance.
- [x] Record applied migration metadata.
- [x] Verify diffs, generated artifact ignores, and instruction-kit status.
- [!] Commit and push blocked by pre-existing unrelated untracked image/icon
      backup files in the working tree.
- [!] Commit and push were blocked by pre-existing unrelated untracked files.

### Instruction Kit Update 2026-06-18

Goal: update the copied `general-instructions` kit from `2026.06.16.11` to
`2026.06.18.4`.

Planned changes:

- [x] Apply contract-based service self-registration guidance.
- [x] Add post-launch verification requirements for `gi reboot` / `gi restart`.
- [x] Replace active `gi root rebuild` wording with `gi rebuild` plus
      `gi tools rebuild` / `gi rag rebuild`.
- [x] Add thematic, intent-preserving `gi summary` handoff guidance.
- [x] Update RAG rebuild command metadata to `gi tools rebuild`.
- [x] Record applied migration metadata.
- [x] Verify no pending instruction migrations and run `git diff --check`.
- [x] Commit and push scoped instruction-kit changes after a separate
      `ги пуш` request, leaving unrelated working-tree files untouched.

### Instruction Kit Update 2026-06-19

Goal: update the copied `general-instructions` kit from `2026.06.18.4` to
`2026.06.19.2`.

Planned changes:

- [x] Apply RAG retrieval eval check guidance.
- [x] Apply connected-projects register guidance.
- [x] Apply plain inline checkbox marker guidance for chat selections.
- [x] Apply default English/Russian unified-language fallback.
- [x] Apply full project app-set restart guidance.
- [x] Apply `gi start sprint` task-manager routing guidance.
- [x] Record applied migration metadata.
- [x] Verify diffs, RAG impact, and instruction-kit status.
- [!] Commit and push scoped instruction-kit changes if not blocked by
      pre-existing unrelated working-tree changes.

### Module Test Expansion 2026-06-19

Goal: add practical regression tests across the Python modules, run the test
suite, and start the app.

Planned changes:

- [x] Inspect current module boundaries and existing API contract tests.
- [x] Add focused unit tests for parser, config, storage, API, and service
      helpers that can run without private local logs.
- [x] Run compile and unittest checks.
- [x] Start/restart the app with documented startup command and verify health.
- [x] Report remaining untested areas or blockers.

### Full App Reboot Contract 2026-06-19

Goal: make `gi reboot` / `gi restart` launch every documented Token Lens app,
including the web/API server and desktop mini client.

Planned changes:

- [x] Update `start.ps1` to manage server and mini-client processes with
      separate PID files.
- [x] Update runbook startup and smoke-check docs for the full app set.
- [x] Verify compile/tests, then run `.\start.ps1 -Restart`.
- [x] Verify server API and mini-client process/window signal.

### Instruction Kit Update 2026-06-19.3

Goal: update the copied `general-instructions` kit from `2026.06.19.2` to
`2026.06.19.3`.

Planned changes:

- [x] Apply per-app accounting requirements for `gi reboot` / `gi restart`.
- [x] Record applied migration metadata.
- [x] Verify diffs, RAG impact, and instruction-kit status.
- [!] Commit and push scoped instruction-kit changes if not blocked by
      pre-existing unrelated working-tree changes.

### Mini Client Single Window Fix 2026-06-19

Goal: make `gi reboot` / `gi restart` show only the Token Lens Mini window for
the desktop mini client, without an extra Python console window.

Planned changes:

- [x] Update `start.ps1` to launch the desktop mini client with GUI Python when
      available.
- [x] Update runbook startup notes for the single-window expectation.
- [x] Restart and verify web/API plus mini-client process/window state.

### Mini Client Server Self-Heal 2026-06-21

Goal: keep Token Lens Mini connected when the local API server exits and preserve enough logs to diagnose future exits.

Planned changes:

- [x] Add local API restart/retry behavior in the mini client for refused local connections.
- [x] Capture server stdout/stderr from project startup scripts.
- [x] Avoid noisy broken-client tracebacks from JSON responses.
- [x] Run focused tests and restart verification.

### Full Runtime Logging 2026-06-21

Goal: add production-style local logging for Token Lens server, imports, API failures, and mini-client recovery.

Planned changes:

- [x] Add shared rotating-file logging configuration.
- [x] Log server startup, import lifecycle, API errors, and client disconnects.
- [x] Log mini-client local server recovery events.
- [x] Document runtime logging behavior in project memory.
- [x] Run tests, restart, and verify log output.

### Codex Usage Import Format Fix 2026-06-24

Goal: make Codex usage import include the current token usage log format and
avoid double-counting duplicate usage rows.

Planned changes:

- [x] Compare dashboard totals with imported SQLite rows and source Codex log
      patterns.
- [x] Extend Codex reader/parser for token usage rows without
      `instrument_name`.
- [x] Deduplicate parsed token usage rows with a stable synthetic response id.
- [x] Add regression coverage and run focused verification.
- [x] Reimport and recheck 2026-06-24 totals.

### Codex State Total Display Fix 2026-07-01

Goal: stop Codex thread state token estimates from replacing real usage-log totals in task/detail summaries.

Planned changes:

- [x] Change Codex task/detail/summary aggregation so `total_tokens` and `total_tokens_per_call` use usage-log rows.
- [x] Preserve `state_tokens_used` as separate reference metadata when available.
- [x] Update UI labels to make log total primary and state estimate secondary.
- [x] Update regression tests and run focused verification.

### Mini Lightweight Poll State 2026-07-12

Goal: prevent Token Lens Mini from appearing permanently busy when the local
raw-log archive is large.

Planned changes:

- [x] Reproduce the delay and isolate it to the full `/api/state` raw-log
      aggregate.
- [x] Add a backward-compatible lightweight state mode for Mini polling.
- [x] Add focused regression coverage and verify endpoint latency after restart.

### Raw Log Current-Month Retention 2026-07-17

Goal: enforce the agreed policy that full `raw_logs.feedback_log_body` values
are retained only for the current calendar month while analytics rows and token
aggregates remain intact.

- [x] Stop Token Lens and record pre-maintenance row counts and file size.
- [x] Clear only non-empty raw bodies before the current month in bounded
      transactions, then compact the SQLite file.
- [x] Verify old bodies are empty, current-month bodies remain, and `turns` and
      `raw_logs` row counts are unchanged.
- [x] Add configured automatic current-month retention for future imports and
      month transitions.
- [x] Add focused tests, update the durable retention contract, restart the app,
      and verify live health/import status.

### Full Launcher Failure Recovery 2026-07-17

Goal: make `start.ps1` the reliable single entry point for the complete Token
Lens app set on Windows.

- [x] Use the lightweight API state route for startup health so a large raw-log
      archive cannot cause a false timeout.
- [x] Treat PyManager parent/child processes as one application tree and repair
      missing or stale PID files without creating duplicate trees.
- [x] Roll back only processes started by the current launcher invocation when
      API or Mini verification fails.
- [x] Require a live API response and a verified Mini window before reporting
      the full app set ready; include bounded error-log diagnostics on failure.
- [x] Add launcher contract checks, update the runbook, and verify a complete
      restart through `start.ps1 -Restart`.
