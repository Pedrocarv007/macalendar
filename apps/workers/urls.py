from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkerViewSet, SSORestaurantViewSet

router = DefaultRouter()
router.register('restaurants', SSORestaurantViewSet, basename='sso-restaurants')
router.register('', WorkerViewSet, basename='workers')

urlpatterns = [path('', include(router.urls))]
