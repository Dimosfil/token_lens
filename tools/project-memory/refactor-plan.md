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
