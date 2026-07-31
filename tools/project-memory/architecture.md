# Token Lens Architecture And Stack

token-lens/
  app/
    api/              # HTTP handler, response helpers, server bootstrap
    core/             # configuration, paths, shared types
    services/         # import orchestration, analytics facade, background work
    sources/base.py   # source adapter protocol
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
- Configuration: portable JSON defaults at `config.json` plus ignored
  machine-local overrides at `config.local.json`.
- Agent memory: local/generated SQLite at `tools/project-memory/project_memory.sqlite`.

## Runtime Resilience

`start.ps1` launches the web/API server and desktop mini client as separate
processes and records their PIDs under `data/`. Server stdout and stderr are
captured in `data/server.out.log` and `data/server.err.log` so future unexpected
exits have local diagnostic evidence. PyManager launcher and worker PIDs belong
to one application tree and must not be treated as duplicate runtimes. Startup
health uses `/api/state?include_raw=0` so raw-archive size cannot create a false
timeout. A full launch succeeds only after one server tree answers that route
and one Mini tree exposes a window handle. If either check fails, `start.ps1`
prints bounded error-log tails and stops only the processes created by that
launcher invocation; a healthy pre-existing component reused without
`-Restart` remains running.
Runtime stop/restart paths must stop the full process tree for the web/API
server and mini client. The web/API server may own a persistent child
`codex app-server --stdio` process for account-limit reads, so stopping only
the Python PID can leave Codex CLI descendants behind.

The Python runtime configures standard `logging` with a rotating UTF-8 log file.
By default it writes `data/token-lens.log`, keeps five backups, and rotates at
5 MB. `config.local.json` may override `log_file`, `log_level`,
`log_max_bytes`, and `log_backup_count`. At the default `INFO` level, the log
records server startup and shutdown, import start/success/failure stats, HTTP
warnings/errors, client disconnects, and desktop mini self-heal attempts. Set
`log_level` to `DEBUG` to include routine HTTP access lines.

Every runtime log line includes the emitting process ID and thread name. Import
runs also carry a process-scoped `run_id`; Codex and OpenCode phases record
their own wall duration, process CPU time, and row statistics, while the final
run line records total wall duration, process CPU time, and one-core-equivalent
CPU utilization. These diagnostics must not contain prompts, responses, raw log
bodies, or other private source content.

`start.ps1` writes its process discovery and lifecycle decisions to the bounded
`data/launcher.log`, rotating the previous file to `launcher.log.1` after 1 MB.
This log records PID-file state and matching project process IDs so an orphaned
runtime or duplicate launch can be reconstructed after the console closes.

Token Lens may also forward the same standard Python logging records to an
external ai_logger ingest server. The optional adapter is installed as the
native `AiLoggerHttpHandler`; it supplements rather than replaces the rotating
file and stderr handlers. `start.ps1` and `start-mini.ps1` load machine-local
settings from ignored `ai-logger-client.local.ps1` when present. The file owns
the remote URL, optional bearer token, project/service/environment context,
timeout, and fallback JSONL path. When the URL is absent or the package cannot
be loaded, local logging remains available. Delivery failures must not escape
into application code and are written to the configured project-local fallback
file.

The desktop mini client treats a refused connection to a local API URL as a
recoverable local-runtime failure. It starts `run_server.py`, waits for
`/api/state`, then retries the failed poll or refresh. Recovery is limited to
localhost-style URLs and rate-limited so remote or misconfigured API endpoints
are not masked by spawning local processes repeatedly. A recovery child is
single-flight: while that process is still alive, later recovery attempts reuse
it instead of starting another server. On Windows, the HTTP server also claims
the listening port with exclusive address use so parallel server processes
cannot share one configured endpoint.

