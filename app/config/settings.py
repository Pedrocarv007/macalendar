"""
Configurações da aplicação MAC Calendar
"""
import os
import json
from datetime import timedelta
from pathlib import Path


# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Config:
    """Configuração base da aplicação"""
    
    # Configurações básicas do Flask
    SECRET_KEY = os.getenv('SECRET_KEY') 
    DEBUG = os.getenv('FLASK_DEBUG')
    APPLICATION_ROOT = os.getenv('APPLICATION_ROOT')
    APP_BASE_URL = os.getenv('APP_BASE_URL')
    
    # Configurações do banco de dados
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Configurações JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') 
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    
    # Configurações de upload
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # Configurações de roles de usuário (podem ser sobrescritas por env)
    roles_env = os.getenv('VALID_ROLES')
    staff_roles_env = os.getenv('STAFF_ROLES')
    super_roles_env = os.getenv('SUPER_ROLES')
    if roles_env:
        VALID_ROLES = [r.strip().lower() for r in roles_env.split(',') if r.strip()]
    if staff_roles_env:
        STAFF_ROLES = [r.strip().lower() for r in staff_roles_env.split(',') if r.strip()]
    if super_roles_env:
        SUPER_ROLES = [r.strip().lower() for r in super_roles_env.split(',') if r.strip()]
    


    _default_role_env = os.getenv('DEFAULT_ROLE', 'employee').strip().lower()
    DEFAULT_ROLE = _default_role_env if _default_role_env in VALID_ROLES else (VALID_ROLES[0] if VALID_ROLES else 'employee')
    
    # Configurações de sessão
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'mac-calendar:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)  # Duração quando "lembrar-me" está ativo
    SESSION_COOKIE_SECURE = False  # True apenas em produção com HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Previne acesso via JavaScript
    SESSION_COOKIE_SAMESITE = 'Lax'  # Proteção contra CSRF
    SESSION_COOKIE_PATH = os.getenv('APPLICATION_ROOT')  # Path do cookie deve corresponder ao APPLICATION_ROOT
    SESSION_COOKIE_NAME = 'mac_session'  # Nome específico para evitar conflitos
    
    
    # Configurações de email
    MAIL_SERVER = os.getenv('MAIL_SERVER') 
    MAIL_PORT = os.getenv('MAIL_PORT')
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS')  # Padrão para TLS
    MAIL_USERNAME = os.getenv('MAIL_USERNAME') 
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    _mail_profiles_env = os.getenv('MAIL_PROFILES')
    try:
        MAIL_PROFILES = json.loads(_mail_profiles_env) if _mail_profiles_env else {}
    except Exception:
        MAIL_PROFILES = {}

    # Perfis padrão: thecarv (default) e noreply, podem ser sobrescritos por MAIL_PROFILES.
    if not MAIL_PROFILES:
        MAIL_PROFILES = {
            "default": {
                "server": MAIL_SERVER,
                "port": MAIL_PORT,
                "use_tls": MAIL_USE_TLS,
                "username": os.getenv('MAIL_USERNAME'),
                "password": os.getenv('MAIL_PASSWORD') ,
                "default_sender": os.getenv('MAIL_DEFAULT_SENDER'),
            },
            "noreply": {
                "server":  MAIL_SERVER,
                "port": MAIL_PORT,
                "use_tls":  MAIL_USE_TLS,
                "username": os.getenv('MAIL_USERNAME_NOREPLY'),
                "password": os.getenv('MAIL_PASSWORD'),
                "default_sender": os.getenv('MAIL_DEFAULT_SENDER'),
            },
        }
    
    # Configurações de timezone
    TIMEZONE = 'Europe/Lisbon'
    
    # Configurações de logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = BASE_DIR / 'logs' / 'app.log'
    
    # Configurações de templates
    TEMPLATES_AUTO_RELOAD = True
    
    # Configurações de segurança
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Configurações de cache
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    @classmethod
    def init_app(cls, app):
        """Inicializar configurações específicas da aplicação"""
        
        # Criar diretórios necessários
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.UPLOAD_FOLDER / 'employees', exist_ok=True)
        os.makedirs(cls.UPLOAD_FOLDER / 'workers', exist_ok=True)
        os.makedirs(cls.UPLOAD_FOLDER / 'documents', exist_ok=True)
        os.makedirs(BASE_DIR / 'instance', exist_ok=True)
        os.makedirs(BASE_DIR / 'logs', exist_ok=True)

class DevelopmentConfig(Config):
    """Configurações para desenvolvimento"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configurações para produção"""
    DEBUG = False
    TESTING = False
    
    # Configurações mais restritivas para produção
    SESSION_COOKIE_SECURE = True  # HTTPS obrigatório
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_PATH = os.getenv('APPLICATION_ROOT')
    SESSION_COOKIE_DOMAIN = None  # Let Flask handle it automatically
    
    # Logging mais detalhado
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    """Configurações para testes"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuração padrão
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}