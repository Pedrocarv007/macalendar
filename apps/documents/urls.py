from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet

router = DefaultRouter(trailing_slash=False)
router.register('', DocumentViewSet, basename='documents')

urlpatterns = [path('', include(router.urls))]
