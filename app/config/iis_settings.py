"""
Configurações específicas para rodando via IIS com reverse proxy
Será importado automaticamente se a variável de ambiente RUNNING_ON_IIS=1
"""
import os
from datetime import timedelta
from pathlib import Path

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent

class IISConfig:
    """Configuração específica para IIS"""
    
    # Configurações básicas do Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mac-calendar-secret-key-2024-dev'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'  # NUNCA debug em produção
    APPLICATION_ROOT = '/mac'  # Raiz quando rodando via /mac no IIS
    
    # Configurações do banco de dados
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{BASE_DIR}/instance/macalendar.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Configurações JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-mac-2024'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    
    # Configurações de upload
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # Configurações de sessão
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'mac-calendar:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)
    SESSION_COOKIE_SECURE = True  # HTTPS em produção via IIS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configurações de email
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
