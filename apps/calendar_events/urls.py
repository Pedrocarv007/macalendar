from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CalendarEventViewSet, ServiceCalendarEventsView, ServiceBirthdaysView

router = DefaultRouter(trailing_slash=False)
router.register('events', CalendarEventViewSet, basename='calendar-events')

urlpatterns = [
    path('', include(router.urls)),
    path('service/events', ServiceCalendarEventsView.as_view(), name='service-calendar-events'),
    path('service/birthdays', ServiceBirthdaysView.as_view(), name='service-birthdays'),
]
