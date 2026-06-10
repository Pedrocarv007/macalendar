from django.urls import path
from .views import (
    DashboardStatsView, RecentEventsView, ActivityFeedView,
    ServiceEmployeeOfMonthView,
)

urlpatterns = [
    path('stats', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('events/upcoming', RecentEventsView.as_view(), name='dashboard-events'),
    path('activities', ActivityFeedView.as_view(), name='dashboard-activities'),
    path('service/employee-of-month',
         ServiceEmployeeOfMonthView.as_view(),
         name='service-employee-of-month'),
]
