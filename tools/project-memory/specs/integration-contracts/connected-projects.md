# Connected Projects

This register tracks external projects, tools, and sources that Token Lens
depends on or regularly interacts with. It is not permission to inspect external
folders; project scope and explicit user requests still govern filesystem
access.

## Shared General Instructions

- Purpose: source of accepted reusable GI rules, templates, migrations, command
  contracts, and project-memory patterns.
- Role in Token Lens: provides the copied local instruction kit used by
  `gi start`, `gi обновить`, command handling, RAG startup, and project-memory
  workflows.
- Local folder: configured source cache outside this repository; resolve it
  through `tools/project-memory/instruction-kit.json`.
- Canonical Git URL: `https://github.com/Dimosfil/general-instructions.git`.
- Service IDs or runtime endpoints: none.
- Source of truth: upstream Git history, `VERSION.md`, and ordered migrations.
- Data/API contract: Token Lens copies accepted instruction files and records
  applied migration IDs only after local file changes are applied and verified.
- Safe commands: `.\tools\check-instruction-kit-updates.ps1` for status, then
  project-local `gi обновить` semantics for applying migrations.
- Privacy boundaries: do not copy Token Lens private data, local databases,
  logs, generated indexes, secrets, or unrelated working-tree changes into the
  shared instruction source.
- Status: active.
- Reason retained: keeps project-local agent workflows consistent with the
  reusable GI instruction kit.

## Codex Local Usage Logs

- Purpose: read-only source of Codex usage metadata for analytics import.
- Role in Token Lens: source adapter imports token usage counts into the
  project-owned SQLite analytics database.
- Local folder: user-private Codex log locations outside this repository; do
  not inspect them unless the user gives an explicit path and action.
- Canonical URLs: none; local application data is the source.
- Service IDs or runtime endpoints: none.
- Source of truth: local Codex runtime logs and Token Lens import code.
- Data/API contract: imports usage metadata read-only from auto-discovered
  Codex paths or ignored `config.local.json` overrides and stores analytics in
  `data/analytics.sqlite`; raw log bodies are private maintenance data.
  Discovery checks `CODEX_HOME`, `CODEX_CONFIG_HOME`, and the current user's
  `.codex` folder for known layouts. When a discovered source path is blank or
  stale in the loaded config, startup writes the fresh value to ignored
  `config.local.json`. `codex_logs_db` is a SQLite file; `codex_session_index`
  may be a JSONL file, sessions directory, or glob over session JSONL files. If
  the local Codex source is not configured or readable, import is skipped with a
  logged warning and no source fallback is guessed.
- Launch-prep rule for agents: read `AGENTS.md`, `tools/AGENT_RUNBOOK.md`,
  `app/core/config.py`, and `app/core/codex_discovery.py` before configuring or
  starting a clean checkout. If both `~\.codex\sqlite\logs_2.sqlite` and
  `~\.codex\logs_2.sqlite` exist, prefer `sqlite\logs_2.sqlite`; root-level
  `logs_2.sqlite` is legacy fallback. Do not inspect private log schema,
  row-counts, timestamps, prompts, responses, or raw bodies just to choose the
  source path.
- Safe commands: use `.\tools\configure-local-sources.ps1` to set local paths,
  then project-local import, maintenance, and cleanup workflows documented in
  `AGENTS.md`, `README.md`, and runbook files.
- Privacy boundaries: never commit logs, raw bodies, user telemetry, secrets,
  credentials, or generated local databases.
- Status: active.
- Reason retained: Token Lens exists to inspect local Codex token usage.

## Codex Account Limits

- Purpose: live display of Codex account remaining limits such as 5h, weekly,
  and Spark buckets.
- Role in Token Lens: `/api/usage-limits`, dashboard limit widget, and desktop
  mini client source context.
- Source of truth: local Codex launcher stdio protocol,
  `codex app-server --stdio`, method `account/rateLimits/read`.
- Implementation map: `app/services/codex_account_service.py`,
  `app/core/codex_discovery.py`, `app/services/analytics_service.py`,
  `web/js/render/limits.js`, and `desktop/mini_client.py`.
- Data/API contract: successful responses have `ok: true`,
  `source: codex_app_server`, and non-empty `groups` or `windows`; windows may
  include labels such as `5h` and `weekly`, and Spark appears only when the
  account reports a Spark bucket.
- Configuration: `codex_app_server_command` in ignored `config.local.json` may
  override launcher discovery when Windows resolves a blocked WindowsApps shim
  or another unusable command.
- Privacy boundaries: this flow is separate from OpenAI API usage/costs/rate
  limits, `OPENAI_API_KEY`, OpenAI Admin API keys, and local SQLite analytics.
  Do not inspect Codex log contents to verify account limits.
- Safe check:
  `Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/usage-limits"` after
  `.\start.ps1`.
- Status: active.
  Reason retained: lets Token Lens show live Codex subscription/account budget
  alongside local token analytics without mixing the two data sources.

## OpenCode Local Usage Sources

- Purpose: optional local source of OpenCode token usage metadata.
- Role in Token Lens: source adapter imports usage counts from configured
  OpenCode SQLite DB messages and token-tracker JSONL records into the
  project-owned SQLite analytics database.
- Local folder: user-private OpenCode data locations outside this repository;
  current config keys are `opencode_db` and `opencode_tokens_jsonl`, configured
  through ignored `config.local.json` when used.
- Canonical URLs: none; local application data is the source.
- Service IDs or runtime endpoints: none.
- Source of truth: local OpenCode runtime data and Token Lens import/parsing
  code in `app/sources/opencode/`, `app/services/import_service.py`, and
  `app/api/handlers.py`.
- Data/API contract: imports usage metadata read-only from local files when
  they exist; startup auto-discovers standard OpenCode user data/config paths
  and writes blank or stale discovered paths to ignored `config.local.json`.
  `/api/ingest/opencode` accepts a JSON event payload for ingest.
- Safe commands: use project-local import and API workflows documented in
  `README.md`, `tools/AGENT_RUNBOOK.md`, and source tests.
- Privacy boundaries: never commit local OpenCode data, telemetry, prompts,
  responses, secrets, credentials, or generated analytics databases. Do not
  inspect user-home OpenCode paths unless the user gives an explicit path and
  action.
- Status: active.
- Reason retained: broadens Token Lens beyond Codex-only usage analytics while
  preserving the same local/private data boundary.
