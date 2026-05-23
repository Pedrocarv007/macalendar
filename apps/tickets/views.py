import os
import time
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsRHOrAbove
from .models import Ticket
from .serializers import TicketSerializer


class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'rh']:
            qs = Ticket.objects.all()
        else:
            qs = Ticket.objects.filter(employee=user)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs.select_related('employee', 'restaurant').order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        screenshot = self.request.FILES.get('screenshot')
        filename = ''
        if screenshot:
            ext = os.path.splitext(screenshot.name)[1].lower()
            filename = f"ticket_{user.id}_{int(time.time())}{ext}"
            upload_dir = settings.MEDIA_ROOT / 'tickets'
            upload_dir.mkdir(parents=True, exist_ok=True)
            with open(upload_dir / filename, 'wb+') as f:
                for chunk in screenshot.chunks():
                    f.write(chunk)

        serializer.save(employee=user, restaurant=user.restaurant, screenshot_filename=filename)

    @action(detail=True, methods=['put'], url_path='status')
    def update_status(self, request, pk=None):
        if request.user.role not in ['admin', 'rh']:
            return Response({'error': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)

        ticket = self.get_object()
        new_status = request.data.get('status')
        if new_status not in dict(Ticket.STATUS_CHOICES):
            return Response({'error': 'Estado inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        ticket.status = new_status
        if new_status in ['resolved', 'closed']:
            ticket.resolved_at = timezone.now()
        ticket.save()
        return Response(TicketSerializer(ticket).data)
