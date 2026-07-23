"""
Employee CRUD views.
"""
import os
import logging
import threading
from PIL import Image, UnidentifiedImageError
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import EmployeeListSerializer, EmployeeDetailSerializer, EmployeeCreateSerializer
from .permissions import (
    IsRH, CanManageEmployees, SameRestaurantOrAbove, is_super_role,
    can_manage_employee, can_manage_employees, can_manage_role, canonical_role,
    GLOBAL_MANAGEMENT_ROLES,
)
from apps.core.models import ActivityLog
from apps.core.utils import get_client_ip, success_response

logger = logging.getLogger(__name__)
Employee = get_user_model()

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

# Mapeamento de perfis do SSO para perfis do MC
_SSO_ROLE_MAP = {
    'admin':          'admin',
    'rh':             'rh',
    'marketing':      'marketing',
    'administrativa': 'administrativa',
    'manager':         'manager',
    'sub_manager':     'sub_manager',
    'shift_manager':   'shift_manager',
    'treinador':       'treinador',
    'coucher':         'coucher',
    'rp':              'rp',
    'gerente_loja':    'manager',
    'sub_gerente':     'sub_manager',
    'gerente_turno':   'shift_manager',
    'funcionario':    'employee',
    'employee':       'employee',
    'colaborador':    'employee',
}


def _sync_employee_from_sso(sso_user):
    """
    Garante que existe um Employee local correspondente ao SSOUser.
    Cria se não existir; actualiza campos se tiverem mudado no SSO.
    Devolve o Employee local.
    """
    from apps.restaurants.models import Restaurant

    # Resolve o restaurante local via sso_id
    local_restaurant = None
    if sso_user.restaurant_id:
        local_restaurant = Restaurant.objects.filter(sso_id=sso_user.restaurant_id).first()

    mac_role = _SSO_ROLE_MAP.get(sso_user.role, 'employee')
    sso_name = sso_user.name

    try:
        emp = Employee.objects.get(email__iexact=sso_user.email)
    except Employee.DoesNotExist:
        emp = Employee(email=sso_user.email.lower())
        emp.set_unusable_password()

    changed = []
    if emp.name != sso_name:
        emp.name = sso_name
        changed.append('name')
    if emp.role != mac_role:
        emp.role = mac_role
        changed.append('role')
    if emp.is_active != sso_user.is_active:
        emp.is_active = sso_user.is_active
        changed.append('is_active')
    # Também limpa uma associação antiga quando o SSO já não tem restaurante.
    # Se o SSO aponta para um ID desconhecido, mantém o valor local até o
    # catálogo de restaurantes ser corrigido, evitando uma perda acidental.
    restaurant_was_resolved = not sso_user.restaurant_id or local_restaurant is not None
    expected_restaurant_id = local_restaurant.id if local_restaurant else None
    if restaurant_was_resolved and emp.restaurant_id != expected_restaurant_id:
        emp.restaurant = local_restaurant
        changed.append('restaurant')
    if sso_user.phone and emp.phone != sso_user.phone:
        emp.phone = sso_user.phone
        changed.append('phone')
    if sso_user.birth_date and emp.birth_date != sso_user.birth_date:
        emp.birth_date = sso_user.birth_date
        changed.append('birth_date')
    if sso_user.hire_date and emp.hire_date != sso_user.hire_date:
        emp.hire_date = sso_user.hire_date
        changed.append('hire_date')

    if emp.pk is None:
        emp.save()
        logger.info('Employee criado via SSO sync: %s', emp.email)
    elif changed:
        emp.save(update_fields=changed)

    return emp


