param(
  [switch]$Restart,
  [switch]$NoMini
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataDir = Join-Path $root "data"
$serverPidFile = Join-Path $dataDir "server.pid"
$miniPidFile = Join-Path $dataDir "mini_client.pid"
$launcherLog = Join-Path $dataDir "launcher.log"
$aiLoggerEnvFile = Join-Path $root "ai-logger-client.local.ps1"
$script:startedApps = New-Object System.Collections.Generic.List[object]

New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

function Write-Status([string]$Message) {
  Write-Host $Message
  $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ssK') [launcher_pid=$PID] $Message"
  [System.IO.File]::AppendAllText($launcherLog, "$line`r`n", [System.Text.UTF8Encoding]::new($false))
}

if (Test-Path -LiteralPath $aiLoggerEnvFile) {
  try {
    . $aiLoggerEnvFile
  }
  catch {
    Write-Status "Failed to load local ai_logger environment: $($_.Exception.Message)"
    throw
  }
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

function Get-TokenLensProcessRoots($Processes) {
  $processes = @($Processes)
  $processIds = @{}
  foreach ($process in $processes) {
    $processIds[[int]$process.Id] = $true
  }

  @($processes | Where-Object {
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue
    -not $processInfo -or -not $processIds.ContainsKey([int]$processInfo.ParentProcessId)
  })
}

function Resolve-ProjectPython {
  $codexPython = Join-Path $env:USERPROFILE ".codex\bin\python.exe"
  if (Test-Path -LiteralPath $codexPython) {
    return $codexPython
  }

  $pathPython = Get-Command "python.exe" -ErrorAction SilentlyContinue
  if (-not $pathPython -or -not (Test-Path -LiteralPath $pathPython.Source)) {
    throw "No usable python.exe was found in the trusted project or PATH locations."
  }

  return $pathPython.Source
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

function Get-TokenLensRuntimeSettings {
  $bindHost = "127.0.0.1"
  $bindPort = 8765
  $apiTimeoutSeconds = 60
  $miniTimeoutSeconds = 15
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
    if ($config.PSObject.Properties.Name -contains "launcher_api_timeout_seconds" -and $config.launcher_api_timeout_seconds) {
      $apiTimeoutSeconds = [int]$config.launcher_api_timeout_seconds
    }
    if ($config.PSObject.Properties.Name -contains "launcher_mini_timeout_seconds" -and $config.launcher_mini_timeout_seconds) {
      $miniTimeoutSeconds = [int]$config.launcher_mini_timeout_seconds
    }
  }

  if ($apiTimeoutSeconds -lt 1 -or $miniTimeoutSeconds -lt 1) {
    throw "Launcher timeout settings must be positive integers."
  }

  return [pscustomobject]@{
    Url = "http://$bindHost`:$bindPort"
    ApiTimeoutSeconds = $apiTimeoutSeconds
    MiniTimeoutSeconds = $miniTimeoutSeconds
  }
}

function Get-PidFileProcess([string]$PidFile) {
  if (-not (Test-Path -LiteralPath $PidFile)) {
    return $null
  }

  $rawPid = [string](Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  $existingPid = 0
  if (-not [int]::TryParse($rawPid.Trim(), [ref]$existingPid) -or $existingPid -le 0) {
    Write-Status "Ignoring invalid PID file: $PidFile"
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
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
    return $false
  }

  $liveProcess = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
  if (-not $liveProcess) {
    return $false
  }

  & taskkill.exe /PID $Process.Id /F /T 2>$null | Out-Null
  [void]$liveProcess.WaitForExit(5000)
  if (Get-Process -Id $Process.Id -ErrorAction SilentlyContinue) {
    Stop-Process -Id $Process.Id -Force -ErrorAction Stop
  }
  if (Get-Process -Id $Process.Id -ErrorAction SilentlyContinue) {
    throw "$Name did not stop. PID: $($Process.Id)"
  }
  Write-Status "$Name stopped. PID: $($Process.Id)"
  return $true
}

function Start-TokenLensApp(
  [string]$Name,
  [string]$PidFile,
  [string[]]$Markers,
  [string[]]$SourcePaths,
  [string[]]$Arguments,
  [string]$FilePath = "",
  [System.Diagnostics.ProcessWindowStyle]$WindowStyle,
  [string]$StandardOutputPath = "",
  [string]$StandardErrorPath = ""
) {
  $existingProcess = Get-PidFileProcess $PidFile
  $matchingProcesses = @(Find-TokenLensPythonProcesses $Markers)
  $rootProcesses = @(Get-TokenLensProcessRoots $matchingProcesses)
  $candidateIds = @($matchingProcesses | ForEach-Object { $_.Id }) -join ","
  $rootIds = @($rootProcesses | ForEach-Object { $_.Id }) -join ","
  $pidFileId = if ($existingProcess) { [string]$existingProcess.Id } else { "none" }
  Write-Status "$Name discovery: pid_file_process=$pidFileId matching_processes=$($matchingProcesses.Count) candidate_pids=$candidateIds root_processes=$($rootProcesses.Count) root_pids=$rootIds restart=$Restart"

  if ($existingProcess -and -not (Test-TokenLensPythonProcess $existingProcess $Markers)) {
    Write-Status "Ignoring stale $Name PID file. PID $($existingProcess.Id) belongs to $($existingProcess.ProcessName)."
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    $existingProcess = $null
  }

  if ($rootProcesses.Count -gt 1) {
    Write-Status "$Name has multiple independent process trees; replacing them with one clean tree."
    foreach ($process in $rootProcesses) {
      [void](Stop-TokenLensProcess $process $Name)
    }
    $existingProcess = $null
  }
  elseif ($Restart -and $rootProcesses.Count -eq 1) {
    [void](Stop-TokenLensProcess $rootProcesses[0] $Name)
    $existingProcess = $null
  }
  elseif (-not $existingProcess -and $rootProcesses.Count -eq 1) {
    $existingProcess = $rootProcesses[0]
    Set-Content -Path $PidFile -Value $existingProcess.Id -Encoding ASCII
    Write-Status "$Name adopted existing process tree root. PID: $($existingProcess.Id)"
  }

  if ($existingProcess) {
    $sourceChanged = Test-SourceChanged $existingProcess $SourcePaths
    if (-not $Restart -and -not $sourceChanged) {
      Write-Status "$Name already running. PID: $($existingProcess.Id)"
      return $existingProcess
    }

    $processToStop = if ($rootProcesses.Count -eq 1) { $rootProcesses[0] } else { $existingProcess }
    [void](Stop-TokenLensProcess $processToStop $Name)
  }

  $launchFilePath = if ([string]::IsNullOrWhiteSpace($FilePath)) { $script:python } else { $FilePath }
  $startArgs = @{
    FilePath = $launchFilePath
    ArgumentList = $Arguments
    WorkingDirectory = $root
    WindowStyle = $WindowStyle
    PassThru = $true
  }
  if (-not [string]::IsNullOrWhiteSpace($StandardOutputPath)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StandardOutputPath) | Out-Null
    $startArgs.RedirectStandardOutput = $StandardOutputPath
  }
  if (-not [string]::IsNullOrWhiteSpace($StandardErrorPath)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StandardErrorPath) | Out-Null
    $startArgs.RedirectStandardError = $StandardErrorPath
  }
  $proc = Start-Process @startArgs
  Set-Content -Path $PidFile -Value $proc.Id -Encoding ASCII
  $script:startedApps.Add([pscustomobject]@{
    Name = $Name
    ProcessId = [int]$proc.Id
    PidFile = $PidFile
    Markers = $Markers
  })
  Write-Status "$Name started. PID: $($proc.Id) file=$launchFilePath arguments=$($Arguments -join ' ')"
  return $proc
}

function Wait-TokenLensApi([string]$Url, [int]$TimeoutSeconds, [int]$ProcessId = 0) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    if ($ProcessId -gt 0 -and -not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
      return $null
    }
    try {
      $state = Invoke-RestMethod -Uri "$Url/api/state?include_raw=0" -TimeoutSec 5
      if ($state -and $state.version) {
        return $state
      }
    }
    catch {
      Start-Sleep -Milliseconds 500
    }
  } while ((Get-Date) -lt $deadline)

  return $null
}

