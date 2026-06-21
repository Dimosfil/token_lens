# Agent Working Agreements

## Scope

- Keep changes small and tied to the current request.
- Ask before expanding into unrelated modules.
- If a task requires files outside the agreed working area, say so first.
- Treat the current project root as the filesystem boundary for normal work.
  Do not read, search, edit, create, delete, move, or inspect files in another
  project or arbitrary external folder unless the user gives an explicit
  concrete path and action. Use APIs, connectors, or task-manager endpoints for
  cross-project communication.
- Keep configuration values at the configuration boundary: do not hard-code
  deployment, user, runtime, host-machine, service, credential,
  filesystem-layout, feature-flag, or operational-policy values in source code,
  committed examples, or shared instructions. Use documented local config,
  redacted examples, environment variables, service discovery, or
  platform-native config, and validate configured paths at startup or I/O
  boundaries.
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

## User Changes

- Do not revert user changes unless explicitly requested.
- Treat dirty worktrees as normal.
- If user changes affect the task, work with them.
- Preserve recorded feature workflow contracts. If a feature has an agreed
  runtime workflow, loading order, branching state flow, background work, or
  user-visible guarantee, read that contract before changing the feature and
  update it in the same scoped change when behavior intentionally changes.
- For non-trivial features, keep the feature idea, functional description,
  workflow contract, implementation plan, sprint breakdown, task breakdown,
  definitions of done, and verification connected. Tasks do not replace the
  feature contract.
- Treat `tools/summary/` as compact chat handoff state and
  `tools/project-memory/` as durable product/project specifications. For
  non-trivial feature, business-rule, data-model, integration, or architecture
  work, update the relevant project-memory specification in the same scoped
  change.
- When this project depends on, researches, vendors, or regularly interacts with
  external repositories, cloned examples, services, libraries, documentation
  sites, or upstream tools, keep
  `tools/project-memory/specs/integration-contracts/connected-projects.md` as
  the connected-projects register. Read it before touching integrations,
  nested repositories, cloned examples, or external project folders, and update
  it when a connected project is added, removed, replaced, relocated, or
  materially changes role.

## Git

- Default: the agent edits and verifies; the user reviews and commits.
- Treat `gi коммит`, `gi пуш`, `gi коммит пуш`, and `gi только пуш` as explicit
  git finish requests. `gi коммит` commits scoped current changes only; `gi пуш`
  and `gi коммит пуш` commit scoped current changes and push the current branch;
  `gi только пуш` pushes existing local commits without creating a new commit.
  Inspect status, keep unrelated/user changes out, follow commit-message
  preferences, and stop on ambiguous scope, missing remote, conflicts, secrets,
  or push failures.
- Exception: after a successful `gi обновить` / `gi обновись`, commit and push
  only the resulting instruction-kit update changes when this project is a git
  repository with a configured remote. If unrelated/user changes, no remote,
  push failure, or conflicts are present, stop and explain the blocker.
- Branch naming: use `codex/` by default for agent-created branches unless the
  user asks for another name.
- Generated files policy: keep `data/`, logs, caches, virtual environments, and
  local agent memory databases out of commits.
- Never commit secrets, credentials, local databases, logs, or caches.
- Follow `tools/project-memory/git-preferences.json` for commit-message
  languages. English is primary; selected additional languages are included when
  the user explicitly asks the agent to commit.
- When the user asks in chat to change commit-message languages, update
  `tools/project-memory/git-preferences.json` directly and summarize the new
  setting.
- Do not infer additional commit-message languages from the user's UI language
  or message language. If the requested languages are ambiguous, ask which
  additional languages to enable.
- For ambiguous commit-language selection, ask with a concise numbered Markdown
  checklist showing `English` as always selected and current additional
  languages as checked. Explain that `English` is the required primary
  commit-message language and cannot be disabled. Ask the user to reply with
  language names or numbers. Render each option as a plain inline checkbox
  marker with the number and label on the same physical line, such as
  `[x] 1. English` or `[ ] 2. Russian`. Do not use Markdown task-list syntax
  such as `- [x] 1. English` or ordered-task syntax such as `1. [x] English`,
  because some chat renderers split the checkbox control and label onto
  separate lines. Never emit a standalone checkbox line followed by a separate
  numbered label line.
