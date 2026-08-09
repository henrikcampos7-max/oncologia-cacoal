[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$secretsDirectory = Join-Path $env:LOCALAPPDATA "OncologiaCacoal"
$postgresSecretPath = Join-Path $secretsDirectory "postgres-superuser.dpapi"
$appSecretPath = Join-Path $secretsDirectory "postgres-app.dpapi"
$demoSecretPath = Join-Path $secretsDirectory "demo-password.dpapi"
$micromambaDirectory = Join-Path $secretsDirectory "micromamba"
$micromambaExecutable = Join-Path $micromambaDirectory "micromamba.exe"
$mambaRoot = Join-Path $secretsDirectory "mamba-root"
$postgresPrefix = Join-Path $secretsDirectory "postgresql17"
$postgresData = Join-Path $secretsDirectory "postgres-data"
$postgresLog = Join-Path $secretsDirectory "postgresql.log"
$appRole = "oncologia_cacoal_dev"
$appDatabase = "oncologia_cacoal_dev"

function New-LocalPassword {
    $alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    $bytes = New-Object byte[] 28
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }

    $randomPart = -join ($bytes | ForEach-Object { $alphabet[$_ % $alphabet.Length] })
    return "Pg17!$randomPart"
}

function Save-ProtectedSecret([string]$Path, [string]$Value) {
    $secureValue = ConvertTo-SecureString -String $Value -AsPlainText -Force
    $encryptedValue = ConvertFrom-SecureString -SecureString $secureValue
    Set-Content -LiteralPath $Path -Value $encryptedValue -Encoding ASCII
}

function Read-ProtectedSecret([string]$Path) {
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

function Get-PostgresExecutable([string]$Name) {
    $portableExecutable = Join-Path $postgresPrefix "Library\bin\$Name.exe"
    if (Test-Path -LiteralPath $portableExecutable) {
        return $portableExecutable
    }

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidate = Get-ChildItem -Path "C:\Program Files\PostgreSQL\*\bin\$Name.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if ($candidate) {
        return $candidate.FullName
    }
    return $null
}

New-Item -ItemType Directory -Path $secretsDirectory -Force | Out-Null

if (-not (Test-Path -LiteralPath $postgresSecretPath)) {
    Save-ProtectedSecret -Path $postgresSecretPath -Value (New-LocalPassword)
}
$postgresPassword = Read-ProtectedSecret -Path $postgresSecretPath

$psql = Get-PostgresExecutable "psql"
if (-not $psql) {
    New-Item -ItemType Directory -Path $micromambaDirectory -Force | Out-Null
    if (-not (Test-Path -LiteralPath $micromambaExecutable)) {
        $micromambaArchive = Join-Path $micromambaDirectory "micromamba.tar.bz2"
        Write-Host "Obtendo o instalador portátil Micromamba..."
        Invoke-WebRequest -UseBasicParsing `
            -Uri "https://micro.mamba.pm/api/micromamba/win-64/latest" `
            -OutFile $micromambaArchive
        & tar.exe -xf $micromambaArchive -C $micromambaDirectory "Library/bin/micromamba.exe"
        if ($LASTEXITCODE -ne 0) {
            throw "Não foi possível extrair o Micromamba."
        }
        $extractedMicromamba = Join-Path $micromambaDirectory "Library\bin\micromamba.exe"
        Move-Item -LiteralPath $extractedMicromamba -Destination $micromambaExecutable -Force
    }

    Write-Host "Instalando PostgreSQL 17.10 localmente para este usuário..."
    $env:MAMBA_ROOT_PREFIX = $mambaRoot
    & $micromambaExecutable create --prefix $postgresPrefix --channel conda-forge `
        --strict-channel-priority "postgresql=17.10" --no-mamba-repodata-parsing --yes
    if ($LASTEXITCODE -ne 0) {
        throw "A instalação portátil do PostgreSQL não foi concluída (código $LASTEXITCODE)."
    }

    $psql = Get-PostgresExecutable "psql"
    if (-not $psql) {
        throw "A instalação terminou, mas o executável psql não foi localizado."
    }
}

$initdb = Get-PostgresExecutable "initdb"
$pgCtl = Get-PostgresExecutable "pg_ctl"
$pgIsReady = Get-PostgresExecutable "pg_isready"
if (-not $initdb -or -not $pgCtl -or -not $pgIsReady) {
    throw "As ferramentas do servidor PostgreSQL não foram localizadas."
}

$postgresVersionFile = Join-Path $postgresData "PG_VERSION"
if (-not (Test-Path -LiteralPath $postgresVersionFile)) {
    New-Item -ItemType Directory -Path $postgresData -Force | Out-Null
    $temporaryPasswordFile = Join-Path $secretsDirectory "initdb-password.tmp"
    [IO.File]::WriteAllText(
        $temporaryPasswordFile,
        $postgresPassword,
        (New-Object Text.UTF8Encoding($false))
    )
    try {
        & $initdb -D $postgresData -U postgres --pwfile=$temporaryPasswordFile `
            --encoding=UTF8 --locale=C --auth-local=scram-sha-256 --auth-host=scram-sha-256
        if ($LASTEXITCODE -ne 0) {
            throw "Não foi possível inicializar o banco local."
        }
    }
    finally {
        if ((Resolve-Path -LiteralPath $temporaryPasswordFile -ErrorAction SilentlyContinue).Path -like "$secretsDirectory\*") {
            Remove-Item -LiteralPath $temporaryPasswordFile -Force -ErrorAction SilentlyContinue
        }
    }
}

