# WorkNest Task Manager Adapter

Use this reference only when the project has enabled the `worknest` manager or
the user explicitly asks to connect WorkNest.

## Configuration

Store non-secret WorkNest settings in `tools/project-memory/task-managers.json`:

- `id`: `worknest`
- `enabled`: `true` or `false`
- `service_id`: config-service lookup key, normally `worknest`
- `workspace`: WorkNest workspace slug or name, if known
- `project`: WorkNest project slug, board, or list, if known
- `intake_mode`: `raw` for the current HTTP intake MVP
- `default_status`: optional default status for newly created tasks

Do not store API tokens, cookies, passwords, or private workspace data in the
shared instruction files or committed project memory.

`service_id` is required when enabling WorkNest. Resolve it through GI
config-service with `GET /services/worknest`, check `endpoints.availability`,
read `endpoints.guide` when present, read `endpoints.contract`, and use
`endpoints.api` for operations. Do not store or copy WorkNest runtime URLs in
project memory when the service is registered in config-service.

Local project memory may name WorkNest with `service_id: "worknest"` and a
default project such as `worknest-core`. Historical local URLs such as
`http://127.0.0.1:4190` or startup commands such as
`tools/start-worknest.ps1 -IncludeAgent -SkipWeb` are only operator context.
External agents must resolve the current WorkNest API URL through
config-service before every workflow instead of treating a remembered URL as
canonical.

## Current Intake MVP

The current WorkNest working version exposes a minimal raw HTTP intake for
external agents.

Known commands from the WorkNest project:

```powershell
npm run check:api
npm run dev:api
```

Known endpoints:

- `GET /health`
- `GET /agent-intake/guide` when the live service exposes an agent guide
- `GET /agent-intake/contract`
- `POST /agent-intake/raw`
- `GET /agent-intake/raw`
- `GET /agent-intake/raw/:id`
- `GET /agent-intake/next-task?project=<project>&sprintId=<sprintId>`
- `POST /agent-intake/task-completed`

The external-agent contract is: send a task or plan, request assigned work, and
return execution results. WorkNest manager owns status transitions, timing,
archival, task ordering, and task movement unless the live contract explicitly
delegates a specific lifecycle operation to the external agent.

Use `/health` only as a basic liveness check. Before posting a plan, verify the
agent guide when present, then verify the raw intake contract or raw intake
endpoint. Before running `gi start sprint`, verify active/next task and
completion endpoints required by the current workflow, including the documented
HTTP method and query parameters. If `/health` succeeds but required workflow
endpoints return missing or incompatible responses, re-read the guide and this
adapter contract, report a stale or misconfigured WorkNest API endpoint when
the contract still does not match, and stop before sending work.

If WorkNest accepts `type: "task"` or another single-task intake payload, verify
that the response either creates an executable sprint/task and returns the IDs
needed by `/agent-intake/next-task` and `/agent-intake/task-completed`, rejects
the payload with a clear contract error, or documents it as raw intake only. Do
not create a replacement one-task plan to complete a raw task receipt that lacks
execution identifiers.

Do not replace a requested WorkNest object type with another object type. If a
visible Cycle/Sprint is required and `/product/cycles` or the documented cycle
operation returns `401 Authentication required`, a permission error, or a
contract mismatch, stop and report that Cycle creation is blocked. Do not create
a Work Item, raw receipt, or local `pending-tasks.md` note as a substitute for
the missing Cycle.

Do not send `kind: "sprint-plan"` with `type: "raw"` and treat the receipt as a
created sprint. Before sending sprint work, read `/agent-intake/contract` and
use the documented executable plan shape. For the current WorkNest sprint
workflow, that means a supported plan payload with fields such as `type:
"plan"`, `project`, `title`, and `items[]`, unless the project-local contract
documents a newer equivalent. If the contract does not support executable
sprint creation, stop and report the mismatch instead of adding compatibility
code or claiming a sprint was created.

