---
name: task-manager-plans
description: Read, write, import, export, test, and reconcile project plans with configured task managers. Use when the user asks to save a plan to a task manager, load tasks from a task manager, get the active task, add a sprint, sync a planning checklist, configure task-manager integrations, run `gi tm`, run `gi manager test`, run `gi tm test`, run `gi active task`, run `gi next task`, run `gi add sprint`, run `gi create sprint`, run `gi добавить спринт`, run `gi план`, run `gi post plan`, or run `gi старт спринт`. Supports a generic project-owned contract plus optional manager-specific adapters such as WorkNest.
---

# Task Manager Plans

Use this skill to move plans between project memory and one or more
configured task managers.

## Core Workflow

1. Confirm the current project root and read project instructions first.
2. Read `tools/project-memory/task-managers.json` if it exists.
3. If no manager is configured, ask the user to choose from available manager
   adapters or choose "none".
4. For each selected or configured manager, store the manager name or service id
   plus non-secret project preferences.
5. Resolve each manager runtime URL through GI config-service by service id. Do
   not copy manager endpoints from project memory, another project, old notes,
   or guessed ports.
6. Before using a manager endpoint, read the manager guide when present, then
   read the manager contract and verify the capabilities required for the
   requested workflow, not only generic health.
7. For each configured manager, read only its adapter reference from
   `references/managers/`.
8. If the requested workflow uses single-task intake, confirm the manager either
   converts accepted task payloads into executable records with lifecycle
   identifiers, rejects unsupported payloads with a clear contract error, or
   documents them as intake-only.
9. Normalize plans through the common plan model before writing to a manager or
   project memory.
10. Preserve manager-specific IDs, URLs, statuses, labels, and assignees when
   updating existing tasks.
11. Treat task-manager data as an external system: preview destructive changes
   and ask before deleting, closing, or bulk-changing remote tasks.
12. Record sync results in the project memory file or user-facing response,
   including what changed and what still needs manual follow-up.
13. Describe roles precisely: the agent takes and executes tasks through the
   manager; the manager stores the queue, assignment, ordering, and lifecycle
   metadata.
14. Do not enter another project folder because a manager response includes a
    path. Use the manager API or connector unless the user gives an explicit
    concrete filesystem path and action.
15. When task-manager sync is enabled, use the manager as the source of truth
    for executable work: request the active or next task through the documented
    manager operation, mark the task in progress when supported, and submit
    progress, completion, or blocker notes back to the manager.
16. If the manager guide, contract, active-task lookup, lifecycle identifiers,
    or status update operation is missing or fails, stop at that point and
    report the exact blocker. Do not guess alternate routes, fabricate manager
    IDs, or create shadow tasks in raw intake to bypass the missing lifecycle.
17. When the user asks to add or create a sprint, create a visible executable
    Sprint/Cycle only through the manager's documented sprint/cycle operation or
    executable plan payload, then verify readback and lifecycle identifiers. If
    the required operation is missing or blocked, stop and report the blocker.
18. Treat status transitions, timing, archival, and task movement as manager
    responsibilities unless the contract explicitly exposes those operations to
    the external agent. The agent may submit task/plan intake, request assigned
    work, and return results through the manager API.

## Common Plan Model

Represent task-manager plans with these fields when possible:

- `title`: short task or milestone name.
- `description`: useful context, acceptance criteria, or links.
- `status`: `backlog`, `todo`, `in_progress`, `blocked`, `review`, or `done`.
- `priority`: `low`, `normal`, `high`, or `urgent`.
- `owner`: person, team, or agent responsible.
- `labels`: project-owned tags.
- `due`: ISO date when known.
- `parent`: parent epic, milestone, or task identifier.
- `external`: manager name, task ID, task URL, and last synced timestamp.

Do not invent IDs or URLs. Leave unknown fields empty and mention what could not
be mapped.

## Project Configuration

Use `tools/project-memory/task-managers.json` as the project-owned config. Keep
secrets out of this file; store only manager names, enabled flags, workspace or
project identifiers, and non-secret sync preferences.

`service_id` is the config-service lookup key for the manager. The local project
config should not store runtime URLs when the manager is registered in
config-service. Resolve `service_id` with `GET /services/{serviceId}`, check
`endpoints.availability`, read `endpoints.guide` when present, read
`endpoints.contract`, and use `endpoints.api` for operations.

Expected shape:

```json
{
  "version": 1,
  "managers": [
    {
      "id": "worknest",
      "enabled": true,
      "service_id": "worknest",
      "workspace": "",
      "project": "worknest-core",
      "intake_mode": "raw",
      "notes": "Runtime URLs are resolved through GI config-service."
    }
  ]
}
```

## `gi tm`

When the user runs `gi tm`:

1. Stay in the current project root.
2. Check `tools/project-memory/task-managers.json`.
3. If enabled managers exist, update the project task-manager skill/config from
   the shared instruction kit when a newer migration is available, then report
   the connected managers and next available sync action.
