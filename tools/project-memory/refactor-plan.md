# Refactor Plan: Prototype To Modular Structure

Created: 2026-05-20
Status: active in WorkNest manager

## Active Sprint

- Manager: `http://127.0.0.1:4187`
- Intake id:
  `2026-05-20T08-26-23-898Z_unknown-agent_e640e5ac-96d3-49ef-8338-d1fcfcc6925b`
- Project card:
  `projects/token-lens/inbox/new_tasks/2026-05-20T08-26-23-898Z_unknown-agent_e640e5ac-96d3-49ef-8338-d1fcfcc6925b.md`
- Lifecycle status: `in_progress`
- Started: 2026-05-20T08:26:32.262Z

## Manager Intake Attempt

- [x] Configured project-local manager endpoint:
      `tools/project-memory/task-manager.json`.
- [x] Verified `GET http://127.0.0.1:4187/health` returns `200 OK` with
      `service=worknest-api` and `sprintContractVersion=1`.
- [!] Could not discover executable sprint/capabilities endpoints from the
      project-local copied instructions or manager API. Tested common
      `/sprints`, `/plans`, `/tasks`, `/capabilities`, `/workflow/*`,
      `/worknest/*`, `/api/*`, `/v1/*`, `/agent/*`, `/projects`, and
      `/contracts/*` routes; they returned `404 Route not found`.
- [!] Tried `http://127.0.0.1:5173` as an alternate manager URL on user
      request; no server responded on `/`, `/health`, `/api/health`, or common
      discovery routes.
- [!] Tried to create a temporary smoke-test task through
      `http://127.0.0.1:4187` on user request. The service is a Node process
      running `node src/server.js` and responds to `/health`, but tested task,
      intake, sprint, WorkNest, API, versioned API, RPC, and route-discovery
      paths returned `404 Route not found`; no test task was created.
- [x] User provided the raw intake endpoint. `POST /agent-intake/raw` accepted
      a smoke-test task and returned `201 stored` with id
      `2026-05-20T07-14-34-797Z_unknown-agent_c6b4a505-763e-426c-be53-dd09c7688f4f`.
- [x] `gi manager test` later confirmed raw lifecycle endpoints:
      `GET /agent-intake/raw/{id}`,
      `POST /agent-intake/raw/{id}/start`, and
      `POST /agent-intake/raw/{id}/complete`.
- [x] `gi manager test` re-run on 2026-05-20 created disposable no-op task
      `2026-05-20T15-07-58-962Z_unknown-agent_89da78c9-4709-44d3-aa7f-ca1055410951`,
      then verified read, start, complete, and final `done` readback.
- [!] After changing manager URL to `http://127.0.0.1:5173/`, `gi manager test`
      on disposable task
      `2026-05-20T15-10-04-390Z_unknown-agent_3c3b71eb-34ac-407d-8492-37700d1383d8`
      confirmed `/health` and raw create, but lifecycle `start` and `complete`
      returned `404 Not Found`; final readback did not expose expected lifecycle
      status.
- [x] `gi start sprint` created and started the refactor sprint intake with id
      `2026-05-20T08-26-23-898Z_unknown-agent_e640e5ac-96d3-49ef-8338-d1fcfcc6925b`.

## Goal

Move Token Lens from a compact prototype layout to a clearer modular project
structure while preserving current behavior, local-only operation, and existing
API response contracts.

## Planned Changes

- [x] Record current backend API endpoints and JSON response shapes.
- [x] Add a modular backend package layout for core config, storage, source
      adapters, services, API handlers, and background work.
- [x] Split Codex import logic into parser, thread-name loading, source reading,
      and import orchestration modules.
- [x] Split SQLite logic into connection, schema, repositories, and analytics
      query modules.
- [x] Split HTTP server responsibilities into server bootstrap, routing,
      response helpers, API handlers, and static serving.
- [x] Preserve existing `app.server` startup compatibility or update
      `start.ps1` with a compatibility shim.
- [x] Split `web/app.js` into small browser modules without adding a frontend
      build step.
- [x] Add focused tests or smoke checks for parser behavior, cost calculation,
      API shape, and Python/JavaScript syntax.
- [x] Update `README.md` and `tools/project-memory/architecture.md`.

## Execution Order

