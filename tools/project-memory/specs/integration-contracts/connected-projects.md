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
- Data/API contract: imports usage metadata read-only and stores analytics in
  `data/analytics.sqlite`; raw log bodies are private maintenance data.
- Safe commands: use project-local import, maintenance, and cleanup workflows
  documented in `AGENTS.md`, `README.md`, and runbook files.
- Privacy boundaries: never commit logs, raw bodies, user telemetry, secrets,
  credentials, or generated local databases.
- Status: active.
- Reason retained: Token Lens exists to inspect local Codex token usage.

## OpenCode Local Usage Sources

- Purpose: optional local source of OpenCode token usage metadata.
- Role in Token Lens: source adapter imports usage counts from configured
  OpenCode SQLite DB messages and token-tracker JSONL records into the
  project-owned SQLite analytics database.
- Local folder: user-private OpenCode data locations outside this repository;
  current config keys are `opencode_db` and `opencode_tokens_jsonl`.
- Canonical URLs: none; local application data is the source.
- Service IDs or runtime endpoints: none.
- Source of truth: local OpenCode runtime data and Token Lens import/parsing
  code in `app/sources/opencode/`, `app/services/import_service.py`, and
  `app/api/handlers.py`.
- Data/API contract: imports usage metadata read-only from local files when
  they exist; `/api/ingest/opencode` accepts a JSON event payload for ingest.
- Safe commands: use project-local import and API workflows documented in
  `README.md`, `tools/AGENT_RUNBOOK.md`, and source tests.
- Privacy boundaries: never commit local OpenCode data, telemetry, prompts,
  responses, secrets, credentials, or generated analytics databases. Do not
  inspect user-home OpenCode paths unless the user gives an explicit path and
  action.
- Status: active.
- Reason retained: broadens Token Lens beyond Codex-only usage analytics while
  preserving the same local/private data boundary.
