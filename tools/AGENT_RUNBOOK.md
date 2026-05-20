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
Token Lens starts on http://127.0.0.1:8765 and writes data/server.pid.
```

## Logs

```powershell
# No dedicated log file is currently defined.
# Check process state with: Get-Content data\server.pid
```

## Environment Notes

- Current local app data lives under `data/`.
- The README documents Codex local logs as an external read-only source; do not
  inspect private local app data unless the user explicitly requests the
  concrete path and action.
