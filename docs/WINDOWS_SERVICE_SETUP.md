# Configurar MAC Calendar (Waitress) como Serviço do Windows

Este guia mostra como executar o servidor Waitress como um serviço do Windows que inicia automaticamente.

## Opção 1: NSSM (Recomendado)

NSSM (Non-Sucking Service Manager) é a forma mais simples e confiável.

### 1.1 Instalar NSSM

**Via Chocolatey (se tiver instalado):**
```powershell
choco install nssm -y
```

**Via Winget:**
```powershell
winget install NSSM.NSSM
```

**Download Manual:**
1. Baixe de https://nssm.cc/download
2. Extraia para `C:\nssm` (ou outra pasta de sua escolha)
3. Adicione ao PATH ou use o caminho completo

### 1.2 Criar o Serviço

Execute **PowerShell como Administrador** e rode:

```powershell
# Navegue para o diretório do projeto
cd I:\server_apps\macalendar

# Instale o serviço usando NSSM
nssm install pdf2doc "I:\server_apps\pdftoword\.venv\Scripts\python.exe" "python -m uvicorn app:app --host 0.0.0.0 --port 5010"

# Configure o diretório de trabalho
nssm set pdf2doc AppDirectory "I:\server_apps\pdftoword"

# Configure variáveis de ambiente
nssm set MACCalendar AppEnvironmentExtra FLASK_CONFIG=production RUNNING_ON_IIS=1

# Configure para iniciar automaticamente
nssm set MACCalendar Start SERVICE_AUTO_START

# Configure stdout/stderr para logs
nssm set MACCalendar AppStdout "I:\server_apps\macalendar\logs\service-stdout.log"
nssm set MACCalendar AppStderr "I:\server_apps\macalendar\logs\service-stderr.log"

# Configure rotação de logs (10MB)
nssm set MACCalendar AppStdoutCreationDisposition 4
nssm set MACCalendar AppStderrCreationDisposition 4
nssm set MACCalendar AppRotateFiles 1
nssm set MACCalendar AppRotateOnline 1
nssm set MACCalendar AppRotateBytes 10485760

# Inicie o serviço
nssm start MACCalendar
```

### 1.3 Gerenciar o Serviço NSSM

```powershell
# Ver status
nssm status MACCalendar

# Parar
nssm stop MACCalendar

# Reiniciar
nssm restart MACCalendar

# Remover serviço (caso queira desinstalar)
nssm remove MACCalendar confirm
```

### 1.4 Script Automatizado NSSM

Veja `scripts/install-service-nssm.ps1` para instalação automatizada.

---

## Opção 2: Task Scheduler (Alternativa Simples)

Se não puder instalar NSSM, use o Agendador de Tarefas do Windows.

### 2.1 Criar Tarefa via PowerShell

Execute como Administrador:

```powershell
# Importar a tarefa do XML (veja scripts/mac-calendar-task.xml)
Register-ScheduledTask -Xml (Get-Content "I:\server_apps\macalendar\scripts\mac-calendar-task.xml" | Out-String) -TaskName "MAC Calendar Server"

# Ou criar manualmente
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File I:\server_apps\macalendar\scripts\start-waitress-service.ps1"
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 3

Register-ScheduledTask -TaskName "MAC Calendar Server" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings
```

### 2.2 Gerenciar via Task Scheduler

```powershell
# Iniciar
Start-ScheduledTask -TaskName "MAC Calendar Server"

# Parar (terá que matar o processo manualmente)
Stop-Process -Name "python" -Force

# Remover
Unregister-ScheduledTask -TaskName "MAC Calendar Server" -Confirm:$false
```

---

## Opção 3: WinSW (Windows Service Wrapper)

WinSW é outra alternativa ao NSSM.

### 3.1 Download WinSW

1. Baixe de https://github.com/winsw/winsw/releases
2. Renomeie para `MACCalendar-service.exe`
3. Coloque em `I:\server_apps\macalendar\scripts\`

### 3.2 Criar Arquivo de Configuração

Veja `scripts/mac-calendar-service.xml` para a configuração do WinSW.

### 3.3 Instalar e Gerenciar

```powershell
# Instalar
.\scripts\MACCalendar-service.exe install

# Iniciar
.\scripts\MACCalendar-service.exe start

# Parar
.\scripts\MACCalendar-service.exe stop

# Desinstalar
.\scripts\MACCalendar-service.exe uninstall
```

---

## Verificação e Troubleshooting

### Verificar se o serviço está rodando

```powershell
# Via NSSM
nssm status MACCalendar

# Via Services Manager
Get-Service -Name MACCalendar

# Testar endpoint
Invoke-WebRequest -Uri "http://127.0.0.1:6005/api/health" -UseBasicParsing
```

### Logs

- **NSSM:** `I:\server_apps\macalendar\logs\service-stdout.log` e `service-stderr.log`
- **Aplicação:** `I:\server_apps\macalendar\logs\app.log`
- **Windows Event Viewer:** Applications and Services Logs

### Problemas Comuns

**Serviço não inicia:**
1. Verifique permissões da pasta e arquivos
2. Confirme que o Python e venv existem
3. Teste o script manualmente primeiro: `.\scripts\start_waitress.ps1`
4. Revise logs em `logs\service-stderr.log`

**Variáveis de ambiente não carregadas:**
- Para NSSM, use `nssm set MACCalendar AppEnvironmentExtra` ou configure `.env` absoluto
- Para Task Scheduler, carregue `.env` no script PowerShell

**Porta em uso:**
- Altere a porta em `AppParameters` (NSSM) ou script
- Verifique conflitos: `netstat -ano | findstr :6005`

---

## Integração com IIS (ARR)

Se usar IIS como reverse proxy na porta 443/80:

1. Garanta que o Waitress esteja em `127.0.0.1:6005` (localhost)
2. Configure ARR para proxy `/mac` → `http://127.0.0.1:6005`
3. Defina `RUNNING_ON_IIS=1` e `BEHIND_PROXY=1` nas variáveis de ambiente

---

## Segurança

- Execute o serviço com conta de serviço dedicada (não SYSTEM) em produção
- Restrinja permissões na pasta `I:\server_apps\macalendar`
- Use HTTPS no IIS/proxy frontal
- Mantenha logs rotativos para evitar consumo de disco

---

## Recomendação Final

**Para produção:** Use **NSSM** pela facilidade de gestão, logs automáticos e reinício em caso de falha.

**Para desenvolvimento/teste:** Use o script `start_waitress.ps1` diretamente ou Task Scheduler.
