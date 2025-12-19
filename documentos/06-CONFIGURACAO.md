# Configuração e Deployment - MAC Calendar

## Sumário

- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Configurações do Flask](#configurações-do-flask)
- [Banco de Dados](#banco-de-dados)
- [Deployment no IIS](#deployment-no-iis)
- [Deployment Local](#deployment-local)
- [Docker (Opcional)](#docker-opcional)
- [Troubleshooting](#troubleshooting)

---

## Variáveis de Ambiente

### Arquivo: `.env`

Criar arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# Flask
FLASK_APP=run.py
FLASK_ENV=production  # development ou production
SECRET_KEY=sua-chave-secreta-muito-forte-aqui
APPLICATION_ROOT=/mac

# Database
DATABASE_URL=sqlite:///instance/macalendar.db
# Para SQL Server (produção):
# DATABASE_URL=mssql+pyodbc://user:password@server/database?driver=ODBC+Driver+17+for+SQL+Server

# Email (Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-de-app-do-gmail
MAIL_DEFAULT_SENDER=seu-email@gmail.com

# Session
SESSION_TYPE=filesystem
SESSION_FILE_DIR=./flask_session
PERMANENT_SESSION_LIFETIME=86400  # 24 horas em segundos

# JWT
JWT_SECRET_KEY=outra-chave-secreta-diferente
JWT_ACCESS_TOKEN_EXPIRES=3600  # 1 hora em segundos

# Upload
UPLOAD_FOLDER=app/static/uploads
MAX_CONTENT_LENGTH=5242880  # 5MB em bytes

# IIS (apenas para produção)
FASTCGI_SCRIPT=run.py
PYTHONPATH=i:\server_apps\macalendar
```

---

### Gerando SECRET_KEY

```python
import secrets
print(secrets.token_hex(32))
```

---

## Configurações do Flask

### Arquivo: `app/config/settings.py`

```python
import os
from datetime import timedelta

class Config:
    """Configuração base"""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/macalendar.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Session
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_session')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # True em produção com HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Upload
    UPLOAD_FOLDER = 'app/static/uploads'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # Application
    APPLICATION_ROOT = os.environ.get('APPLICATION_ROOT', '/mac')


class DevelopmentConfig(Config):
    """Configuração de desenvolvimento"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True  # Log de queries SQL


class ProductionConfig(Config):
    """Configuração de produção"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Requer HTTPS
    
    # Database (SQL Server)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class TestingConfig(Config):
    """Configuração de testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Dicionário de configurações
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
```

---

### Uso no `app/__init__.py`

```python
from flask import Flask
from app.config.settings import config

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inicializar extensões
    from app.extensions.database import db
    db.init_app(app)
    
    from flask_session import Session
    Session(app)
    
    from flask_jwt_extended import JWTManager
    jwt = JWTManager(app)
    
    # Registrar blueprints
    from app.api.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    return app
```

---

## Banco de Dados

### SQLite (Desenvolvimento)

**Vantagens:**
- Fácil setup (arquivo único)
- Não requer servidor
- Portável

**Limitações:**
- Não recomendado para produção
- Concorrência limitada

**Configuração:**
```python
SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/macalendar.db'
```

---

### SQL Server (Produção)

**Instalação do Driver:**
```bash
# Windows
# Download: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

# Instalar pyodbc
pip install pyodbc
```

**Configuração:**
```python
SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://username:password@server/database?driver=ODBC+Driver+17+for+SQL+Server'

# Exemplo real:
# SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://macadmin:SenhaForte123!@localhost/MacCalendar?driver=ODBC+Driver+17+for+SQL+Server'
```

---

### Migrations

**Inicializar Flask-Migrate:**
```bash
flask db init
```

**Criar migration:**
```bash
flask db migrate -m "Initial migration"
```

**Aplicar migration:**
```bash
flask db upgrade
```

**Reverter migration:**
```bash
flask db downgrade
```

---

### Script de Inicialização

**Arquivo:** `scripts/init_db.py`

```python
from app import create_app
from app.extensions.database import db
from app.models.employee import Employee
from app.models.restaurant import Restaurant

app = create_app()

with app.app_context():
    # Criar tabelas
    db.create_all()
    
    # Criar usuário admin
    admin = Employee(
        name="Administrador",
        email="admin@thecarv.com",
        position="admin",
        department="admin",
        role="admin",
        is_active=True
    )
    admin.set_password("Admin123!")
    
    db.session.add(admin)
    db.session.commit()
    
    print("Banco de dados inicializado!")
    print(f"Admin criado: {admin.email} / Admin123!")
```

**Executar:**
```bash
python scripts/init_db.py
```

---

## Deployment no IIS

### Pré-requisitos

1. **IIS instalado** com módulo CGI
2. **Python instalado** (3.11+)
3. **wfastcgi** instalado:
   ```bash
   pip install wfastcgi
   wfastcgi-enable
   ```

---

### Configuração do IIS

#### 1. Criar Site no IIS

- Abrir IIS Manager
- Adicionar novo site:
  - **Nome:** MAC Calendar
  - **Caminho físico:** `i:\server_apps\macalendar`
  - **Binding:** https, porta 443, hostname: www.thecarv.com

---

#### 2. Configurar Handler Mapping

**Adicionar FastCGI:**

1. No site, abrir "Handler Mappings"
2. Adicionar "Module Mapping":
   - **Request path:** `*`
   - **Module:** FastCgiModule
   - **Executable:** `C:\Python311\python.exe|C:\Python311\Lib\site-packages\wfastcgi.py`
   - **Name:** Python FastCGI

---

#### 3. Arquivo `web.config`

**Arquivo:** `i:\server_apps\macalendar\web.config`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <appSettings>
    <add key="PYTHONPATH" value="i:\server_apps\macalendar" />
    <add key="WSGI_HANDLER" value="run.app" />
    <add key="WSGI_LOG" value="i:\server_apps\macalendar\logs\wfastcgi.log" />
  </appSettings>
  
  <system.webServer>
    <handlers>
      <add name="PythonHandler" 
           path="*" 
           verb="*" 
           modules="FastCgiModule" 
           scriptProcessor="C:\Python311\python.exe|C:\Python311\Lib\site-packages\wfastcgi.py" 
           resourceType="Unspecified" 
           requireAccess="Script" />
    </handlers>
    
    <rewrite>
      <rules>
        <rule name="Static Files" stopProcessing="true">
          <match url="^static/(.*)$" />
          <action type="Rewrite" url="app/static/{R:1}" />
        </rule>
        
        <rule name="Uploads" stopProcessing="true">
          <match url="^uploads/(.*)$" />
          <action type="Rewrite" url="app/static/uploads/{R:1}" />
        </rule>
      </rules>
    </rewrite>
    
    <staticContent>
      <mimeMap fileExtension=".json" mimeType="application/json" />
      <mimeMap fileExtension=".woff" mimeType="application/font-woff" />
      <mimeMap fileExtension=".woff2" mimeType="application/font-woff2" />
    </staticContent>
  </system.webServer>
</configuration>
```

---

#### 4. Configurar FastCGI Settings

No IIS Manager, nível do servidor:

1. Abrir "FastCGI Settings"
2. Adicionar aplicação:
   - **Full Path:** `C:\Python311\python.exe`
   - **Arguments:** `C:\Python311\Lib\site-packages\wfastcgi.py`
   - **Environment Variables:**
     - `PYTHONPATH`: `i:\server_apps\macalendar`
     - `WSGI_HANDLER`: `run.app`

---

#### 5. Permissões

Garantir que `IIS_IUSRS` tem permissões de leitura/escrita em:
- `i:\server_apps\macalendar`
- `i:\server_apps\macalendar\instance`
- `i:\server_apps\macalendar\logs`
- `i:\server_apps\macalendar\flask_session`
- `i:\server_apps\macalendar\app\static\uploads`

```powershell
icacls "i:\server_apps\macalendar" /grant "IIS_IUSRS:(OI)(CI)F" /T
```

---

### Arquivo `run.py` para IIS

```python
import os
import sys

# Garantir que o diretório do projeto está no path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app

# Criar aplicação
app = create_app('production')

# Para wfastcgi
if __name__ == '__main__':
    app.run()
```

---

### Logs

**Arquivo:** `i:\server_apps\macalendar\logs\wfastcgi.log`

Verificar logs em caso de erros:
```powershell
Get-Content i:\server_apps\macalendar\logs\wfastcgi.log -Tail 50
```

---

## Deployment Local

### Desenvolvimento

```bash
# Ativar ambiente virtual
.venv\Scripts\Activate.ps1

# Definir variáveis
$env:FLASK_APP = "run.py"
$env:FLASK_ENV = "development"

# Executar
flask run --host=0.0.0.0 --port=6005
```

**Acessar:** http://localhost:6005/mac

---

### Produção (Gunicorn - Linux)

```bash
# Instalar Gunicorn
pip install gunicorn

# Executar
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

**Systemd Service:**

**Arquivo:** `/etc/systemd/system/macalendar.service`

```ini
[Unit]
Description=MAC Calendar
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/macalendar
Environment="PATH=/var/www/macalendar/.venv/bin"
ExecStart=/var/www/macalendar/.venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 "run:app"

[Install]
WantedBy=multi-user.target
```

**Habilitar:**
```bash
sudo systemctl enable macalendar
sudo systemctl start macalendar
```

---

## Docker (Opcional)

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p instance logs flask_session app/static/uploads

# Expor porta
EXPOSE 5000

# Comando de inicialização
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
```

---

### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=sqlite:///instance/macalendar.db
      - SECRET_KEY=${SECRET_KEY}
      - MAIL_USERNAME=${MAIL_USERNAME}
      - MAIL_PASSWORD=${MAIL_PASSWORD}
    volumes:
      - ./instance:/app/instance
      - ./logs:/app/logs
      - ./app/static/uploads:/app/static/uploads
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./app/static:/usr/share/nginx/html/static:ro
    depends_on:
      - web
    restart: unless-stopped
```

---

### nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream macalendar {
        server web:5000;
    }

    server {
        listen 80;
        server_name www.thecarv.com;

        location /mac/static {
            alias /usr/share/nginx/html/static;
            expires 30d;
        }

        location /mac {
            proxy_pass http://macalendar;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

---

### Executar Docker

```bash
# Build
docker-compose build

# Iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down
```

---

## Troubleshooting

### Erro 500 - Internal Server Error

**Verificar:**
1. Logs do IIS: Event Viewer → Application
2. Logs do wfastcgi: `logs\wfastcgi.log`
3. Permissões de arquivos/pastas
4. Variáveis de ambiente no `web.config`

---

### Erro 404 - Not Found

**Verificar:**
1. `APPLICATION_ROOT` no `.env` e `web.config`
2. URL: `https://www.thecarv.com/mac` (com `/mac`)
3. Rewrite rules no `web.config`

---

### Database Locked (SQLite)

**Solução:**
- Usar SQL Server em produção
- Ou configurar timeout:
  ```python
  SQLALCHEMY_ENGINE_OPTIONS = {
      'connect_args': {'timeout': 15}
  }
  ```

---

### Email não enviado

**Verificar:**
1. Credenciais do Gmail no `.env`
2. "App Password" habilitado (não usar senha normal)
3. Logs da aplicação

---

### Upload de arquivos falha

**Verificar:**
1. Permissões de escrita em `app/static/uploads`
2. `MAX_CONTENT_LENGTH` no config
3. Limite do IIS: `maxAllowedContentLength` no `web.config`

---

### Session expirada frequentemente

**Ajustar:**
```python
# Em settings.py
PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # Aumentar

# Em login:
session.permanent = True
```

---

## Backup

### Script de Backup (Windows)

**Arquivo:** `scripts\backup.ps1`

```powershell
$backupDir = "i:\backups\macalendar"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = "$backupDir\backup_$timestamp"

# Criar diretório de backup
New-Item -ItemType Directory -Path $backupPath -Force

# Backup do banco de dados
Copy-Item "i:\server_apps\macalendar\instance\macalendar.db" "$backupPath\macalendar.db"

# Backup dos uploads
Copy-Item "i:\server_apps\macalendar\app\static\uploads" "$backupPath\uploads" -Recurse

# Comprimir
Compress-Archive -Path $backupPath -DestinationPath "$backupPath.zip"
Remove-Item $backupPath -Recurse

Write-Host "Backup concluído: $backupPath.zip"

# Remover backups antigos (manter últimos 30 dias)
Get-ChildItem $backupDir -Filter "*.zip" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item
```

**Agendar no Task Scheduler:**
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File i:\server_apps\macalendar\scripts\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
Register-ScheduledTask -TaskName "MAC Calendar Backup" -Action $action -Trigger $trigger
```

---

**Última atualização:** 18 de Dezembro de 2025
