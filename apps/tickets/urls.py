from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet

router = DefaultRouter(trailing_slash=False)
router.register('', TicketViewSet, basename='tickets')

urlpatterns = [path('', include(router.urls))]
