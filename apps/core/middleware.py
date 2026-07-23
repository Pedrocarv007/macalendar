"""
Core middleware: security headers and session timeout.
"""
from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone
from django.http import JsonResponse
import datetime


class SecurityHeadersMiddleware:
    """
    Adds security-related HTTP headers to every response.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        # Nota: X-XSS-Protection foi deliberadamente removido — esta deprecated e
        # pode introduzir vulnerabilidades em browsers antigos (recomendacao OWASP).
        # HSTS (Strict-Transport-Security) e tratado pelo SecurityMiddleware do Django
        # via SECURE_HSTS_* nas settings de producao (inclui preload + includeSubDomains),
        # para evitar headers duplicados/conflituosos.

        return response


class SessionTimeoutMiddleware:
    """
    Enforces session timeout based on user's UserSettings.
    Defaults to 8 hours if no setting is configured.
    """
    DEFAULT_TIMEOUT_MINUTES = 480  # 8 hours

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity_key = '_session_last_activity'
            now = timezone.now()

            last_activity_str = request.session.get(last_activity_key)
            if last_activity_str:
                try:
                    last_activity = datetime.datetime.fromisoformat(last_activity_str)
                    timeout_minutes = self._get_timeout_minutes(request.user)
                    delta = now - last_activity
                    if delta.total_seconds() > timeout_minutes * 60:
                        logout(request)
                        if request.path.startswith('/api/'):
                            return JsonResponse(
                                {'error': 'A sessão terminou. Inicie sessão novamente.'},
                                status=401
                            )
                except (ValueError, TypeError):
                    pass

            request.session[last_activity_key] = now.isoformat()

        return self.get_response(request)

    def _get_timeout_minutes(self, user):
        try:
            return user.settings.session_timeout_minutes
        except Exception:
            return self.DEFAULT_TIMEOUT_MINUTES
