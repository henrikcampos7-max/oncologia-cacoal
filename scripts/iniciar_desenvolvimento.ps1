[CmdletBinding()]
param(
    [switch]$SomentePreparar,
    [switch]$DadosFicticios,
    [string]$Endereco = "127.0.0.1:8000"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$secretsDirectory = Join-Path $env:LOCALAPPDATA "OncologiaCacoal"
$appSecretPath = Join-Path $secretsDirectory "postgres-app.dpapi"
$demoSecretPath = Join-Path $secretsDirectory "demo-password.dpapi"
$postgresPrefix = Join-Path $secretsDirectory "postgresql17"
$postgresData = Join-Path $secretsDirectory "postgres-data"
$postgresLog = Join-Path $secretsDirectory "postgresql.log"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

function Read-ProtectedSecret([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Configuração local ausente. Execute scripts\configurar_postgresql_local.ps1 primeiro."
    }
    $encryptedValue = (Get-Content -LiteralPath $Path -Raw).Trim()
    $secureValue = $encryptedValue | ConvertTo-SecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Ambiente virtual ausente em $python."
}

$pgCtl = Join-Path $postgresPrefix "Library\bin\pg_ctl.exe"
$pgIsReady = Join-Path $postgresPrefix "Library\bin\pg_isready.exe"
if (-not (Test-Path -LiteralPath $pgCtl) -or -not (Test-Path -LiteralPath $pgIsReady)) {
    throw "PostgreSQL local ausente. Execute scripts\configurar_postgresql_local.ps1 primeiro."
}

$null = & $pgIsReady -h 127.0.0.1 -p 5432 2>$null
if ($LASTEXITCODE -ne 0) {
    & $pgCtl -D $postgresData -l $postgresLog -o "-h 127.0.0.1 -p 5432" start -w
    if ($LASTEXITCODE -ne 0) {
        throw "O PostgreSQL local não iniciou. Consulte $postgresLog."
    }
}

$env:DJANGO_DEBUG = "true"
$env:POSTGRES_DB = "oncologia_cacoal_dev"
$env:POSTGRES_USER = "oncologia_cacoal_dev"
$env:POSTGRES_PASSWORD = Read-ProtectedSecret -Path $appSecretPath
$env:POSTGRES_HOST = "127.0.0.1"
$env:POSTGRES_PORT = "5432"

Push-Location $projectRoot
try {
    & $python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) {
        throw "As migrações não foram aplicadas."
    }

    if ($DadosFicticios) {
        $env:ONCOLOGIA_DEMO_PASSWORD = Read-ProtectedSecret -Path $demoSecretPath
        & $python manage.py seed_demo --confirmar-dados-ficticios
        if ($LASTEXITCODE -ne 0) {
            throw "A carga de dados fictícios não foi concluída."
        }
    }

    if (-not $SomentePreparar) {
        Write-Host "Abrindo Oncologia Cacoal em http://$Endereco/"
        & $python manage.py runserver $Endereco
    }
}
finally {
    Remove-Item Env:POSTGRES_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:ONCOLOGIA_DEMO_PASSWORD -ErrorAction SilentlyContinue
    Pop-Location
}