- [x] Baseline: inspect endpoint map and run compile/syntax checks.
- [x] Backend phase 1: create packages and move config/storage primitives.
- [x] Backend phase 2: refactor Codex source adapter and import service.
- [x] Backend phase 3: refactor analytics queries and HTTP API.
- [x] Frontend phase: split static JavaScript into modules.
- [x] Verification phase: run compile checks, JS syntax check, and local smoke
      checks against sample/project-owned data only.
- [x] Documentation phase: update project docs and memory.

## Risks Or Dependencies

- [x] Avoid changing JSON contracts consumed by `web/app.js`.
- [x] Avoid reading private external Codex data during verification unless the
      user explicitly asks for a concrete path/action.
- [x] Keep `data/`, logs, caches, and generated SQLite files out of commits.
- [x] Keep refactor scoped; no broad feature work during structure migration.

## Verification

- [x] `python -m compileall app`
- [x] JavaScript syntax check for changed web modules.
- [x] Analytics service smoke checks for dashboard and data-state payload shapes.
- [x] `git diff --check`

## Next Refactor Steps

The prototype-to-modular migration is complete. The next useful refactor layer is
stability and extensibility around the new module boundaries.

- [x] Rework auto-refresh so browser polling uses `GET /api/state` first and
      only reloads dashboard data when the state version changes. Keep manual
      refresh/import behavior explicit through `POST /api/refresh`.
- [x] Add API contract or smoke tests using project-owned sample data for
      `/api/summary`, `/api/state`, `/api/daily`, `/api/turns`, `/api/tasks`,
      `/api/models`, and refresh payload shapes.
- [x] Harden API query parsing, especially `limit` handling, with safe fallback,
      positive integer validation, and the existing max-limit clamp.
- [x] Add import observability for background imports: last run time, stats,
      status, and captured error summary instead of silently swallowing failures.
- [x] Reduce parser row-building duplication between legacy token usage rows and
      response events after parser fixtures are in place.
- [x] Introduce a source adapter interface only when the next non-Codex source
      or importer cleanup needs it, keeping the current Codex adapter behavior
      unchanged.

## Current Refactor Plan 2026-07-01

Status: planning only. Do not start broad implementation from this section
until the current dirty working tree is accounted for.

### Current Baseline

- Backend and frontend are already modular enough for targeted batches.
- `app/storage/queries.py` is the main refactor target at roughly 1100 lines:
  it still owns shared SQL helpers, source-specific summaries, task lists,
  bucket detail queries, task detail shaping, state metadata, models, data
  state, and dashboard composition.
- `app/api/handlers.py` still contains legacy compatibility instance methods
  that call storage queries directly even though current request routing uses
  `app.services.analytics_service`.
- `app/services/codex_account_service.py` combines process lifecycle,
  stdio protocol calls, cache policy, command resolution, process-tree cleanup,
  and rate-limit normalization.
- Frontend modules are mostly split, but `web/js/detail-modal.js` and
  `web/js/table-resize.js` remain good candidates for small responsibility
  splits after backend query boundaries are safer.
- Existing uncommitted work touches `app/storage/queries.py` and
  `tools/project-memory/pending-tasks.md`; preserve it and verify before
  layering new refactor changes.

### GI Engineering Rule Gate

Apply these rules before and during every implementation batch. They come from
the current GI patterns:

- `patterns/SENIOR_AGENT_ENGINEERING_STANDARD.md`
- `patterns/ARCHITECTURE_AND_CODE_QUALITY.md`
- `patterns/PROJECT_TESTING_STRATEGY.md`
- `patterns/COHERENT_BATCH_VERIFICATION.md`
- `patterns/CONFIGURATION_BOUNDARIES.md`

Execution standard:

- [ ] Act as maintainer, not snippet generator: load only relevant current
      context, separate source truth from old notes, keep scope deliberate, and
      preserve user-visible behavior unless explicitly changed.
- [ ] Keep each batch coherent: one architecture, behavior, configuration, or
      verification goal per batch; no broad formatting churn, generated noise,
      or opportunistic rewrites.
- [ ] Use TDD/test-first where behavior moves or contracts change: first add or
      identify a focused failing/guarding test for the behavior, then refactor,
      then rerun the focused test and the wider suite justified by risk.
- [ ] For pure mechanical moves with existing coverage, prove coverage first:
      run the focused current tests before moving code, then rerun the same
      tests after the move.
- [ ] Prefer behavior and contract tests over implementation-detail tests.
      Tests should protect API payloads, source-specific analytics semantics,
      parser boundaries, config validation, and UI-visible workflows.
