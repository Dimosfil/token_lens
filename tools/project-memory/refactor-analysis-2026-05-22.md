# Refactor Analysis 2026-05-22

Goal: identify small, low-risk refactor steps after the prototype-to-modular
migration.

## Current Shape

- Backend boundaries are already useful: API, services, storage, source
  adapters, and core config are separated.
- Compatibility shims in `app/config.py`, `app/db.py`, `app/importer.py`, and
  `app/server.py` keep old commands working.
- The largest backend pressure point is `app/storage/queries.py`: it combines
  range normalization, bucket math, JSON payload compaction, SQL analytics, task
  detail shaping, data-state shaping, and dashboard composition.
- The largest frontend pressure points are `web/app.js` and
  `web/js/table-resize.js`: the entrypoint owns settings, date/range rules,
  refresh state, rendering orchestration, and event binding; the table utility
  owns persistence keys, column identity, ordering, resizing, scroll sync, drag,
  and mutation observation.
- `web/js/render/tasks.js` and `web/js/render/turns.js` duplicate HTML escaping,
  id detection, task-name fallback, and task-detail tooltip formatting.
- API handler routing is readable, but `AnalyticsHandler` still contains legacy
  instance methods that call `app.storage.queries` directly and are not used by
  the current request path.

## Recommended Atomic Refactor Order

1. Extract shared frontend HTML helpers.
   - Add `web/js/render/html.js` or `web/js/dom.js` for `escapeHtml`, `value`,
     `looksLikeId`, `taskName`, and task tooltip helpers.
   - Update `tasks.js`, `turns.js`, and optionally `detail-modal.js`.
   - Verify JavaScript syntax and unchanged dashboard/detail behavior.

2. Split dashboard UI state from `web/app.js`.
   - Move page-settings persistence, date conversion, range/bucket/task-mode
     rules, and query building into `web/js/dashboard-state.js`.
   - Keep `web/app.js` as orchestration: bind events, refresh, render.
   - Verify custom range, bucket disabling, chart mode, and task mode.

3. Split table resize by responsibility.
   - Extract storage/key helpers first.
   - Then extract column identity/order helpers.
   - Then extract scroll sync.
   - Leave `initResizableTables()` as the stable public API.
   - Verify resize, column reorder, table width, and horizontal scroll
     persistence after each extraction.

4. Split query support helpers from `app/storage/queries.py`.
   - Move range/bucket/task-mode normalization into
     `app/storage/query_params.py`.
   - Move JSON decode and compact event payload helpers into
     `app/storage/payloads.py` or `app/services/detail_payloads.py`.
   - Update tests around range, bucket, task mode, and detail compaction.

5. Split analytics queries by endpoint family.
   - Keep public imports stable via `app/storage/queries.py` initially.
   - Move summary/daily/models/state to a metrics module.
   - Move turns/tasks/task buckets/task detail to a tasks module.
   - Move dashboard composition either to `app/services/analytics_service.py` or
     a dedicated dashboard query module.
   - Verify API contract tests after each move.

6. Clean API handler legacy methods.
   - Remove unused `dashboard`, `summary`, `daily`, `turns`, `tasks`, `models`,
     and `data_state` instance methods after confirming tests do not depend on
     them.
   - This is small and safe, but do it after query module moves so failures are
     easier to attribute.

7. Prepare token-suspect analysis as a new vertical slice.
   - Add measurement helpers that operate on parsed `event_json` without
     changing import behavior.
   - Add a query/service/API endpoint only after helper tests exist.
   - Keep external Codex logs read-only and store analysis output only in the
     Token Lens database if persistence is needed.

## Verification Baseline

- Backend: `python -m compileall app`
- API contracts: `python -m unittest discover -s tests`
- Frontend: JavaScript syntax checks for changed modules.
- Runtime: restart with `.\start.ps1 -Restart` and smoke-check changed API/UI
  paths when backend or frontend contracts change.

