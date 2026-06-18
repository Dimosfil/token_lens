# Agent Instructions

## Project

Token Lens is a local analytics app for inspecting token usage by request,
task, model, and day. Its current source adapter reads Codex usage metadata
read-only from local Codex logs and imports usage counts into the project's own
SQLite analytics database.

Primary surface: local Python web app served from `app.server` with static UI in
`web/`.

## Windows Command Policy

- Prefer PowerShell-native networking commands such as `Invoke-RestMethod` and
  `Invoke-WebRequest` instead of `curl.exe`.
- Do not probe for `curl.exe` with `where.exe curl` or `Get-Command curl` unless
  the user explicitly asks for curl diagnostics.
- Prefer trusted helper binaries from `C:\Users\<user>\.codex\bin` before
  WindowsApps or System32 shims.
- If Windows or antivirus tools block agent commands with `Access denied`,
  trust narrow Codex-owned tool folders such as `.codex\.sandbox-bin\` and
  `.codex\bin\`; do not add broad exclusions for System32 or PowerShell itself.

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

Treat RAG as a layered system, not as a synonym for vector search. Use Markdown
and project memory for reviewable specifications, SQLite/FTS for exact paths,
commands, symbols, errors, identifiers, and dependency edges, and optional vector
retrieval only as a complementary semantic layer over curated chunks. Verify
current source files before editing because generated memory indexes can be
stale.

`tools/summary/` is compact chat handoff state. `tools/project-memory/` is
durable product and project knowledge: feature algorithms, business rules,
workflow contracts, data rules, integration contracts, architecture migration
history, verification guarantees, and current implementation maps. For
non-trivial feature, business-rule, data-model, integration, or architecture
work, update the relevant project-memory specification in the same scoped
change.

Treat `gi summary` / `gi саммари` as requests to write a thematic handoff
summary under `tools/summary/`. Summaries should preserve the meaning of the
thread, not routine terminal or git bookkeeping: break the thread into
meaningful topic sections, list key theses under each topic, include user
intent, important decisions, code or architecture changes, business/product
logic, verification evidence, blockers, and next useful context. Omit routine
successful commit/push/staging/branch/hash details when they are recoverable
from git logs or command history. Mention repository state only when it changes
the next agent's action. If procedural history is important, keep it separate as
`Thread Timeline`. For architecture or research threads about an external
project, article, pattern, or tool, preserve the user's integration intent, map
external concepts to current project components, and distinguish decisions from
hypotheses.

When answering where a previous thread stopped, treat handoff summaries as
evidence rather than sole authority. Reconcile them with the latest visible
thread conclusion, screenshots, direct quotes, or other user-provided evidence,
and prefer the last explicit architectural/product decision, open question, or
agreed next direction over incidental caveats or old next-step bullets.

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
- Treat requests to periodically clean or trim old raw log bodies as a
  Token Lens database maintenance task. In `data/analytics.sqlite`, clear only
  `raw_logs.feedback_log_body` for rows outside the current calendar month,
  keep current-month bodies, do not delete `raw_logs` rows, and do not alter
  `turns` or token analytics. After committing the cleanup transaction, run
  `VACUUM` so SQLite returns freed pages to disk, then verify that non-current
  months have zero non-empty bodies and current-month bodies remain.
- Treat `gi help`, `gi хелп`, `ги help`, `ги хелп`, `gi commands`,
  `gi команды`, and `ги команды` as read-only requests to show the compact local
  GI command index. Do not run startup restore, resume old work, call services
  or task managers, mutate files, or execute listed commands for help alone.
- When a feature has an agreed runtime workflow, loading order, branching state
  flow, background work, or user-visible guarantee, record it in project-local
  docs or project memory. Before changing that feature, read the relevant
  feature workflow contract and preserve its guarantees unless the user
  explicitly changes the agreement.
- For non-trivial feature work, keep the feature idea, functional description,
  workflow contract, implementation plan, sprint breakdown, task breakdown,
  definitions of done, and verification linked together. Tasks do not replace
  the feature contract: tasks say what to change, while the contract says what
  behavior must remain true.
- When preparing this project for a repository, publishing to GitHub, or
  removing "unneeded" files, do not classify `AGENTS.md`, `tools/`,
  `tools/project-memory/`, `skills/`, bootstrap scripts, update scripts, deploy
  scripts, or agent-facing instruction/config files as removable only because
  they look internal or tool-related. Inspect their purpose first and treat them
  as possible RAG/startup infrastructure. Delete them only when the user
  explicitly confirms they are temporary or unrelated to the project.
- During repository cleanup, classify SQLite and database files before acting.
  Do not delete or commit `*.sqlite`, `*.sqlite3`, or `*.db` files solely
  because they are binary or local-looking. Keep generated agent-memory indexes
  such as `tools/project-memory/project_memory.sqlite` ignored when they are
  rebuildable, and commit the reviewable README, Markdown/JSON memory exports,
  schema, and indexing scripts instead. Do not commit databases containing
  secrets, private data, telemetry, task-manager state, absolute local paths, or
  agent conversation history.
- Preserve text encodings when editing files. On Windows, do not rewrite source
  files with PowerShell pipelines such as `Get-Content ... | Set-Content ...`
  unless both read and write encodings are explicit and known correct. Prefer
  `apply_patch`, editor-native saves, or language APIs that read and write the
  file with an explicit encoding such as UTF-8. If non-ASCII text appears as
  mojibake after a command, stop, restore the last clean file version, and
  reapply only the intended small patch.
- Ask before destructive operations, broad refactors, or unrelated scope
  expansion.
- Treat this project root as the filesystem boundary for normal work. Do not
  read, search, edit, create, delete, move, or inspect files in another project
  or arbitrary external folder unless the user gives an explicit concrete path
  and action. Use APIs, connectors, or task-manager endpoints for cross-project
  communication.
- Do not hard-code deployment, user, runtime, host-machine, service,
  credential, filesystem-layout, feature-flag, or operational-policy values in
  source code, committed examples, or shared instructions. Keep project-local
  config in documented config files, redacted examples, environment variables,
  service-discovery records, or platform-native config. For configured paths,
  resolve and validate absolute paths at startup or I/O boundaries and fail
  clearly if a value is missing, unsafe, or outside the allowed workspace/data
  root. Internal constants belong in code only when they are true algorithmic or
  protocol invariants.
- Treat `gi config`, `gi конфиг`, `ги конфиг`, `gi config service`,
  `ги конфиг сервис`, `ги конфиг сервис url=<url>`, and
  `ги конфиг сервис урл=<url>` as requests to get or set the bootstrap config
  for the config/discovery service. Read the project-local override only if
  local instructions define one, then read GI main config from the configured
  shared-instruction source repo checkout/cache, the current shared-instruction
  checkout, or `GENERAL_INSTRUCTIONS_HOME`. Use its `config/gi-main.json`
  `configServiceUrl` to query the config service. Resolve local app and
  task-manager runtime URLs by service id through config-service; project
  task-manager config should keep only the selected manager name/id and
  non-secret project preferences. For the
  `url=<url>` form, validate a full `http://` or `https://` URL with no
  secrets, update the shared `configServiceUrl` or the explicit project-local
  override, and tell services to use that URL for registration and discovery.
  Do not scan sibling project folders, guess ports, copy URLs from old
  task-manager memory, or use stale task-manager records as a runtime fallback.
