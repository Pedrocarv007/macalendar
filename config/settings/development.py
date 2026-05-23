"""
Development settings for Mac Calendar.
"""
from .base import *  # noqa
import dj_database_url
import os
from dotenv import load_dotenv


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Read env file if it exists
load_dotenv(os.path.join(BASE_DIR, '.env'))


DEBUG = True

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
# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# CORS — allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Show emails in console during development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable password validators for easier testing
AUTH_PASSWORD_VALIDATORS = []

# Django Debug Toolbar (optional — install separately if needed)
# staticfiles already included in base INSTALLED_APPS

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