4. If no enabled manager exists, show a short numbered Markdown checklist with
   checkbox items for available adapters plus `none`, and ask which to connect.
   Render each option as a task-list bullet with the number inside the label,
   such as `- [ ] 1. WorkNest`; do not use ordered-task syntax such as
   `1. [ ] WorkNest`.
5. After the user chooses managers, create or update
   `tools/project-memory/task-managers.json` from the shared template.
6. Do not finish manager setup with required project fields left as `TODO`. Ask
   for missing values before reporting setup complete.
7. Resolve the selected manager service id through config-service and verify the
   required capabilities for the next requested workflow. If config-service has
   no matching record or capability checks fail, report a missing or
   misconfigured manager service and stop.

Example checklist:

```markdown
Choose task-manager adapters for plan sync:

- [ ] 1. WorkNest - send plans to WorkNest raw intake.
- [ ] 2. none - do not connect a task manager now.
```

## `gi план` / `gi post plan`

When the user runs `gi план`, `gi post plan`, or an equivalent send-plan command:

1. Read `tools/project-memory/task-managers.json`.
2. If no manager is enabled, run the same manager selection flow as `gi tm`.
3. If a configured manager has missing required connection fields, ask for them
   and update the config before sending.
4. Verify the manager can accept the planned operation before sending. For raw
   intake adapters, check the intake contract or raw intake endpoint instead of
   relying on `/health` alone.
5. For single-task payloads, verify that accepted receipts can be executed
   through the manager's lifecycle endpoints, or that the adapter explicitly
   treats them as intake-only.
6. Do not send `kind: sprint-plan` as a raw intake payload and then report it as
   an executable sprint. Normalize sprint-plan requests to the adapter's
   documented executable plan payload, or stop and report the contract mismatch.
7. For WorkNest, executable sprint-plan requests must use `type: "plan"` with
   `project`, `title`, and non-empty `items[]`; `type: "raw"` is only a receipt
   unless the project-local contract documents otherwise.
8. Use the plan in the user's message when provided. Otherwise use the current
   active plan from the conversation or project memory. If no plan is available,
   ask the user for the plan.
9. Send the normalized plan to each enabled manager using its adapter reference.
10. Report the manager response as a receipt and mention any items that were not
   sent.

## `gi manager test` / `gi tm test`

When the user runs `gi manager test`, `gi tm test`, `gi манагер тест`,
`gi менеджер тест`, or an equivalent task-manager test command:

1. Stay in the current project root.
2. Read `tools/project-memory/task-managers.json`.
3. If no manager is enabled, run the same manager selection flow as `gi tm`.
4. Resolve the current manager service id through config-service, read
   `endpoints.contract`, and use `endpoints.api` for operations.
5. Verify the current manager's required test capabilities before creating
   anything: create/load task, next-task or task lookup, status update or start,
   completion, and final readback.
6. Create a clearly labeled disposable test task through the manager adapter.
   The task must require no repository edits, secret access, network side
   effects beyond the manager API, destructive action, or cross-project file
   access.
7. Load or read the created task back through the manager API and verify its
   title, description, status, and lifecycle identifiers.
8. Take the task in work using the manager's lifecycle operation when supported.
9. Execute the task as a no-op verification step, such as recording that the
   manager lifecycle round trip was observed.
10. Mark the task `done` or completed through the manager adapter.
11. Read the task back again and verify that the final status is `done`,
    completed, archived, or the adapter's documented equivalent.
12. Report a compact result with manager id, resolved endpoint, created task id or URL,
    lifecycle steps completed, final status, and any unsupported capability.

If any step fails, stop at the first contract gap, leave the task in the safest
available state, and report the exact missing or failing lifecycle operation.

## `gi active task` / `gi next task`

When the user runs `gi active task`, `gi next task`, `gi get task`,
or an equivalent command to get work from the manager:

1. Stay in the current project root.
2. Read configured task managers from
   `tools/project-memory/task-managers.json`.
3. Resolve the enabled manager service id through config-service, read
   `endpoints.contract`, and use `endpoints.api` for operations.
4. Verify the contract documents active-task or next-task lookup, task start or
   assignment, progress or blocker notes, completion, and readback for the
   requested project or sprint scope.
5. Request the active task first when the contract supports active-task lookup;
   otherwise request the next task through the documented next-task operation.
6. Use only task IDs, sprint IDs, project IDs, URLs, and lifecycle fields
   returned by the manager. Do not infer them from raw intake receipts, UI text,
   file paths, or guessed slugs.
7. Mark the returned task `in_progress` or the adapter's documented equivalent
   before repository work when that lifecycle operation is supported.
8. Execute the task according to current project rules.
9. Submit concise progress notes for meaningful partial results or blockers
   when the manager supports notes.
