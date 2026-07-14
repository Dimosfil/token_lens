<p align="center">
  <img src="docs/images/token-lens-readme-banner.png" alt="Token Lens" width="838">
</p>

# Token Lens

Локальная аналитика расхода токенов для Codex и OpenCode.

Token Lens собирает usage metadata из локальных источников и помогает ответить
на практический вопрос:

> Сколько токенов потратил отдельный model call, запрос, задача или agent run?

Приложение работает локально, читает исходные журналы в режиме read-only и
сохраняет нормализованную аналитику в собственную SQLite-базу.

## Возможности

- статистика `input`, `cached`, `non-cached`, `output`, `reasoning` и `total`;
- расход токенов по model call и задаче целиком;
- агрегация по часам, дням и месяцам;
- фильтры по периоду, модели, источнику и режиму времени;
- сравнение среднего расхода разных моделей;
- список самых дорогих запросов и подробности отдельных вызовов;
- отдельные представления Codex и OpenCode;
- автоматический фоновый импорт новых usage records;
- живые лимиты Codex `5h`, `weekly` и Spark, когда они доступны аккаунту;
- web dashboard и компактный desktop Mini client.

## Быстрый запуск

Проект ориентирован на локальный запуск в Windows с установленным Python.
Отдельного dependency manifest сейчас нет.

```powershell
git clone https://github.com/Dimosfil/token_lens.git
cd token_lens
.\tools\configure-local-sources.ps1
.\start.ps1
```

После запуска:

- web dashboard: `http://127.0.0.1:8765`;
- desktop Mini запускается автоматически;
- локальная аналитическая БД создаётся в `data\analytics.sqlite`.

Полезные команды:

```powershell
# Перезапустить server и Mini
.\start.ps1 -Restart

# Запустить только web/API server
.\start.ps1 -NoMini

# Остановить приложение
.\stop.ps1
```

## Local Source Setup

Машинно-зависимые пути хранятся только в игнорируемом
`config.local.json`. Коммитить локальные пути в `config.json` не нужно.

Интерактивная настройка:

```powershell
.\tools\configure-local-sources.ps1
```

Автоматическое обнаружение без запуска приложения:

```powershell
python -c "from app.core.config import load_config; print(load_config())"
```

`load_config()` загружает `config.json`, накладывает `config.local.json`, а
затем обнаруживает отсутствующие или устаревшие локальные источники. Уже
настроенные и доступные пути из `config.local.json` имеют приоритет.

### Codex

Token Lens проверяет `CODEX_HOME`, `CODEX_CONFIG_HOME` и папку `.codex`
текущего пользователя. Поддерживаются обе раскладки:

```text
~\.codex\sqlite\logs_2.sqlite
~\.codex\logs_2.sqlite
```

Если доступны оба файла, выбор активного источника выполняет
`app/core/codex_discovery.py` по безопасным файловым метаданным. Для имён
сессий используется `~\.codex\sessions`, а при его отсутствии — legacy-файл
`~\.codex\session_index.jsonl`.

### OpenCode

Автообнаружение ищет стандартные пользовательские расположения для:

```text
opencode.db
logs\token-tracker\tokens.jsonl
```

Если источник не найден, приложение всё равно запускается и продолжает работать
с уже импортированными данными.

## Живые лимиты Codex

Лимиты аккаунта читаются через локальный Codex launcher:

```text
codex app-server --stdio
```

Это лимиты Codex `5h`, `weekly` и Spark, а не OpenAI API usage/costs. Для них
не используется `OPENAI_API_KEY`.

Проверить локальный endpoint после запуска:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/usage-limits"
```

Успешный ответ содержит `ok: true`, `source: codex_app_server` и непустые
`groups` или `windows`.

## Приватность

Исходные Codex/OpenCode-файлы находятся вне репозитория и открываются
адаптерами только для чтения. В аналитическую БД импортируются usage metadata:

- идентификаторы и timestamps;
- модель и статус вызова;
- thread/session metadata;
- значения token usage.

Prompts, responses, tool payloads, secrets и исходные приватные журналы не
сохраняются в `data\analytics.sqlite`.

## Конфигурация

Переносимые настройки находятся в `config.json`, локальные overrides — в
игнорируемом `config.local.json`.

Основные параметры:

| Параметр | Назначение |
| --- | --- |
| `analytics_db` | Собственная SQLite-база Token Lens |
| `host`, `port` | Адрес локального web/API server |
| `auto_import_seconds` | Интервал фонового импорта |
| `codex_logs_db` | Активная Codex SQLite-база |
| `codex_session_index` | Файл, папка или glob с Codex sessions |
| `opencode_db` | Локальная OpenCode SQLite-база |
| `opencode_tokens_jsonl` | OpenCode token-tracker JSONL |
| `model_prices_per_million` | Необязательные цены моделей |

Если цена модели не настроена, cost остаётся `0`, а source of truth — значения
token usage.

## API

Основные локальные endpoints:

| Endpoint | Назначение |
| --- | --- |
| `GET /api/state` | Текущее состояние приложения и импорта |
| `GET /api/dashboard` | Сводные данные dashboard |
| `GET /api/usage-limits` | Живые лимиты Codex account |
| `GET /api/tasks` | Агрегированные или отдельные задачи |
| `GET /api/task-detail` | Детализация выбранной задачи |
| `GET /api/models` | Статистика по моделям |
| `POST /api/refresh` | Обновление локальной аналитики |

## Архитектура

Token Lens использует Python standard library на backend, vanilla HTML/CSS/JS
на frontend и SQLite для хранения аналитики.

```text
app/
  api/              HTTP handlers и JSON responses
  core/             config, discovery, paths и shared types
  services/         orchestration, analytics и background jobs
  sources/          read-only adapters для Codex и OpenCode
  storage/          schema, repositories и analytics queries
desktop/
  mini_client.py    компактный desktop client
web/
  index.html        dashboard shell
  js/               API, state и render modules
  styles.css        интерфейс dashboard
tests/
  test_*.py         API, parser, storage и desktop tests
```

Новые источники можно добавлять через source adapter contract в
`app/sources/base.py`.

## Проверка

```powershell
python -m compileall app desktop
python -m unittest discover -s tests
```

Дополнительная документация:

- [`tools/AGENT_RUNBOOK.md`](tools/AGENT_RUNBOOK.md) — запуск и troubleshooting;
- [`tools/project-memory/specs/technology-stack.md`](tools/project-memory/specs/technology-stack.md) — проверенный stack inventory;
- [`INDEX.md`](INDEX.md) — индекс agent-facing инструкций.
