"""Configuração do MC para o stack Docker local."""

from .development import *  # noqa: F401,F403


_portal = (THECARV_SSO_PORTAL or "http://localhost:8886").rstrip("/")

LOGIN_URL = f"{_portal}/portal/sistema/mac-calendar/"
LOGOUT_REDIRECT_URL = f"{_portal}/portal/"

SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_NAME = "thecarv_calendar_sessionid"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_NAME = "thecarv_calendar_csrftoken"
CSRF_COOKIE_SAMESITE = "Lax"
