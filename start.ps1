param(
  [switch]$Restart
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root "data\server.pid"

function Test-TokenLensServerProcess($Process) {
  if (-not $Process) {
    return $false
  }

  $processName = [string]$Process.ProcessName
  if ($processName -notlike "python*") {
    return $false
  }

  $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($Process.Id)" -ErrorAction SilentlyContinue
  $commandLine = if ($processInfo) { [string]$processInfo.CommandLine } else { "" }
  return $commandLine -like "*app.server*"
}

function Resolve-ProjectPython {
  $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
  if (Test-Path $uv) {
    $resolved = & $uv run python -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $resolved) {
      $resolvedLines = @($resolved)
      return [string]$resolvedLines[0]
    }
  }

  return (Get-Command "python.exe").Source
}

New-Item -ItemType Directory -Force -Path (Join-Path $root "data") | Out-Null

if (Test-Path $pidFile) {
  $existingPid = Get-Content $pidFile -ErrorAction SilentlyContinue
  $existingProcess = if ($existingPid) { Get-Process -Id $existingPid -ErrorAction SilentlyContinue } else { $null }
  if ($existingProcess) {
    if (-not (Test-TokenLensServerProcess $existingProcess)) {
      Write-Host "Ignoring stale Token Lens PID file. PID $existingPid belongs to $($existingProcess.ProcessName)."
      Remove-Item -LiteralPath $pidFile -Force
      $existingProcess = $null
    }
  }

  if ($existingProcess) {
    $appFiles = Get-ChildItem -Path (Join-Path $root "app") -Recurse -Filter "*.py"
    $appChanged = @($appFiles | Where-Object { $_.LastWriteTime -gt $existingProcess.StartTime }).Count -gt 0
    if (-not $Restart -and -not $appChanged) {
      Write-Host "Token Lens already running. PID: $existingPid"
      Write-Host "URL: http://127.0.0.1:8765"
      exit 0
    }

    Stop-Process -Id $existingPid
    [void]$existingProcess.WaitForExit(5000)
  }
}

$python = Resolve-ProjectPython
$args = @("-m", "app.server")
$proc = Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $root -WindowStyle Hidden -PassThru
Set-Content -Path $pidFile -Value $proc.Id -Encoding ASCII

Start-Sleep -Seconds 1
Write-Host "Token Lens started. PID: $($proc.Id)"
Write-Host "URL: http://127.0.0.1:8765"
