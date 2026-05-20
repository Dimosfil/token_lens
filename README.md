# Token Lens

Сбор аналитики потребления токенов в запросах.

Локальное приложение для ответа на простой вопрос:

> Сколько токенов потратил один запрос, задача или agent run?

Сейчас первый источник данных - Codex local logs. Дальше приложение можно
расширить на другие агенты и LLM-провайдеры через новые source adapters.

## Current Source: Codex

Token Lens читает Codex logs read-only из:

```text
C:\Users\Fil-Dom\.codex\logs_2.sqlite
```

и импортирует только usage metadata в свою БД:

```text
token-lens\data\analytics.sqlite
```

## Запуск

```powershell
.\start.ps1
```

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
## Project Structure

The app is split into small standard-library Python modules and static browser
modules:

```text
app/
  api/              HTTP handler, JSON responses, server bootstrap
  core/             config, paths, shared types
  services/         import orchestration, analytics facade, background jobs
  sources/codex/    read-only Codex source adapter and parsers
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
```

The compatibility shims keep existing commands working while the implementation
lives in the modular packages.