- For agent-facing HTTP services, prefer a service-owned guide endpoint plus a
  strict contract endpoint. Resolve runtime URLs through config-service. Read
  `endpoints.guide` first when present, then `endpoints.contract` before
  sending state-changing requests. Treat the guide as onboarding and the
  contract as workflow validation. If they disagree, stop and report the
  mismatch. Do not infer permissions from filesystem paths, stale memory, old
  dashboard URLs, or raw task receipts.
- Treat `gi manager`, `gi tm`, `gi manager test`, `ги менеджер`,
  `ги манагер`, and equivalent task-manager status or test wording as requests
  to inspect the configured task manager through config-service. Read the
  enabled manager id or `service_id` from project-local task-manager config,
  resolve it through `GET /services/{serviceId}`, read `endpoints.guide` when
  present, read `endpoints.contract`, then use `endpoints.api` for documented
  manager operations. Stop with the exact blocker if the manager id is missing,
  config-service is unavailable, no matching service record exists, or the
  guide/contract lacks the requested capability. Do not fall back to `base_url`,
  stale task-manager memory, port scans, sibling projects, or guessed endpoints.
- Treat `gi config service on`, `gi config service off`,
  `ги конфиг сервис on`, and `ги конфиг сервис off` as requests to set the
  current application's project-local config-service self-registration flag.
  `on` means the app should publish or refresh its own service record during
  startup; `off` means it must not. Do not reinterpret this as starting or
  stopping config-service itself. When setting `on`, first confirm a
  config-service URL is already configured in the same local config area or
  documented GI bootstrap config; if no URL is configured, tell the user to set
  `gi config service url=<url>` before enabling self-registration. Ask one short
  question if no local config location is documented.
