from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.conf import settings

from apps.accounts.permissions import IsServiceClient
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        # Build audience filter
        if user.role in settings.SUPER_ROLES:
            qs = Notification.objects.all()
        else:
            # Employee sees notifications for their restaurant + their role
            manager_roles = ['gerente_loja', 'sub_gerente', 'gerente_turno']
            audience_filter = ['all']
            if user.role in manager_roles:
                audience_filter.append('manager')
            else:
                audience_filter.append('employee')

            qs = Notification.objects.filter(
                audience__in=audience_filter,
            ).filter(
                restaurant_id=user.restaurant_id
            ) | Notification.objects.filter(
                user=user
            ) | Notification.objects.filter(
                restaurant__isnull=True,
                audience__in=audience_filter,
            )

        # Unread filter
        unread_only = params.get('unread')
        if unread_only == 'true':
            qs = qs.filter(read_at__isnull=True)

        return qs.order_by('-created_at').distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        ids = request.data.get('ids', [])
        now = timezone.now()
        if ids:
            Notification.objects.filter(id__in=ids, user=request.user).update(read_at=now)
        else:
            # Mark all as read
            self.get_queryset().filter(read_at__isnull=True).update(read_at=now)
        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = self.get_queryset().filter(read_at__isnull=True).count()
        return Response({'count': count})


class ServiceNotificationsView(APIView):
    """
    Endpoint sistema-para-sistema com notificações ativas de um restaurante.
    Inclui notificações globais (restaurant=NULL). Limita por `limit` (default 10).

    Autenticação: header X-Service-Key: <SERVICE_API_KEY>
    Query params: restaurant_id (obrigatório), limit (default 10)
    """
    permission_classes = [IsServiceClient]
    authentication_classes = []

    def get(self, request):
        restaurant_id = request.query_params.get('restaurant_id')
        if not restaurant_id:
            return Response({'detail': 'restaurant_id em falta'}, status=400)
        try:
            restaurant_id = int(restaurant_id)
        except (TypeError, ValueError):
            return Response({'detail': 'restaurant_id inválido'}, status=400)

        try:
            limit = max(1, min(int(request.query_params.get('limit', 10)), 100))
        except (TypeError, ValueError):
            limit = 10

        qs = Notification.objects.filter(
            audience__in=['all', 'employee'],
        ).filter(
            restaurant_id=restaurant_id,
        ) | Notification.objects.filter(
            restaurant__isnull=True,
            audience__in=['all', 'employee'],
        )

        qs = qs.distinct().order_by('-created_at')[:limit]
        data = [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'category': n.category,
                'created_at': n.created_at.isoformat(),
            }
            for n in qs
        ]
        return Response({'count': len(data), 'results': data})