- When reporting this change, mention the plain
  `tools/project-memory/git-preferences.json` path instead of malformed or
  placeholder markdown links.
- If the user explicitly wants to configure languages manually, they can run:

```powershell
.\tools\select-git-commit-languages.ps1
```

or:

```powershell
.\tools\agent-start.ps1 -ConfigureGitCommitLanguages
```

## Agent Language

- Follow `tools/project-memory/system-preferences.json` for the agent's
  user-facing working language in this project.
- Apply the configured system or project language to progress updates, final
  answers, clarifying questions, user-facing explanations, agent-created task
  titles, task descriptions, task-manager updates, plans, and checklists.
- For task titles, descriptions, and task-manager updates, treat the first
  configured task language as the main language. If exactly one task language is
  configured, write task text only in that language. If multiple task languages
  are configured, write the main-language text first and then add one clear
  translation per additional language. Do not duplicate the same content twice
  in one language, and do not mix untranslated labels, templates, or Definition
  of Done text from another configured language into the main-language text.
- Do not apply the system or project language to existing task text, code,
  commands, logs, quoted text, or a response language the user explicitly
  requested for a specific message.
- Treat `gi language`, `gi язык`, `ги язык`, `gi project language`,
  `gi проект язык`, `ги проект язык`, `gi язык проекта`, and `ги язык проекта`
  as requests to configure three ordered language sequences: project working
  environment, commit messages, and tasks.
- If the unified project-language command does not include explicit languages,
  ask in three numbered steps. For each step, show a concise plain inline
  numbered checkbox marker checklist with the available languages and the
  current selection, then accept the user's next answer as numbers or language
  names for that step.
- When a unified project-language step has no current selection, default it to
  `1 2`: `English`, then `Russian`.
- If the user replies with only numbers, such as `1 2`, map them to the most
  recent checklist and preserve that order. Do not ask what those numbers mean
  after showing the checklist.
- Treat `gi system language`, `gi систем язык`, and `ги систем язык` as
  requests to configure this preference.
- Keep this setting separate from commit-message languages. `gi commit
  language`, `gi коммит язык`, `ги коммит язык`, and older `gi язык коммита`
  forms configure `tools/project-memory/git-preferences.json`, not the agent's
  working language. The unified project-language command updates both
  preference files.
- If the user explicitly wants to configure the system language manually, they
  can run:

```powershell
.\tools\select-system-language.ps1
```

or:

```powershell
.\tools\agent-start.ps1 -ConfigureSystemLanguage
```

## Context Hygiene

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
- Launch applications in the background so focus does not jump away from the
  user's current window.
- Treat a short first message as a possible chat title: restore context, then
  ask what to do next instead of executing the title as a task.
- Treat short chat commands that start with `gi` as shared instruction-kit
  commands for the copied `general-instructions` kit in this project. `gi` is
  the only short prefix; do not rename it to `GAI` or another alias.
  If a `gi` command is missing a needed parameter, ask one short clarification
  question instead of guessing.
- Use the instruction kit as a token-economy and RAG-startup layer: restore only
  task-relevant context from local instructions, summaries, targeted searches,
  and project memory instead of broad repository reads or large outputs.
- Treat RAG as layered retrieval: Markdown/project-memory for reviewable specs,
  SQLite/FTS for exact paths, commands, symbols, identifiers, errors, and
  dependency edges, and optional vectors only as a complementary semantic layer.
  Verify current source files before editing because generated indexes can be
  stale.
- Keep `gi` command responses scoped to the shared instruction-kit command. Do
  not resume an older product task after a `gi` command unless the user
  explicitly asks.
- Treat `gi help`, `gi хелп`, `ги help`, `ги хелп`, `gi commands`,
  `gi команды`, and `ги команды` as read-only command-index requests. Do not run
  startup restore, call services or task managers, mutate files, or execute
  listed commands for help alone.
