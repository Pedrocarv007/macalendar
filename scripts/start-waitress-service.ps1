<#
.SYNOPSIS
    Inicia Waitress como serviço de longa duração (para Task Scheduler ou uso direto)
.DESCRIPTION
    Script wrapper para executar Waitress que mantém processo ativo,
    carrega .env, e loga output para arquivo.
#>

param(
    [string]$Listen = "127.0.0.1:6005",
    [int]$Threads = 8,
    [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
)

# Configurar logs
$logsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}
$logFile = Join-Path $logsDir "waitress-service.log"

function Write-ServiceLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] $Message"
    Add-Content -Path $logFile -Value $logLine
    Write-Host $logLine
}

Write-ServiceLog "=== MAC Calendar Service Starting ==="
Write-ServiceLog "Project Root: $ProjectRoot"
Write-ServiceLog "Listen: $Listen"
Write-ServiceLog "Threads: $Threads"

# Carregar .env
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Write-ServiceLog "Loading .env from: $envFile"
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^(\s*#|\s*$)') { return }
        $parts = $_ -split '=', 2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $val = $parts[1].Trim()
            if ($key) {
                Set-Item -Path Env:$key -Value $val
                Write-ServiceLog "  ENV: $key=$val"
            }
        }
    }
} else {
    Write-ServiceLog "WARNING: .env not found at $envFile"
}

# Configurar variáveis obrigatórias
$env:RUNNING_ON_IIS = "1"
$env:FLASK_CONFIG = "production"
$env:BEHIND_PROXY = "1"

# Verificar venv
$venvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-ServiceLog "ERROR: Virtualenv not found at $venvActivate"
    exit 1
}

Write-ServiceLog "Activating virtualenv: $venvActivate"
. $venvActivate

# Verificar waitress
try {
    $waitressVersion = & python -m waitress --help 2>&1 | Select-Object -First 1
    Write-ServiceLog "Waitress available"
} catch {
    Write-ServiceLog "ERROR: Waitress not installed. Run: pip install waitress"
    exit 1
}

# Iniciar Waitress (processo bloqueante)
Write-ServiceLog "Starting Waitress on $Listen with $Threads threads..."
Write-ServiceLog "Command: python -m waitress --listen=$Listen --threads=$Threads run:app"

try {
    # Redirecionar stdout/stderr para o log
    $env:PYTHONUNBUFFERED = "1"
    
    # Executar Waitress
    & python -m waitress --listen=$Listen --threads=$Threads run:app 2>&1 | ForEach-Object {
        Write-ServiceLog $_
    }
} catch {
    Write-ServiceLog "ERROR: Waitress crashed - $_"
    exit 1
} finally {
    Write-ServiceLog "=== MAC Calendar Service Stopped ==="
}
