"""
Configuração principal de endereços do MC.
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as static_serve
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.service_views import ServiceEmployeeOfMonthView


def health(_request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    # Health (container / load-balancer probe)
    path('healthz/', health, name='health'),

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
    path('api/workers/', include('apps.workers.urls')),
    path(
        'api/dashboard/service/employee-of-month',
        ServiceEmployeeOfMonthView.as_view(),
        name='service-employee-of-month',
    ),

    # Web / Template routes
    path('', include('apps.core.web_urls')),
]

if settings.DEBUG or getattr(settings, 'SERVE_SSO_MEDIA_LOCALLY', False):
    urlpatterns.insert(
        -1,
        path('sso-media/<path:path>', static_serve, {'document_root': settings.SSO_MEDIA_ROOT}),
    )

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Always serve media files (no nginx in this deployment; gunicorn is the only server)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
