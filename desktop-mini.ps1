param(
  [int]$Rows = 4,
  [int]$RefreshSeconds = 5,
  [string]$BaseUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$powershell = (Get-Command "powershell.exe").Source
& $powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "start.ps1")
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

$refreshMs = [Math]::Max(1, $RefreshSeconds) * 1000
$py = Get-Command "py.exe" -ErrorAction SilentlyContinue
$pythonw = Get-Command "pythonw.exe" -ErrorAction SilentlyContinue
$python = if ($py) { $py.Source } elseif ($pythonw) { $pythonw.Source } else { (Get-Command "python.exe").Source }
$client = Join-Path $root "desktop\mini_client.py"

function Quote-ProcessArgument([object]$Value) {
  $text = [string]$Value
  if ($text -notmatch '[\s"]') {
    return $text
  }
  return '"' + ($text -replace '"', '\"') + '"'
}

$arguments = @()
if ($py) {
  $arguments += "-3"
}
$arguments += @(
  $client,
  "--base-url", $BaseUrl,
  "--limit", $Rows,
  "--refresh-ms", $refreshMs
)
$argumentLine = ($arguments | ForEach-Object { Quote-ProcessArgument $_ }) -join " "

$proc = Start-Process -FilePath $python -ArgumentList $argumentLine -WorkingDirectory $root -WindowStyle Hidden -PassThru
Write-Host "Token Lens Mini started. PID: $($proc.Id)"
