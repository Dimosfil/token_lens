# Token Lens GI Commands

This is the compact local command index for agent chat commands. These are not
PowerShell commands unless a command explicitly points to a script path.

`gi help`, `gi хелп`, `ги help`, `ги хелп`, `gi commands`, `gi команды`, and
`ги команды` are read-only help requests. They show this command list without
running startup restore, resuming old work, calling task managers, mutating
files, or executing any listed command.

| Command | Description |
| --- | --- |
| `gi help`, `ги хелп`, `gi commands`, `ги команды` | Show this local command list. |
| `gi обновить`, `gi обновись` | Apply accepted instruction-kit migrations. |
| `gi start`, `gi restore` | Restore minimal project context and ask for the current task. |
| `gi summary`, `gi саммари` | Write a thematic handoff summary under `tools/summary/`. |
| `gi language`, `gi язык` | Configure project language preferences. |
| `gi commit language`, `gi коммит язык` | Configure commit-message language preferences. |
| `gi system language`, `gi систем язык` | Configure user-facing agent response language. |
| `gi sql`, `gi sqlite` | Inspect SQLite/FTS project-memory readiness and metrics. |
| `gi trim raw bodies`, `gi clean raw bodies` | Clear only old `raw_logs.feedback_log_body` outside the current month, then `VACUUM`. |
| `gi vector` | Inspect semantic/vector retrieval readiness and metrics. |
| `gi rebuild` | Rebuild the current project/application output through documented local build instructions. |
| `gi tools rebuild`, `gi rag rebuild` | Rebuild the full configured GI/RAG tooling layer after explicit confirmation. |
| `gi tools rebuild sql`, `gi rag rebuild sql` | Rebuild only the SQL/FTS structured-memory node. |
| `gi tools rebuild chunks`, `gi rag rebuild chunks` | Rebuild only semantic chunk exports. |
| `gi tools rebuild vector`, `gi rag rebuild vector` | Rebuild only the vector retrieval node. |
| `gi tools rebuild manifest`, `gi rag rebuild manifest` | Rebuild only source manifest/inventory metadata. |
| `gi tools rebuild evals`, `gi rag rebuild evals` | Run configured RAG health and retrieval eval checks only. |
| `gi config`, `gi config service` | Inspect config/discovery service settings. |
| `gi config service url=<url>` | Set the config-service URL after validation. |
| `gi config service on`, `gi config service off` | Toggle this app's config-service self-registration flag. |
| `gi reboot`, `gi restart`, `ги ребут`, `ги рестарт` | Start or restart all documented Token Lens apps using project-local run instructions. |
| `gi first test`, `gi первый тест` | Reset documented first-run state and verify first-launch behavior. |
| `gi install`, `gi инсталл`, `ги инсталл` | Build/package the project and verify an installer artifact when packaging is configured. |
| `gi ftp config`, `gi ftp service`, `gi ftp folder` | Inspect or configure FTP/SFTP deployment settings without uploading. |
| `gi ftp`, `gi ftp push`, `gi deploy ftp`, `gi upload ftp` | Upload configured build output to the configured FTP/SFTP target. |
| `gi tm`, `gi manager` | Inspect the configured task manager through config-service. |
| `gi manager test`, `gi tm test` | Test the configured task manager contract and operations. |
| `gi active task`, `gi next task`, `gi get task` | Get executable work from the configured task manager. |
| `gi add sprint`, `gi create sprint` | Create a visible Sprint/Cycle through the configured task manager. |
| `gi plan`, `gi план`, `gi post plan` | Send the current plan to the configured task manager. |
| `gi start sprint`, `gi старт спринт` | Take the active Sprint/Cycle into work through the configured task manager. |
| `gi test plan`, `gi тест-план` | Build a verification plan from current project contracts. |
| `gi git summary`, `gi гит-обзор` | Summarize recent git state without printing a full diff. |
| `gi commit`, `gi коммит` | Commit scoped changes. |
| `gi push`, `gi пуш` | Commit and push scoped changes. |
| `gi only push`, `gi только пуш` | Push the current branch without creating a commit. |
| `gi commit push`, `gi коммит пуш` | Commit and push scoped changes. |
| `gi pull`, `gi пул` | Fetch and pull the current branch. |