Use the same executable creation rule for `gi add sprint`, `gi create sprint`,
`gi добавить спринт`, and equivalent add-sprint commands. The result must be a
visible executable Cycle/Sprint with readback or lifecycle identifiers. If
WorkNest only returns a raw receipt or the Cycle/Sprint route requires UI
authentication, stop and report the blocker.

Raw intake payloads are stored under `storage/agent-intake/raw/` in the WorkNest
project and may contain user-supplied data. Do not commit, print, or log full
raw payloads by default.

Future WorkNest storage stages:

- `storage/agent-intake/parsed/`
- `storage/agent-intake/routed/`
- `storage/agent-intake/rejected/`

The intake API is intentionally neutral. Do not bind an intake item directly to
a project or folder unless the user explicitly asks. Parser/router stages should
later convert raw envelopes into normalized events and routed candidates.

Executable sprint plans are not plain raw text. For the current WorkNest
contract, use a structured plan payload with `type: "plan"`, `project`, `title`,
and non-empty `items[]`. WorkNest turns that payload into an executable sprint
and tasks, then returns identifiers the agent must use for later `next-task` and
`task-completed` calls.

## Sprint Workflow For Markdown Projects

When a WorkNest-style Markdown project receives an accepted plan, WorkNest may
store it internally as a sprint. The sprint folder is the internal execution
unit, and numbered task files define the order in which WorkNest assigns work.

Create a unique dated sprint folder directly inside the target project:

```text
projects/<project-id>/YYYY-MM-DD_<sprint-slug>/
```

Do not create a shared `sprints/` container by default. Each active sprint is
its own project-level folder. Completed sprint folders can later be moved to the
project archive.

Add `sprint.md` inside the sprint folder with:

- sprint title;
- status;
- project id;
- start date;
- source plan or source request;
- sprint goal;
- ordered task list.

Split the plan into numbered task files:

```text
001_short-task-title.md
002_short-task-title.md
003_short-task-title.md
```

Each task file should include at minimum:

```text
# Human-readable task title

Status: todo
Sprint: YYYY-MM-DD_<sprint-slug>
Order: 001
Project: <project-id>
Agent: <agent-or-unassigned>
SourcePlanId: <source-plan-id>
DependsOn: none
Tags: [...]
```

Local agents running inside the WorkNest project may execute sprint task files
in ascending `Order` when project-local instructions allow that mode. External
agents must not scan these files; they request the next task through the
WorkNest API.

When an external agent completes a task, it sends concise result notes through
`POST /agent-intake/task-completed`. WorkNest updates internal Markdown status,
timing, archival, and movement according to its own manager rules.

Testing tasks can be added later. Do not block the initial sprint workflow on a
full testing model.

## Active Sprint Execution

Use this workflow for `gi старт спринт`, `gi start sprint`, or equivalent
commands.

WorkNest manages sprint records, task ordering, assignment metadata, and status
transitions. The external agent is the worker: it requests the next task,
implements it in the target project, verifies the result, and submits completion
notes back to WorkNest.

WorkNest `sprintPath`, task `path`, and raw intake `file` fields are manager
metadata. They are not permission to browse or edit WorkNest storage or another
project folder from the current repository. Use the WorkNest API for task
state, and access external filesystem paths only when the user gives a concrete
path and action.

Find active sprints through WorkNest API or connector surfaces when available.
Do not scan WorkNest project folders from another repository. Filesystem scans
are allowed only inside the current project root, or when the user gives an
explicit concrete path and action.

If exactly one active sprint exists, the agent takes it in work through WorkNest.
If there are no active sprints or several active sprints, show the concise list
and ask the user to choose.

For the selected sprint:

1. Request the next task through the WorkNest API or connector.
2. Use returned task identifiers, title, order, and instructions as the work
   contract.
3. Treat status changes such as `in_progress` and `done` as WorkNest lifecycle
   records.
4. Execute the task in the current project according to its instructions and
   project rules.
5. Submit progress or blocker notes through WorkNest when the task cannot be
   completed in the same run.
