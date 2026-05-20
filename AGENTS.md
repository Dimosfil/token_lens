# Agent Instructions

## Project

Token Lens is a local analytics app for inspecting token usage by request,
task, model, and day. Its current source adapter reads Codex usage metadata
read-only from local Codex logs and imports usage counts into the project's own
SQLite analytics database.

Primary surface: local Python web app served from `app.server` with static UI in
`web/`.

## Restore Context

If the user only sends a short greeting, thanks, acknowledgement, or
status-neutral message, do not run startup restore or read project files. Reply
briefly and ask what they want to do next.

Start here:

```powershell
.\tools\agent-start.ps1
```

If the startup script is unavailable, read only the smallest useful slices of:

- `AGENTS.md`
- latest file in `tools/summary/`
- `tools/AGENT_WORKING_AGREEMENTS.md`
- `tools/AGENT_RUNBOOK.md`
- relevant notes in `tools/project-memory/`

Use the RAG startup flow: retrieve only task-relevant context, search memory by
specific terms, and query SQLite memory only with small `LIMIT`s. For `gi start`,
`gi restore`, or title-only first messages, restore only enough orientation for
the next turn; do not read full summaries, runbooks, memory notes, logs, or diffs
unless a concrete task needs them.

The copied instruction kit is a token-economy and RAG-startup layer for this
project. Use it to restore only the needed context from local instructions,
handoff summaries, targeted searches, and project memory instead of reading the
whole repository or printing broad outputs.

Treat `cached input` as a symptom, not the main optimization target. Keep total
live context small by starting new sessions for unrelated tasks, using compact
handoff summaries instead of long investigation history, and splitting multi-step
R&D when later steps do not need the full previous reasoning trace.

## Durable Memory

Durable project knowledge lives in:

```text
tools/project-memory/
```

Important findings should be written there or in a handoff summary, not only
left in chat.

For analysis, refactoring, migration, or multi-step implementation tasks, create
or update a concise checklist in `tools/project-memory/pending-tasks.md` or a
dedicated task plan in `tools/project-memory/` before editing code. Keep plans
task-relevant and update progress as meaningful steps complete.

When this project reveals a reusable improvement to agent instructions,
workflows, templates, or checklists, write a dated recommendation to the shared
instruction library's `updates/` folder if it is available. If it is not
available, use a local intake folder such as `tools/instruction-updates/` or
`tools/project-memory/instruction-updates/`. Treat recommendations as intake,
not accepted rules.

Use this project as an experience source for `gi`: capture reusable workflows,
failure patterns, token-saving tactics, and agent-instruction improvements that
could help other projects. Keep recommendations concise, evidence-backed, and
free of secrets, private user data, production data, and unnecessary
project-specific details.

## Common Commands

Install dependencies:

```powershell
# Uses the system/local Python environment. No project dependency manifest is
# currently present.
```

Run:

```powershell
.\start.ps1
```

Test:

```powershell
python -m compileall app
```

Build:

```powershell
# No separate build step is currently defined.
```

Inspect logs:

```powershell
# Runtime PID: data\server.pid
# App data: data\analytics.sqlite
```

## Working Areas

- Source: `app/`, `web/`
- Tests: no dedicated test suite currently present
- Tools: `tools/`
- Summaries: `tools/summary/`
- Project memory: `tools/project-memory/`

## Rules

- Do not revert user changes unless explicitly requested.
- Treat dirty worktrees as normal.
- Keep changes scoped to the current task.
- Ask before destructive operations, broad refactors, or unrelated scope
  expansion.
- Treat this project root as the filesystem boundary for normal work. Do not
  read, search, edit, create, delete, move, or inspect files in another project
  or arbitrary external folder unless the user gives an explicit concrete path
  and action. Use APIs, connectors, or task-manager endpoints for cross-project
  communication.