- For `gi start`, `gi restore`, and title-only startup messages, restore only
  compact orientation for the next turn. Mention remembered plans, stale task
  notes, old refactoring phases, or local commits ahead of a remote only as
  context when relevant. Do not offer to continue, run, finish, or push
  remembered work unless the user explicitly asks for that action.
- Treat `gi start sprint`, `gi sprint start`, and equivalent active-sprint
  wording as more specific than plain `gi start`: continue through the
  configured task-manager workflow instead of stopping after generic startup
  restore.
- Run `gi` commands against this project root. Do not switch to another
  repository, the shared instruction library, or a path from an older task unless
  the user explicitly asks.
- Task-manager paths, raw intake metadata, summaries, or previous chat context
  are not permission to enter another project folder.
- `gi` means `general-instructions`, not `git`. Missing `.git` blocks only the
  automatic commit/push step after a successful GI update; it does not block
  checking or applying instruction-kit file updates.
- Treat `gi саммари` and `gi summary` as requests to write a handoff summary
  file under `tools/summary/`, not only as requests to summarize in chat.
  Summaries should be thematic handoffs, not routine terminal or git ledgers:
  break the thread into meaningful topic sections, list the key theses under
  each topic, and include user intent, important decisions, code or architecture
  changes, business/product logic, verification evidence, blockers, and next
  useful context. Omit routine command bookkeeping such as successful commits,
  pushes, staging counts, branch names, push targets, and commit hashes when
  those facts are recoverable from git logs or command history. Mention
  repository state only when it changes the next agent's action, such as
  uncommitted work, conflicts, failed pushes, or a required follow-up. If a
  thread has detailed procedural history, keep it in a separate `Thread
  Timeline` section or artifact. For architecture or research threads about an
  external project, article, pattern, or tool, preserve the user's integration
  intent, map external concepts to current project components, and distinguish
  decisions from hypotheses.
- When answering where a previous thread stopped, treat handoff summaries as
  evidence rather than the sole authority. Compare them with the latest visible
  thread conclusion, screenshots, direct quotes, or other user-provided
  evidence. Prefer the last explicit architectural/product decision, open
  question, or agreed next direction over incidental caveats or old next-step
  bullets.
- Treat `gi гит-обзор` and `gi git summary` as requests to summarize the latest
  git commit in the current project in chat. Include commit metadata, changed
  files, compact stats, inferred purpose, and notable risks or checks. Do not
  print a full diff, create a summary file, commit, or push for this command.
- Treat `gi пул`, `gi pull`, and `ги пул` as explicit requests to fetch and pull
  the current branch from its configured upstream. Before pulling, inspect
  `git status --short`, the current branch, and upstream configuration. Pull
  only the current branch; do not switch branches, rewrite history, rebase, or
  pull from another remote unless the user explicitly asks. If local changes
  make the pull unsafe, unresolved conflicts already exist, the project is not a
  git repository, or no upstream is configured, stop and explain the blocker.
  If conflicts appear during pull, resolve only obvious, low-risk conflicts
  where intent is clear and user changes are preserved; otherwise stop and ask.
- Treat `gi config`, `gi конфиг`, `ги конфиг`, `gi config service`,
  `ги конфиг сервис`, `ги конфиг сервис url=<url>`, and
  `ги конфиг сервис урл=<url>` as requests to get or set the bootstrap config
  for the config/discovery service. Resolve local app and task-manager runtime
  URLs by service id through config-service. Validate saved service URLs as full
  `http://` or `https://` URLs without usernames, passwords, tokens, query
  strings, or fragments.
- Treat `gi config service on`, `gi config service off`,
  `ги конфиг сервис on`, and `ги конфиг сервис off` as requests to set the
  current application's project-local config-service self-registration flag, not
  as commands to start or stop config-service itself. Enabling the flag requires
  an existing config-service URL in the same local config area or documented GI
  bootstrap config.