- [ ] Apply SOLID pragmatically:
      SRP means each module/function has one reason to change; OCP means new
      sources or renderers can be added through adapters/facades where useful;
      LSP/ISP mean protocols expose only what callers need; DIP means
      infrastructure such as SQLite, filesystem, stdio process management, and
      browser storage stays behind service/repository/client boundaries.
- [ ] Apply DRY to shared knowledge, not shared-looking syntax. Duplicate local
      code may remain when Codex and OpenCode semantics differ; shared helpers
      are allowed only for truly source-neutral range, bucket, payload, or
      formatting behavior.
- [ ] Add abstractions only when they remove meaningful duplication, protect a
      real boundary, simplify callers, or match an established local pattern.
      Do not introduce speculative interfaces for a single implementation.
- [ ] Keep clean architecture boundaries: HTTP handlers parse requests and send
      responses; services orchestrate workflows; storage modules own SQLite
      queries; source adapters parse/read external source metadata read-only;
      frontend modules render and manage UI state without duplicating backend
      domain rules.
- [ ] Keep configuration boundaries clear. Runtime paths, commands, ports,
      credentials, limits, provider choices, and operational policy belong in
      config, documented resources, service discovery, adapters, or project
      memory, not inline feature code.
- [ ] Validate inputs at boundaries: API query parameters, JSON request bodies,
      config paths, task modes, source IDs, bucket/range values, and external
      process payloads should be normalized or rejected before core logic.
- [ ] Update durable project memory when behavior, business rules, data shape,
      integration contracts, or architecture boundaries change. A checklist or
      chat summary is not a replacement for the relevant spec.

Batch design checklist:

- [ ] Name the authoritative source for any behavior, default, policy, workflow,
      data shape, or contract changed by the batch.
- [ ] Name the module contract being created or preserved: caller, callee,
      input shape, output shape, error/empty-state behavior, ownership of side
      effects, and invariants that must not leak across the boundary.
- [ ] Identify every consuming layer before editing: backend query, service,
      API route, frontend renderer/state, desktop mini client, tests, README,
      runbook, and project-memory specs.
- [ ] Decide the smallest verification ladder: syntax/static check, focused
      unit/contract test, integration/API check, runtime smoke, and manual UI
      checklist only when the change needs it.
- [ ] Define rollback scope: each batch should be reviewable and revertible
      without undoing unrelated user work.
- [ ] Stop and ask before destructive operations, data migrations, public API
      or storage contract changes, secret handling, production/deploy actions,
      dependency replacements, or broad filesystem scope.

### Contract-First Module Boundaries

The refactor goal is explicit contracts between modules, not only smaller files.
Every extracted module should make its boundary obvious through names, function
signatures, docstrings or tests where useful, and stable public entry points.

- [ ] API contract: `app/api/handlers.py` owns HTTP parsing, status codes, and
      JSON response sending. It must call `analytics_service` and refresh/ingest
      services instead of reaching into storage query internals.
- [ ] Service contract: `app/services/*` owns workflow orchestration, caching,
      refresh/import status, and external process coordination. Services should
      depend on storage/source/client contracts, not SQL strings or UI details.
- [ ] Storage contract: `app/storage/*` owns SQLite schema, repositories, and
      query functions. Query modules return plain dictionaries/lists with stable
      API-facing field names and keep SQL/private helper details inside storage.
- [ ] Source adapter contract: `app/sources/base.py` defines what a usage source
      yields. Codex and OpenCode adapters may share that protocol while keeping
      source-specific parsing, identity, raw fallback, and invalid-row rules
      separate.
- [ ] Parser/reader contract: readers perform read-only source access and return
      raw records; parsers transform records into normalized usage metadata
      without reading files, opening SQLite connections, or mutating analytics
      storage.
- [ ] Codex account contract: public limit reads go through
      `read_usage_limits()`. Process/stdin/stdout lifecycle, command discovery,
      and rate-limit normalization should be separated so each can be tested
      without spawning real private/runtime processes.
- [ ] Frontend module contract: `dashboard-state.js` owns query/page state;
      render modules accept data and update DOM; modal modules own modal
      interactions; table utilities expose stable initialization functions and
      keep storage/drag/scroll details private.
