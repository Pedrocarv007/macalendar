"""
Auth views: login, logout, profile, SSO.
"""
import logging
import jwt as pyjwt
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.views import View
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    LoginSerializer, EmployeeDetailSerializer, ProfileUpdateSerializer,
)
from apps.core.models import ActivityLog
from apps.core.utils import get_client_ip, success_response

logger = logging.getLogger(__name__)
Employee = get_user_model()


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class LoginView(APIView):
    """
    POST /api/auth/login
    Accepts email + password, returns JWT tokens.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, email=email, password=password)
        if user is None:
            # Try Django's built-in backend explicitly
            from django.contrib.auth.backends import ModelBackend
            backend = ModelBackend()
            user = backend.authenticate(request, username=email, password=password)

        if user is None or not user.is_active:
            return Response(
                {'success': False, 'error': 'Invalid credentials or account inactive.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = get_tokens_for_user(user)
        login(request, user)

        ActivityLog.log(
            activity_type='login',
            description=f"{user.name} logged in.",
            user=user,
            restaurant=user.restaurant,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        return Response(success_response(
            data={
                'tokens': tokens,
                'user': EmployeeDetailSerializer(user, context={'request': request}).data,
            },
            message='Login successful.',
        ))


class LogoutView(APIView):
    """
    POST /api/auth/logout
    Blacklists the refresh token and logs out the session.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        ActivityLog.log(
            activity_type='logout',
            description=f"{request.user.name} logged out.",
            user=request.user,
        )
        logout(request)
        return Response(success_response(message='Logged out successfully.'))


class MeView(APIView):
    """
    GET /api/auth/me
    Returns the current authenticated user's full profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = EmployeeDetailSerializer(request.user, context={'request': request})
        return Response(success_response(data=serializer.data))


class ProfileView(APIView):
    """
    PUT /api/auth/profile
    Updates the current user's own profile (limited fields).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = EmployeeDetailSerializer(request.user, context={'request': request})
        return Response(success_response(data=serializer.data))

    def put(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True, context={'request': request}
        )
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        ActivityLog.log(
            activity_type='update',
            description=f"{request.user.name} updated their profile.",
            user=request.user,
        )
        return Response(success_response(
            data=EmployeeDetailSerializer(request.user, context={'request': request}).data,
            message='Profile updated.',
        ))

    def patch(self, request):
        return self.put(request)


class SSOCallbackView(View):
    """
    GET /auth/sso/callback?sso_token=<jwt>

    Recebe o token JWT do TheCarv SSO, valida-o, faz login do utilizador
    e redireciona para o dashboard.

    O segredo de verificação é lido de THECARV_SSO_SECRET no .env.
    """

    def get(self, request):
        token = request.GET.get('sso_token', '').strip()
        if not token:
            return HttpResponseBadRequest('Token SSO em falta.')

        secret = getattr(settings, 'THECARV_SSO_SECRET', None)
        if not secret:
            logger.error('THECARV_SSO_SECRET nao configurado.')
            return HttpResponseBadRequest('Configuracao SSO incompleta.')

        try:
            payload = pyjwt.decode(token, secret, algorithms=['HS256'])
        except pyjwt.ExpiredSignatureError:
            return HttpResponseBadRequest('Token SSO expirado. Inicia sessao novamente.')
        except pyjwt.InvalidTokenError as exc:
            logger.warning('Token SSO invalido: %s', exc)
            return HttpResponseBadRequest('Token SSO invalido.')

        email = payload.get('email', '').strip().lower()
        if not email:
            return HttpResponseBadRequest('Token sem email.')

        Employee = get_user_model()
        try:
            user = Employee.objects.get(email__iexact=email)
        except Employee.DoesNotExist:
            # Cria o colaborador automaticamente se vier do SSO
            name = payload.get('name', email.split('@')[0])
            parts = name.split()
            user = Employee(
                email=email,
                name=name,
                role=payload.get('role', 'employee') or 'employee',
                is_active=True,
            )
            user.set_unusable_password()
            user.save()
            logger.info('Colaborador criado via SSO: %s', email)

        if not user.is_active:
            return HttpResponseBadRequest('Conta inativa.')

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        ActivityLog.log(
            activity_type='login',
            description=f'{user.name} autenticado via TheCarv SSO.',
            user=user,
            restaurant=user.restaurant,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        next_url = request.GET.get('next') or '/dashboard'
        return redirect(next_url)
