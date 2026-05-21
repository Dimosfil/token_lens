param(
  [int]$Rows = 4,
  [int]$RefreshSeconds = 5,
  [string]$BaseUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $root "start.ps1")

$refreshMs = [Math]::Max(1, $RefreshSeconds) * 1000
$pythonw = Get-Command "pythonw.exe" -ErrorAction SilentlyContinue
$python = if ($pythonw) { $pythonw.Source } else { (Get-Command "python.exe").Source }
$client = Join-Path $root "desktop\mini_client.py"
$arguments = @(
  $client,
  "--base-url", $BaseUrl,
  "--limit", $Rows,
  "--refresh-ms", $refreshMs
)

Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden
