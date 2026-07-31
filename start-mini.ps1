param(
  [switch]$Restart
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataDir = Join-Path $root "data"
$miniPidFile = Join-Path $dataDir "mini_client.pid"
$aiLoggerEnvFile = Join-Path $root "ai-logger-client.local.ps1"

if (Test-Path -LiteralPath $aiLoggerEnvFile) {
  . $aiLoggerEnvFile
}

function Get-ProcessCommandLine($Process) {
  if (-not $Process) {
    return ""
  }

  $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($Process.Id)" -ErrorAction SilentlyContinue
  if ($processInfo) {
    return [string]$processInfo.CommandLine
  }
  return ""
}

function Test-TokenLensMiniProcess($Process) {
  if (-not $Process) {
    return $false
  }

  $processName = [string]$Process.ProcessName
  if ($processName -notlike "python*") {
    return $false
  }

  $commandLine = Get-ProcessCommandLine $Process
  return $commandLine -like "*desktop\mini_client.py*" -or $commandLine -like "*desktop/mini_client.py*"
}

function Find-TokenLensMiniProcesses {
  @(Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
    Test-TokenLensMiniProcess $_
  })
}

function Select-TokenLensMiniProcess($Processes) {
  foreach ($process in $Processes) {
    $process.Refresh()
    if ($process.MainWindowHandle -ne 0) {
      return $process
    }
  }

  return @($Processes | Select-Object -First 1)[0]
}

function Get-PidFileProcess([string]$PidFile) {
  if (-not (Test-Path -LiteralPath $PidFile)) {
    return $null
  }

  $existingPid = Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $existingPid) {
    return $null
  }

  return Get-Process -Id $existingPid -ErrorAction SilentlyContinue
}

function Resolve-ProjectPython {
  $codexPython = Join-Path $env:USERPROFILE ".codex\bin\python.exe"
  if (Test-Path -LiteralPath $codexPython) {
    return $codexPython
  }

  return (Get-Command "python.exe").Source
}

function Resolve-ProjectPythonw([string]$PythonPath) {
  $nearPythonw = Join-Path (Split-Path -Parent $PythonPath) "pythonw.exe"
  if (Test-Path -LiteralPath $nearPythonw) {
    return $nearPythonw
  }

  $codexPythonw = Join-Path $env:USERPROFILE ".codex\bin\pythonw.exe"
  if (Test-Path -LiteralPath $codexPythonw) {
    return $codexPythonw
  }

  $pathPythonw = Get-Command "pythonw.exe" -ErrorAction SilentlyContinue
  if ($pathPythonw) {
    return $pathPythonw.Source
  }

  return $PythonPath
}

function Get-TokenLensUrl {
  $bindHost = "127.0.0.1"
  $bindPort = 8765
  foreach ($path in @((Join-Path $root "config.json"), (Join-Path $root "config.local.json"))) {
    if (-not (Test-Path -LiteralPath $path)) {
      continue
    }

    $config = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    if ($config.PSObject.Properties.Name -contains "host" -and $config.host) {
      $bindHost = [string]$config.host
    }
    if ($config.PSObject.Properties.Name -contains "port" -and $config.port) {
      $bindPort = [int]$config.port
    }
  }

  return "http://$bindHost`:$bindPort"
}

function Stop-TokenLensMini($Process) {
  if (-not $Process) {
    return
  }

  $liveProcess = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
  if (-not $liveProcess) {
    return
  }

  & taskkill.exe /PID $Process.Id /F /T 2>$null | Out-Null
  [void]$Process.WaitForExit(5000)
  if (Get-Process -Id $Process.Id -ErrorAction SilentlyContinue) {
    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
  }
  Write-Host "Token Lens mini stopped. PID: $($Process.Id)"
}

function Get-ChildProcessIds([int]$ProcessId) {
  $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue)
  $ids = @()
  foreach ($child in $children) {
    $childId = [int]$child.ProcessId
    $ids += $childId
    $ids += @(Get-ChildProcessIds $childId)
  }
  return $ids
}

function Wait-TokenLensMiniWindow([int]$ProcessId, [int]$TimeoutSeconds = 10) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    $candidateIds = @($ProcessId) + @(Get-ChildProcessIds $ProcessId)
    foreach ($candidateId in ($candidateIds | Select-Object -Unique)) {
      $process = Get-Process -Id $candidateId -ErrorAction SilentlyContinue
      if (-not $process) {
        continue
      }
      if (-not (Test-TokenLensMiniProcess $process)) {
        continue
      }

      $process.Refresh()
      if ($process.MainWindowHandle -ne 0) {
        return $process
      }
    }

    Start-Sleep -Milliseconds 300
  } while ((Get-Date) -lt $deadline)

  return $null
}

New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

$existingProcess = Get-PidFileProcess $miniPidFile
$matchingProcesses = @(Find-TokenLensMiniProcesses)

if ($Restart -and $matchingProcesses.Count -gt 0) {
  foreach ($process in $matchingProcesses) {
    Stop-TokenLensMini $process
  }
  $existingProcess = $null
}
elseif (-not $existingProcess -and $matchingProcesses.Count -eq 1) {
  $existingProcess = $matchingProcesses[0]
  Set-Content -Path $miniPidFile -Value $existingProcess.Id -Encoding ASCII
}

if ($existingProcess -and -not (Test-TokenLensMiniProcess $existingProcess)) {
  Write-Host "Ignoring stale Token Lens mini PID file. PID $($existingProcess.Id) belongs to $($existingProcess.ProcessName)."
  Remove-Item -LiteralPath $miniPidFile -Force
  $existingProcess = $null
}

if (-not $existingProcess -and -not $Restart -and $matchingProcesses.Count -gt 0) {
  $existingProcess = Select-TokenLensMiniProcess $matchingProcesses
  Set-Content -Path $miniPidFile -Value $existingProcess.Id -Encoding ASCII
}

if ($existingProcess -and -not $Restart) {
  Write-Host "Token Lens mini already running. PID: $($existingProcess.Id)"
  exit 0
}

$python = Resolve-ProjectPython
$pythonw = Resolve-ProjectPythonw $python
$url = Get-TokenLensUrl

$proc = Start-Process `
  -FilePath $pythonw `
  -ArgumentList @("desktop\mini_client.py", "--base-url", $url) `
  -WorkingDirectory $root `
  -WindowStyle Normal `
  -RedirectStandardOutput (Join-Path $dataDir "mini-client.out.log") `
  -RedirectStandardError (Join-Path $dataDir "mini-client.err.log") `
  -PassThru

Set-Content -Path $miniPidFile -Value $proc.Id -Encoding ASCII
Write-Host "Token Lens mini started. PID: $($proc.Id)"

$miniWindowProcess = Wait-TokenLensMiniWindow -ProcessId $proc.Id
if ($miniWindowProcess) {
  Set-Content -Path $miniPidFile -Value $miniWindowProcess.Id -Encoding ASCII
  Write-Host "Token Lens mini window verified. PID: $($miniWindowProcess.Id)"
}
elseif (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue) {
  Write-Host "Token Lens mini process is running, but no window handle was verified. PID: $($proc.Id)"
}
else {
  Write-Host "Token Lens mini exited during startup."
  exit 1
}