- For web-facing applications that expose a port, HTTP API, web UI,
  task-manager service, or local daemon endpoint, require a live config-service
  config check on every process startup before binding or reserving a port when
  self-registration is enabled. On startup, query the app's own `service_id`.
  If the service record exists, bind only the port recorded in config-service
  and use config-service records for neighboring service endpoints. If the
  service record is missing and the project-local self-registration flag is
  `on`, read the config-service guide and contract, list current service
  records, choose a port that is both free on the local host and absent from
  config-service, bind it, verify the local health endpoint, and create or
  update the record through the documented config-service operation. If the
  service record is missing and self-registration is `off`, config-service is
  unavailable, or the guide/contract lacks documented registration operations,
  startup should report the blocker and wait instead of guessing, writing
  directly to config-service storage, reusing stale local runtime config, or
  binding fallback ports. Desktop apps, CLI tools, libraries, scripts, and
  other non-web applications must not query or publish to config-service during
  normal startup unless local instructions explicitly define a discoverable
  web/API runtime. Use cached config only as an explicit degraded-startup
  fallback documented by local run instructions.
- Treat `gi active task`, `gi next task`, `gi get task`, and equivalent
  active-task wording as requests to get executable work from the configured
  task manager. Resolve the manager through config-service, read the manager
  contract, request the active or next task through the documented operation,
  update manager lifecycle state and notes, and stop with the exact blocker if
  the contract, auth, permissions, lifecycle IDs, or requested object type is
  missing or mismatched. Do not create raw intake receipts, local checklist
  notes, or a different manager object type as a substitute for the requested
  task, sprint, or cycle.
- Treat task-manager sync commands as routine integration steps after the user
  has supplied sprint/task content or selected the workflow. Still follow
  config-service discovery, service guide, strict contract, documented payloads,
  lifecycle identifiers, readback, and blocker reporting. Do not replace manager
  API work with project-memory notes, pending checklists, raw intake receipts,
  guessed commands, Work Items, or requests for the user to provide a terminal
  command.
- Treat `gi add sprint`, `gi create sprint`, `gi добавить спринт`, and
  equivalent add-sprint wording as requests to create a visible executable
  Sprint/Cycle through the configured task manager. Resolve the manager through
  config-service, read the manager contract, use only the documented sprint or
  cycle creation operation, verify readback/lifecycle identifiers, and stop with
  the exact blocker if auth, permissions, schema, lifecycle, or object type
  mismatches. Do not downgrade the request to raw intake, Work Items, local
  checklists, or one-task plans.
- Treat `gi ftp`, `ги фтп`, `gi ftp push`, `ги фтп пуш`, `gi upload ftp`,
  `gi deploy ftp`, and `gi залей на фтп` as requests to upload this project's
  configured build output to FTP, FTPS, or SFTP. Treat `gi ftp config`,
  `gi ftp конфиг`, and `ги фтп конфиг` as requests to create, inspect, or update
  the project-local FTP/SFTP config without uploading. Treat `gi ftp folder`,
  `gi ftp папка`, and `ги фтп папка` as requests to inspect, choose, or update
  the remote upload folder (`remotePath`) without uploading. Treat
  `gi ftp service`, `gi ftp сервис`, and `ги фтп сервис` as requests to manually
  register, inspect, or select an FTP/FTPS/SFTP service record in config-service
  without uploading. Read project-local deploy instructions and
  `tools/deploy/ftp.local.json` first; when this project needs FTP and local
  config does not name a target service, query config-service for FTP-capable
  services. If exactly one matching service exists, use it after verifying its
  contract; if several exist, ask the user to choose with the same numbered
  Markdown checkbox style used by language selection. Keep secrets out of
  config-service: store only discovery metadata and secret references such as
  environment variable names. Keep project-specific deploy settings in the
  separate project-local config file rather than shared instructions or chat
  history. Prefer `tools/deploy/ftp.local.example.json` only as a redacted
  shape. Do not commit hostnames, usernames, passwords, tokens, private keys, or
  private remote paths unless project policy explicitly marks them non-secret.
