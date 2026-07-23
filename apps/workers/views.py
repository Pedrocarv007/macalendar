import os
import time
import threading
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import (
    GLOBAL_MANAGEMENT_ROLES,
    can_manage_employee,
    canonical_role,
    is_super_role,
)
from apps.core.models import ActivityLog
from .models import Worker, SSORestaurant
from .serializers import WorkerSerializer, SSORestaurantSerializer

PHOTO_MAX_BYTES = 5 * 1024 * 1024
PHOTO_FORMAT_EXTENSIONS = {
    'JPEG': '.jpg',
    'PNG': '.png',
    'WEBP': '.webp',
}


def _validated_photo_extension(upload):
    if getattr(upload, 'size', 0) > PHOTO_MAX_BYTES:
        return None, 'A fotografia não pode exceder 5 MB.'
    try:
        image = Image.open(upload)
        image_format = (image.format or '').upper()
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return None, 'O ficheiro não é uma imagem válida.'
    finally:
        upload.seek(0)
    extension = PHOTO_FORMAT_EXTENSIONS.get(image_format)
    if not extension:
        return None, 'Formato não suportado. Use JPG, PNG ou WebP.'
    return extension, None


class SSORestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista de restaurantes lida direto do SSO (para filtros no frontend)."""
    serializer_class   = SSORestaurantSerializer
    permission_classes = [IsAuthenticated]
    pagination_class   = None

    def get_queryset(self):
        return SSORestaurant.objects.filter(is_active=True)


class WorkerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Colaboradores lidos diretamente do SSO (apenas leitura no MC).
    A gestão de workers é feita no SSO Portal.
    Upload de foto continua disponível aqui.
    """
    serializer_class   = WorkerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class   = None

    def get_queryset(self):
        user   = self.request.user
        params = self.request.query_params
        # employee_number__isnull=False filtra apenas colaboradores operacionais
        # (Usuários é agora a tabela unificada SSO — contém também contas internas sem matrícula)
        qs     = Worker.objects.filter(is_active=True, restaurant_id__isnull=False)

        # Filtro por restaurante ──────────────────────────────────────────────
        restaurant_id = params.get('restaurant_id')

        if is_super_role(user):
            # Admin/RH/Marketing: vê todos, aceita filtro opcional
            if restaurant_id:
                qs = qs.filter(restaurant_id=restaurant_id)
        elif user.restaurant_id:
            # Gerentes: filtra pelo restaurante do utilizador
            # Mapeia o restaurante do MC para o SSO através do nome
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
        if canonical_role(request.user) not in GLOBAL_MANAGEMENT_ROLES:
            return Response({'error': 'Sem permissão para transferir colaboradores.'},
                            status=status.HTTP_403_FORBIDDEN)
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
        is_self = bool(
            request.user.email and worker.email
            and request.user.email.lower() == worker.email.lower()
        )
        if not is_self and not can_manage_employee(
            request.user, worker, sso_restaurant=True
        ):
            return Response({'error': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)
        if 'photo' not in request.FILES:
            return Response({'error': 'Ficheiro não fornecido.'}, status=status.HTTP_400_BAD_REQUEST)

        photo = request.FILES['photo']
        ext, photo_error = _validated_photo_extension(photo)
        if photo_error:
            return Response({'error': photo_error}, status=status.HTTP_400_BAD_REQUEST)

        filename   = f'worker_{worker.id}_{int(time.time())}{ext}'
        upload_dir = settings.MEDIA_ROOT / 'photos' / 'workers'
        upload_dir.mkdir(parents=True, exist_ok=True)

        with open(upload_dir / filename, 'wb+') as f:
            for chunk in photo.chunks():
                f.write(chunk)

        # Escreve o photo_filename diretamente no SSO DB
        Worker.objects.using('sso').filter(pk=worker.pk).update(photo_filename=filename)

        # Limpar cache do avatar ao vivo (TTL 5 min em sso_avatar_url_for_email)
        if worker.email:
            cache.delete(f'sso_avatar:{worker.email.lower()}')

        # Regenerar cartões de aniversário (mês atual + futuros) em background
        def _regen():
            from apps.calendar_events.birthday_service import BirthdayService
            BirthdayService(user=request.user).regenerate_cards_for_person(
                worker_id=worker.pk
            )

        threading.Thread(target=_regen, daemon=True).start()

        ActivityLog.log('worker_photo', f'Foto de "{worker.name}" atualizada', request.user)
        return Response({'photo_url': f'/media/photos/workers/{filename}'})
