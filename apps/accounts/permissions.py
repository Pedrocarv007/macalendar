"""Permissões de perfis e restaurantes do MC."""
import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission


ROLE_ALIASES = {
    'gerente_loja': 'manager',
    'sub_gerente': 'sub_manager',
    'gerente_turno': 'shift_manager',
    'funcionario': 'employee',
    'colaborador': 'employee',
    'relacoes_publicas': 'rp',
}

GLOBAL_VIEW_ROLES = {'admin', 'rh', 'marketing'}
GLOBAL_MANAGEMENT_ROLES = {'admin', 'rh'}
LOCAL_MANAGEMENT_ROLES = {
    'administrativa', 'manager', 'sub_manager', 'shift_manager',
}
ROLE_RANKS = {
    'admin': 0,
    'rh': 0,
    'administrativa': 1,
    'manager': 2,
    'sub_manager': 3,
    'shift_manager': 4,
    'coucher': 5,
    'treinador': 5,
    'rp': 6,
    'employee': 7,
}


def canonical_role(user_or_role):
    role = (
        user_or_role
        if isinstance(user_or_role, str)
        else getattr(user_or_role, 'role', '')
    )
    return ROLE_ALIASES.get(role, role)


def is_super_role(user):
    """Admin, RH and Marketing can view every restaurant."""
    return (
        getattr(user, 'is_authenticated', False)
        and canonical_role(user) in GLOBAL_VIEW_ROLES
    )


def can_manage_employees(user):
    """Roles allowed to change employee data."""
    role = canonical_role(user)
    return (
        getattr(user, 'is_authenticated', False)
        and role in (GLOBAL_MANAGEMENT_ROLES | LOCAL_MANAGEMENT_ROLES)
    )


def can_manage_restaurant(user):
    """Roles allowed to change restaurant settings."""
    return (
        getattr(user, 'is_authenticated', False)
        and canonical_role(user) in {'admin', 'rh', 'administrativa', 'manager'}
    )


def can_create_posts(user):
    return getattr(user, 'is_authenticated', False)


def role_rank(user_or_role):
    return ROLE_RANKS.get(canonical_role(user_or_role), 999)


def outranks(user, other_user):
    return role_rank(user) < role_rank(other_user)


def can_manage_role(user, target_role):
    """Apply the agreed role hierarchy consistently with the SSO portal."""
    if not getattr(user, 'is_authenticated', False):
        return False
    actor_role = canonical_role(user)
    target_role = canonical_role(target_role)
    if actor_role in GLOBAL_MANAGEMENT_ROLES:
        return True
    if actor_role not in LOCAL_MANAGEMENT_ROLES:
        return False
    if target_role in GLOBAL_VIEW_ROLES:
        return False
    actor_rank = ROLE_RANKS.get(actor_role, 999)
    target_rank = ROLE_RANKS.get(target_role, -1)
    if actor_role in {'administrativa', 'manager'}:
        return actor_rank <= target_rank
    return actor_rank < target_rank


def can_manage_employee(user, employee, *, sso_restaurant=False):
    """Apply the role hierarchy and the appropriate restaurant boundary."""
    actor_role = canonical_role(user)
    if actor_role in GLOBAL_MANAGEMENT_ROLES:
        return True
    if not can_manage_role(user, getattr(employee, 'role', 'employee')):
        return False
    if sso_restaurant:
        actor_restaurant_id = getattr(
            getattr(user, 'restaurant', None), 'sso_id', None
        )
    else:
        actor_restaurant_id = getattr(user, 'restaurant_id', None)
    return bool(
        actor_restaurant_id
        and actor_restaurant_id == getattr(employee, 'restaurant_id', None)
    )


class IsAdmin(BasePermission):
    message = 'É necessário o perfil de administrador.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and canonical_role(request.user) == 'admin'
        )


class IsRH(BasePermission):
    message = 'RH role or above required.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and canonical_role(request.user) in GLOBAL_MANAGEMENT_ROLES
        )


class IsMarketing(BasePermission):
    message = 'Marketing role or above required.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and canonical_role(request.user) in GLOBAL_VIEW_ROLES
        )


class IsManagerOrAbove(BasePermission):
    message = 'Manager role or above required.'

    def has_permission(self, request, view):
        return can_manage_employees(request.user)


class IsShiftManagerOrAbove(IsManagerOrAbove):
    message = 'Shift manager role or above required.'


class IsEmployeeOrAbove(BasePermission):
    message = 'Authentication required.'

    def has_permission(self, request, view):
        return request.user.is_authenticated


class SameRestaurantOrAbove(BasePermission):
    message = "You do not have access to this restaurant's data."

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if is_super_role(request.user):
            return True
        target_restaurant_id = getattr(obj, 'restaurant_id', None)
        return bool(
            target_restaurant_id
            and request.user.restaurant_id == target_restaurant_id
        )


class CanManageEmployees(BasePermission):
    message = 'You do not have permission to manage employees.'

    def has_permission(self, request, view):
        return can_manage_employees(request.user)


class CanManageRestaurant(BasePermission):
    message = 'You do not have permission to manage restaurant settings.'

    def has_permission(self, request, view):
        return can_manage_restaurant(request.user)


class IsServiceClient(BasePermission):
    message = 'Chave de serviço inválida ou ausente.'

    def has_permission(self, request, view):
        key = request.META.get('HTTP_X_SERVICE_KEY', '')
        service_key = getattr(settings, 'SERVICE_API_KEY', '')
        if not key or not service_key:
            return False
        return hmac.compare_digest(key, service_key)


IsAdminOnly = IsAdmin
IsRHOrAbove = IsRH
