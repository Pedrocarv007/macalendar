import os
import time
import uuid
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.models import ActivityLog
from apps.accounts.permissions import IsServiceClient
from .models import CalendarEvent
from .serializers import CalendarEventSerializer


class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        qs = CalendarEvent.objects.select_related('restaurant', 'created_by', 'employee')

        # Date filters
        start = params.get('start')
        end = params.get('end')
        if start:
            qs = qs.filter(start_date__gte=start)
        if end:
            qs = qs.filter(start_date__lte=end)

        # Event type filter
        event_type = params.get('event_type')
        if event_type:
            qs = qs.filter(event_type=event_type)

        # Scope: super roles can filter by restaurant; others see only their restaurant + global
        if user.role in settings.SUPER_ROLES:
            restaurant_id = params.get('restaurant_id')
            if restaurant_id:
                qs = qs.filter(restaurant_id=restaurant_id)
        else:
            qs = qs.filter(
                restaurant_id__in=[user.restaurant_id] if user.restaurant_id else []
            ) | qs.filter(restaurant__isnull=True)

        return qs.order_by('start_date')

    def perform_create(self, serializer):
        user = self.request.user
        # Non-super-roles can only create events for their own restaurant
        extra = {}
        if user.role not in settings.SUPER_ROLES:
            extra['restaurant'] = user.restaurant
        event = serializer.save(created_by=user, **extra)
        ActivityLog.log('event_created', f'Evento "{event.title}" criado', user,
                        restaurant=event.restaurant)

    def perform_update(self, serializer):
        event = serializer.save()
        ActivityLog.log('event_updated', f'Evento "{event.title}" actualizado', self.request.user)

    def perform_destroy(self, instance):
        ActivityLog.log('event_deleted', f'Evento "{instance.title}" eliminado', self.request.user)
        instance.delete()

    @action(detail=True, methods=['put'], url_path='mark-posted')
    def mark_posted(self, request, pk=None):
        event = self.get_object()
        event.is_posted = True
        event.posted_at = timezone.now()
        event.save(update_fields=['is_posted', 'posted_at'])
        return Response({'status': 'posted', 'posted_at': event.posted_at})

    @action(detail=False, methods=['get'], url_path='birthdays')
    def birthdays(self, request):
        from apps.workers.models import Worker

        month = int(request.query_params.get('month', timezone.now().month))

        user = request.user
        if user.role in settings.SUPER_ROLES:
            restaurant_id = request.query_params.get('restaurant_id')
        else:
            restaurant_id = user.restaurant_id

        qs = Worker.objects.filter(is_active=True, birth_date__month=month)
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)

        results = [
            {
                'type': 'colaborador', 'id': wkr.id, 'name': wkr.name,
                'birth_date': str(wkr.birth_date), 'photo_url': wkr.photo_url,
                'days_until': wkr.days_until_birthday,
            }
            for wkr in qs
        ]
        results.sort(key=lambda x: x.get('days_until') or 999)
        return Response(results)

    @action(detail=True, methods=['post'], url_path='photo')
    def upload_photo(self, request, pk=None):
        event = self.get_object()
        photo = request.FILES.get('photo')
        if not photo:
            return Response({'error': 'Foto não fornecida.'}, status=status.HTTP_400_BAD_REQUEST)
        ext = os.path.splitext(photo.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            return Response({'error': 'Extensão inválida.'}, status=status.HTTP_400_BAD_REQUEST)
        filename = f"event_{event.id}_{uuid.uuid4().hex[:8]}{ext}"
        upload_dir = settings.MEDIA_ROOT / 'events' / 'photos'
        upload_dir.mkdir(parents=True, exist_ok=True)
        full_path = upload_dir / filename
        with open(full_path, 'wb') as f:
            for chunk in photo.chunks():
                f.write(chunk)
        event.photo_path = f"/media/events/photos/{filename}"
        event.save(update_fields=['photo_path'])
        return Response({'photo_url': event.photo_path})

    @action(detail=False, methods=['post'], url_path='generate-mystery')
    def generate_mystery(self, request):
        from .mystery_service import MysteryService
        data = request.data
        restaurant_id = data.get('restaurant_id') or request.user.restaurant_id
        month = data.get('month')
        year = data.get('year')
        if not month or not year:
            return Response({'error': 'month e year são obrigatórios.'}, status=400)
        if not restaurant_id:
            return Response({'error': 'restaurant_id é obrigatório (ou associe o utilizador a um restaurante).'}, status=400)

        service = MysteryService(request.user)
        result = service.generate_for_month(restaurant_id, int(month), int(year))
        return Response(result)


class ServiceCalendarEventsView(APIView):
    """
    Endpoint sistema-para-sistema para consultar eventos do calendário.
    Autenticação: header  X-Service-Key: <SERVICE_API_KEY>
    Query params: restaurant_id, start (YYYY-MM-DD), end (YYYY-MM-DD), event_type
    """
    permission_classes = [IsServiceClient]
    authentication_classes = []  # sem autenticação JWT — usa apenas a API key

    def get(self, request):
        params = request.query_params
        qs = CalendarEvent.objects.select_related('restaurant', 'created_by')

        restaurant_id = params.get('restaurant_id')
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)

        start = params.get('start')
        end = params.get('end')
        if start:
            qs = qs.filter(start_date__gte=start)
        if end:
            qs = qs.filter(start_date__lte=end)

        event_type = params.get('event_type')
        if event_type:
            qs = qs.filter(event_type=event_type)

        serializer = CalendarEventSerializer(qs.order_by('start_date'), many=True)
        return Response({'count': qs.count(), 'results': serializer.data})