Desktop HTTP polling and refresh work runs in daemon worker threads. Before a
worker starts, the Tkinter main thread snapshots the selected source, row limit,
and range into a plain request payload. Workers return render/status callbacks
through a queue drained by the Tkinter event loop; they must not read widget
variables, select tabs, schedule `root.after`, or otherwise call Tkinter APIs.
Worker exceptions are captured into callback defaults before Python clears the
exception scope. A failed UI callback is logged and isolated so later callbacks
and the queue timer continue instead of leaving Mini frozen on stale data.
Routine desktop polling requests `/api/state` with `include_raw=0` as the cheap
fast path. The lightweight response keeps the `turns`-derived version fields
used for change detection but skips aggregate counts over the potentially large
`raw_logs` archive. The default `/api/state` response remains full and backward
compatible. If the state version has not changed, Codex account limits are
refreshed once per configured Mini polling cycle, while other source context
keeps the longer throttle interval. Manual refreshes and changed-version polls
still refresh rows and source context immediately. Limit reads remain in the
worker thread, so fresh account balances do not block Tkinter or force table
reloads.

`auto_import_seconds` controls server-owned imports: positive values wait that
interval before the first background import and then repeat at the same cadence,
`0` runs one delayed startup import only, and negative values disable automatic
imports entirely. Manual refresh/import endpoints remain available in every
mode.

The desktop mini client stores user UI settings in
`data/mini_settings.json` and keeps a matching
`data/mini_settings.json.bak`. On startup it loads the primary settings file,
falls back to the backup if the primary file is corrupt or unreadable, and
repairs the primary file from the backup when possible. If no valid backup
exists, the corrupt primary file is preserved as `mini_settings.json.corrupt-*`
and new settings saves are allowed so the UI does not stay permanently reset.

Codex and OpenCode source paths are machine-local runtime configuration. The
tracked `config.json` keeps these external source paths blank; users or agents
may configure them with `tools/configure-local-sources.ps1`, which writes
ignored `config.local.json`. When config values are blank and
`auto_discover_codex_sources` is true, `app.core.codex_discovery` searches
`CODEX_HOME`, `CODEX_CONFIG_HOME`, and the current user's `.codex` folder for
known Codex layouts such as `.codex\sqlite\logs_2.sqlite`,
`.codex\logs_2.sqlite`, and `.codex\sessions`. When both Codex SQLite layouts
exist, discovery chooses the active candidate by safe file metadata. Explicit
`config.local.json` values override discovery.
`app.core.config` resolves configured paths and validates Codex sources at the
import boundary. `codex_logs_db` must be a readable SQLite file.
`codex_session_index` may be a single JSONL file, a sessions directory, or a
glob pattern such as `~\.codex\sessions\2026\06\24\rollout-*.jsonl`. If the
Codex SQLite path is blank, missing, or unreadable,
`app.services.import_service.import_codex_logs` logs a clear warning and returns
empty import stats instead of crashing startup or hard-coding a fallback path.

## Main Paths

- `app/core/config.py`: loads `config.json`, merges `config.local.json`,
  resolves local paths, and validates source paths at runtime boundaries.
- `app/core/codex_discovery.py`: discovers standard Codex local source layouts
  from environment and user-profile roots when config paths are blank, and
  chooses the active Codex SQLite candidate when both current and legacy layouts
  exist.
- `app/core/types.py`: shared dataclasses such as `ImportStats`.
- `app/storage/connection.py`: SQLite connection helper.
- `app/storage/schema.py`: analytics schema and lightweight schema updates.
- `app/storage/repositories.py`: write operations for imported rows.
- `app/storage/queries.py`: summary, daily, turn, task, model, and state queries.
- `app/sources/base.py`: protocol for usage sources.
- `app/sources/codex/adapter.py`: Codex usage source implementation.
- `app/sources/codex/parser.py`: parses Codex token usage and response events.
- `app/sources/codex/reader.py`: reads configured Codex log SQLite rows read-only.
- `app/sources/codex/thread_names.py`: loads thread display names.
- `app/services/import_service.py`: coordinates source-specific imports into
  analytics DB.
