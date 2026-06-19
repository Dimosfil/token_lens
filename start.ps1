param(
  [switch]$Restart,
  [switch]$NoMini
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataDir = Join-Path $root "data"
$serverPidFile = Join-Path $dataDir "server.pid"
$miniPidFile = Join-Path $dataDir "mini_client.pid"

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

function Test-TokenLensPythonProcess($Process, [string[]]$Markers) {
  if (-not $Process) {
    return $false
  }

  $processName = [string]$Process.ProcessName
  if ($processName -notlike "python*") {
    return $false
  }

  $commandLine = Get-ProcessCommandLine $Process
  foreach ($marker in $Markers) {
    if ($commandLine -like "*$marker*") {
      return $true
    }
  }
  return $false
}

function Find-TokenLensPythonProcesses([string[]]$Markers) {
  @(Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
    Test-TokenLensPythonProcess $_ $Markers
  })
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

function Test-SourceChanged($Process, [string[]]$Paths) {
  if (-not $Process) {
    return $false
  }

  foreach ($path in $Paths) {
    if (-not (Test-Path -LiteralPath $path)) {
      continue
    }

    $item = Get-Item -LiteralPath $path
    $files = if ($item.PSIsContainer) {
      Get-ChildItem -LiteralPath $path -Recurse -File
    }
    else {
      @($item)
    }

    if (@($files | Where-Object { $_.LastWriteTime -gt $Process.StartTime }).Count -gt 0) {
      return $true
    }
  }

  return $false
}

function Stop-TokenLensProcess($Process, [string]$Name) {
  if (-not $Process) {
    return
  }

  Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
  [void]$Process.WaitForExit(5000)
  if (Get-Process -Id $Process.Id -ErrorAction SilentlyContinue) {
    & taskkill.exe /PID $Process.Id /F /T | Out-Null
  }
  Write-Host "$Name stopped. PID: $($Process.Id)"
}

function Start-TokenLensApp(
  [string]$Name,
  [string]$PidFile,
  [string[]]$Markers,
  [string[]]$SourcePaths,
  [string[]]$Arguments,
  [string]$FilePath = "",
  [System.Diagnostics.ProcessWindowStyle]$WindowStyle
) {
  $existingProcess = Get-PidFileProcess $PidFile
  $matchingProcesses = @(Find-TokenLensPythonProcesses $Markers)

  if ($Restart -and $matchingProcesses.Count -gt 0) {
    foreach ($process in $matchingProcesses) {
      Stop-TokenLensProcess $process $Name
    }
    $existingProcess = $null
  }
  elseif (-not $existingProcess -and $matchingProcesses.Count -eq 1) {
    $existingProcess = $matchingProcesses[0]
    Set-Content -Path $PidFile -Value $existingProcess.Id -Encoding ASCII
  }

  if ($existingProcess -and -not (Test-TokenLensPythonProcess $existingProcess $Markers)) {
    Write-Host "Ignoring stale $Name PID file. PID $($existingProcess.Id) belongs to $($existingProcess.ProcessName)."
    Remove-Item -LiteralPath $PidFile -Force
    $existingProcess = $null
  }

  if ($existingProcess) {
    $sourceChanged = Test-SourceChanged $existingProcess $SourcePaths
    if (-not $Restart -and -not $sourceChanged) {
      Write-Host "$Name already running. PID: $($existingProcess.Id)"
      return $existingProcess
    }

    Stop-TokenLensProcess $existingProcess $Name
  }

  $launchFilePath = if ([string]::IsNullOrWhiteSpace($FilePath)) { $script:python } else { $FilePath }
  $proc = Start-Process -FilePath $launchFilePath -ArgumentList $Arguments -WorkingDirectory $root -WindowStyle $WindowStyle -PassThru
  Set-Content -Path $PidFile -Value $proc.Id -Encoding ASCII
  Write-Host "$Name started. PID: $($proc.Id)"
  return $proc
}

function Wait-TokenLensApi([string]$Url, [int]$TimeoutSeconds = 20) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    try {
      return Invoke-RestMethod -Uri "$Url/api/state" -TimeoutSec 2
    }
    catch {
      Start-Sleep -Milliseconds 500
    }
  } while ((Get-Date) -lt $deadline)

  return $null
}

function Wait-ProcessWindow([int]$ProcessId, [int]$TimeoutSeconds = 10) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $process) {
      return $false
    }
    $process.Refresh()
    if ($process.MainWindowHandle -ne 0) {
      return $true
    }
    Start-Sleep -Milliseconds 300
  } while ((Get-Date) -lt $deadline)

  return $false
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

function Wait-TokenLensWindowProcess([int]$ProcessId, [string[]]$Markers, [int]$TimeoutSeconds = 10) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    $candidateIds = @($ProcessId) + @(Get-ChildProcessIds $ProcessId)
    foreach ($candidateId in ($candidateIds | Select-Object -Unique)) {
      $process = Get-Process -Id $candidateId -ErrorAction SilentlyContinue
      if (-not $process) {
        continue
      }
      if (-not (Test-TokenLensPythonProcess $process $Markers)) {
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
$url = Get-TokenLensUrl
$script:python = Resolve-ProjectPython
$script:pythonw = Resolve-ProjectPythonw $script:python

$server = Start-TokenLensApp `
  -Name "Token Lens server" `
  -PidFile $serverPidFile `
  -Markers @("run_server.py") `
  -SourcePaths @((Join-Path $root "app"), (Join-Path $root "run_server.py")) `
  -Arguments @("run_server.py") `
  -WindowStyle Hidden

$state = Wait-TokenLensApi $url
if (-not $state) {
  Write-Host "Token Lens API did not respond at $url/api/state."
  exit 1
}

Write-Host "Token Lens API ready. URL: $url"

if (-not $NoMini) {
  $miniMarkers = @("desktop\mini_client.py", "desktop/mini_client.py")
  $mini = Start-TokenLensApp `
    -Name "Token Lens mini" `
    -PidFile $miniPidFile `
    -Markers $miniMarkers `
    -SourcePaths @((Join-Path $root "desktop\mini_client.py")) `
    -Arguments @("desktop\mini_client.py", "--base-url", $url) `
    -FilePath $script:pythonw `
    -WindowStyle Normal

  $miniWindowProcess = Wait-TokenLensWindowProcess -ProcessId $mini.Id -Markers $miniMarkers
  if ($miniWindowProcess) {
    Set-Content -Path $miniPidFile -Value $miniWindowProcess.Id -Encoding ASCII
    Write-Host "Token Lens mini window verified. PID: $($miniWindowProcess.Id)"
  }
  elseif (Get-Process -Id $mini.Id -ErrorAction SilentlyContinue) {
    Write-Host "Token Lens mini process is running, but no window handle was verified. PID: $($mini.Id)"
  }
  else {
    Write-Host "Token Lens mini exited during startup."
    exit 1
  }
}

Write-Host "Token Lens app set ready."