- For web-facing applications that expose a port, HTTP API, web UI,
  task-manager service, or local daemon endpoint, startup must check live
  config-service config before binding or reserving a port when
  self-registration is enabled. If the app's own service record exists, bind
  only the port recorded in config-service. If the record is missing and
  project-local self-registration is `on`, read the config-service guide and
  contract, list current service records, choose a locally free port absent from
  config-service, bind it, verify the local health endpoint, and create or
  update the record through the documented operation. If config-service is
  missing, unreachable, incomplete, lacks a registration contract, or
  self-registration is `off`, startup reports the blocker and waits instead of
  guessing, writing storage directly, reusing stale runtime config, or falling
  back to stale ports. Non-web apps do not query or publish to config-service
  during normal startup unless local instructions define a discoverable web/API
  runtime.
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
- Treat `gi reboot`, `ги ребут`, `gi restart`, and `ги рестарт` as requests to
  start or restart all documented applications in the current project using
  project-local run instructions. If local instructions define a preferred
  start/restart command that launches the full app set, use it. Otherwise
  enumerate every documented app or runtime, such as desktop app, web/API app,
  and background workers, then restart each running app and start each missing
  app in the background. After launch, wait briefly and verify a documented
  startup success signal for each app beyond PID creation: still-running
  expected processes, visible desktop windows when applicable, health/discovery
  endpoints for web/API apps, worker readiness signals, and relevant startup or
  crash logs when documented. The final report must account for each app by name
  or role with started/restarted/skipped status and verification evidence. Do not
  report success from a PID alone, from a web health check alone, or while any
  expected desktop app, web/API app, or worker is unlaunched or unverified. If
  any expected signal is missing, report startup as failed or partially
  unverified with concrete evidence.
- Treat `gi ftp`, `ги фтп`, `gi ftp push`, and `ги фтп пуш` as requests to
  upload configured build output to FTP, FTPS, or SFTP. Treat `gi ftp config`
  as FTP/SFTP config setup without uploading, `gi ftp folder` as remote folder
  selection without uploading, and `gi ftp service` as selecting or registering
  an FTP-capable config-service record. Keep credentials, tokens, private keys,
  private remote paths, and other secrets out of git, config-service records,
  logs, and final responses.
- Treat `gi install`, `gi инсталл`, `ги инсталл`, and obvious typo variants
  such as `gi иснтлл` as requests to build the current project and produce an
  installer. Use Inno Setup by default when no installer tool is named; use the
  named packaging tool when the user supplies one. Read local build and
  packaging instructions first, resolve the application version from
  project-local metadata, and keep production build, installer metadata, and
  artifact naming aligned when local tooling supports it. Ask one short
  clarification question if build, installer, or versioning contracts are
  missing or ambiguous. Dependency restore, build, and tests alone are
  preliminary checks, not completion of `gi install`; success requires running
  the packaging command and verifying a current installer artifact.
- Treat `gi тест-план` and `gi test plan` as requests to inspect local project
  test commands and produce a compact verification plan for the current feature,
  bug fix, or release check. Plan first; run checks only when the user asks or
  when the current task already requires verification. Verify exact commands,
  flags, ports, routes, health endpoints, payload fields, and environment
  variables from current local instructions, runbooks, manifests, config entry
  points, or source before recommending or running checks.
- Treat `gi first test`, `gi первый тест`, and `ги первый тест` as first-launch
  verification requests. Reset only documented project-owned first-run cache,
  generated state, temporary profiles, and rebuildable app settings; ask one
  concise question if reset paths or commands are not documented.
- Treat a first message that points to a shared instruction library as an
  instruction bootstrap, not as a request to add that library as a dependency.
- Treat `init <source>`, `инит <source>`, `инициализируй <source>`, and
  `инит правила <source>` as shared-instruction bootstrap/startup requests when
  the source points to a known `general-instructions` checkout, cache,
  canonical repository, or `GENERAL_INSTRUCTIONS_HOME`; do not reinterpret those
  forms as `git init`, project creation, folder creation, package init, or
  virtualenv setup unless the user explicitly names that action.
- If the user asks to update from a shared instruction library and this project
  has no `tools/project-memory/instruction-kit.json`, treat that as first-time
  instruction bootstrap/init.
