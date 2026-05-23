import os
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsRHOrAbove, can_manage_restaurant
from apps.core.models import ActivityLog
from apps.workers.models import SSORestaurant
from .models import Restaurant
from .serializers import RestaurantSerializer


def _get_local_for_sso(sso):
    """
    Devolve (ou cria) o registo local para um SSORestaurant.
    Tenta primeiro por sso_id, depois por code (para registos
    criados antes de sso_id existir).
    """
    obj = Restaurant.objects.filter(sso_id=sso.id).first()

    if obj is None and sso.code:
        # Registo antigo sem sso_id mas com o mesmo code
        obj = Restaurant.objects.filter(code=sso.code, sso_id__isnull=True).first()
        if obj:
            obj.sso_id = sso.id
            obj.save(update_fields=['sso_id'])

    if obj is None:
        obj = Restaurant.objects.create(
            sso_id=sso.id,
            name=sso.name,
            code=sso.code or None,
        )
        return obj

    # Mantém nome e code sincronizados com o SSO
    changed = []
    if obj.name != sso.name:
        obj.name = sso.name
        changed.append('name')
    if sso.code and obj.code != sso.code:
        obj.code = sso.code
        changed.append('code')
    if changed:
        obj.save(update_fields=changed)
    return obj


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        """
        Fonte de verdade: SSO.
        Para cada restaurante SSO garante que existe um registo local
        (para FKs de Employee, CalendarEvent, etc.) e devolve os locais.
        """
        user = self.request.user

        # Determina quais restaurantes SSO este utilizador pode ver
        sso_qs = SSORestaurant.objects.filter(is_active=True)
        if not user.role in settings.SUPER_ROLES:
            # Não-admin: só vê o seu próprio restaurante (via code/sso_id)
            if user.restaurant_id:
                local = Restaurant.objects.filter(id=user.restaurant_id).first()
                if local and local.sso_id:
                    sso_qs = sso_qs.filter(id=local.sso_id)
                elif local and local.code:
                    sso_qs = sso_qs.filter(code=local.code)
                else:
                    return Restaurant.objects.none()
            else:
                return Restaurant.objects.none()

        # Garante registo local para cada SSO restaurant e recolhe os IDs locais
        local_ids = [_get_local_for_sso(sso).id for sso in sso_qs]
        return Restaurant.objects.filter(id__in=local_ids, is_active=True)

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsRHOrAbove()]
        if self.action in ['update', 'partial_update']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        restaurant = serializer.save()
        ActivityLog.log('restaurant_created', f'Restaurante "{restaurant.name}" criado', self.request.user)

    def perform_update(self, serializer):
        user = self.request.user
        restaurant = self.get_object()
        if not can_manage_restaurant(user) and user.restaurant_id != restaurant.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Sem permissão para editar este restaurante.")
        serializer.save()
        ActivityLog.log('restaurant_updated', f'Restaurante "{restaurant.name}" actualizado', user)

    def perform_destroy(self, instance):
        if not can_manage_restaurant(self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Sem permissão para remover restaurantes.")
        instance.is_active = False
        instance.save()
        ActivityLog.log('restaurant_deleted', f'Restaurante "{instance.name}" removido', self.request.user)

    @action(detail=True, methods=['post'], url_path='photo')
    def upload_photo(self, request, pk=None):
        restaurant = self.get_object()
        if 'photo' not in request.FILES:
            return Response({'error': 'Ficheiro não fornecido.'}, status=status.HTTP_400_BAD_REQUEST)

        photo = request.FILES['photo']
        ext = os.path.splitext(photo.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            return Response({'error': 'Formato não suportado.'}, status=status.HTTP_400_BAD_REQUEST)

        import time
        filename = f"restaurant_{restaurant.id}_{int(time.time())}{ext}"
        upload_dir = settings.MEDIA_ROOT / 'photos' / 'restaurants'
        upload_dir.mkdir(parents=True, exist_ok=True)

        with open(upload_dir / filename, 'wb+') as f:
            for chunk in photo.chunks():
                f.write(chunk)

        restaurant.photo_filename = filename
        restaurant.save(update_fields=['photo_filename'])
        return Response({'photo_url': restaurant.photo_url})
