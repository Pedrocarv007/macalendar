"""
Template context processors.

Exposes the TheCarV SSO portal URLs to every template so the navbar can link
"Perfil" to the SSO profile page and "Sair" back to the SSO hub (without logging
the user out of Mac Calendar). The base URL comes from THECARV_SSO_PORTAL so it
works in both dev (http://localhost:8886) and production.
"""
from django.conf import settings


def sso_urls(request):
    base = (getattr(settings, 'THECARV_SSO_PORTAL', '') or '').rstrip('/')
    return {
        'sso_portal_base': base,
        'sso_profile_url': f'{base}/portal/perfil/',
        'sso_home_url': f'{base}/portal/',
    }
