import os
import time
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.models import ActivityLog
from .models import Worker, SSORestaurant
from .serializers import WorkerSerializer, SSORestaurantSerializer


class SSORestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista de restaurantes lida direto do SSO (para filtros no frontend)."""
    serializer_class   = SSORestaurantSerializer
    permission_classes = [IsAuthenticated]
    pagination_class   = None

    def get_queryset(self):
        return SSORestaurant.objects.filter(is_active=True)


class WorkerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Workers lidos direto do SSO (read-only no Mac Calendar).
    A gestão de workers é feita no SSO Portal.
    Upload de foto continua disponível aqui.
    """
    serializer_class   = WorkerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class   = None

    def get_queryset(self):
        user   = self.request.user
        params = self.request.query_params
        qs     = Worker.objects.filter(is_active=True)

        # Filtro por restaurante ──────────────────────────────────────────────
        restaurant_id = params.get('restaurant_id')

        if user.role in settings.SUPER_ROLES:
            # Admin/RH/Marketing: vê todos, aceita filtro opcional
            if restaurant_id:
                qs = qs.filter(restaurant_id=restaurant_id)
        elif user.restaurant_id:
            # Gerentes: filtra pelo restaurante do utilizador
            # Mapeia o restaurante do Mac Calendar para o SSO via nome
            mac_rest_name = user.restaurant.name if user.restaurant else None
            if mac_rest_name:
                sso_rest = SSORestaurant.objects.filter(
                    name__iexact=mac_rest_name
                ).first()
                if not sso_rest:
                    # Fallback: procura por nome parcial
                    sso_rest = SSORestaurant.objects.filter(
                        name__icontains=mac_rest_name.split()[0]
                    ).first()
                if sso_rest:
                    qs = qs.filter(restaurant_id=sso_rest.id)
                else:
                    return qs.none()
            else:
                return qs.none()
        else:
            return qs.none()

        # Pesquisa por nome ───────────────────────────────────────────────────
        search = params.get('search', '').strip()
        if search:
            qs = qs.filter(first_name__icontains=search) | \
                 qs.filter(last_name__icontains=search)

        return qs

    @action(detail=True, methods=['patch'], url_path='restaurant')
    def update_restaurant(self, request, pk=None):
        worker      = self.get_object()
        rest_id_raw = request.data.get('restaurant_id')
        if not rest_id_raw:
            return Response({'error': 'restaurant_id é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rest_id = int(rest_id_raw)
        except (ValueError, TypeError):
            return Response({'error': 'restaurant_id inválido.'}, status=status.HTTP_400_BAD_REQUEST)
        if not SSORestaurant.objects.filter(pk=rest_id).exists():
            return Response({'error': 'Restaurante não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        Worker.objects.using('sso').filter(pk=worker.pk).update(restaurant_id=rest_id)
        rest = SSORestaurant.objects.get(pk=rest_id)
        ActivityLog.log('worker_restaurant', f'Restaurante de "{worker.name}" alterado para "{rest.name}"', request.user)
        return Response({'restaurant_id': rest_id, 'restaurant_name': rest.name})

    @action(detail=True, methods=['post'], url_path='photo')
    def upload_photo(self, request, pk=None):
        worker = self.get_object()
        if 'photo' not in request.FILES:
            return Response({'error': 'Ficheiro não fornecido.'}, status=status.HTTP_400_BAD_REQUEST)

        photo = request.FILES['photo']
        ext   = os.path.splitext(photo.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            return Response({'error': 'Formato não suportado.'}, status=status.HTTP_400_BAD_REQUEST)

        filename   = f'worker_{worker.id}_{int(time.time())}{ext}'
        upload_dir = settings.MEDIA_ROOT / 'photos' / 'workers'
        upload_dir.mkdir(parents=True, exist_ok=True)

        with open(upload_dir / filename, 'wb+') as f:
            for chunk in photo.chunks():
                f.write(chunk)

        # Escreve o photo_filename diretamente no SSO DB
        Worker.objects.using('sso').filter(pk=worker.pk).update(photo_filename=filename)

        ActivityLog.log('worker_photo', f'Foto de "{worker.name}" atualizada', request.user)
        return Response({'photo_url': f'/media/photos/workers/{filename}'})
