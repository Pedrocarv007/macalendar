"""Formatação de texto e tipografia usada nos templates gerados."""

import os
import re
from datetime import date, datetime


MONTHS_PT = (
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)

MONTH_TRANSLATIONS = {
    "january": "Janeiro",
    "february": "Fevereiro",
    "march": "Março",
    "april": "Abril",
    "may": "Maio",
    "june": "Junho",
    "july": "Julho",
    "august": "Agosto",
    "september": "Setembro",
    "october": "Outubro",
    "november": "Novembro",
    "december": "Dezembro",
}


def first_last(name):
    parts = str(name or "").split()
    if len(parts) <= 2:
        return " ".join(parts)
    return f"{parts[0]} {parts[-1]}"


def safe_text(value):
    """Mantém acentos portugueses e remove apenas caracteres de controlo."""
    text = str(value or "")
    return "".join(char for char in text if char in "\n\t" or ord(char) >= 32).strip()


def format_date_pt(value):
    """Devolve sempre a data em ``dd/mm/aaaa``."""
    if not value:
        return datetime.now().strftime("%d/%m/%Y")
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")

    raw = str(value).strip()
    for parser in (
        lambda item: datetime.fromisoformat(item.replace("Z", "")),
        lambda item: date.fromisoformat(item[:10]),
    ):
        try:
            return parser(raw).strftime("%d/%m/%Y")
        except (TypeError, ValueError):
            pass

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return raw


def format_month_year_pt(value=None, now=None):
    """Normaliza o mês/ano para português, incluindo entradas em inglês."""
    current = now or datetime.now()
    raw = safe_text(value)
    if not raw:
        return f"{MONTHS_PT[current.month]} {current.year}"

    translated = raw
    for english, portuguese in MONTH_TRANSLATIONS.items():
        translated = re.sub(
            rf"\b{english}\b",
            portuguese,
            translated,
            flags=re.IGNORECASE,
        )
    return translated


def load_font(size=40):
    from PIL import ImageFont

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/segoeuil.ttf",
        "C:/Windows/Fonts/seguisli.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def fit_font(text, max_w, preferred_size, min_size=34, max_h=None):
    size = preferred_size
    while size >= min_size:
        font = load_font(size)
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= max_w and (max_h is None or height <= max_h):
            return font
        size -= 4
    return load_font(min_size)


def draw_centered(draw, text, font, cy, img_width, fill=(255, 255, 255, 255)):
    try:
        draw.text((img_width // 2, cy), text, font=font, anchor="mm", fill=fill)
    except (TypeError, ValueError):
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        draw.text(
            ((img_width - width) // 2, cy - height // 2),
            text,
            font=font,
            fill=fill,
        )
