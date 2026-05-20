# Token Lens Architecture And Stack

token-lens/
  app/
    config.py     # читает config.json, резолвит пути
    db.py         # SQLite schema + подключение к analytics DB
    importer.py   # импорт usage metadata из Codex logs
    server.py     # HTTP server, API, static web
  web/
    index.html    # UI
    app.js        # fetch API + рендер таблиц/метрик/графика
    styles.css    # стили
  data/
    analytics.sqlite  # локальная БД приложения, ignored
    server.pid        # PID запущенного сервера
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
- Frontend: vanilla HTML, CSS, and JavaScript under `web/`.
- Runtime scripts: PowerShell `start.ps1` and `stop.ps1`.
- Configuration: JSON file at `config.json`.
- Agent memory: local/generated SQLite at `tools/project-memory/project_memory.sqlite`.

## Main Paths

- `app/config.py`: loads `config.json` and resolves local paths.
- `app/db.py`: owns the product analytics schema and SQLite connection helper.
- `app/importer.py`: reads Codex usage metadata and imports parsed rows.
- `app/server.py`: serves static UI files and JSON API endpoints.
- `web/index.html`: static UI shell.
- `web/app.js`: fetches API data and renders metrics, charts, and tables.
- `web/styles.css`: UI styling.
- `tools/project-memory/index_project.py`: local agent-memory SQLite CLI.

## Data Flow

1. `app.importer` reads configured Codex log sources read-only.
2. It extracts response and token-usage metadata, not prompt or response bodies.
3. Parsed usage rows are written into the `turns` table in `data/analytics.sqlite`.
4. `app.server` exposes summary, daily, turn, task, and model endpoints.
5. `web/app.js` renders the returned JSON in the browser.

## Boundaries

- `data/analytics.sqlite` is the application database.
- `tools/project-memory/project_memory.sqlite` is agent memory and must not be
  used by the application runtime.
- Do not store secrets, raw logs, prompts, responses, or private local app data
  in agent memory.
