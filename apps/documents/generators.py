"""Compatibilidade para o antigo import ``apps.documents.generators``.

A implementação foi dividida por responsabilidade em ``documents.generation``.
"""

from .generation.config import (
    RESTAURANT_TEMPLATE_OVERRIDES,
    TEMPLATES,
)
from .generation.layout import paste_photo as _paste_photo
from .generation.people import (
    match_sso_worker as _match_sso_worker,
    sso_restaurant_id as _sso_restaurant_id,
)
from .generation.photos import resolve_person_photo
from .generation.service import DocumentGenerator
from .generation.text import (
    draw_centered as _draw_centered,
    first_last as _first_last,
    fit_font as _fit_font,
    format_date_pt as _format_date_pt,
    load_font as _load_font,
    safe_text as _safe_text,
)


TEMPLATE_FILES = {key: item.filename for key, item in TEMPLATES.items()}
RESTAURANT_OVERRIDES = RESTAURANT_TEMPLATE_OVERRIDES


def _get_photo(photo_filename, person_type="employee", sso_avatar=None):
    """Interface antiga: devolve apenas a imagem resolvida."""
    return resolve_person_photo(
        sso_avatar=sso_avatar,
        photo_references=((photo_filename, person_type),),
    ).image


__all__ = [
    "DocumentGenerator",
    "TEMPLATE_FILES",
    "RESTAURANT_OVERRIDES",
    "_get_photo",
    "_paste_photo",
    "_match_sso_worker",
    "_sso_restaurant_id",
    "_draw_centered",
    "_first_last",
    "_fit_font",
    "_format_date_pt",
    "_load_font",
    "_safe_text",
]