- `app/services/data_refresh.py`: owns import/update orchestration, import
  status, source freshness warnings, refresh payload decoration, and the
  background auto-import loop.
- `app/services/analytics_service.py`: API-facing analytics facade.
- `app/services/background.py`: compatibility exports for the data refresh
  runtime.
- `app/services/codex_account_service.py`: public Codex account-limit service,
  cache policy, Codex app-server command resolution, and stdio process
  orchestration.
- `app/services/codex_app_server_client.py`: reusable Codex app-server stdio
  client and process-tree cleanup boundary.
- `app/services/codex_rate_limits.py`: pure normalization helpers for Codex
  app-server `account/rateLimits/read` payloads.
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
- `GET /api/import-status`
- `GET /api/daily`
- `GET /api/turns?limit=100&model=...`
- `GET /api/tasks?limit=100`
- `GET /api/models`
- `POST /api/import`
- `POST /api/refresh?model=...`

Dashboard responses also include `usage_limits`, a cached live snapshot from
`codex app-server` method `account/rateLimits/read`. It reports the Codex
account's rolling primary and secondary limits, remaining percentages derived
from app-server `usedPercent`, reset timestamps, plan type, and available limit
ids. `usage_limits.groups` keeps per-limit buckets such as the main `codex`
bucket and `codex_bengalfox` / GPT-5.3-Codex-Spark, while
`usage_limits.windows` is a flattened list for simple UI rendering. This is
separate from the SQLite analytics data used by tables and charts. The Codex
command is resolved from `codex_app_server_command` when configured, then from
standard user-local locations such as `.codex\bin`, user npm bin folders, and
PATH.
After the first successful account-limit read, transient Codex app-server
timeouts or error payloads return the last successful snapshot marked as
`stale: true`, with `last_success_at` and `stale_error`. Limit widgets must keep
showing that snapshot and only replace it when a newer successful response is
available.
`app.services.codex_account_service` keeps one reusable
`codex app-server --stdio` stdio process by default and owns public cache,
configuration, and command-resolution policy. `app.services.codex_app_server_client`
owns the stdio process lifecycle: it initializes the Codex app-server once,
serializes account-limit requests through that process, closes idle clients,
and restarts after process exit, broken pipes, or timeout. On Windows, cleanup
must stop the full process tree because npm `.cmd` launchers create a
`cmd.exe -> node.exe -> codex.exe` chain, and killing only the wrapper can leave
orphaned Node/Codex processes that accumulate memory. Rate-limit payload
normalization is a separate pure contract in `app.services.codex_rate_limits`,
so process lifecycle tests and payload-shape tests can evolve independently.

## Data Flow

1. `app.services.import_service` validates configured Codex log sources and
   reads them read-only through the `UsageSource` protocol and current
   `CodexUsageSource` when configured.
2. `app.sources.codex.parser` extracts response and token-usage metadata, not
   prompt or response bodies.
3. `app.storage.repositories` writes parsed usage rows into the `turns` table in
   `data/analytics.sqlite`.
4. `app.services.data_refresh` records import status, timing, stats, errors,
   and source freshness warnings. It also guards against silent stale local
   overrides by comparing configured Codex paths with the discovered active
   source path without inspecting private log contents.
5. `app.services.analytics_service` exposes query results from
   `app.storage.queries` and attaches import status/source warnings to state and
   dashboard payloads.
6. `app.api.handlers` serves JSON API responses and static web files. API
   handlers own HTTP parsing/status/response sending and call service-layer
   contracts instead of reaching into storage query internals.
7. `web/app.js` and `web/js/*` render the returned JSON in the browser.

## Boundaries

- `data/analytics.sqlite` is the application database.
- `tools/project-memory/project_memory.sqlite` is agent memory and must not be
  used by the application runtime.
- Do not store secrets, raw logs, prompts, responses, or private local app data
  in agent memory.