6. On success, submit concise completion notes with changed files, checks, and
   important caveats, then read the task back when the API supports readback.
7. Continue to the next `todo` or `ready` task in order through the manager.

Stop the sprint run and report the blocker when a task needs user input, has
missing access, conflicts with project instructions, requires a destructive
action, or fails verification in a way that should not be papered over.

## Mapping

Map the common plan model to WorkNest concepts using the project-owned names:

- Plan item `title` -> WorkNest task title.
- Plan item `description` -> WorkNest task description or notes.
- Plan item `status` -> WorkNest board column or task state.
- Plan item `priority` -> WorkNest priority when available; otherwise use a
  label.
- Plan item `owner` -> WorkNest assignee when the user provides an exact name.
- Plan item `labels` -> WorkNest tags or labels.
- Plan item `parent` -> WorkNest epic, parent task, or project section.

When WorkNest field names differ in a project, prefer the project's existing
board/list vocabulary over these defaults.

## Read Plan

When reading from WorkNest:

1. Identify the workspace/project from project config or ask the user.
2. Fetch only the relevant board, list, epic, or task set.
3. Convert tasks into the common plan model.
4. Preserve WorkNest IDs and URLs in `external`.
5. Summarize imported tasks without dumping the whole manager export.

## Write Plan

When writing to the current WorkNest intake or adding a sprint:

1. Resolve `service_id` through config-service; stop if the service record is
   missing.
2. Read the resolved contract endpoint before sending sprint-plan work or
   adding a sprint, and follow the documented executable plan shape.
3. Use the resolved API endpoint for writes.
4. Prefer the documented raw intake operation with a compact payload containing:
   - `agent`
   - `type`
   - `title` or `body`
   - optional `source`
   - optional `metadata` or `tags`
5. Use `type: "task"` for task candidates unless the plan item is clearly an
   idea, note, report, project candidate, decision, or unknown.
6. Treat the raw intake response as a receipt, not as proof that a WorkNest card
   or executable task exists.
7. If the caller needs executable sprint work, require a response with lifecycle
   identifiers or send a supported executable payload such as `type: "plan"`
   with `project`, `title`, and `items[]`. Do not downgrade `kind:
   "sprint-plan"` to `type: "raw"`.
8. Do not auto-edit WorkNest project files. The parser/router and later
   accept/reject flow decide what becomes a real card.

Executable sprint-plan payloads for the current WorkNest API must be sent to
`POST /agent-intake/raw` with `type: "plan"`, not with `type: "raw"`:

```json
{
  "agent": "codex",
  "type": "plan",
  "project": "project-slug",
  "title": "Sprint: short sprint title",
  "goal": "What the sprint should achieve.",
  "sourcePlanId": "stable-local-plan-id-or-path",
  "items": [
    {
      "title": "First executable task",
      "body": "What to do.",
      "done": "How to verify completion.",
      "tags": ["sprint"]
    }
  ]
}
```

If an agent only has `description`, `planned_changes`, `verification`, or a
local `plan_path`, it must normalize those fields into `items[]` before sending.
Never send that shape as `{ "type": "raw", "kind": "sprint-plan" }` and report
it as a sprint.

When the user explicitly asks to turn a plan into a WorkNest Markdown sprint,
use the sprint workflow above instead of treating the plan as only a raw intake
receipt.

When writing to a future concrete WorkNest task API:

1. Match existing tasks by WorkNest ID first, then by exact title only if the
   user accepts the risk of title collisions.
2. Create missing tasks only after showing a concise preview.
3. Update changed fields while preserving WorkNest-only metadata.
4. Ask before closing, deleting, reassigning, or bulk-moving tasks.

## Unknowns

The current shared adapter knows only the raw intake MVP. It does not yet define
concrete card, board, or accept/reject APIs. Use project runbooks,
official WorkNest docs, configured MCP connectors, browser automation, or
user-provided export files when those surfaces become available.
