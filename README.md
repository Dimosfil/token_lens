# Token Lens

Сбор аналитики потребления токенов в запросах.

Локальное приложение для ответа на простой вопрос:

> Сколько токенов потратил один запрос, задача или agent run?

Сейчас источники данных - Codex local logs и локальные OpenCode token sources.
Дальше приложение можно расширить на другие агенты и LLM-провайдеры через новые
source adapters.

## Current Sources

Token Lens читает Codex logs read-only из:

```text
.codex\logs_2.sqlite
```

Также поддерживаются локальные OpenCode sources, если они настроены и доступны:

```text
~/.local/share/opencode/opencode.db
~/.config/opencode/logs/token-tracker/tokens.jsonl
```

Все источники импортируют usage metadata в свою БД:

```text
data\analytics.sqlite
```

## Запуск

```powershell
.\start.ps1
```

Скрипт запускает web/API server и desktop mini client.

Открой:

```text
http://127.0.0.1:8765
```

## Остановка

```powershell
.\stop.ps1
```

## Что показывает

- токены по одному model call;
- токены по задаче целиком, сгруппированные по `turn_id`;
- input/output/cached/non-cached/reasoning/total tokens;
- динамику по дням;
- топ дорогих по токенам запросов;
- фильтр по модели;
- фильтр по source, если импортировано несколько источников;
- имя thread из `session_index.jsonl`, если найдено.

## Безопасность

Импортируются только поля usage metadata: ids, timestamps, model, token counts,
thread names. Prompts, responses, tool payloads, raw logs и secrets не
сохраняются в analytics DB.

## Настройки

Файл:

```text
config.json
```

Цены необязательны. Если цена модели неизвестна, cost будет `0`, а source of
truth остаются токены.

## Стек и документация

Канонический inventory текущего стека:

```text
tools/project-memory/specs/technology-stack.md
```

Операционные команды и troubleshooting notes:

```text
tools/AGENT_RUNBOOK.md
```

## Project Structure

## Local Source Setup

Machine-specific source paths must live in ignored `config.local.json`, not in
application code or committed defaults. On a new machine, run:

```powershell
.\tools\configure-local-sources.ps1
```

The script asks for the local Codex/OpenCode files and writes only
`config.local.json`. Use `config.local.example.json` as the redacted shape.
By default, Token Lens auto-discovers Codex sources from `CODEX_HOME`,
`CODEX_CONFIG_HOME`, and the current user's `.codex` folder, and OpenCode
sources from standard user data/config locations. When discovered source paths
are blank or stale in the loaded config, Token Lens writes the fresh values to
ignored `config.local.json` during startup. `codex_logs_db` must point to the
active Codex SQLite file, commonly `~\.codex\sqlite\logs_2.sqlite` or
`~\.codex\logs_2.sqlite`.
`codex_session_index` may point to one JSONL file, a sessions folder, or a glob
such as `~\.codex\sessions\2026\06\24\rollout-*.jsonl`. Existing readable
values in `config.local.json` override auto-discovery. If Codex paths remain
blank, missing, or unreadable, Token Lens still starts and keeps the analytics
database available, but the Codex import is skipped until the local source is
configured.
For agents preparing a checkout: do not choose between
`~\.codex\sqlite\logs_2.sqlite` and `~\.codex\logs_2.sqlite` by querying private
log contents. The project contract is to follow `app/core/codex_discovery.py`:
prefer `~\.codex\sqlite\logs_2.sqlite` unless safe file metadata shows
`~\.codex\logs_2.sqlite` is the active updated source. To trigger discovery and
write ignored `config.local.json` without starting the app, run:

```powershell
python -c "from app.core.config import load_config; print(load_config())"
```

Live account limits use `codex app-server --stdio`; the Codex command is
auto-discovered from `.codex\bin`, user npm bin folders, or PATH and persisted
to ignored `config.local.json` when found. WindowsApps aliases are ignored
because they can fail with access denied. Set `codex_app_server_command` in
`config.local.json` only when a machine uses a custom command path. By default,
Token Lens keeps one reusable app-server process for live limit reads, restarts
it on timeout or pipe failure, and closes it after the configured idle timeout.
These Codex 5h/weekly/Spark limits are not OpenAI API usage/costs/rate limits
and do not use `OPENAI_API_KEY`. To verify them locally:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/usage-limits"
```

A successful response has `ok: true`, `source: codex_app_server`, and non-empty
`groups` or `windows`.

The app is split into small standard-library Python modules and static browser
modules:

```text
app/
  api/              HTTP handler, JSON responses, server bootstrap
  core/             config, paths, shared types
  services/         import orchestration, analytics facade, background jobs
  sources/base.py   source adapter protocol
  sources/codex/    read-only Codex source adapter and parsers
  sources/opencode/ OpenCode DB/JSONL parsers and readers
  storage/          SQLite connection, schema, repositories, analytics queries
  config.py         compatibility shim
  db.py             compatibility shim
  importer.py       compatibility shim
  server.py         compatibility shim used by python -m app.server
web/
  app.js            browser entrypoint
  js/               static ES modules for API, formatting, renderers, status
  index.html
  styles.css
desktop/
  mini_client.py    desktop mini client launched by start.ps1
tests/
  test_*.py         API/query, parser, storage, OpenCode, and desktop smoke tests
```

The compatibility shims keep existing commands working while the implementation
lives in the modular packages.
