"""Páginas web do MC."""

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import path

from apps.accounts.views import SSOCallbackView

from .module_registry import get_module


def splash(request):
    return render(request, 'splash.html')


@login_required
def calendar_page(request):
    return render(request, get_module('calendar')['template'])


@login_required
def documents_page(request):
    return render(request, get_module('documents')['template'])


@login_required
def notifications_page(request):
    return render(request, get_module('notifications')['template'])


def redirect_to_support(_request):
    portal = (getattr(settings, 'THECARV_SSO_PORTAL', '') or '').rstrip('/')
    return redirect(f'{portal}/portal/suporte/')


urlpatterns = [
    path('', lambda request: redirect('/calendar'), name='index'),
    path('splash', splash, name='splash'),
    path('calendar', calendar_page, name='calendar'),
    path('documents', documents_page, name='documents'),
    path('notifications', notifications_page, name='notifications'),
    path('dashboard', lambda request: redirect('/calendar'), name='legacy-dashboard'),
    path('restaurants', lambda request: redirect('/calendar'), name='legacy-restaurants'),
    path('tickets', redirect_to_support, name='legacy-support'),
    path('auth/login', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('auth/logout', auth_views.LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
    path('auth/sso/callback', SSOCallbackView.as_view(), name='sso-callback'),
]
