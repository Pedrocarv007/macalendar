"""Contexto comum da interface e das ligações ao portal local."""
from django.conf import settings

from .module_registry import INTERFACE, module_for_url_name, modules_for_user


def sso_urls(request):
    base = (getattr(settings, 'THECARV_SSO_PORTAL', '') or '').rstrip('/')
    return {
        'sso_portal_base': base,
        'sso_profile_url': f'{base}/portal/perfil/',
        'sso_home_url': f'{base}/portal/',
        'sso_support_url': f'{base}/portal/suporte/',
    }


def interface_config(request):
    resolver_match = getattr(request, "resolver_match", None)
    url_name = getattr(resolver_match, "url_name", None)
    current_module = module_for_url_name(url_name)
    user = getattr(request, "user", None)
    return {
        "interface_config": INTERFACE,
        "current_module": current_module,
        "primary_modules": modules_for_user(user, navigation="primary"),
        "support_link": {
            "route": f"{(getattr(settings, 'THECARV_SSO_PORTAL', '') or '').rstrip('/')}/portal/suporte/",
            "label": "Suporte",
            "icon": "fa-headset",
        },
        "notifications_module": module_for_url_name("notifications"),
    }
