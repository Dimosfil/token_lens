# Token Lens Instruction Index

This index catalogs reusable instruction-kit files currently copied into this
project. It is an agent-facing map, not product documentation.

## Entrypoints

- `AGENTS.md`: project-local agent instructions and GI command routing.
- `COMMANDS.md`: compact local GI command index.
- `tools/AGENT_WORKING_AGREEMENTS.md`: local collaboration and operating rules.
- `tools/AGENT_RUNBOOK.md`: project run, test, startup, and troubleshooting
  commands.
- `tools/agent-start.ps1`: compact startup restore helper.

## Runtime Modules

- `patterns/AGENTS_RUNTIME/01-purpose.md`
- `patterns/AGENTS_RUNTIME/02-repository-map.md`
- `patterns/AGENTS_RUNTIME/03-rule-precedence.md`
- `patterns/AGENTS_RUNTIME/04-content-and-authoring.md`
- `patterns/AGENTS_RUNTIME/05-windows-command-policy.md`
- `patterns/AGENTS_RUNTIME/06-tool-usage-and-token-economy.md`
- `patterns/AGENTS_RUNTIME/07-startup-and-scope.md`
- `patterns/AGENTS_RUNTIME/08-config-service-and-task-manager.md`
- `patterns/AGENTS_RUNTIME/09-project-operation-commands.md`
- `patterns/AGENTS_RUNTIME/10-private-scope-and-missing-context.md`
- `patterns/AGENTS_RUNTIME/11-language-preferences.md`
- `patterns/AGENTS_RUNTIME/12-ui-and-focus.md`
- `patterns/AGENTS_RUNTIME/13-progress-updates.md`
- `patterns/AGENTS_RUNTIME/14-update-intake.md`
- `patterns/AGENTS_RUNTIME/15-verification.md`
- `patterns/AGENTS_RUNTIME/16-git-policy.md`

## Patterns

- `patterns/API_KEY_SECRET_SAFETY.md`: credential handling, secret storage,
  leak rotation, and client-bundle safety.
- `patterns/ARCHITECTURE_AND_CODE_QUALITY.md`: architecture and code-quality
  boundaries for maintainable application work.
- `patterns/COHERENT_BATCH_VERIFICATION.md`: source-of-truth consistency and
  verification after meaningful batches.
- `patterns/CONFIGURATION_BOUNDARIES.md`: rules for keeping deploy, runtime,
  credential, path, and policy values out of application logic.
- `patterns/DEVELOPMENT_TOOL_PRODUCT_BOUNDARIES.md`: separation between tools,
  orchestrators, generated products, and selected workflow state.
- `patterns/FIRST_MESSAGE_HANDLING.md`: first-message title handling and
  shared-instruction bootstrap behavior.
- `patterns/GIT_WORKFLOW.md`: git policy, dirty worktrees, explicit finish
  commands, and commit-message language preferences.
- `patterns/PROJECT_DEV_PROD_SERVICES.md`: development versus live production
  service workflow.
- `patterns/PROJECT_DOCUMENTATION_LAYERS.md`: split between user docs and
  implementation-driving project memory.
- `patterns/PROJECT_MEMORY_SPECIFICATIONS.md`: durable memory specifications
  for behavior, business rules, integrations, and architecture.
- `patterns/PROJECT_TESTING_STRATEGY.md`: project-aware feature and release
  verification.
- `patterns/SENIOR_AGENT_ENGINEERING_STANDARD.md`: compact maintainer-level
  execution checklist for coding agents.
- `patterns/TECHNOLOGY_STACK_INVENTORY.md`: verified stack inventory rules.

## Templates

- `templates/FEATURE_WORKFLOW_CONTRACT.template.md`
- `templates/TECHNOLOGY_STACK.template.md`
- `templates/instruction-kit.template.json`
- `templates/project-memory-README.template.md`
- `templates/rag-system.template.json`

## Skills

- `skills/task-manager-plans/SKILL.md`: optional task-manager plan sync skill.
- `skills/task-manager-plans/references/managers/worknest.md`: WorkNest
  adapter notes for the task-manager plan skill.

## Project Memory

- `tools/project-memory/README.md`
- `tools/project-memory/STUDY_PLAN.md`
- `tools/project-memory/pending-tasks.md`
- `tools/project-memory/rag-system.json`
- `tools/project-memory/retrieval-evals.json`
- `tools/project-memory/specs/technology-stack.md`
- `tools/project-memory/specs/integration-contracts/connected-projects.md`
