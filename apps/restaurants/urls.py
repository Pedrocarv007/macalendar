from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RestaurantViewSet

router = DefaultRouter(trailing_slash=False)
router.register('', RestaurantViewSet, basename='restaurants')

urlpatterns = [
    path('', include(router.urls)),
]
