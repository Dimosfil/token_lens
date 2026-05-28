param(
  [int]$Rows = 4,
  [int]$RefreshSeconds = 5,
  [string]$BaseUrl = "http://127.0.0.1:8765",
  [int]$SignalThreshold = 100000,
  [ValidateSet("Simple", "Asterisk", "Exclamation", "Hand", "Question")]
  [string]$Signal = "Exclamation",
  [switch]$NoSignal
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$powershell = (Get-Command "powershell.exe").Source
& $powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "start.ps1")
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

$refreshMs = [Math]::Max(1, $RefreshSeconds) * 1000
$client = Join-Path $root "desktop\mini_client.py"

function Resolve-ProjectDesktopPython {
  $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
  if (Test-Path $uv) {
    $resolved = & $uv run python -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $resolved) {
      $resolvedLines = @($resolved)
      $python = [string]$resolvedLines[0]
      $pythonw = Join-Path (Split-Path -Parent $python) "pythonw.exe"
      if (Test-Path $pythonw) {
        return $pythonw
      }
      return $python
    }
  }

  $pythonwCommand = Get-Command "pythonw.exe" -ErrorAction SilentlyContinue
  if ($pythonwCommand) {
    return $pythonwCommand.Source
  }

  return (Get-Command "python.exe").Source
}

function Quote-ProcessArgument([object]$Value) {
  $text = [string]$Value
  if ($text -notmatch '[\s"]') {
    return $text
  }
  return '"' + ($text -replace '"', '\"') + '"'
}

$arguments = @()
$arguments += @(
  $client,
  "--base-url", $BaseUrl,
  "--limit", $Rows,
  "--refresh-ms", $refreshMs,
  "--signal-threshold", $SignalThreshold,
  "--signal", $Signal
)
if ($NoSignal) {
  $arguments += "--no-signal-enabled"
}
$argumentLine = ($arguments | ForEach-Object { Quote-ProcessArgument $_ }) -join " "

$python = Resolve-ProjectDesktopPython
$proc = Start-Process -FilePath $python -ArgumentList $argumentLine -WorkingDirectory $root -WindowStyle Hidden -PassThru
Write-Host "Token Lens Mini started. PID: $($proc.Id)"