class EmployeeListCreateView(APIView):
    """
    GET  /api/employees/   — list employees (fonte: SSO Usuários)
    POST /api/employees/   — create employee (RH or above)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.workers.models import SSOUser

        user = request.user
        params = request.query_params

        # Lê utilizadores do SSO como fonte de verdade
        sso_qs = SSOUser.objects.filter(is_active=True)

        # Se não for super role, restringe ao restaurante do utilizador
        if not is_super_role(user):
            if user.restaurant and user.restaurant.sso_id:
                sso_qs = sso_qs.filter(restaurant_id=user.restaurant.sso_id)
            else:
                sso_qs = SSOUser.objects.none()

        # Filtros opcionais
        search = params.get('search', '').strip()
        if search:
            sso_qs = sso_qs.filter(
                first_name__icontains=search
            ) | sso_qs.filter(
                last_name__icontains=search
            ) | sso_qs.filter(
                email__icontains=search
            )

        restaurant_filter = params.get('restaurant', '')
        if restaurant_filter and is_super_role(user):
            from apps.restaurants.models import Restaurant
            local = Restaurant.objects.filter(id=restaurant_filter).first()
            if local and local.sso_id:
                sso_qs = sso_qs.filter(restaurant_id=local.sso_id)

        # Sincroniza SSO → local e recolhe IDs locais
        local_ids = [_sync_employee_from_sso(u).pk for u in sso_qs]

        qs = Employee.objects.select_related('restaurant').filter(
            pk__in=local_ids
        ).order_by('name')

        role_filter = params.get('role', '')
        if role_filter:
            qs = qs.filter(role=role_filter)

        serializer = EmployeeListSerializer(qs, many=True, context={'request': request})
        return Response(success_response(
            data=serializer.data,
            count=len(serializer.data),
        ))

    def post(self, request):
        if not can_manage_employees(request.user):
            return Response(
                {'success': False, 'error': 'Sem permissão.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EmployeeCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_role = serializer.validated_data.get('role', 'employee')
        target_restaurant = serializer.validated_data.get('restaurant')
        actor_role = canonical_role(request.user)
        save_kwargs = {}
        if actor_role not in GLOBAL_MANAGEMENT_ROLES:
            if not can_manage_role(request.user, target_role):
                return Response({'success': False, 'error': 'Sem permissão.'}, status=403)
            if not request.user.restaurant_id:
                return Response({'success': False, 'error': 'O restaurante é obrigatório.'}, status=403)
            if target_restaurant and target_restaurant.id != request.user.restaurant_id:
                return Response({'success': False, 'error': 'Sem permissão.'}, status=403)
            save_kwargs['restaurant'] = request.user.restaurant

        employee = serializer.save(**save_kwargs)
        ActivityLog.log(
            activity_type='create',
            description=f'{request.user.name} criou o utilizador {employee.name}.',
            user=request.user,
            restaurant=employee.restaurant,
            target_id=employee.id,
            target_type='Employee',
        )
        return Response(
            success_response(
                data=EmployeeDetailSerializer(employee, context={'request': request}).data,
                message='Utilizador criado.',
            ),
            status=status.HTTP_201_CREATED,
        )


class EmployeeDetailView(APIView):
    """
    GET    /api/employees/{id}/   — retrieve
    PUT    /api/employees/{id}/   — update (managers+)
    DELETE /api/employees/{id}/   — deactivate (RH+)
    """
    permission_classes = [IsAuthenticated, SameRestaurantOrAbove]

    def _get_employee(self, pk):
        try:
            return Employee.objects.select_related('restaurant').get(pk=pk)
        except Employee.DoesNotExist:
            return None

    def get(self, request, pk):
        employee = self._get_employee(pk)
        if not employee:
            return Response({'success': False, 'error': 'Utilizador não encontrado.'}, status=404)
        self.check_object_permissions(request, employee)
        serializer = EmployeeDetailSerializer(employee, context={'request': request})
        return Response(success_response(data=serializer.data))

    def put(self, request, pk):
        employee = self._get_employee(pk)
        if not employee:
            return Response({'success': False, 'error': 'Utilizador não encontrado.'}, status=404)
        self.check_object_permissions(request, employee)
        if not can_manage_employee(request.user, employee):
            return Response({'success': False, 'error': 'Sem permissão.'}, status=403)

        serializer = EmployeeDetailSerializer(
            employee, data=request.data, partial=True, context={'request': request}
        )
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        if canonical_role(request.user) not in GLOBAL_MANAGEMENT_ROLES:
            target_role = serializer.validated_data.get('role', employee.role)
            target_restaurant = serializer.validated_data.get('restaurant', employee.restaurant)
            if not can_manage_role(request.user, target_role):
                return Response({'success': False, 'error': 'Sem permissão.'}, status=403)
            if not target_restaurant or target_restaurant.id != request.user.restaurant_id:
                return Response({'success': False, 'error': 'Sem permissão.'}, status=403)

        serializer.save()
        ActivityLog.log(
            activity_type='update',
            description=f'{request.user.name} atualizou o utilizador {employee.name}.',
            user=request.user,
            target_id=employee.id,
            target_type='Employee',
        )
        return Response(success_response(
            data=EmployeeDetailSerializer(employee, context={'request': request}).data,
            message='Utilizador atualizado.',
        ))

    def patch(self, request, pk):
        return self.put(request, pk)

    def delete(self, request, pk):
        if request.user.role not in ['admin', 'rh']:
            return Response({'success': False, 'error': 'Sem permissão.'}, status=403)

        employee = self._get_employee(pk)
        if not employee:
            return Response({'success': False, 'error': 'Utilizador não encontrado.'}, status=404)

        employee.is_active = False
        employee.save(update_fields=['is_active'])
        ActivityLog.log(
            activity_type='delete',
            description=f"{request.user.name} deactivated employee {employee.name}.",
            user=request.user,
            target_id=employee.id,
            target_type='Employee',
        )
        return Response(success_response(message='Utilizador desativado.'))


class EmployeePhotoView(APIView):
    """
    POST /api/employees/{id}/photo/  — upload employee photo
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            employee = Employee.objects.get(pk=pk)
        except Employee.DoesNotExist:
            return Response({'success': False, 'error': 'Utilizador não encontrado.'}, status=404)

        # Only the employee themselves or a manager (gerente+) can upload
        if request.user.pk != employee.pk and not can_manage_employee(request.user, employee):
            return Response({'success': False, 'error': 'Sem permissão.'}, status=403)

        photo_file = request.FILES.get('photo')
        if not photo_file:
            return Response({'success': False, 'error': 'Selecione uma fotografia.'}, status=400)

        ext, photo_error = _validated_photo_extension(photo_file)
        if photo_error:
            return Response({'success': False, 'error': photo_error}, status=400)

        filename = f"employee_{employee.pk}{ext}"
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'photos', 'employees')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, 'wb') as f:
            for chunk in photo_file.chunks():
                f.write(chunk)

        employee.photo_filename = filename
        employee.save(update_fields=['photo_filename'])

        # Limpar cache do avatar ao vivo (TTL 5 min em sso_avatar_url_for_email)
        if employee.email:
            cache.delete(f'sso_avatar:{employee.email.lower()}')

        # Regenerar cartões de aniversário (mês atual + futuros) em background
        emp_id = employee.pk

        def _regen():
            from apps.calendar_events.birthday_service import BirthdayService
            BirthdayService(user=request.user).regenerate_cards_for_person(
                employee_id=emp_id
            )

        threading.Thread(target=_regen, daemon=True).start()

        return Response(success_response(
            data={'photo_url': employee.photo_url},
            message='Fotografia atualizada.',
        ))
