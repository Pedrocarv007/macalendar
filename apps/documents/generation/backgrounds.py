"""Localização e carregamento dos fundos gráficos por restaurante."""

import unicodedata
from pathlib import Path

from django.conf import settings

from .config import RESTAURANT_TEMPLATE_OVERRIDES


def normalize_key(value):
    raw = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(char for char in raw if not unicodedata.combining(char))
        .casefold()
        .split()
    )


def find_template_path(definition, restaurant_name):
    base = Path(getattr(settings, "TEMPLATES_BASE_DIR"))
    restaurant_key = normalize_key(restaurant_name)
    filename = RESTAURANT_TEMPLATE_OVERRIDES.get(restaurant_key, {}).get(
        definition.key,
        definition.filename,
    )

    if not restaurant_key or not base.is_dir():
        return None

    for folder in base.iterdir():
        if (
            folder.is_dir()
            and normalize_key(folder.name) == restaurant_key
            and (folder / filename).is_file()
        ):
            return folder / filename
    return None


def load_template_image(definition, restaurant_name):
    from PIL import Image

    path = find_template_path(definition, restaurant_name)
    if path is None:
        return None, None
    image = Image.open(path)
    image.load()
    return image.convert("RGBA"), path
