"""
Production settings for Mac Calendar.
"""
from .base import *  # noqa
import dj_database_url
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]

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
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'  # Cross-site SSO redirect chain requires SameSite=None
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# SSO portal (production)
LOGIN_URL = os.getenv('THECARV_SSO_PORTAL', 'https://carloscardoso.thecarv.com') + '/portal/sistema/mac-calendar/'
LOGOUT_REDIRECT_URL = os.getenv('THECARV_SSO_PORTAL', 'https://carloscardoso.thecarv.com') + '/portal/'

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
            'filename': '/app/logs/django.log',
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