- Treat `gi reboot`, `ги ребут`, `gi restart`, and `ги рестарт` as requests to
  start or restart the current application using project-local run instructions.
  If the app is running, restart it; if it is not running, start it. Launch in
  the background so focus does not jump away from the user's current window.
  After launch, wait briefly and verify the documented startup success signal:
  a still-running expected process, visible desktop window when applicable,
  health/discovery endpoint for web/API apps, and relevant startup or crash logs
  when documented. Do not report reboot success from a PID alone. If the process
  exits, no expected window or health signal appears, or a new startup traceback
  is present, report the reboot as failed or unverified with concrete evidence.
- Treat `gi first test`, `gi первый тест`, and `ги первый тест` as first-launch
  verification requests. Read project-local run, cleanup, cache reset, and test
  instructions before clearing anything. Reset only documented project-owned
  cache, generated state, temporary first-run profiles, and rebuildable local app
  settings; never delete user documents, production data, secrets, credentials,
  external service data, shared system caches, sibling projects, or arbitrary
  user-home folders. If exact reset paths or commands are missing, ask one
  concise clarification question.
- Treat `gi install`, `gi инсталл`, `ги инсталл`, and obvious typo variants
  such as `gi иснтлл` as requests to build the current project and produce an
  installer. Use Inno Setup by default when no installer tool is named. If the
  user writes a program after `gi install` / `gi инсталл`, use that program as
  the preferred packaging tool. Read project-local build and packaging
  instructions, scripts, manifests, and installer configs first. Resolve the
  application version from project-local metadata such as manifests, package
  files, assembly attributes, release files, or installer configs before
  packaging; update the version in build output, installer metadata, and the
  installer filename or artifact name when the local tooling supports it. Ask a
  short clarification question if the build, installer, or versioning contract
  is missing instead of inventing one. Do not report `gi install` as complete
  after dependency restore, build, or tests alone; success requires running the
  packaging command and verifying a current installer artifact.
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
- Prefer one language command with three ordered choices when the user wants
  language preferences for project work. Treat `gi language`, `gi язык`,
  `ги язык`, `gi project language`, `gi проект язык`, `ги проект язык`,
  `gi язык проекта`, and `ги язык проекта` as requests to configure, in order:
  project working environment languages, commit-message languages, and task
  languages in `tools/project-memory/system-preferences.json` and
  `tools/project-memory/git-preferences.json`.
- Apply the configured project working-environment language order to plans,
  checklists, progress updates, final answers, clarifying questions, and
  user-facing explanations. Do not use it to rewrite existing task text, code,
  commands, logs, quoted text, or a response language the user explicitly
  requested for a specific message.
- Apply the configured task language order to agent-created task titles, task
  descriptions, and task-manager updates.
- For task titles, descriptions, and task-manager updates, treat the first
  configured task language as the main language. If exactly one task language is
  configured, write task text only in that language. If multiple task languages
  are configured, write the main-language text first and then add one clear
  translation per additional language. Do not duplicate the same content twice
  in one language, and do not mix untranslated labels, templates, or Definition
  of Done text from another configured language into the main-language text.
- For each `gi язык` choice, preserve the user's selected order. The first
  selected language in each choice is primary for that surface.
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
- When creating or running a test, smoke-check, or verification plan, verify
  exact commands, CLI flags, ports, routes, health endpoints, request payload
  fields, and environment variables from current project-local instructions,
  runbooks, manifests, config entry points, or source code. Treat handoff
  summaries, task notes, screenshots, and old chat examples as status evidence,
  not authoritative command contracts.
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
- `gi start` and `gi restore` must not promote remembered plans, old task notes,
  or local commits ahead of a remote into suggested next actions unless the user
  explicitly asks to continue, run, push, or finish them.
