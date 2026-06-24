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
