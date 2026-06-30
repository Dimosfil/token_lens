# Agent Runbook

Every command should be copy-pasteable from the project root.

## Install

```powershell
# Uses the system/local Python environment. No dependency manifest is currently present.
```

## Prepare Local Source Config

Run this before a first launch from a new checkout/root, before diagnosing
`0` imported rows, or whenever `config.local.json` is missing:

```powershell
python -c "from app.core.config import load_config; print(load_config())"
```

Expected result:

- `config.local.json` is created or updated when Codex/OpenCode source paths are
  blank or stale.
- Existing readable values in `config.local.json` are preserved.
- The app does not need committed machine-specific paths in `config.json`.

Source-of-truth files for this behavior:

```text
app/core/config.py
app/core/codex_discovery.py
README.md
```

Do not manually choose between multiple Codex SQLite candidates by querying
private log contents. The active-file selection in
`app/core/codex_discovery.py` is the contract:

```text
1. Prefer ~\.codex\sqlite\logs_2.sqlite when it is the active candidate.
2. Use ~\.codex\logs_2.sqlite when safe file metadata shows it is the active
   updated source.
```

Checking path existence and file metadata is enough for configuration. Do not
run schema, row-count, prompt, response, raw-body, or content-inspection queries
against user-private Codex/OpenCode files just to prepare startup.

The interactive equivalent is:

```powershell
.\tools\configure-local-sources.ps1
```

Accept the suggested values unless the user explicitly gives a different local
source path.

## Verify Codex Account Limits

Use this section when the user asks whether Codex 5h, weekly, Spark, or account
remaining limits work.

Important distinction:

- Codex 5h/weekly/Spark limits come from `codex app-server --stdio`.
- They do not come from `OPENAI_API_KEY`, OpenAI Admin API, OpenAI usage/costs
  endpoints, or `data\analytics.sqlite`.
- OpenAI API usage/costs/rate limits are a separate future integration.
- Token Lens keeps one reusable `codex app-server --stdio` process by default
  and sends repeated `account/rateLimits/read` requests through it. The process
  is restarted on timeout or pipe failure and closed after the configured idle
  timeout.

Read these files before changing limit behavior:

```text
app/services/codex_account_service.py
app/core/codex_discovery.py
app/services/analytics_service.py
web/js/render/limits.js
desktop/mini_client.py
```

Start or reuse the local app:

```powershell
.\start.ps1
```

Check the API endpoint with PowerShell-native HTTP:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/usage-limits"
```

Expected successful shape:

```text
ok: true
source: codex_app_server
groups: one or more limit groups
windows: one or more windows
window labels: 5h and/or weekly
Spark: a separate group/window when the account reports it, commonly with a
       display name like GPT-5.3-Codex-Spark
```

If the response is unavailable:

- `codex command not found`: set or repair the local Codex launcher path.
- `[WinError 5] Access denied`: Windows likely resolved a blocked WindowsApps
  shim or another unusable launcher.
- `timed out`: the launcher started but did not answer the stdio protocol in
  time.

Preferred fix for launcher resolution is an ignored local config override:

```json
{
  "codex_app_server_command": "C:\\Users\\Fil-Dom\\.codex\\bin\\codex.cmd"
}
```

Use the actual current user's path when different. Prefer Codex-owned helper
locations such as `.codex\bin` or user npm bin folders over WindowsApps shims.
Do not solve this with `OPENAI_API_KEY`, OpenAI Admin API keys, broad antivirus
exclusions, System32 exclusions, or SQLite log inspection.

Do not report "codex is not installed" or tell the user to install OpenAI Codex
CLI until the project discovery path has been checked:

```powershell
python -c "from app.core.config import load_config; print(load_config().get('codex_app_server_command'))"
```

If that prints a real file outside WindowsApps, use it. If it prints nothing,
check whether `%USERPROFILE%\.codex\bin\codex.cmd` exists and add that path to
ignored `config.local.json`. WindowsApps aliases are treated as unusable even if
`where codex` or PATH discovery finds them.

## Run

```powershell
.\start.ps1
```

Starts the documented Token Lens app set:

- web/API server: `python run_server.py`, PID in `data\server.pid`;
- desktop mini client: `python desktop\mini_client.py`, PID in
  `data\mini_client.pid`.

Use `.\start.ps1 -Restart` for `gi reboot` / `gi restart`. Use
`.\start.ps1 -NoMini` only when deliberately running the web/API server without
the desktop mini client.

The desktop mini client should open as a single GUI window. `start.ps1` uses
`pythonw.exe` when available so an extra Python console window is not expected.

For `gi reboot` / `gi restart`, report each documented app separately:
web/API server and desktop mini client. Include whether each app was started,
restarted, or skipped, plus verification evidence such as live process/PID,
health endpoint for the web/API server, mini-client window or process signal,
and relevant startup or crash-log findings. Do not report reboot success from a
web health check alone when the mini client is expected.

## Test

```powershell
python -m compileall app
```

## Build

```powershell
# No separate build step is currently defined.
```

## Smoke Check

```powershell
.\start.ps1
# Open manually when requested: http://127.0.0.1:8765
```

Expected result:

```text
Token Lens starts on http://127.0.0.1:8765, writes data/server.pid, starts the
desktop mini client, and writes data/mini_client.pid.
```

## Logs

```powershell
# No dedicated log file is currently defined.
# Check process state with: Get-Content data\server.pid
# Check mini-client process state with: Get-Content data\mini_client.pid
```

## Environment Notes

- Current local app data lives under `data/`.
- The README documents Codex local logs as an external read-only source; do not
  inspect private local app data unless the user explicitly requests the
  concrete path and action.