function Write-FailureLogTail([string]$Name, [string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    return
  }

  $lines = @(Get-Content -LiteralPath $Path -Tail 20 -Encoding UTF8 -ErrorAction SilentlyContinue | Where-Object {
    -not [string]::IsNullOrWhiteSpace($_)
  })
  if ($lines.Count -eq 0) {
    return
  }

  Write-Status "$Name recent error output follows: $Path"
  foreach ($line in $lines) {
    Write-Host "  $line"
  }
}

function Undo-StartedApps {
  for ($index = $script:startedApps.Count - 1; $index -ge 0; $index--) {
    $entry = $script:startedApps[$index]
    $process = Get-Process -Id $entry.ProcessId -ErrorAction SilentlyContinue
    if ($process -and (Test-TokenLensPythonProcess $process $entry.Markers)) {
      [void](Stop-TokenLensProcess $process "$($entry.Name) rollback")
    }

    if (Test-Path -LiteralPath $entry.PidFile) {
      $rawPid = [string](Get-Content -LiteralPath $entry.PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
      if ($rawPid.Trim() -eq [string]$entry.ProcessId) {
        Remove-Item -LiteralPath $entry.PidFile -Force -ErrorAction SilentlyContinue
      }
    }
  }
}

function Assert-SingleTokenLensTree([string]$Name, [string[]]$Markers) {
  $matches = @(Find-TokenLensPythonProcesses $Markers)
  $roots = @(Get-TokenLensProcessRoots $matches)
  if ($roots.Count -ne 1) {
    $rootIds = @($roots | ForEach-Object { $_.Id }) -join ","
    throw "$Name verification expected one process tree but found $($roots.Count). Root PIDs: $rootIds"
  }
  return $roots[0]
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

try {
  if ((Test-Path -LiteralPath $launcherLog) -and (Get-Item -LiteralPath $launcherLog).Length -gt 1MB) {
    Move-Item -LiteralPath $launcherLog -Destination "$launcherLog.1" -Force
  }

  $runtimeSettings = Get-TokenLensRuntimeSettings
  $url = $runtimeSettings.Url
  $script:python = Resolve-ProjectPython
  $script:pythonw = Resolve-ProjectPythonw $script:python
  Write-Status "startup requested root=$root url=$url restart=$Restart no_mini=$NoMini python=$script:python pythonw=$script:pythonw api_timeout_seconds=$($runtimeSettings.ApiTimeoutSeconds) mini_timeout_seconds=$($runtimeSettings.MiniTimeoutSeconds)"

  $serverMarkers = @("run_server.py")
  $server = Start-TokenLensApp `
    -Name "Token Lens server" `
    -PidFile $serverPidFile `
    -Markers $serverMarkers `
    -SourcePaths @((Join-Path $root "app"), (Join-Path $root "run_server.py")) `
    -Arguments @("run_server.py") `
    -WindowStyle Hidden `
    -StandardOutputPath (Join-Path $dataDir "server.out.log") `
    -StandardErrorPath (Join-Path $dataDir "server.err.log")

  $state = Wait-TokenLensApi `
    -Url $url `
    -TimeoutSeconds $runtimeSettings.ApiTimeoutSeconds `
    -ProcessId $server.Id
  if (-not $state) {
    throw "Token Lens API did not return a valid lightweight state at $url/api/state?include_raw=0."
  }

  $serverRoot = Assert-SingleTokenLensTree -Name "Token Lens server" -Markers $serverMarkers
  Write-Status "Token Lens API ready. URL: $url root_pid=$($serverRoot.Id)"

  if (-not $NoMini) {
    $miniMarkers = @("desktop\mini_client.py", "desktop/mini_client.py")
    $mini = Start-TokenLensApp `
      -Name "Token Lens mini" `
      -PidFile $miniPidFile `
      -Markers $miniMarkers `
      -SourcePaths @((Join-Path $root "desktop\mini_client.py")) `
      -Arguments @("desktop\mini_client.py", "--base-url", $url) `
      -FilePath $script:pythonw `
      -WindowStyle Normal `
      -StandardOutputPath (Join-Path $dataDir "mini-client.out.log") `
      -StandardErrorPath (Join-Path $dataDir "mini-client.err.log")

    $miniWindowProcess = Wait-TokenLensWindowProcess `
      -ProcessId $mini.Id `
      -Markers $miniMarkers `
      -TimeoutSeconds $runtimeSettings.MiniTimeoutSeconds
    if (-not $miniWindowProcess) {
      if (Get-Process -Id $mini.Id -ErrorAction SilentlyContinue) {
        throw "Token Lens mini is running but no window was verified within $($runtimeSettings.MiniTimeoutSeconds) seconds. PID: $($mini.Id)"
      }
      throw "Token Lens mini exited during startup."
    }

    Set-Content -Path $miniPidFile -Value $miniWindowProcess.Id -Encoding ASCII
    if ($miniWindowProcess.Id -ne $mini.Id -and @($script:startedApps | Where-Object { $_.ProcessId -eq $mini.Id }).Count -gt 0) {
      $script:startedApps.Add([pscustomobject]@{
        Name = "Token Lens mini"
        ProcessId = [int]$miniWindowProcess.Id
        PidFile = $miniPidFile
        Markers = $miniMarkers
      })
    }
    $miniRoot = Assert-SingleTokenLensTree -Name "Token Lens mini" -Markers $miniMarkers
    Write-Status "Token Lens mini window verified. PID: $($miniWindowProcess.Id) root_pid=$($miniRoot.Id)"
  }

  $finalState = Wait-TokenLensApi -Url $url -TimeoutSeconds 10 -ProcessId $server.Id
  if (-not $finalState) {
    throw "Token Lens API stopped responding during final app-set verification."
  }
  Write-Status "Token Lens app set ready. server_root_pid=$($serverRoot.Id) mini_required=$(-not $NoMini)"
}
catch {
  Write-Status "Token Lens app set startup failed: $($_.Exception.Message)"
  Write-FailureLogTail -Name "Server" -Path (Join-Path $dataDir "server.err.log")
  if (-not $NoMini) {
    Write-FailureLogTail -Name "Mini" -Path (Join-Path $dataDir "mini-client.err.log")
  }
  Undo-StartedApps
  exit 1
}
