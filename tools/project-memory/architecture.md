# Token Lens Architecture And Stack

token-lens/
  app/
    api/              # HTTP handler, response helpers, server bootstrap
    core/             # configuration, paths, shared types
    services/         # import orchestration, analytics facade, background work
    sources/codex/    # read-only Codex source adapter, parser, thread names
    storage/          # SQLite connection, schema, repositories, analytics queries
    config.py         # compatibility shim for app.core.config
    db.py             # compatibility shim for app.storage
    importer.py       # compatibility shim for app.services.import_service
    server.py         # compatibility shim for app.api.server
    static_server.py  # static web file serving
  web/
    index.html        # UI shell
    app.js            # browser entrypoint
    js/               # static ES modules for API, formatting, renderers, status
    styles.css        # UI styling
  data/
    analytics.sqlite  # local application DB, ignored
    server.pid        # running server PID
  tools/
    ... agent instruction kit / project memory
  config.json
  start.ps1
  stop.ps1

## Purpose

Token Lens is a local token-usage analytics app. It imports usage metadata from
Codex local logs into a project-owned SQLite database, then serves a small web UI
for summaries, daily trends, model calls, and grouped tasks.

## Stack

- Backend: Python standard library only.
- HTTP server: `http.server.ThreadingHTTPServer` with `BaseHTTPRequestHandler`.
- Product database: SQLite via Python `sqlite3`, stored at `data/analytics.sqlite`.
- Frontend: vanilla HTML, CSS, and JavaScript ES modules under `web/`.
- Runtime scripts: PowerShell `start.ps1` and `stop.ps1`.
- Configuration: JSON file at `config.json`.
- Agent memory: local/generated SQLite at `tools/project-memory/project_memory.sqlite`.

## Main Paths

- `app/core/config.py`: loads `config.json` and resolves local paths.
- `app/core/types.py`: shared dataclasses such as `ImportStats`.
- `app/storage/connection.py`: SQLite connection helper.
- `app/storage/schema.py`: analytics schema and lightweight schema updates.
- `app/storage/repositories.py`: write operations for imported rows.
- `app/storage/queries.py`: summary, daily, turn, task, model, and state queries.
- `app/sources/codex/parser.py`: parses Codex token usage and response events.
- `app/sources/codex/reader.py`: reads configured Codex log SQLite rows read-only.
- `app/sources/codex/thread_names.py`: loads thread display names.
- `app/services/import_service.py`: coordinates Codex import into analytics DB.
- `app/services/analytics_service.py`: API-facing analytics facade.
- `app/services/background.py`: import lock and auto-import loop.
- `app/api/handlers.py`: HTTP request handler and route dispatch.
- `app/api/server.py`: server startup.
- `web/app.js`: browser entrypoint and refresh orchestration.
- `web/js/render/`: metrics, chart, table, and model renderers.

## Compatibility Shims

The former prototype entry points remain available:

- `app.config`
- `app.db`
- `app.importer`
- `app.server`

They import from the modular packages so existing commands such as
`python -m app.server` and `.\start.ps1` keep working.

## API Surface

- `GET /api/summary`
- `GET /api/state`
- `GET /api/daily`
- `GET /api/turns?limit=100&model=...`
- `GET /api/tasks?limit=100`
- `GET /api/models`
- `POST /api/import`
- `POST /api/refresh?model=...`

## Data Flow

1. `app.services.import_service` reads configured Codex log sources read-only
   through `app.sources.codex.reader`.
2. `app.sources.codex.parser` extracts response and token-usage metadata, not
   prompt or response bodies.
3. `app.storage.repositories` writes parsed usage rows into the `turns` table in
   `data/analytics.sqlite`.
4. `app.services.analytics_service` exposes query results from
   `app.storage.queries`.
5. `app.api.handlers` serves JSON API responses and static web files.
6. `web/app.js` and `web/js/*` render the returned JSON in the browser.

## Boundaries

- `data/analytics.sqlite` is the application database.
- `tools/project-memory/project_memory.sqlite` is agent memory and must not be
  used by the application runtime.
- Do not store secrets, raw logs, prompts, responses, or private local app data
  in agent memory.
