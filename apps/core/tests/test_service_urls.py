from django.test import SimpleTestCase
from django.urls import resolve

from apps.core.service_views import ServiceEmployeeOfMonthView


class ServiceCompatibilityUrlTests(SimpleTestCase):
    def test_employee_of_month_service_url_is_available(self):
        match = resolve("/api/dashboard/service/employee-of-month")

        self.assertIs(
            match.func.view_class,
            ServiceEmployeeOfMonthView,
        )
