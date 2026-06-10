from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, ServiceNotificationsView

router = DefaultRouter(trailing_slash=False)
router.register('', NotificationViewSet, basename='notifications')

urlpatterns = [
    # Endpoint sistema-para-sistema (X-Service-Key) — declarado ANTES do router
    # para não ser engolido por uma rota dinâmica do viewset.
    path('service/', ServiceNotificationsView.as_view(), name='service-notifications'),
    path('', include(router.urls)),
]
