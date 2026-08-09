[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$startScript = Join-Path $PSScriptRoot "iniciar_desenvolvimento.ps1"
$localRoot = Join-Path $env:LOCALAPPDATA "OncologiaCacoal"
$stdout = Join-Path $localRoot "django.out.log"
$stderr = Join-Path $localRoot "django.err.log"
$url = "http://127.0.0.1:8000/"

function Test-OncologiaCacoal {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "${url}saude/" -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

if (-not (Test-OncologiaCacoal)) {
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $startScript
    )
    Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WindowStyle Hidden `
        -WorkingDirectory $projectRoot -RedirectStandardOutput $stdout -RedirectStandardError $stderr

    $started = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        Start-Sleep -Seconds 1
        if (Test-OncologiaCacoal) {
            $started = $true
            break
        }
    }
    if (-not $started) {
        throw "O sistema não iniciou. Consulte $stderr."
    }
}

Start-Process $url
