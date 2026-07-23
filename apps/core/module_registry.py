"""Configuração central da interface e dos módulos do MC."""

from copy import deepcopy


INTERFACE = {
    "produto": "MC",
    "organizacao": "TheCarv",
    "idioma": "pt-PT",
    "tema": {
        "cor_marca": "#FFBC0D",
        "cor_destaque": "#2D2D2D",
        "cor_sucesso": "#176B52",
        "cor_fundo": "#F5F5F5",
        "cor_texto": "#2D2D2D",
    },
    "versao_estatica": "20260723-mc4",
}


MODULES = {
    "calendar": {
        "key": "calendar",
        "label": "Calendário",
        "short_label": "Calendário",
        "description": "Planeamento de eventos, publicações e aniversários.",
        "route": "/calendar",
        "url_name": "calendar",
        "template": "calendar/index.html",
        "icon": "fa-calendar-days",
        "accent": "#FFBC0D",
        "accent_soft": "#FFF4CC",
        "accent_text": "#2D2D2D",
        "stylesheet": "/static/css/modules/calendar.css",
        "script": "/static/js/modules/calendar.js",
        "navigation": "primary",
        "roles": (),
    },
    "documents": {
        "key": "documents",
        "label": "Templates",
        "short_label": "Templates",
        "description": "Templates gráficos e ficheiros organizados por finalidade.",
        "route": "/documents",
        "url_name": "documents",
        "template": "documents/index.html",
        "icon": "fa-layer-group",
        "accent": "#FFBC0D",
        "accent_soft": "#FFF3C4",
        "accent_text": "#2D2D2D",
        "stylesheet": "/static/css/modules/documents.css",
        "script": "/static/js/modules/documents.js",
        "navigation": "primary",
        "roles": (),
    },
    "notifications": {
        "key": "notifications",
        "label": "Notificações",
        "short_label": "Notificações",
        "description": "Avisos e atualizações que precisam da sua atenção.",
        "route": "/notifications",
        "url_name": "notifications",
        "template": "notifications/index.html",
        "icon": "fa-bell",
        "accent": "#FFBC0D",
        "accent_soft": "#FFF3C4",
        "accent_text": "#2D2D2D",
        "stylesheet": "/static/css/modules/notifications.css",
        "script": "/static/js/modules/notifications.js",
        "navigation": "utility",
        "roles": (),
    },
}


def get_module(key):
    module = MODULES.get(key)
    return deepcopy(module) if module else None


def module_for_url_name(url_name):
    for module in MODULES.values():
        if module["url_name"] == url_name:
            return deepcopy(module)
    return get_module("calendar")


def modules_for_user(user, navigation=None):
    role = getattr(user, "role", "")
    visible = []
    for module in MODULES.values():
        roles = module.get("roles") or ()
        if roles and role not in roles:
            continue
        if navigation and module.get("navigation") != navigation:
            continue
        visible.append(deepcopy(module))
    return visible
