"""Sincronização e resolução dos restaurantes oficiais do SSO."""

from apps.workers.models import SSORestaurant

from .models import Restaurant


def get_or_sync_local_restaurant(sso_restaurant):
    """Obtém o restaurante local canónico para um restaurante do SSO."""
    restaurant = Restaurant.objects.filter(sso_id=sso_restaurant.id).first()

    if restaurant is None and sso_restaurant.code:
        restaurant = Restaurant.objects.filter(
            code=sso_restaurant.code,
            sso_id__isnull=True,
        ).first()
        if restaurant:
            restaurant.sso_id = sso_restaurant.id
            restaurant.save(update_fields=["sso_id"])

    if restaurant is None:
        return Restaurant.objects.create(
            sso_id=sso_restaurant.id,
            name=sso_restaurant.name,
            code=sso_restaurant.code or None,
        )

    changed = []
    if restaurant.name != sso_restaurant.name:
        restaurant.name = sso_restaurant.name
        changed.append("name")
    if sso_restaurant.code and restaurant.code != sso_restaurant.code:
        restaurant.code = sso_restaurant.code
        changed.append("code")
    if changed:
        restaurant.save(update_fields=changed)
    return restaurant


def get_local_restaurant_for_sso_id(sso_id):
    """Resolve um ID externo do SSO para o registo local usado pelas FKs."""
    sso_restaurant = SSORestaurant.objects.filter(
        id=sso_id,
        is_active=True,
    ).first()
    if sso_restaurant is None:
        return None
    return get_or_sync_local_restaurant(sso_restaurant)


def active_canonical_restaurants(*, sync=True):
    """Devolve apenas os restaurantes ativos publicados pelo SSO."""
    sso_restaurants = list(SSORestaurant.objects.filter(is_active=True))
    if sync:
        local_ids = [
            get_or_sync_local_restaurant(sso_restaurant).id
            for sso_restaurant in sso_restaurants
        ]
        return Restaurant.objects.filter(id__in=local_ids, is_active=True)

    sso_ids = [restaurant.id for restaurant in sso_restaurants]
    return Restaurant.objects.filter(
        sso_id__in=sso_ids,
        is_active=True,
    )
