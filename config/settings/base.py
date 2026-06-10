"""
Base Django settings for Mac Calendar project.
"""
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    value = os.getenv(name, default)
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Read env file if it exists
load_dotenv(os.path.join(BASE_DIR, '.env'))

# SECURITY
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = env_bool('DEBUG', False)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS')

APPEND_SLASH = False

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
]

LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.restaurants',
    'apps.calendar_events',
    'apps.documents',
    'apps.notifications',
    'apps.tickets',
    'apps.dashboard',
    'apps.workers',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.SecurityHeadersMiddleware',
    'apps.core.middleware.SessionTimeoutMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': os.getenv('DATABASE_URL'),
    'sso':     os.getenv('SSO_DB_URL'),   # SSO DB: fonte de verdade para Workers/Restaurants
}

DATABASE_ROUTERS = ['apps.workers.router.SSORouter']

# Custom user model
AUTH_USER_MODEL = 'accounts.Employee'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'apps.accounts.backends.TheCarVSSOBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'pt-pt'
TIME_ZONE = 'Europe/Lisbon'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'collected_static'

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# SSO Portal media — URL para o browser e caminho no disco para o gerador de cartões
# Serve por uma rota local (/sso-media/) para não depender do portal SSO estar online.
SSO_MEDIA_BASE_URL = os.getenv('SSO_MEDIA_BASE_URL', '/sso-media/')
SSO_MEDIA_ROOT     = Path(os.getenv('SSO_MEDIA_ROOT', r'I:\server_apps\Thecarv_django\media'))
SERVE_SSO_MEDIA_LOCALLY = env_bool('SERVE_SSO_MEDIA_LOCALLY', DEBUG)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'EXCEPTION_HANDLER': 'apps.core.utils.custom_exception_handler',
}

# SimpleJWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    # JWT_SECRET_KEY env var, fallback to SECRET_KEY for backwards compat
    'SIGNING_KEY': os.getenv('JWT_SECRET_KEY') or None,  # None → SimpleJWT uses SECRET_KEY
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS
# --- CORS ---
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True

# Session settings
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 28800  # 8 hours

# CSRF
CSRF_COOKIE_HTTPONLY = False  # JS needs to read it
CSRF_COOKIE_SAMESITE = 'Lax'

# Login URL
LOGIN_URL = 'http://localhost:51/account/login/'
LOGIN_REDIRECT_URL = '/dashboard'
LOGOUT_REDIRECT_URL = 'http://localhost:51/account/login/'

# Service-to-service API key (used by external systems to call /api/service/ endpoints)
SERVICE_API_KEY = os.getenv('SERVICE_API_KEY', '')

# Pasta raiz das templates de imagens (por restaurante) usada em documents/generators.py
# Em produção Linux, aponta para o caminho onde as pastas por restaurante estão montadas.
TEMPLATES_BASE_DIR = os.getenv('TEMPLATES_BASE_DIR', 'I:/server_apps/macalendar/templates_generate')

# External services
THECARV_SSO_URL      = os.getenv('THECARV_SSO_URL')
THECARV_SSO_SECRET   = os.getenv('THECARV_SSO_SECRET')   # segredo JWT partilhado com o SSO Portal
THECARV_SSO_PORTAL   = os.getenv('THECARV_SSO_PORTAL')
THECARV_MAIL_URL     = os.getenv('THECARV_MAIL_URL')
THECARV_MAIL_API_KEY = os.getenv('THECARV_MAIL_API_KEY')

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL')

# Birthday generation window
BIRTHDAY_GENERATION_MONTHS_AHEAD = int(os.getenv('BIRTHDAY_GENERATION_MONTHS_AHEAD', '1'))

# Role constants
ROLE_ADMIN = 'admin'
ROLE_RH = 'rh'
ROLE_MARKETING = 'marketing'
ROLE_GERENTE_LOJA = 'gerente_loja'
ROLE_SUB_GERENTE = 'sub_gerente'
ROLE_GERENTE_TURNO = 'gerente_turno'
ROLE_EMPLOYEE = 'employee'

ROLE_HIERARCHY = [
    ROLE_ADMIN,
    ROLE_RH,
    ROLE_MARKETING,
    ROLE_GERENTE_LOJA,
    ROLE_SUB_GERENTE,
    ROLE_GERENTE_TURNO,
    ROLE_EMPLOYEE,
]

SUPER_ROLES = [ROLE_ADMIN, ROLE_RH, ROLE_MARKETING]
MANAGER_ROLES = [ROLE_GERENTE_LOJA, ROLE_SUB_GERENTE, ROLE_GERENTE_TURNO]

# File upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_UPLOAD_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.docx', '.xlsx']
