<#
.SYNOPSIS
    Instala MAC Calendar como serviço do Windows usando NSSM
.DESCRIPTION
    Script para automatizar instalação do Waitress como serviço Windows via NSSM.
    Execute como Administrador.
.EXAMPLE
    .\install-service-nssm.ps1
.EXAMPLE
    .\install-service-nssm.ps1 -ServiceName "MACCalendar" -Port 6005
#>

param(
    [string]$ServiceName = "MACCalendar",
    [string]$Listen = "127.0.0.1:6005",
    [int]$Threads = 8,
    [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$NssmPath = "nssm" # Assumindo que está no PATH
)

# Verificar se está executando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Este script precisa ser executado como Administrador"
    exit 1
}

# Verificar se NSSM está instalado
try {
    $nssmVersion = & $NssmPath version 2>&1
    Write-Host "NSSM encontrado: $nssmVersion" -ForegroundColor Green
} catch {
    Write-Error @"
NSSM não encontrado. Instale via:
  choco install nssm -y
  OU
  winget install NSSM.NSSM
  OU
  Baixe de https://nssm.cc/download
"@
    exit 1
}

# Verificar se o serviço já existe
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Serviço '$ServiceName' já existe. Removendo..." -ForegroundColor Yellow
    & $NssmPath stop $ServiceName
    & $NssmPath remove $ServiceName confirm
    Start-Sleep -Seconds 2
}

# Caminhos
$pythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$logsDir = Join-Path $ProjectRoot "logs"
$stdoutLog = Join-Path $logsDir "service-stdout.log"
$stderrLog = Join-Path $logsDir "service-stderr.log"

# Verificar Python venv
if (-not (Test-Path $pythonExe)) {
    Write-Error "Python venv não encontrado em: $pythonExe"
    Write-Host "Execute primeiro: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Criar diretório de logs se não existir
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

Write-Host "`nInstalando serviço '$ServiceName'..." -ForegroundColor Cyan

# Instalar serviço
$appArgs = "-m waitress --listen=$Listen --threads=$Threads run:app"
& $NssmPath install $ServiceName $pythonExe $appArgs

# Configurar diretório de trabalho
& $NssmPath set $ServiceName AppDirectory $ProjectRoot

# Configurar variáveis de ambiente (carregar de .env se existir)
$envFile = Join-Path $ProjectRoot ".env"
$envVars = @()
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -notmatch '^\s*#|^\s*$') {
            $envVars += $_
        }
    }
}
# Adicionar variáveis obrigatórias
$envVars += "FLASK_CONFIG=production"
$envVars += "RUNNING_ON_IIS=1"
$envVars += "BEHIND_PROXY=1"

$envString = $envVars -join "`r`n"
& $NssmPath set $ServiceName AppEnvironmentExtra $envString

# Configurar logs
& $NssmPath set $ServiceName AppStdout $stdoutLog
& $NssmPath set $ServiceName AppStderr $stderrLog

# Configurar rotação de logs (10MB)
& $NssmPath set $ServiceName AppStdoutCreationDisposition 4
& $NssmPath set $ServiceName AppStderrCreationDisposition 4
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateBytes 10485760

# Configurar início automático
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

# Configurar ações de falha (reiniciar automaticamente)
& $NssmPath set $ServiceName AppThrottle 5000
& $NssmPath set $ServiceName AppExit Default Restart
& $NssmPath set $ServiceName AppRestartDelay 5000

# Configurar descrição
& $NssmPath set $ServiceName Description "MAC Calendar - Sistema de gestão para restaurantes (Waitress WSGI Server)"
& $NssmPath set $ServiceName DisplayName "MAC Calendar Server"

Write-Host "`nServiço instalado com sucesso!" -ForegroundColor Green
Write-Host "`nDetalhes do serviço:" -ForegroundColor Cyan
Write-Host "  Nome: $ServiceName"
Write-Host "  Endereço: http://$Listen"
Write-Host "  Threads: $Threads"
Write-Host "  Logs: $logsDir"
Write-Host "  Python: $pythonExe"
Write-Host "  Diretório: $ProjectRoot"

Write-Host "`nIniciando serviço..." -ForegroundColor Cyan
& $NssmPath start $ServiceName

Start-Sleep -Seconds 3

# Verificar status
$status = & $NssmPath status $ServiceName
Write-Host "`nStatus: $status" -ForegroundColor $(if ($status -eq "SERVICE_RUNNING") { "Green" } else { "Red" })

if ($status -eq "SERVICE_RUNNING") {
    Write-Host "`nTeste o serviço:" -ForegroundColor Yellow
    Write-Host "  Invoke-WebRequest -Uri 'http://$Listen/api/health' -UseBasicParsing"
    Write-Host "`nComandos úteis:" -ForegroundColor Yellow
    Write-Host "  nssm status $ServiceName"
    Write-Host "  nssm restart $ServiceName"
    Write-Host "  nssm stop $ServiceName"
    Write-Host "  Get-Content '$stdoutLog' -Tail 50"
} else {
    Write-Warning "Serviço não iniciou corretamente. Verifique os logs:"
    Write-Host "  Get-Content '$stderrLog'"
}

Write-Host "`nPara desinstalar:" -ForegroundColor Gray
Write-Host "  nssm stop $ServiceName"
Write-Host "  nssm remove $ServiceName confirm"