- [ ] Compatibility contract: shims such as `app.server`, `app.config`,
      `app.db`, and `app.importer` stay as thin compatibility entry points until
      a documented removal decision exists.
- [ ] Contract tests: each boundary should have focused tests or smoke checks
      that prove behavior through the public module/API entry point rather than
      through private helper internals.
- [ ] No leakage rule: API handlers should not know SQL, storage should not know
      DOM/UI labels, parsers should not know analytics DB writes, frontend
      renderers should not recreate backend aggregation rules, and source
      adapters should not inspect or mutate private data beyond the documented
      read-only metadata boundary.

### Batch 0: Protect Current Work

- [ ] Inspect the current diff for `app/storage/queries.py` and
      `tools/project-memory/pending-tasks.md`.
- [ ] Run the focused tests for the active Codex query-state metadata change.
- [ ] Decide whether the active change should be completed before starting the
      next refactor batch.

### Batch 1: Split Storage Query Families

- [ ] Before moving code, add or identify tests that lock current
      `source-analytics-query-contract.md` behavior for Codex/OpenCode summary,
      task rows, bucket detail, raw-only rows, state-token metadata, and invalid
      Codex usage filtering.
- [ ] Keep `app/storage/queries.py` as the public compatibility facade.
- [ ] Move source-neutral SQL/range/bucket fill helpers into a dedicated query
      support module, leaving `query_params.py` for normalization constants and
      parsing rules.
- [ ] Move summary, daily, model, and data-state query functions into a metrics
      query module.
- [ ] Move Codex/OpenCode task, bucket, and detail query functions into
      source-specific task query modules.
- [ ] Preserve the source analytics contract: Codex and OpenCode task identity,
      raw fallback, invalid-usage filtering, and state-token metadata must stay
      source-specific.
- [ ] After each move, run the focused API/storage tests before moving the next
      function family.

### Batch 2: Remove Legacy API Handler Methods

- [x] Confirm tests and runtime routes use `analytics_service`, not handler
      instance methods.
- [x] Remove unused `dashboard`, `summary`, `daily`, `turns`, `tasks`,
      `models`, and `data_state` methods from `AnalyticsHandler`.
- [x] Keep request parsing helpers stable unless a focused test covers the
      replacement.

### Batch 3: Split Codex Account Limit Service

- [x] Before extraction, identify tests covering command resolution,
      WindowsApps alias rejection, persistent client reuse, timeout/restart,
      process-tree cleanup, cache behavior, and limit normalization.
- [x] Extract app-server stdio client/process lifecycle from
      `codex_account_service.py`.
- [x] Extract rate-limit normalization into a pure helper module with existing
      tests preserved.
- [x] Keep the public `read_usage_limits()` behavior and cache settings
      unchanged.
- [x] Keep process, protocol, and normalization concerns separate: client module
      owns stdio/process lifecycle, service module owns public cache/orchestration,
      pure normalizer owns payload shaping.

### Batch 4: Frontend Responsibility Splits

- [ ] Before splitting, run `node --check` on the current modules and identify
      existing UI/API contract tests or add minimal DOM-free helper tests where
      helpers become pure enough to test.
- [ ] Split detail modal payload rendering, copy-button/request-size labels,
      and token comparison helpers while preserving the current modal API.
- [ ] Split table resize storage, order, width, drag, and scroll-sync behavior
      only if each step can keep `initResizableTables()` as the stable public
      entry point.
- [ ] Keep frontend state ownership explicit: `dashboard-state.js` owns query
      state; render modules render data; modal modules own modal interactions;
      table utilities own table behavior only.

### Verification Per Batch

- [ ] Reread edited files and compare them against the relevant GI pattern and
      project-memory contract before running broad checks.
- [ ] `python -m compileall app`
- [ ] `python -m unittest discover -s tests`
- [ ] `node --check` for changed web modules when JavaScript changes.
- [ ] `git diff --check`
- [ ] Restart with `.\start.ps1 -Restart` and smoke-check affected API/UI paths
      only when backend/frontend runtime contracts change.
- [ ] Report checked/not checked/risk explicitly, including any line-ending
      warnings, skipped runtime restart, or deferred RAG rebuild.

### Boundaries

- Preserve user-visible behavior and current API response shapes unless the
  user explicitly approves a contract change.
- Do not inspect private Codex/OpenCode source contents for refactor
  verification.
- Do not run data migrations, delete local databases, or clean untracked
  artifacts as part of this plan.
