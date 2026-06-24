param(
  [string]$CodexLogsDb = "",
  [string]$CodexSessionIndex = "",
  [string]$OpenCodeDb = "",
  [string]$OpenCodeTokensJsonl = "",
  [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Read-OptionalPath {
  param(
    [string]$Prompt,
    [string]$CurrentValue,
    [string]$SuggestedValue,
    [switch]$Required
  )

  if ($NonInteractive) {
    return $CurrentValue
  }

  $suffix = ""
  if ($CurrentValue) {
    $suffix = " [$CurrentValue]"
  } elseif ($SuggestedValue) {
    $suffix = " [$SuggestedValue]"
  }

  while ($true) {
    $value = Read-Host "$Prompt$suffix"
    if ([string]::IsNullOrWhiteSpace($value)) {
      if ($CurrentValue) { return $CurrentValue }
      if ($SuggestedValue) { return $SuggestedValue }
      if (-not $Required) { return "" }
    } else {
      return $value.Trim()
    }
  }
}

function Test-ConfiguredFile {
  param(
    [string]$Label,
    [string]$PathValue,
    [switch]$Required
  )

  if ([string]::IsNullOrWhiteSpace($PathValue)) {
    if ($Required) {
      Write-Warning "$Label is not configured."
      return $false
    }
    return $true
  }

  $expanded = [Environment]::ExpandEnvironmentVariables($PathValue)
  if (-not (Test-Path -LiteralPath $expanded -PathType Leaf)) {
    Write-Warning "$Label was saved but does not point to a readable file: $PathValue"
    return (-not $Required)
  }
  return $true
}

function Test-ConfiguredPathSet {
  param(
    [string]$Label,
    [string]$PathValue,
    [switch]$Required
  )

  if ([string]::IsNullOrWhiteSpace($PathValue)) {
    if ($Required) {
      Write-Warning "$Label is not configured."
      return $false
    }
    return $true
  }

  $expanded = [Environment]::ExpandEnvironmentVariables($PathValue)
  if (Test-Path -LiteralPath $expanded -PathType Leaf) {
    return $true
  }
  if (Test-Path -LiteralPath $expanded -PathType Container) {
    return $true
  }

  $matches = @(Get-ChildItem -Path $expanded -File -ErrorAction SilentlyContinue)
  if ($matches.Count -gt 0) {
    return $true
  }

  Write-Warning "$Label was saved but does not point to a readable file, folder, or glob: $PathValue"
  return (-not $Required)
}

function Read-JsonObject {
  param([string]$Path)

  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    return [ordered]@{}
  }
  $content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  if ([string]::IsNullOrWhiteSpace($content)) {
    return [ordered]@{}
  }
  $object = $content | ConvertFrom-Json
  $result = [ordered]@{}
  foreach ($property in $object.PSObject.Properties) {
    $result[$property.Name] = $property.Value
  }
  return $result
}

function Config-String {
  param([System.Collections.IDictionary]$Config, [string]$Key)
  if ($Config.Contains($Key) -and $null -ne $Config[$Key]) {
    return [string]$Config[$Key]
  }
  return ""
}

function Get-CodexRoots {
  $roots = New-Object System.Collections.Generic.List[string]
  foreach ($value in @($env:CODEX_HOME, $env:CODEX_CONFIG_HOME)) {
    if (-not [string]::IsNullOrWhiteSpace($value)) {
      $roots.Add($value)
    }
  }
  if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
    $roots.Add((Join-Path $env:USERPROFILE ".codex"))
  }
  if (-not [string]::IsNullOrWhiteSpace($env:HOME)) {
    $roots.Add((Join-Path $env:HOME ".codex"))
  }

  $seen = @{}
  $result = @()
  foreach ($rootValue in $roots) {
    $key = [string]$rootValue
    if (-not $seen.ContainsKey($key)) {
      $seen[$key] = $true
      $result += $rootValue
    }
  }
  return $result
}

function Get-UserHomeRoots {
  $roots = New-Object System.Collections.Generic.List[string]
  foreach ($value in @($env:USERPROFILE, $env:HOME)) {
    if (-not [string]::IsNullOrWhiteSpace($value)) {
      $roots.Add($value)
    }
  }

  $seen = @{}
  $result = @()
  foreach ($rootValue in $roots) {
    $key = [string]$rootValue
    if (-not $seen.ContainsKey($key)) {
      $seen[$key] = $true
      $result += $rootValue
    }
  }
  return $result
}

function Find-FirstExistingFile {
  param([string[]]$Paths)
  foreach ($pathValue in $Paths) {
    if (Test-Path -LiteralPath $pathValue -PathType Leaf) {
      return $pathValue
    }
  }
  return ""
}

function Find-FirstExistingPath {
  param([string[]]$Paths)
  foreach ($pathValue in $Paths) {
    if ((Test-Path -LiteralPath $pathValue -PathType Leaf) -or
        (Test-Path -LiteralPath $pathValue -PathType Container)) {
      return $pathValue
    }
  }
  return ""
}

function Find-CodexLogsDb {
  $roots = Get-CodexRoots
  $paths = @()
  foreach ($codexRoot in $roots) {
    $paths += (Join-Path $codexRoot "sqlite\logs_2.sqlite")
  }
  foreach ($codexRoot in $roots) {
    $paths += (Join-Path $codexRoot "logs_2.sqlite")
  }
  return Find-FirstExistingFile $paths
}

