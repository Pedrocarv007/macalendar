"""
Employee CRUD views.
"""
import os
import logging
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import EmployeeListSerializer, EmployeeDetailSerializer, EmployeeCreateSerializer
from .permissions import (
    IsRH, CanManageEmployees, SameRestaurantOrAbove, is_super_role
)
from apps.core.models import ActivityLog
from apps.core.utils import get_client_ip, success_response

logger = logging.getLogger(__name__)
Employee = get_user_model()

# Mapeamento de roles do SSO para roles do Mac Calendar
_SSO_ROLE_MAP = {
    'admin':          'admin',
    'rh':             'rh',
    'marketing':      'marketing',
    'gerente_loja':   'gerente_loja',
    'sub_gerente':    'sub_gerente',
    'gerente_turno':  'gerente_turno',
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
    if local_restaurant and emp.restaurant_id != local_restaurant.id:
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
        if not request.user.role in ['admin', 'rh', 'gerente_loja']:
            return Response(
                {'success': False, 'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EmployeeCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee = serializer.save()
        ActivityLog.log(
            activity_type='create',
            description=f"{request.user.name} created employee {employee.name}.",
            user=request.user,
            restaurant=employee.restaurant,
            target_id=employee.id,
            target_type='Employee',
        )
        return Response(
            success_response(
                data=EmployeeDetailSerializer(employee, context={'request': request}).data,
                message='Employee created.',
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
            return Response({'success': False, 'error': 'Not found.'}, status=404)
        self.check_object_permissions(request, employee)
        serializer = EmployeeDetailSerializer(employee, context={'request': request})
        return Response(success_response(data=serializer.data))

    def put(self, request, pk):
        if not request.user.role in ['admin', 'rh', 'marketing', 'gerente_loja', 'sub_gerente', 'gerente_turno']:
            return Response({'success': False, 'error': 'Permission denied.'}, status=403)

        employee = self._get_employee(pk)
        if not employee:
            return Response({'success': False, 'error': 'Not found.'}, status=404)
        self.check_object_permissions(request, employee)

        serializer = EmployeeDetailSerializer(
            employee, data=request.data, partial=True, context={'request': request}
        )
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=400)

        serializer.save()
        ActivityLog.log(
            activity_type='update',
            description=f"{request.user.name} updated employee {employee.name}.",
            user=request.user,
            target_id=employee.id,
            target_type='Employee',
        )
        return Response(success_response(
            data=EmployeeDetailSerializer(employee, context={'request': request}).data,
            message='Employee updated.',
        ))

    def patch(self, request, pk):
        return self.put(request, pk)

    def delete(self, request, pk):
        if request.user.role not in ['admin', 'rh']:
            return Response({'success': False, 'error': 'Permission denied.'}, status=403)

        employee = self._get_employee(pk)
        if not employee:
            return Response({'success': False, 'error': 'Not found.'}, status=404)

        employee.is_active = False
        employee.save(update_fields=['is_active'])
        ActivityLog.log(
            activity_type='delete',
            description=f"{request.user.name} deactivated employee {employee.name}.",
            user=request.user,
            target_id=employee.id,
            target_type='Employee',
        )
        return Response(success_response(message='Employee deactivated.'))


class EmployeePhotoView(APIView):
    """
    POST /api/employees/{id}/photo/  — upload employee photo
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            employee = Employee.objects.get(pk=pk)
        except Employee.DoesNotExist:
            return Response({'success': False, 'error': 'Not found.'}, status=404)

        # Only the employee themselves or a manager (gerente+) can upload
        if request.user.pk != employee.pk and not request.user.role in [
            'admin', 'rh', 'marketing', 'gerente_loja', 'sub_gerente', 'gerente_turno'
        ]:
            return Response({'success': False, 'error': 'Permission denied.'}, status=403)

        photo_file = request.FILES.get('photo')
        if not photo_file:
            return Response({'success': False, 'error': 'No photo file provided.'}, status=400)

        ext = os.path.splitext(photo_file.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return Response({'success': False, 'error': 'Invalid file type.'}, status=400)

        filename = f"employee_{employee.pk}{ext}"
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'photos', 'employees')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, 'wb') as f:
            for chunk in photo_file.chunks():
                f.write(chunk)

        employee.photo_filename = filename
        employee.save(update_fields=['photo_filename'])

        return Response(success_response(
            data={'photo_url': employee.photo_url},
            message='Photo uploaded.',
        ))