class ServiceBirthdaysView(APIView):
    """
    Aniversários do mês para um restaurante, com a imagem gerada pela template
    'birthday'. Se ainda não existir Document para esse colaborador+mês+restaurante, gera agora.

    Autenticação: header X-Service-Key: <SERVICE_API_KEY>
    Query params: restaurant_id (obrigatório), month (1-12, default = mês corrente)
    """
    permission_classes = [IsServiceClient]
    authentication_classes = []

    def get(self, request):
        from apps.workers.models import Worker
        from apps.documents.models import Document
        from apps.documents.generators import DocumentGenerator
        from apps.accounts.models import Employee

        restaurant_id = request.query_params.get('restaurant_id')
        if not restaurant_id:
            return Response({'detail': 'restaurant_id em falta'}, status=400)
        try:
            restaurant_id = int(restaurant_id)
        except (TypeError, ValueError):
            return Response({'detail': 'restaurant_id inválido'}, status=400)

        now = timezone.now()
        try:
            month = int(request.query_params.get('month', now.month))
        except (TypeError, ValueError):
            month = now.month
        year = now.year

        workers = list(Worker.objects.filter(
            is_active=True,
            birth_date__month=month,
            restaurant_id=restaurant_id,
        ))

        system_user = Employee.objects.filter(role='admin', is_active=True).first()

        generator = DocumentGenerator()
        results = []
        for wkr in workers:
            existing = (
                Document.objects.filter(
                    document_type='birthday',
                    worker_id=wkr.id,
                    restaurant_id=restaurant_id,
                    created_at__year=year,
                    created_at__month=month,
                    status='generated',
                )
                .order_by('-created_at')
                .first()
            )
            if existing and existing.filename:
                image_url = request.build_absolute_uri(
                    f'/media/documents/generated/{existing.filename}'
                )
            else:
                gen = generator.generate(
                    'birthday',
                    {'worker_id': wkr.id, 'restaurant_id': restaurant_id, 'name': wkr.name},
                    system_user,
                )
                if 'error' in gen:
                    image_url = None
                else:
                    image_url = request.build_absolute_uri(gen['file_url'])

            results.append({
                'id': wkr.id,
                'name': wkr.name,
                'birth_date': str(wkr.birth_date) if wkr.birth_date else None,
                'age': getattr(wkr, 'age', None),
                'days_until': getattr(wkr, 'days_until_birthday', None),
                'image_url': image_url,
            })

        results.sort(key=lambda x: x.get('days_until') or 999)
        return Response({'count': len(results), 'birthdays': results})
