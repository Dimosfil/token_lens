# Agent Runbook

Every command should be copy-pasteable from the project root.

## Install

```powershell
# Uses the system/local Python environment. No dependency manifest is currently present.
```

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
