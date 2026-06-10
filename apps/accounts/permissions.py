"""
Role-based DRF permission classes for Mac Calendar.
"""
import hmac
from rest_framework.permissions import BasePermission
from django.conf import settings


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def is_super_role(user):
    """True for admin, rh, marketing — roles that see all restaurants."""
    return user.is_authenticated and user.role in settings.SUPER_ROLES


def can_manage_employees(user):
    """True for any role above plain employee."""
    return user.is_authenticated and user.role != 'employee'


def can_manage_restaurant(user):
    """True for roles that may edit restaurant settings."""
    return user.is_authenticated and user.role in ['admin', 'rh', 'gerente_loja']


def can_create_posts(user):
    """All authenticated users may create posts/events."""
    return user.is_authenticated


def role_rank(user):
    """Returns the numeric rank of a user's role (lower = more powerful)."""
    hierarchy = settings.ROLE_HIERARCHY
    try:
        return hierarchy.index(user.role)
    except ValueError:
        return len(hierarchy)


def outranks(user, other_user):
    """True if user has a strictly higher role than other_user."""
    return role_rank(user) < role_rank(other_user)


# ---------------------------------------------------------------------------
# Permission classes
# ---------------------------------------------------------------------------

class IsAdmin(BasePermission):
    """Only the admin role."""
    message = 'Admin role required.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsRH(BasePermission):
    """Admin or RH."""
    message = 'RH role or above required.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'rh']


class IsMarketing(BasePermission):
    """Admin, RH, or Marketing."""
    message = 'Marketing role or above required.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'rh', 'marketing']


class IsManagerOrAbove(BasePermission):
    """
    Gerente de loja, sub-gerente, gerente de turno, plus all super roles.
    Essentially everyone except plain employees.
    """
    message = 'Manager role or above required.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [
            'admin', 'rh', 'marketing', 'gerente_loja', 'sub_gerente', 'gerente_turno'
        ]


class IsShiftManagerOrAbove(BasePermission):
    """Gerente de turno and all roles above."""
    message = 'Shift manager role or above required.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [
            'admin', 'rh', 'marketing', 'gerente_loja', 'sub_gerente', 'gerente_turno'
        ]


class IsEmployeeOrAbove(BasePermission):
    """Any authenticated user (all roles)."""
    message = 'Authentication required.'

    def has_permission(self, request, view):
        return request.user.is_authenticated


class SameRestaurantOrAbove(BasePermission):
    """
    Allows access if the user is a super role (sees all restaurants)
    OR if the user's restaurant matches the requested resource's restaurant.
    Expects the view or queryset to enforce restaurant filtering additionally.
    """
    message = 'You do not have access to this restaurant\'s data.'

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_super_role(user):
            return True
        obj_restaurant_id = getattr(obj, 'restaurant_id', None)
        if obj_restaurant_id is None:
            return True
        return user.restaurant_id == obj_restaurant_id


class CanManageEmployees(BasePermission):
    """Any role that can manage other employees."""
    message = 'You do not have permission to manage employees.'

    def has_permission(self, request, view):
        return can_manage_employees(request.user)


class CanManageRestaurant(BasePermission):
    """Roles that can edit restaurant settings."""
    message = 'You do not have permission to manage restaurant settings.'

    def has_permission(self, request, view):
        return can_manage_restaurant(request.user)


class IsServiceClient(BasePermission):
    """
    Autenticação sistema-para-sistema via header X-Service-Key.
    Usado em endpoints /api/service/ que só sistemas internos devem chamar.
    """
    message = 'Chave de serviço inválida ou ausente.'

    def has_permission(self, request, view):
        key = request.META.get('HTTP_X_SERVICE_KEY', '')
        service_key = getattr(settings, 'SERVICE_API_KEY', '')
        if not key or not service_key:
            return False
        return hmac.compare_digest(key, service_key)


# Aliases for convenience
IsAdminOnly = IsAdmin
IsRHOrAbove = IsRH