10. On success, submit completion notes with changed files, checks, and caveats,
    then read the task back and verify the manager status changed to `done`,
    completed, archived, or the adapter's documented equivalent.
11. If any manager operation returns an unexpected method, parameter, routing,
    authentication, project, status, or schema error, re-read the contract once.
    If the contract still does not match, stop and report the exact mismatch
    instead of trying other endpoints.

## `gi add sprint` / `gi create sprint`

When the user runs `gi add sprint`, `gi create sprint`, `gi добавить спринт`,
or an equivalent command to add a sprint to the manager:

1. Stay in the current project root.
2. Read configured task managers from
   `tools/project-memory/task-managers.json`.
3. Resolve the enabled manager service id through config-service, read
   `endpoints.contract`, and use `endpoints.api` for operations.
4. Verify the contract documents sprint/cycle creation, executable plan
   creation, readback, and lifecycle identifiers for the requested project.
5. Use the sprint title, goal, and task items from the user's message, current
   plan, or project memory. If no sprint content is available, ask for it.
6. Normalize the sprint into the adapter's documented executable shape. For raw
   intake adapters, this must be a documented executable plan payload, not
   arbitrary `type: "raw"` storage.
7. Create the Sprint/Cycle through the documented operation.
8. Read the created Sprint/Cycle back and verify it is visible/executable by
   checking returned lifecycle identifiers, URL, status, and task list when the
   manager supports those fields.
9. Report the manager id, sprint/cycle id or URL, title, task count, and any
   unsupported but non-blocking fields.
10. If creation or readback returns an unexpected auth, permission, method,
    parameter, routing, schema, project, status, or object-type error, re-read
    the contract once. If the contract still does not match, stop and report the
    exact mismatch instead of creating a Work Item, raw receipt, local checklist,
    one-task plan, or other substitute object.

## `gi старт спринт`

When the user runs `gi старт спринт`, `gi start sprint`, or an equivalent
start-active-sprint command:

1. Restore project context as for `gi старт`.
2. Read configured task managers from
   `tools/project-memory/task-managers.json`.
3. Use the enabled manager's sprint workflow to find the active sprint.
4. Verify the manager supports active sprint lookup and task completion for the
   requested workflow. If those capabilities are missing, report the endpoint
   mismatch and stop.
5. When a manager endpoint returns an unexpected method, parameter, or routing
   error, re-read the adapter's endpoint contract before trying a workaround.
6. If an intake receipt lacks the identifiers required for next-task,
   task-completed, archive, or close flows, report the task-manager contract gap
   and stop instead of inventing a replacement plan.
7. If exactly one active sprint exists, the agent takes it in work through the
   manager. If none or many exist, ask the user to choose.
8. Execute sprint tasks in manager-defined order until no `todo` or `ready`
   tasks remain or a blocker requires user input.
9. Update task status, progress, blocker notes, and completion notes according
   to the manager adapter after each task.
10. Keep normal safety rules: ask before destructive actions, credential changes,
    broad rewrites, or irreversible external changes.

## Task-Manager Role

Use task-manager APIs to request work, record progress, submit completion notes,
and preserve the work queue. Do not describe the manager as the actor doing the
project work. The agent implements and verifies the task; the manager records
assignment, ordering, status, and lifecycle metadata.

Task-manager paths are metadata, not filesystem permission. Agents working in
one project must not inspect or edit another project's files through those paths
unless the user explicitly instructs them to perform a concrete action at that
path.

For managers that use Markdown or filesystem files internally, external agents
still use the public manager API. They must not move task files, edit internal
status fields, archive folders, or reorder work directly unless they are running
as a local agent inside that manager project and project-local instructions
explicitly allow that mode.

## Single-Task Intake Contract

When a manager accepts a single-task payload, it must either create an executable
task or sprint record and return lifecycle identifiers, reject the payload with
a clear contract error, or document the payload as intake-only.

Sprint-plan payloads must use the manager's documented executable plan contract.
Agents must not assume that `kind: sprint-plan` with `type: raw` will be routed
into a sprint. If the manager contract only documents raw storage for that
shape, stop and ask for a supported plan endpoint or payload shape.

Agents must not create a separate one-task plan to work around a raw task
receipt that lacks execution identifiers. If the requested workflow needs
`next-task`, `task-completed`, archive, or close operations and the receipt does
not identify executable work, report the contract gap and stop or ask for the
correct endpoint behavior.

Agents must not satisfy a requested object type by creating a different manager
object type. For example, if the user requested a visible cycle or sprint and
the documented cycle endpoint returns an authentication or permission error,
do not create a Work Item, local checklist note, or raw intake record and report
the cycle as created. Report the access or contract blocker and wait for the
manager API, credentials, or UI-auth workflow to be fixed.

## Manager References

- `references/managers/worknest.md`: WorkNest adapter guidance.