- Run `gi обновить` quietly by default: do not narrate step-by-step reasoning,
  repeated progress, command transcripts, broad file reads, or full diffs during
  normal successful updates. Apply the update, then report a compact summary
  with versions, migration counts/IDs, changed files, checks, commit/push
  result, and blockers if any.
- During `gi обновить`, inspect newly applied migrations for RAG-impacting
  changes and compare them with `tools/project-memory/rag-system.json` rebuild
  state. Report stale nodes and run or offer only documented rebuild nodes.
  Never commit generated SQLite databases, semantic corpora, vector indexes,
  logs, secrets, telemetry, or private runtime data.
- Treat `gi sql` / `gi sqlite` and `gi vector` as read-only diagnostics for
  project-memory/RAG readiness, counts, staleness, and recommendations.
- Treat `gi rebuild` and `ги ребилд` as requests to rebuild only the current
  project/application output through documented local build instructions. Do not
  reinterpret it as dependency restore, tests-only verification, RAG-only
  rebuild, or combined project-plus-RAG rebuild. If no project rebuild contract
  exists, ask one short clarification question instead of inventing a command.
- Treat `gi tools rebuild`, `gi rag rebuild`, `ги тулс ребилд`, and
  `ги раг ребилд` as heavy full GI/RAG tooling rebuild requests requiring
  explicit confirmation immediately before execution. Node forms for `sql`,
  `chunks`, `vector`, `manifest`, and `evals` rebuild only that documented node.
  For `evals`, prefer machine-checkable retrieval checks that verify index
  health, count consistency, generated-index ignore rules, and expected source
  paths in top keyword, semantic, or hybrid results; do not treat an answer's
  wording as the primary eval target.
- During `gi обновить`, migrations that change RAG source rules, indexers,
  chunking, embedding metadata, vector schemas, retrieval adapters, or eval
  scripts leave affected rebuild state stale until documented rebuild and
  status checks succeed.
- Use Context7 or similar external documentation retrieval only when configured
  or explicitly requested for public library, framework, SDK, and API docs. Do
  not send secrets, credentials, private source, business rules, user data,
  production data, telemetry, local paths, or project-memory contents to
  external doc services unless explicit private-source configuration exists and
  the user approves the exact scope.
- For web applications, assume the user will inspect the UI manually. Do not
  open, browse, screenshot, or visually inspect the UI automatically unless the
  user explicitly asks for that.
- Treat `gi default`, `gi defaults`, and `ги дефолт` as requests to restore the
  documented first-run/default state. Use only documented reset targets and
  stop for clarification if reset targets are missing or data removal could be
  irreversible.
- Treat `gi refactor`, `gi рефактор`, and `ги рефактор` as approval for a
  current-project refactor according to applicable GI rules. Work in small
  verified batches, preserve user-visible behavior unless explicitly changed,
  and stop before destructive, data-affecting, external, or contract-breaking
  actions.
- Keep developer tools, orchestrators, task managers, agent harnesses, and code
  generators separate from generated products and selected task data. Product,
  customer, demo, stack, and workflow-run specifics belong in payloads,
  manifests, fixtures, adapters, project-local config, service discovery, or
  user-selected state.
- Keep reusable GI rule explanations project-agnostic unless the user asks for
  a concrete comparison.
- Keep query interpretation, translation, prompt normalization, provider
  prompts, model names, budgets, fallbacks, timeouts, and privacy policy behind
  a module, resource, service, pipeline, or adapter boundary. Preserve original
  user text separately from interpreted intent and model-facing queries.
- Build and review application code against
  `patterns/ARCHITECTURE_AND_CODE_QUALITY.md`.
- Finish meaningful batches with
  `patterns/COHERENT_BATCH_VERIFICATION.md`: source-of-truth consistency,
  durable spec writeback when behavior or architecture changes, scoped diff
  inspection, and evidence-backed checks.
- Keep the durable stack inventory at
  `tools/project-memory/specs/technology-stack.md` current when stack facts or
  commands change.

## Editing

