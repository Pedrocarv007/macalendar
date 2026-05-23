from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import Employee
        from apps.workers.models import Worker
        from apps.restaurants.models import Restaurant
        from apps.calendar_events.models import CalendarEvent
        from apps.documents.models import Document

        user = request.user
        is_super = user.role in settings.SUPER_ROLES
        rid = user.restaurant_id

        def scoped(qs, field='restaurant_id'):
            return qs if is_super else qs.filter(**{field: rid})

        employees = scoped(Employee.objects.filter(is_active=True)).count()
        workers = scoped(Worker.objects.filter(is_active=True)).count()
        restaurants = Restaurant.objects.filter(is_active=True).count() if is_super else 1
        documents = scoped(Document.objects.all()).count()

        now = timezone.now()
        upcoming_events = scoped(
            CalendarEvent.objects.filter(start_date__gte=now, start_date__lte=now + timezone.timedelta(days=7))
        ).count()

        # Birthdays this month
        today = timezone.now().date()
        birthdays_month = scoped(
            Employee.objects.filter(is_active=True, birth_date__month=today.month)
        ).count()

        return Response({
            'employees': employees,
            'workers': workers,
            'restaurants': restaurants,
            'documents': documents,
            'upcoming_events': upcoming_events,
            'birthdays_this_month': birthdays_month,
        })


class RecentEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.calendar_events.models import CalendarEvent
        from apps.calendar_events.serializers import CalendarEventSerializer

        user = request.user
        now = timezone.now()

        qs = CalendarEvent.objects.filter(
            start_date__gte=now,
            start_date__lte=now + timezone.timedelta(days=7),
        ).select_related('restaurant', 'created_by')

        if user.role not in settings.SUPER_ROLES:
            qs = qs.filter(
                restaurant_id=user.restaurant_id
            ) | qs.filter(restaurant__isnull=True)

        qs = qs.order_by('start_date').distinct()[:10]
        return Response(CalendarEventSerializer(qs, many=True).data)


class ActivityFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.core.models import ActivityLog
        from apps.core.serializers import ActivityLogSerializer

        user = request.user
        qs = ActivityLog.objects.select_related('user', 'restaurant')

        if user.role not in settings.SUPER_ROLES:
            qs = qs.filter(restaurant_id=user.restaurant_id)

        qs = qs.order_by('-created_at')[:50]
        return Response(ActivityLogSerializer(qs, many=True).data)
