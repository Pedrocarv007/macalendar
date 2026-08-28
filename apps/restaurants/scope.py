INVENTORY_ONLY_RESTAURANT_CODE = 'RAFA'


def is_inventory_only_code(code):
    return (code or '').strip().upper() == INVENTORY_ONLY_RESTAURANT_CODE