function Find-CodexSessionIndex {
  $roots = Get-CodexRoots
  $paths = @()
  foreach ($codexRoot in $roots) {
    $paths += (Join-Path $codexRoot "sessions")
  }
  foreach ($codexRoot in $roots) {
    $paths += (Join-Path $codexRoot "session_index.jsonl")
  }
  return Find-FirstExistingPath $paths
}

function Find-OpenCodeDb {
  $paths = @()
  if (-not [string]::IsNullOrWhiteSpace($env:XDG_DATA_HOME)) {
    $paths += (Join-Path $env:XDG_DATA_HOME "opencode\opencode.db")
  }
  if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    $paths += (Join-Path $env:LOCALAPPDATA "opencode\opencode.db")
  }
  foreach ($homeRoot in (Get-UserHomeRoots)) {
    $paths += (Join-Path $homeRoot ".local\share\opencode\opencode.db")
    $paths += (Join-Path $homeRoot "AppData\Local\opencode\opencode.db")
  }
  return Find-FirstExistingFile $paths
}

function Find-OpenCodeTokensJsonl {
  $paths = @()
  if (-not [string]::IsNullOrWhiteSpace($env:XDG_CONFIG_HOME)) {
    $paths += (Join-Path $env:XDG_CONFIG_HOME "opencode\logs\token-tracker\tokens.jsonl")
  }
  if (-not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
    $paths += (Join-Path $env:APPDATA "opencode\logs\token-tracker\tokens.jsonl")
  }
  foreach ($homeRoot in (Get-UserHomeRoots)) {
    $paths += (Join-Path $homeRoot ".config\opencode\logs\token-tracker\tokens.jsonl")
    $paths += (Join-Path $homeRoot "AppData\Roaming\opencode\logs\token-tracker\tokens.jsonl")
  }
  return Find-FirstExistingFile $paths
}

$root = Resolve-ProjectRoot
$localPath = Join-Path $root "config.local.json"
$config = Read-JsonObject $localPath

$suggestedCodexLogs = Find-CodexLogsDb
if (-not $suggestedCodexLogs) {
  $suggestedCodexLogs = Join-Path $env:USERPROFILE ".codex\sqlite\logs_2.sqlite"
}
$suggestedSessionIndex = Find-CodexSessionIndex
if (-not $suggestedSessionIndex) {
  $suggestedSessionIndex = Join-Path $env:USERPROFILE ".codex\sessions"
}
$suggestedOpenCodeDb = Find-OpenCodeDb
$suggestedOpenCodeTokensJsonl = Find-OpenCodeTokensJsonl

if (-not $CodexLogsDb) {
  $CodexLogsDb = Read-OptionalPath `
    -Prompt "Codex logs SQLite path" `
    -CurrentValue (Config-String $config "codex_logs_db") `
    -SuggestedValue $suggestedCodexLogs `
    -Required
}

if (-not $CodexSessionIndex) {
  $CodexSessionIndex = Read-OptionalPath `
    -Prompt "Codex session index file, folder, or glob path" `
    -CurrentValue (Config-String $config "codex_session_index") `
    -SuggestedValue $suggestedSessionIndex
}

if (-not $OpenCodeDb) {
  $OpenCodeDb = Read-OptionalPath `
    -Prompt "OpenCode SQLite path (optional)" `
    -CurrentValue (Config-String $config "opencode_db") `
    -SuggestedValue $suggestedOpenCodeDb
}

if (-not $OpenCodeTokensJsonl) {
  $OpenCodeTokensJsonl = Read-OptionalPath `
    -Prompt "OpenCode token tracker JSONL path (optional)" `
    -CurrentValue (Config-String $config "opencode_tokens_jsonl") `
    -SuggestedValue $suggestedOpenCodeTokensJsonl
}

$config["codex_logs_db"] = $CodexLogsDb
$config["codex_session_index"] = $CodexSessionIndex
$config["opencode_db"] = $OpenCodeDb
$config["opencode_tokens_jsonl"] = $OpenCodeTokensJsonl
if (-not $config.Contains("auto_discover_codex_sources")) { $config["auto_discover_codex_sources"] = $true }
if (-not $config.Contains("analytics_db")) { $config["analytics_db"] = "data\analytics.sqlite" }
if (-not $config.Contains("host")) { $config["host"] = "127.0.0.1" }
if (-not $config.Contains("port")) { $config["port"] = 8765 }
if (-not $config.Contains("auto_import_seconds")) { $config["auto_import_seconds"] = 30 }

$json = $config | ConvertTo-Json -Depth 20
Set-Content -LiteralPath $localPath -Value ($json + "`n") -Encoding UTF8

$codexOk = Test-ConfiguredFile -Label "codex_logs_db" -PathValue $CodexLogsDb -Required
$sessionOk = Test-ConfiguredPathSet -Label "codex_session_index" -PathValue $CodexSessionIndex
$opencodeDbOk = Test-ConfiguredFile -Label "opencode_db" -PathValue $OpenCodeDb
$opencodeJsonlOk = Test-ConfiguredFile -Label "opencode_tokens_jsonl" -PathValue $OpenCodeTokensJsonl

Write-Host "Wrote local runtime config: $localPath"
if ($codexOk -and $sessionOk -and $opencodeDbOk -and $opencodeJsonlOk) {
  Write-Host "Configured source paths are readable or optional."
} else {
  Write-Warning "One or more configured paths need attention before imports will include that source."
}
