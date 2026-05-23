"""
Main URL configuration for Mac Calendar.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Redirect default Django login URL to our login page
    path('accounts/login/', RedirectView.as_view(url='/auth/login', permanent=False)),
    path('accounts/logout/', RedirectView.as_view(url='/auth/logout', permanent=False)),

    # Auth token refresh
    path('api/auth/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),

    # App API routes
    path('api/auth/', include('apps.accounts.urls')),
    path('api/employees/', include('apps.accounts.urls_employees')),
    path('api/restaurants/', include('apps.restaurants.urls')),
    path('api/calendar/', include('apps.calendar_events.urls')),
    path('api/documents/', include('apps.documents.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/tickets/', include('apps.tickets.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/workers/', include('apps.workers.urls')),

    # Web / Template routes
    path('', include('apps.dashboard.web_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