- Prefer patch-style edits for manual changes.
- Avoid unrelated formatting churn.
- Add comments only when they clarify non-obvious behavior.
- Preserve existing file encodings. On Windows, do not rewrite source files with
  PowerShell `Get-Content ... | Set-Content ...` pipelines unless both read and
  write encodings are explicit and known correct. Prefer `apply_patch`,
  editor-native saves, or language APIs that read and write with an explicit
  encoding such as UTF-8. If non-ASCII text appears as mojibake after a command,
  stop, restore the last clean file version, and reapply only the intended small
  patch.

## Task Planning

- For analysis, refactoring, migration, or multi-step implementation tasks,
  create or update a concise checklist in `tools/project-memory/pending-tasks.md`
  or a dedicated task plan in `tools/project-memory/` before editing code.
- Include the goal, planned changes, execution order, risks or dependencies, and
  verification steps.
- Update progress as meaningful steps complete.
- Keep plans concise. Do not store full diffs, large logs, generated outputs,
  secrets, credentials, or private production data.

## Shared Instruction Updates

- When this project reveals a reusable improvement to agent instructions,
  workflows, templates, or checklists, write a dated recommendation to the shared
  instruction library's `updates/` folder if it is available.
- If no shared instruction library is available, use a local intake folder such
  as `tools/instruction-updates/` or
  `tools/project-memory/instruction-updates/`.
- Treat recommendations as intake, not accepted rules.
- Recommendations should explain the observed problem, reusable rule or
  workflow, evidence paths, affected files or commands, risks, and privacy
  review.
- Capture reusable workflows, failure patterns, token-saving tactics, and
  agent-instruction improvements that could improve `gi` for other projects.
- Do not add a shared instruction library as a project dependency, package,
  submodule, symlink, or runtime reference unless the user explicitly asks for
  that.

## Task Managers

- Treat task-manager configuration as project-local state.
- Store only the manager name or `service_id` plus non-secret project
  preferences in project memory.
- Resolve task-manager runtime URLs through GI config-service by service id;
  do not store, guess, or copy API endpoints from old notes or other projects.
- If a configured manager id is missing from config-service, stop with a concise
  blocker instead of falling back to port scans or stale task-manager memory.
- Before posting plans or starting sprint work, read the manager guide when
  present, then verify the workflow-specific manager contract and capabilities,
  not only generic health.
- For agent-facing HTTP services, treat `endpoints.guide` as service-owned
  onboarding and `endpoints.contract` as strict workflow validation. If the
  guide and contract disagree about endpoints, ownership, or permissions, stop
  and report the mismatch instead of inferring behavior from stale memory,
  filesystem paths, dashboard URLs, or raw receipts.
- Treat task managers as work queues and lifecycle recorders, not as the actors
  doing implementation work. The agent takes, implements, verifies, and reports
  tasks through the manager.
- For single-task intake, require executable lifecycle identifiers, a clear
  rejection, or explicit intake-only documentation. Do not create replacement
  one-task plans to work around raw task receipts that cannot be advanced
  through lifecycle endpoints.
- Treat `gi manager test`, `gi tm test`, `gi манагер тест`,
  `gi менеджер тест`, and equivalent wording as requests to test the currently
  configured task manager end to end. Verify create/load task, next-task or task
  lookup, status update or start, completion, and final readback before doing
  real sprint work. Use a clearly labeled disposable no-op task that requires no
  repository edits, secret access, destructive action, or cross-project
  filesystem access. Stop at the first contract gap, leave the task in the
  safest available state, and report the missing lifecycle operation.

- For sprint-plan intake, verify the manager's executable plan contract before
  sending work. Do not send `kind: sprint-plan` as raw intake and report it as
  an executable sprint; use the documented executable payload, such as
  `type: plan`, `project`, `title`, and non-empty `items[]`, or stop and report
  the contract mismatch.

## Verification

- Reread edited files after changes.
- Run the fastest relevant check first.
- Record checks run and failures in the handoff summary.

## Processes

- Ask before closing editors, apps, servers, or other visible processes.
- Launch GUI tools quietly in the background when possible.
