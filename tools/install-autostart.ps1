param(
  [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "Token Lens.lnk"

if ($Uninstall) {
  if (Test-Path $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath
    Write-Host "Token Lens autostart removed: $shortcutPath"
  } else {
    Write-Host "Token Lens autostart was not installed."
  }
  exit 0
}

$desktopLauncher = Join-Path $root "desktop-mini.vbs"
$startScript = Join-Path $root "desktop-mini.ps1"
if (-not (Test-Path $desktopLauncher)) {
  throw "Cannot find desktop launcher: $desktopLauncher"
}
if (-not (Test-Path $startScript)) {
  throw "Cannot find desktop start script: $startScript"
}

$wscript = Join-Path $env:SystemRoot "System32\wscript.exe"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $wscript
$shortcut.Arguments = "`"$desktopLauncher`""
$shortcut.WorkingDirectory = $root
$shortcut.Description = "Start Token Lens web server and desktop mini client"
$shortcut.WindowStyle = 7

$iconPath = Join-Path $root "Logo.ico"
if (Test-Path $iconPath) {
  $shortcut.IconLocation = $iconPath
}

$shortcut.Save()

Write-Host "Token Lens autostart installed: $shortcutPath"
Write-Host "Target: $wscript $($shortcut.Arguments)"
