from django.urls import path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import views as auth_views
from django.conf import settings
from apps.accounts.views import SSOCallbackView


def splash(request):
    return render(request, 'splash.html')


@login_required
def dashboard(request):
    return render(request, 'dashboard/index.html')


@login_required
def calendar_page(request):
    return render(request, 'calendar/index.html')


@login_required
def restaurants_page(request):
    return render(request, 'restaurants/index.html')


@login_required
def documents_page(request):
    return render(request, 'documents/index.html')


@login_required
def notifications_page(request):
    return render(request, 'notifications/index.html')


@login_required
def tickets_page(request):
    return render(request, 'tickets/index.html')


@login_required
def profile_page(request):
    return render(request, 'auth/profile.html')


urlpatterns = [
    path('', lambda req: redirect('/dashboard'), name='index'),
    path('splash', splash, name='splash'),
    path('dashboard', dashboard, name='dashboard'),
    path('calendar', calendar_page, name='calendar'),
    path('restaurants', restaurants_page, name='restaurants'),
    path('documents', documents_page, name='documents'),
    path('notifications', notifications_page, name='notifications'),
    path('tickets', tickets_page, name='tickets'),
    path('profile', profile_page, name='profile'),
    path('auth/login', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('auth/logout', auth_views.LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
    path('auth/sso/callback', SSOCallbackView.as_view(), name='sso-callback'),
]