- Treat nested checkouts, vendored repositories, cloned examples, and
  third-party source trees as separate scope. Do not inspect them as part of the
  main project unless the user explicitly asks, the task is about that nested
  tree, or local instructions identify it as an active workspace component.
- Treat user-home application data and personal telemetry as private external
  sources. Do not read `.codex`, `.cursor`, IDE logs, browser profiles, shell
  history, application SQLite databases, or local app logs outside the project
  root unless the user gives an explicit path and action. For analyzer tasks,
  prefer mock or sample data, or ask for permission to inspect a specific file.
- Treat product plans, `apps.txt`, summaries, and task-manager notes as intent
  signals only. They are not permission to read private local data sources.
- If a required file, skill, config, script, endpoint, task, or other entity is
  missing or not found, first reread the relevant local instructions, runbook,
  project memory, and accepted instruction-kit artifacts for the current scope.
  If the entity is still missing, ask the user a short clarification question.
  Do not use another project folder or the shared instruction library as a
  runtime fallback unless the user explicitly gives that path and action.
- Do not commit secrets, credentials, local databases, logs, or generated caches.
- Do not print full `git diff` output by default. Prefer `git diff --stat` and
  targeted queries for relevant files or patterns.
- For first-pass project study, read local instructions, README, manifests, and
  config entry points before building a file map. Use recursive scans only after
  a targeted search fails or the task clearly requires repository-wide
  inventory.
- Do not read large files in full by default, including large `index.html`,
  bundled JS/CSS, logs, lockfiles, generated files, and build artifacts. Prefer
  targeted searches, heads, tails, or small line ranges such as
  `Get-Content -TotalCount`, `Get-Content -Tail`, and `Select-String` on
  PowerShell.
- For verification, count or query HTML elements programmatically instead of
  printing the whole HTML document.
- After implementing a frontend, backend, API, or full-stack feature, restart
  the affected dev server or backend process when local run instructions provide
  a restart command or hot reload is uncertain. Refresh the browser, client, or
  API caller before verification. Probe changed API endpoints or route contracts
  after restart when they feed the UI. Do not assume updated HTML or JavaScript
  means the backend process has loaded matching code. Mention any restart or
  refresh that was skipped and why.
- Do not produce broad artifacts, such as zip archives, or run full check
  matrices unless the user explicitly asks for that scope.
- Final responses should summarize only the changes, checks, and current status;
  do not restate the full investigation context.
- Search for specific symbols, paths, errors, or patterns before doing broad
  repository scans.
- Do not print large logs. Prefer tails and targeted error searches.
- Keep progress updates phase-level, not command-level. Do not narrate after
  every command batch, report counters such as "ran 4 commands", or live-blog
  each intermediate hypothesis. Update when the phase changes, a meaningful
  finding changes the next step, a blocker appears, or work has been quiet long
  enough that the user needs reassurance.
- Do not duplicate tool-run counters that the chat UI may show automatically;
  system UI counters are not agent progress updates.
- Startup restore must be compact; do not dump large files, full runbooks, full
  SQLite contents, full logs, generated outputs, or full diffs.
- Treat short greetings, thanks, acknowledgements, and status-neutral messages
  as no-ops unless they include an explicit task, path, command, error, or
  project question. Do not run startup restore for those messages.
- Launch applications in the background so focus does not jump away from the
  user's current window.
- Follow the copied `general-instructions` instruction kit for the full set of
  rules. In this project, use `AGENTS.md`, `tools/AGENT_WORKING_AGREEMENTS.md`,
  `tools/AGENT_RUNBOOK.md`, `tools/agent-start.ps1`, and project memory as the
  local authoritative sources.
- Treat shared-library files such as `COMMANDS.md` and `patterns/*.md` as
  upstream source material only when checking or applying accepted instruction
  kit updates; do not assume they exist locally in this project.
- When local project rules conflict with shared instructions, the local
  `AGENTS.md`, runbook, and working agreements take precedence.
