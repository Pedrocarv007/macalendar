import os
import time
import uuid
import requests
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from apps.core.models import ActivityLog
from apps.accounts.permissions import IsServiceClient
from .models import CalendarEvent
from .serializers import CalendarEventSerializer
from apps.restaurants.models import Restaurant
from apps.restaurants.scope import INVENTORY_ONLY_RESTAURANT_CODE


class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        qs = CalendarEvent.objects.select_related(
            'restaurant', 'created_by', 'employee'
        ).prefetch_related('affected_restaurants').exclude(
            restaurant__code__iexact=INVENTORY_ONLY_RESTAURANT_CODE,
        ).filter(
            Q(event_metadata__suppressed=False)
            | Q(event_metadata__suppressed__isnull=True)
        )

        # Date filters
        start = params.get('start')
        end = params.get('end')
        if start:
            qs = qs.filter(
                Q(end_date__gte=start)
                | Q(end_date__isnull=True, start_date__gte=start)
            )
        if end:
            qs = qs.filter(start_date__lt=end)

        # Event type filter. Repeated params allow the legend to act as a
        # multi-select while the old single-value API remains compatible.
        event_types = params.getlist('event_type')
        if len(event_types) == 1 and ',' in event_types[0]:
            event_types = event_types[0].split(',')
        event_types = [value.strip() for value in event_types if value.strip()]
        if event_types:
            valid_types = {value for value, _label in CalendarEvent.EVENT_TYPES}
            selected_types = [value for value in event_types if value in valid_types]
            qs = qs.filter(event_type__in=selected_types) if selected_types else qs.none()

        impact_level = params.get('impact_level')
        if impact_level:
            if impact_level in {'low', 'medium', 'high'}:
                qs = qs.filter(event_metadata__impact_level=impact_level)
            else:
                qs = qs.none()

        search = params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(location__icontains=search)
            )

        # Scope: super roles can filter by restaurant; others see only their restaurant + global
        if user.role in settings.SUPER_ROLES:
            restaurant_id = params.get('restaurant_id')
            if restaurant_id:
                if not Restaurant.objects.filter(pk=restaurant_id).exists():
                    return qs.none()
                qs = qs.filter(
                    Q(restaurant_id=restaurant_id)
                    | Q(affected_restaurants__id=restaurant_id)
                    | (Q(restaurant__isnull=True) & ~Q(event_type='local_impact'))
                )
        else:
            if user.restaurant_id and not Restaurant.objects.filter(
                pk=user.restaurant_id,
            ).exists():
                return qs.none()
            scope = Q(restaurant_id=user.restaurant_id) if user.restaurant_id else Q(pk__in=[])
            scope |= Q(restaurant__isnull=True) & ~Q(event_type='local_impact')
            if user.restaurant_id:
                scope |= Q(
                    event_type='local_impact',
                    affected_restaurants__id=user.restaurant_id,
                )
            qs = qs.filter(scope)
            if getattr(self, 'action', '') in {
                'update', 'partial_update', 'destroy', 'upload_photo', 'mark_posted'
            }:
                qs = qs.filter(restaurant_id=user.restaurant_id)

        return qs.distinct().order_by('start_date')

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
        if (
            (serializer.instance.event_metadata or {}).get('external_source')
            and self.request.user.role not in settings.SUPER_ROLES
        ):
            raise PermissionDenied('Os eventos importados são geridos automaticamente.')
        event = serializer.save()
        ActivityLog.log('event_updated', f'Evento "{event.title}" actualizado', self.request.user)

    def perform_destroy(self, instance):
        metadata = dict(instance.event_metadata or {})
        is_external = bool(metadata.get('external_source'))
        if is_external and self.request.user.role not in settings.SUPER_ROLES:
            raise PermissionDenied('Os eventos importados são geridos automaticamente.')
        if is_external:
            metadata.update({
                'suppressed': True,
                'suppressed_at': timezone.now().isoformat(),
                'suppressed_by': self.request.user.pk,
            })
            instance.event_metadata = metadata
            instance.save(update_fields=['event_metadata', 'updated_at'])
            ActivityLog.log(
                'event_deleted',
                f'Evento externo "{instance.title}" removido da agenda',
                self.request.user,
            )
            return
        ActivityLog.log('event_deleted', f'Evento "{instance.title}" eliminado', self.request.user)
        instance.delete()

    @action(detail=False, methods=['get'], url_path='options')
    def options(self, request):
        return Response({
            'event_types': CalendarEvent.event_type_options(),
            'impact_levels': [
                {'value': 'low', 'label': 'Baixo'},
                {'value': 'medium', 'label': 'Médio'},
                {'value': 'high', 'label': 'Alto'},
            ],
        })

    @action(detail=False, methods=['post'], url_path='sync-external')
    def sync_external(self, request):
        if request.user.role not in settings.SUPER_ROLES:
            raise PermissionDenied('Apenas a gestão pode atualizar eventos da Internet.')
        from .external_events import sync_external_events

        try:
            result = sync_external_events()
        except requests.RequestException:
            return Response(
                {'error': 'As agendas externas não responderam. Tente novamente.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        ActivityLog.log(
            'external_events_synced',
            (
                f'Agenda de movimento atualizada: {result["created"]} novos, '
                f'{result["updated"]} atualizados'
            ),
            request.user,
        )
        return Response({
            **result,
            'sources': result.get('sources', {}),
            'message': (
                f'Análise atualizada: {result["relevant"]} eventos relevantes, '
                f'{result["created"]} novos e {result["updated"]} atualizados.'
            ),
        })

    @action(detail=True, methods=['put'], url_path='mark-posted')
    def mark_posted(self, request, pk=None):
        event = self.get_object()
        event.is_posted = True
        event.posted_at = timezone.now()
        event.save(update_fields=['is_posted', 'posted_at'])
        return Response({
            'status': 'posted',
            'posted_at': event.posted_at,
            'message': 'Evento marcado como publicado.',
        })

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
            return Response({'error': 'O mês e o ano são obrigatórios.'}, status=400)
        if not restaurant_id:
            return Response({
                'error': 'Selecione o restaurante ou associe o utilizador a um restaurante.'
            }, status=400)

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
        qs = CalendarEvent.objects.select_related(
            'restaurant', 'created_by'
        ).prefetch_related('affected_restaurants').exclude(
            restaurant__code__iexact=INVENTORY_ONLY_RESTAURANT_CODE,
        ).filter(
            Q(event_metadata__suppressed=False)
            | Q(event_metadata__suppressed__isnull=True)
        )

        sso_restaurant_id = params.get('restaurant_id')
        if sso_restaurant_id:
            try:
                sso_restaurant_id = int(sso_restaurant_id)
            except (TypeError, ValueError):
                return Response({'detail': 'restaurant_id inválido'}, status=400)
            from apps.restaurants.services import get_local_restaurant_for_sso_id

            if get_local_restaurant_for_sso_id(sso_restaurant_id) is None:
                return Response({'detail': 'Restaurante SSO não encontrado'}, status=404)
            qs = qs.filter(
                Q(restaurant__sso_id=sso_restaurant_id)
                | Q(affected_restaurants__sso_id=sso_restaurant_id)
            ).distinct()

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
        from apps.restaurants.services import get_local_restaurant_for_sso_id

        sso_restaurant_id = request.query_params.get('restaurant_id')
        if not sso_restaurant_id:
            return Response({'detail': 'restaurant_id em falta'}, status=400)
        try:
            sso_restaurant_id = int(sso_restaurant_id)
        except (TypeError, ValueError):
            return Response({'detail': 'restaurant_id inválido'}, status=400)

        restaurant = get_local_restaurant_for_sso_id(sso_restaurant_id)
        if restaurant is None:
            return Response({'detail': 'Restaurante SSO não encontrado'}, status=404)

        now = timezone.now()
        try:
            month = int(request.query_params.get('month', now.month))
        except (TypeError, ValueError):
            month = now.month
        year = now.year

        workers = list(Worker.objects.filter(
            is_active=True,
            birth_date__month=month,
            restaurant_id=sso_restaurant_id,
        ))

        system_user = Employee.objects.filter(role='admin', is_active=True).first()

        generator = DocumentGenerator()
        results = []
        for wkr in workers:
            document_key = (
                f'birthday:worker:{wkr.id}:restaurant:{sso_restaurant_id}:'
                f'year:{year}:month:{month}'
            )
            existing = (
                Document.objects.filter(
                    document_type='birthday',
                    tags=document_key,
                    restaurant_id=restaurant.id,
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
                image_error = None
            else:
                gen = generator.generate(
                    'birthday',
                    {'worker_id': wkr.id, 'restaurant_id': restaurant.id, 'name': wkr.name,
                     'event_year': year, 'document_key': document_key},
                    system_user,
                )
                if 'error' in gen:
                    image_url = None
                    image_error = gen['error']
                else:
                    image_url = request.build_absolute_uri(gen['file_url'])
                    image_error = None

            results.append({
                'id': wkr.id,
                'name': wkr.name,
                'birth_date': str(wkr.birth_date) if wkr.birth_date else None,
                'age': getattr(wkr, 'age', None),
                'days_until': getattr(wkr, 'days_until_birthday', None),
                'image_url': image_url,
                'image_status': 'disponivel' if image_url else 'indisponivel',
                'image_error': image_error,
            })

        results.sort(key=lambda x: x.get('days_until') or 999)
        return Response({'count': len(results), 'birthdays': results})
