"""Correspondência entre utilizadores do Calendar e pessoas do SSO."""

from .backgrounds import normalize_key


def sso_restaurant_id(restaurant):
    if not restaurant:
        return None
    if getattr(restaurant, "sso_id", None):
        return restaurant.sso_id

    from apps.workers.models import SSORestaurant

    match = SSORestaurant.objects.operational().filter(name__iexact=restaurant.name).first()
    if not match and restaurant.name:
        match = SSORestaurant.objects.operational().filter(
            name__icontains=restaurant.name.split()[0]
        ).first()
    return match.id if match else None


def match_sso_worker(employee):
    """Encontra a pessoa equivalente no SSO sem aceitar homónimos ambíguos."""
    from apps.workers.models import Worker

    if getattr(employee, "email", ""):
        match = Worker.objects.filter(email__iexact=employee.email).first()
        if match:
            return match

    employee_number = getattr(employee, "employee_number", "") or ""
    if employee_number:
        match = Worker.objects.filter(employee_number=employee_number).first()
        if match:
            return match

    target = normalize_key(getattr(employee, "name", ""))
    restaurant_id = sso_restaurant_id(getattr(employee, "restaurant", None))
    if target and restaurant_id:
        candidates = [
            worker
            for worker in Worker.objects.filter(
                restaurant_id=restaurant_id,
                is_active=True,
            )
            if normalize_key(worker.name) == target
        ]
        if len(candidates) == 1:
            return candidates[0]
    return None