- Treat short greetings, thanks, acknowledgements, and status-neutral messages
  as no-ops unless they include an explicit task, path, command, error, or
  project question. Do not run startup restore for those messages.
- Treat screenshots, logs, pasted errors, or other bug evidence as requests for
  analysis first. Explain the likely issue and ask what action the user wants
  before editing files, unless the user explicitly says to fix it, such as
  `fix`, `почини`, or `gi почини`.
- Keep commit-message language preferences separate from the agent's
  user-facing working language unless the user uses the unified project-language
  command.
- If `gi язык` or an equivalent unified project-language command is sent without
  explicit languages, run a three-step chat flow instead of asking for one
  free-form line. At each step, show the same numbered Markdown checklist of
  available languages with the current selection checked, name the current
  surface, and tell the user they may reply with numbers or language names.
  Render each option as a task-list bullet with the number inside the label,
  such as `- [x] 1. English`; do not use ordered-task syntax such as
  `1. [x] English`, because some chat renderers split the checkbox and label
  onto separate lines.
- When the user replies to that flow with a numeric-only answer such as `1 2`,
  interpret the numbers against the most recent language checklist and apply the
  resulting ordered languages to the current step. Do not ask which languages
  the numbers mean when the checklist was just shown.
- Treat `gi commit language`, `gi коммит язык`, `ги коммит язык`, and older
  `gi язык коммита` forms as requests to configure commit-message languages in
  `tools/project-memory/git-preferences.json`.
- Treat `gi system language`, `gi систем язык`, and `ги систем язык` as
  requests to configure the agent's project working language in
  `tools/project-memory/system-preferences.json`.
- Follow `tools/project-memory/system-preferences.json` for progress updates,
  final answers, clarifying questions, user-facing explanations, and
  agent-created task artifacts. Do not use it to rewrite existing task text,
  code, commands, logs, quoted text, or a response language the user explicitly
  requested for a specific message.
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
- Treat `gi sql` / `gi sqlite` and `gi vector` as read-only project-memory/RAG
  diagnostics. They report configured sources, counts, readiness, staleness, and
  recommendations; they do not deploy services, install heavy dependencies,
  upload data, or index private sources by default.
- Treat `gi rebuild` and `ги ребилд` as requests to rebuild the current project
  or application output, such as an executable, package, or other documented
  artifact. Read project-local build or rebuild instructions, manifests,
  scripts, and packaging metadata before running the documented command. Do not
  treat `gi rebuild` as dependency restore, tests-only verification, a RAG-only
  rebuild, or a combined project-plus-RAG rebuild. If no project rebuild
  contract exists, ask one short clarification question instead of inventing a
  command.
- Treat `gi tools rebuild`, `gi rag rebuild`, `ги тулс ребилд`, and
  `ги раг ребилд` as heavy full rebuild requests for the configured GI/RAG
  tooling layer. Ask for explicit confirmation immediately before a full
  rebuild, after listing source groups, privacy exclusions, generated paths that
  may be replaced, node commands, status checks, and required external services
  or dependencies. Node forms for `sql`, `chunks`, `vector`, `manifest`, and
  `evals` rebuild only that documented node. Keep `gi sql`, `gi sqlite`, and
  `gi vector` as inspection-only commands.
- During `gi обновить`, inspect newly applied migrations for RAG-impacting
  changes. If they change source rules, chunking, embedding metadata,
  SQLite/vector schemas, retrieval adapters, or project-memory index scripts,
  compare them with `tools/project-memory/rag-system.json` rebuild state and
  report stale nodes. Do not mark rebuild state current until rebuild and
  readback/status checks succeed.
- Use Context7 or similar external documentation retrieval only when configured
  or explicitly requested for current public library, framework, SDK, and API
  documentation. It is not project memory, service discovery, task management,
  or local source truth. Prefer project-local instructions and service
  guide/contract endpoints for project behavior, and official OpenAI
  documentation workflows for OpenAI product questions. Do not send secrets,
  credentials, private source code, private business rules, user data,
  production data, telemetry, local paths, or project-memory contents to
  external documentation services unless explicit private-source configuration
  exists and the user approves the exact scope.
