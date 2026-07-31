# Technology Stack

Last reviewed: 2026-06-24

## Summary

- Primary stack: Python standard library backend with a vanilla HTML/CSS/JS
  frontend.
- Runtime model: local web/API server plus desktop mini client, started by
  PowerShell scripts.
- Current confidence: confirmed from project-local instructions, README,
  architecture notes, runbook snippets, config, API handlers, and source
  adapters.

## Components

| Layer | Technology | Evidence | Notes |
| --- | --- | --- | --- |
| Language/runtime | Python | `README.md`, `tools/project-memory/architecture.md`, `tools/AGENT_RUNBOOK.md` | No dependency manifest is currently documented. |
| Frontend | Vanilla HTML, CSS, JavaScript ES modules | `README.md`, `web/`, `tools/project-memory/architecture.md` | Static UI served by the Python app. |
| Backend/API | Python standard library `http.server.ThreadingHTTPServer` and `BaseHTTPRequestHandler` | `tools/project-memory/architecture.md`, `app/api/` | Primary surface is served from `app.server` compatibility entry points. |
| Data/storage | SQLite via Python `sqlite3` | `README.md`, `tools/project-memory/architecture.md`, `app/storage/` | Product DB is `data/analytics.sqlite`; generated/private runtime data is not committed. |
| Source adapters | Codex local log adapter and OpenCode DB/JSONL adapters | `README.md`, `config.json`, `app/sources/codex/`, `app/sources/opencode/`, `app/services/import_service.py` | Reads usage metadata from configured local sources; private user-home sources require explicit user path/action before manual inspection. |
| Desktop client | Python desktop mini client | `tools/AGENT_RUNBOOK.md`, `desktop/`, `start-mini.ps1` | Started with the server by `start.ps1` unless intentionally skipped; can be started alone with `start-mini.ps1`. |
| Configuration | JSON config files | `config.json`, `config.local.json`, `app/core/config.py` | Local/private overrides belong in local config, not source constants. |
| Build/package | No separate build step currently defined | `AGENTS.md`, `tools/AGENT_RUNBOOK.md` | `gi install` must stop if installer/versioning contract is missing. |
| Test/quality | `python -m compileall app`; unittest discovery when tests are relevant | `AGENTS.md`, `tests/` | No dedicated external test runner is documented. |
| Deployment/runtime | Local PowerShell start/stop scripts | `start.ps1`, `stop.ps1`, `tools/AGENT_RUNBOOK.md` | Stable local URL documented as `http://127.0.0.1:8765`. |
| Agent memory/RAG | Markdown specs plus generated SQLite/vector indexes | `tools/project-memory/README.md`, `tools/project-memory/instruction-kit.json` | Generated indexes are rebuildable/local and should not be committed when private or large. |

## Commands

| Purpose | Command | Evidence |
| --- | --- | --- |
| Install | No project dependency manifest currently present | `AGENTS.md` |
| Run | `.\start.ps1` | `AGENTS.md`, `README.md`, `tools/AGENT_RUNBOOK.md` |
| Restart | `.\start.ps1 -Restart` | `tools/AGENT_RUNBOOK.md`, latest handoff summary |
| Run mini only | `.\start-mini.ps1` | `tools/AGENT_RUNBOOK.md`, project root scripts |
| Restart mini only | `.\start-mini.ps1 -Restart` | `tools/AGENT_RUNBOOK.md`, project root scripts |
| Stop | `.\stop.ps1` | `README.md`, project root scripts |
| Test | `python -m compileall app` | `AGENTS.md` |
| Unit tests | `python -m unittest discover -s tests` | `tests/`, API/parser/storage/OpenCode/desktop helper test files |
| Build | No separate build step currently defined | `AGENTS.md` |

## External Services

| Service | Role | Evidence | Boundary |
| --- | --- | --- | --- |
| Codex local logs | Read-only source of token usage metadata | `README.md`, `app/sources/codex/` | User-home app data is private external data; inspect only when the user gives an explicit path and action. |
| OpenCode local sources | Optional source of token usage metadata from local DB and token-tracker JSONL | `README.md`, `config.json`, `app/sources/opencode/`, `app/services/import_service.py`, `app/api/handlers.py` | User-home app data is private external data; inspect only when the user gives an explicit path and action. |
| Config-service | Optional discovery/config integration for GI commands and self-registration | `AGENTS.md`, `tools/project-memory/specs/integration-contracts/connected-projects.md` | Runtime URL must be resolved through documented config-service flow, not guessed ports or stale records. |
| Task manager | Optional configured manager for GI task/sprint workflows | `AGENTS.md`, `tools/project-memory/task-managers.json` | Use guide/contract/API endpoints through config-service. |

## Generated And Local Artifacts

- `data/analytics.sqlite`, PID files, and runtime logs are local runtime state.
- `tools/project-memory/project_memory.sqlite`, semantic corpora, vector indexes,
  generated manifests, and retrieval eval outputs are rebuildable agent-memory
  artifacts unless local policy says otherwise.
- Secrets, credentials, private logs, telemetry, and user-home application data
  must not be committed.

## Gaps

- Installer/package tooling is not currently documented.
- No lint, type-check, or formatting command is currently documented.
- Config-service and task-manager runtime availability must be discovered at
  execution time through their documented service contracts.
