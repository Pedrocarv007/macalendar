"""
Authentication backend for TheCarV SSO.
"""
import logging
import requests
from django.conf import settings
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

Employee = get_user_model()


class TheCarVSSOBackend:
    """
    Authenticates a user against the TheCarV SSO service.

    Flow:
      1. POST credentials to THECARV_SSO_URL
      2. Receive user profile JSON
      3. Get or create local Employee record matching the SSO email
      4. Return the Employee instance on success, None on failure
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or not password:
            return None

        sso_url = getattr(settings, 'THECARV_SSO_URL', None)
        if not sso_url:
            return None

        try:
            resp = requests.post(
                sso_url,
                json={'email': email, 'password': password},
                timeout=10,
            )
        except requests.RequestException as exc:
            logger.warning("SSO request failed: %s", exc)
            return None

        if resp.status_code != 200:
            return None

        try:
            data = resp.json()
        except ValueError:
            return None

        sso_email = data.get('email') or email
        if not sso_email:
            return None

        try:
            user = Employee.objects.get(email__iexact=sso_email)
        except Employee.DoesNotExist:
            # Primeira autenticação via SSO — cria o registo local automaticamente
            name = data.get('name') or sso_email.split('@')[0]
            role = data.get('role') or 'employee'
            user = Employee(
                email=sso_email,
                name=name,
                role=role,
                is_active=True,
            )
            user.set_unusable_password()
            user.save()
            logger.info('Employee criado automaticamente via SSO: %s', sso_email)

        if not user.is_active:
            return None

        # Actualiza nome e role se o SSO devolver dados diferentes
        changed = []
        sso_name = data.get('name')
        sso_role = data.get('role')
        if sso_name and user.name != sso_name:
            user.name = sso_name
            changed.append('name')
        if sso_role and user.role != sso_role:
            user.role = sso_role
            changed.append('role')
        if changed:
            user.save(update_fields=changed)

        return user

    def get_user(self, user_id):
        try:
            return Employee.objects.get(pk=user_id)
        except Employee.DoesNotExist:
            return None