$null = & $pgIsReady -h 127.0.0.1 -p 5432 2>$null
if ($LASTEXITCODE -ne 0) {
    & $pgCtl -D $postgresData -l $postgresLog -o "-h 127.0.0.1 -p 5432" start -w
    if ($LASTEXITCODE -ne 0) {
        throw "O servidor PostgreSQL local não iniciou. Consulte $postgresLog."
    }
}

$createdb = Get-PostgresExecutable "createdb"
if (-not $createdb) {
    throw "O executável createdb não foi localizado."
}

$env:PGPASSWORD = $postgresPassword

$connected = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    $null = & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -tAc "SELECT 1" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $connected = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $connected) {
    throw "O PostgreSQL foi localizado, mas não respondeu na porta 5432."
}

if (-not (Test-Path -LiteralPath $appSecretPath)) {
    Save-ProtectedSecret -Path $appSecretPath -Value (New-LocalPassword)
}
if (-not (Test-Path -LiteralPath $demoSecretPath)) {
    Save-ProtectedSecret -Path $demoSecretPath -Value (New-LocalPassword)
}
$appPassword = Read-ProtectedSecret -Path $appSecretPath

$roleQueryResult = & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$appRole'"
$roleExists = "$roleQueryResult".Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível consultar os usuários do PostgreSQL."
}

if ($roleExists -eq "1") {
    & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 `
        -c "ALTER ROLE $appRole WITH LOGIN PASSWORD '$appPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;"
}
else {
    & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 `
        -c "CREATE ROLE $appRole WITH LOGIN PASSWORD '$appPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;"
}
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível preparar o usuário exclusivo da aplicação."
}

$databaseQueryResult = & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$appDatabase'"
$databaseExists = "$databaseQueryResult".Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível consultar os bancos do PostgreSQL."
}

if ($databaseExists -ne "1") {
    & $createdb -h 127.0.0.1 -p 5432 -U postgres --owner $appRole $appDatabase
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível criar o banco exclusivo da aplicação."
    }
}
else {
    & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 `
        -c "ALTER DATABASE $appDatabase OWNER TO $appRole;"
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível confirmar o proprietário do banco da aplicação."
    }
}

Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

Write-Host "Aplicando migrações e criando somente dados fictícios..."
& (Join-Path $PSScriptRoot "iniciar_desenvolvimento.ps1") -SomentePreparar -DadosFicticios
if ($LASTEXITCODE -ne 0) {
    throw "A preparação do Django não foi concluída."
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Oncologia Cacoal.lnk"
$launcherPath = Join-Path $PSScriptRoot "abrir_oncologia_cacoal.ps1"
$windowsShell = New-Object -ComObject WScript.Shell
$shortcut = $windowsShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = (Get-Command powershell.exe).Source
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcherPath`""
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = "Abrir o sistema local Oncologia Cacoal"
$shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,1"
$shortcut.WindowStyle = 7
$shortcut.Save()

Write-Host "PostgreSQL local configurado com sucesso."
Write-Host "Os segredos estão criptografados para o usuário atual em $secretsDirectory."
Write-Host "Atalho criado em $shortcutPath."
