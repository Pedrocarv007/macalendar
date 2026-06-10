from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from apps.accounts.permissions import IsServiceClient


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


class ServiceEmployeeOfMonthView(APIView):
    """
    Funcionário do mês corrente para um restaurante. Devolve a imagem PNG
    gerada pela template 'employee_month' (`apps/documents/generators.py`),
    procurando o Document mais recente do mês/ano corrente para o restaurante.

    Autenticação: header X-Service-Key: <SERVICE_API_KEY>
    Query params: restaurant_id (obrigatório)
    """
    permission_classes = [IsServiceClient]
    authentication_classes = []

    def get(self, request):
        from apps.documents.models import Document

        restaurant_id = request.query_params.get('restaurant_id')
        if not restaurant_id:
            return Response({'detail': 'restaurant_id em falta'}, status=400)
        try:
            restaurant_id = int(restaurant_id)
        except (TypeError, ValueError):
            return Response({'detail': 'restaurant_id inválido'}, status=400)

        now = timezone.now()
        doc = (
            Document.objects
            .filter(
                document_type='employee_month',
                restaurant_id=restaurant_id,
                created_at__year=now.year,
                created_at__month=now.month,
                status='generated',
            )
            .select_related('employee')  # 'worker' lives in the sso DB — select_related would JOIN cross-DB; lazy access is safe for .first()
            .order_by('-created_at')
            .first()
        )

        if not doc:
            return Response({'employee_of_month': None})

        person = doc.worker or doc.employee
        name = getattr(person, 'name', None) or doc.title.split('—')[-1].strip()
        image_url = request.build_absolute_uri(
            f'/media/documents/generated/{doc.filename}'
        ) if doc.filename else None

        return Response({
            'employee_of_month': {
                'name': name,
                'month': now.strftime('%Y-%m'),
                'restaurant_id': restaurant_id,
                'image_url': image_url,
            }
        })
