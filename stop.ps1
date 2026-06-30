$ErrorActionPreference = "SilentlyContinue"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root "data\server.pid"

if (-not (Test-Path $pidFile)) {
  Write-Host "Token Lens is not running."
  exit 0
}

$pidValue = Get-Content $pidFile
$proc = Get-Process -Id $pidValue
if ($proc) {
  & taskkill.exe /PID $pidValue /F /T | Out-Null
  if (Get-Process -Id $pidValue -ErrorAction SilentlyContinue) {
    Stop-Process -Id $pidValue -Force
  }
  Write-Host "Stopped Token Lens. PID: $pidValue"
} else {
  Write-Host "No running process for PID: $pidValue"
}

Remove-Item $pidFile -Force
