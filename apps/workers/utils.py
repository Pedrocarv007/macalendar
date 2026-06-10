"""
Utilitários do módulo workers — reutilizáveis por outros módulos.
"""
from django.conf import settings
from django.core.cache import cache


def sso_avatar_url_for_email(email: str) -> str | None:
    """
    Devolve o URL do avatar SSO para o email indicado, ou None se não existir.

    Usa a cache de Django (5 minutos) para evitar uma query à BD SSO em cada
    renderização do base.html (foto do utilizador logado no topo da página).
    """
    if not email:
        return None

    key = f'sso_avatar:{email.lower()}'
    cached = cache.get(key)
    if cached is not None:
        # String vazia == "já verificámos, não há avatar"
        return cached or None

    # Import local para evitar import circular workers → accounts → workers
    from .models import Worker

    worker = Worker.objects.filter(email__iexact=email).only('avatar').first()
    url = ''
    if worker and worker.avatar:
        base = settings.SSO_MEDIA_BASE_URL.rstrip('/')
        url = f"{base}/{worker.avatar.lstrip('/')}"

    cache.set(key, url, 300)
    return url or None
