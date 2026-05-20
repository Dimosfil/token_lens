---
name: task-manager-plans
description: Read, write, import, export, test, and reconcile project plans with configured task managers. Use when the user asks to save a plan to a task manager, load tasks from a task manager, sync a planning checklist, configure task-manager integrations, run `gi tm`, run `gi manager test`, run `gi tm test`, run `gi план`, run `gi post plan`, or run `gi старт спринт`. Supports a generic project-owned contract plus optional manager-specific adapters such as WorkNest.
---

# Task Manager Plans

Use this skill to move plans between project memory and one or more
configured task managers.

## Core Workflow

1. Confirm the current project root and read project instructions first.
2. Read `tools/project-memory/task-managers.json` if it exists.
3. If no manager is configured, ask the user to choose from available manager
   adapters or choose "none".
4. For each selected or configured manager, fill required connection fields from
   project instructions, environment/config, or a short user question.
5. Treat each manager endpoint as project-local state. Do not reuse a manager
   endpoint from another project unless the user explicitly confirms it.
6. Before using a manager endpoint, verify the capabilities required for the
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

`base_url` is the manager API endpoint used for operations. Do not put a UI URL
in `base_url` unless the adapter explicitly says the same URL serves both UI and
API. Do not leave endpoint fields empty, guessed, or set to `TODO` when a
manager is enabled.

Expected shape:

```json
{
  "version": 1,
  "managers": [
    {
      "id": "worknest",
      "enabled": true,
      "base_url": "http://127.0.0.1:4187/",
      "workspace": "",
      "project": "worknest-core",
      "intake_mode": "raw",
      "notes": "Project-local manager API endpoint. UI URLs are documented separately if needed."
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
5. After the user chooses managers, create or update
   `tools/project-memory/task-managers.json` from the shared template.
6. Do not finish manager setup with required fields left as `TODO`. Ask for
   missing values before reporting setup complete.
7. Verify the selected manager's required capabilities for the next requested
   workflow. If health succeeds but required capability checks fail, report a
   stale or misconfigured manager endpoint and stop.

Example checklist:

```markdown
Choose task-manager adapters for plan sync:

1. [ ] WorkNest - send plans to WorkNest raw intake.
2. [ ] none - do not connect a task manager now.
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
4. Verify the current manager's required test capabilities before creating
   anything: create/load task, next-task or task lookup, status update or start,
   completion, and final readback.
5. Create a clearly labeled disposable test task through the manager adapter.
   The task must require no repository edits, secret access, network side
   effects beyond the manager API, destructive action, or cross-project file
   access.
6. Load or read the created task back through the manager API and verify its
   title, description, status, and lifecycle identifiers.
7. Take the task in work using the manager's lifecycle operation when supported.
8. Execute the task as a no-op verification step, such as recording that the
   manager lifecycle round trip was observed.
9. Mark the task `done` or completed through the manager adapter.
10. Read the task back again and verify that the final status is `done`,
    completed, archived, or the adapter's documented equivalent.
11. Report a compact result with manager id, endpoint, created task id or URL,
    lifecycle steps completed, final status, and any unsupported capability.

If any step fails, stop at the first contract gap, leave the task in the safest
available state, and report the exact missing or failing lifecycle operation.

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
5. If an intake receipt lacks the identifiers required for next-task,
   task-completed, archive, or close flows, report the task-manager contract gap
   and stop instead of inventing a replacement plan.
6. If exactly one active sprint exists, the agent takes it in work through the
   manager. If none or many exist, ask the user to choose.
7. Execute sprint tasks in manager-defined order until no `todo` or `ready`
   tasks remain or a blocker requires user input.
8. Update task status and completion notes according to the manager adapter.
9. Keep normal safety rules: ask before destructive actions, credential changes,
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

## Manager References

- `references/managers/worknest.md`: WorkNest adapter guidance.
