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
  language names or numbers. Render each option as a task-list bullet with the
  number inside the label, such as `- [x] 1. English`; do not use
  `1. [x] English`, because some chat renderers split the checkbox and label
  onto separate lines.
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
  ask in three numbered steps. For each step, show a concise numbered Markdown
  checklist with the available languages and the current selection, then accept
  the user's next answer as numbers or language names for that step.
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
- Keep `gi` command responses scoped to the shared instruction-kit command. Do
  not resume an older product task after a `gi` command unless the user
  explicitly asks.
- For `gi start`, `gi restore`, and title-only startup messages, restore only
  compact orientation for the next turn. Mention remembered plans, stale task
  notes, old refactoring phases, or local commits ahead of a remote only as
  context when relevant. Do not offer to continue, run, finish, or push
  remembered work unless the user explicitly asks for that action.
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
  config-service config before publishing or refreshing the app's own service
  record when self-registration is enabled. If config-service is missing,
  unreachable, or incomplete, startup reports the blocker and waits instead of
  guessing or falling back to stale ports. Non-web apps do not query or publish
  to config-service during normal startup unless local instructions define a
  discoverable web/API runtime.
- Treat `gi reboot`, `ги ребут`, `gi restart`, and `ги рестарт` as requests to
  start or restart the current application using project-local run instructions.
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
  missing or ambiguous.
- Treat `gi тест-план` and `gi test plan` as requests to inspect local project
  test commands and produce a compact verification plan for the current feature,
  bug fix, or release check. Plan first; run checks only when the user asks or
  when the current task already requires verification.
- Treat a first message that points to a shared instruction library as an
  instruction bootstrap, not as a request to add that library as a dependency.
- If the user asks to update from a shared instruction library and this project
  has no `tools/project-memory/instruction-kit.json`, treat that as first-time
  instruction bootstrap/init.
- Run `gi обновить` quietly by default: do not narrate step-by-step reasoning,
  repeated progress, command transcripts, broad file reads, or full diffs during
  normal successful updates. Apply the update, then report a compact summary
  with versions, migration counts/IDs, changed files, checks, commit/push
  result, and blockers if any.
- For web applications, assume the user will inspect the UI manually. Do not
  open, browse, screenshot, or visually inspect the UI automatically unless the
  user explicitly asks for that.

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
