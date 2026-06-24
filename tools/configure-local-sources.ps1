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

$root = Resolve-ProjectRoot
$localPath = Join-Path $root "config.local.json"
$config = Read-JsonObject $localPath

$suggestedCodexLogs = Join-Path $env:USERPROFILE ".codex\logs_2.sqlite"
$suggestedSessionIndex = Join-Path $env:USERPROFILE ".codex\session_index.jsonl"

if (-not $CodexLogsDb) {
  $CodexLogsDb = Read-OptionalPath `
    -Prompt "Codex logs SQLite path" `
    -CurrentValue (Config-String $config "codex_logs_db") `
    -SuggestedValue $suggestedCodexLogs `
    -Required
}

if (-not $CodexSessionIndex) {
  $CodexSessionIndex = Read-OptionalPath `
    -Prompt "Codex session index JSONL path" `
    -CurrentValue (Config-String $config "codex_session_index") `
    -SuggestedValue $suggestedSessionIndex
}

if (-not $OpenCodeDb) {
  $OpenCodeDb = Read-OptionalPath `
    -Prompt "OpenCode SQLite path (optional)" `
    -CurrentValue (Config-String $config "opencode_db") `
    -SuggestedValue ""
}

if (-not $OpenCodeTokensJsonl) {
  $OpenCodeTokensJsonl = Read-OptionalPath `
    -Prompt "OpenCode token tracker JSONL path (optional)" `
    -CurrentValue (Config-String $config "opencode_tokens_jsonl") `
    -SuggestedValue ""
}

$config["codex_logs_db"] = $CodexLogsDb
$config["codex_session_index"] = $CodexSessionIndex
$config["opencode_db"] = $OpenCodeDb
$config["opencode_tokens_jsonl"] = $OpenCodeTokensJsonl
if (-not $config.Contains("analytics_db")) { $config["analytics_db"] = "data\analytics.sqlite" }
if (-not $config.Contains("host")) { $config["host"] = "127.0.0.1" }
if (-not $config.Contains("port")) { $config["port"] = 8765 }
if (-not $config.Contains("auto_import_seconds")) { $config["auto_import_seconds"] = 30 }

$json = $config | ConvertTo-Json -Depth 20
Set-Content -LiteralPath $localPath -Value ($json + "`n") -Encoding UTF8

$codexOk = Test-ConfiguredFile -Label "codex_logs_db" -PathValue $CodexLogsDb -Required
$sessionOk = Test-ConfiguredFile -Label "codex_session_index" -PathValue $CodexSessionIndex
$opencodeDbOk = Test-ConfiguredFile -Label "opencode_db" -PathValue $OpenCodeDb
$opencodeJsonlOk = Test-ConfiguredFile -Label "opencode_tokens_jsonl" -PathValue $OpenCodeTokensJsonl

Write-Host "Wrote local runtime config: $localPath"
if ($codexOk -and $sessionOk -and $opencodeDbOk -and $opencodeJsonlOk) {
  Write-Host "Configured source paths are readable or optional."
} else {
  Write-Warning "One or more configured paths need attention before imports will include that source."
}
