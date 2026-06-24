param(
    [ValidateSet('User', 'Process', 'Machine')]
    [string]$Target = 'User',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$envName = 'OPENAI_API_KEY'

if ($Target -eq 'Machine') {
    $principal = [Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        throw 'Machine-level environment variables require running PowerShell as Administrator.'
    }
}

$existing = [Environment]::GetEnvironmentVariable($envName, $Target)
if ($existing -and -not $Force) {
    $answer = Read-Host "$envName already exists for $Target. Overwrite? Type YES"
    if ($answer -ne 'YES') {
        Write-Host 'Canceled. Existing value was not changed.'
        exit 0
    }
}

$secureKey = Read-Host "Enter $envName" -AsSecureString
if ($secureKey.Length -eq 0) {
    throw 'Empty API key was not saved.'
}

$plainKeyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($plainKeyPtr)
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw 'Empty API key was not saved.'
    }

    if ($plainKey -notmatch '^sk-') {
        $answer = Read-Host 'This does not look like an OpenAI API key. Save anyway? Type YES'
        if ($answer -ne 'YES') {
            Write-Host 'Canceled. Value was not saved.'
            exit 0
        }
    }

    [Environment]::SetEnvironmentVariable($envName, $plainKey, $Target)

    if ($Target -ne 'Process') {
        Set-Item -LiteralPath "Env:$envName" -Value $plainKey
    }

    Write-Host "$envName saved for $Target."
    if ($Target -eq 'User') {
        Write-Host 'Open a new terminal or restart apps that need to read the updated variable.'
    }
}
finally {
    if ($plainKeyPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($plainKeyPtr)
    }
    if (Get-Variable -Name plainKey -ErrorAction SilentlyContinue) {
        Remove-Variable -Name plainKey -Force
    }
}
