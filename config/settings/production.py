"""
Production settings for Mac Calendar.
"""
from .base import *  # noqa
import dj_database_url
import os
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]

if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY must be set in production.')

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must be set in production.')

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
    ),
    'sso': dj_database_url.config(
        env='SSO_DB_URL',
        default=os.getenv('SSO_DB_URL'),
        conn_max_age=600,
    ),
}

# HTTPS / proxy headers (nginx terminates SSL)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', True)
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'  # Cross-site SSO redirect chain requires SameSite=None
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'
# X-XSS-Protection esta deprecated (recomendacao OWASP/Django moderno): nao emitir.
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = True

# SSO portal (production)
LOGIN_URL = os.getenv('THECARV_SSO_PORTAL', 'https://carloscardoso.thecarv.com') + '/portal/sistema/mac-calendar/'
LOGOUT_REDIRECT_URL = os.getenv('THECARV_SSO_PORTAL', 'https://carloscardoso.thecarv.com') + '/portal/'

log_file = Path(os.getenv('DJANGO_LOG_FILE', str(BASE_DIR / 'logs' / 'django.log')))
log_file.parent.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(log_file),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
