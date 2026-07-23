"""Resolução segura e observável das fotografias usadas nos cartões."""

import io
import ipaddress
import logging
import socket
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

from django.conf import settings


logger = logging.getLogger(__name__)

REMOTE_IMAGE_MAX_BYTES = 8 * 1024 * 1024
REMOTE_IMAGE_TIMEOUT = 5


@dataclass
class PhotoResolution:
    image: object
    available: bool
    source: str
    reference_present: bool
    attempted: tuple[str, ...] = ()


def placeholder_image():
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (400, 400), (160, 160, 160, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse([100, 40, 300, 240], fill=(120, 120, 120, 255))
    draw.ellipse([60, 230, 340, 400], fill=(120, 120, 120, 255))
    return image


def _host_is_public(hostname):
    if not hostname:
        return False
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                hostname,
                None,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
            )
        }
    except (socket.gaierror, OSError):
        return False
    if not addresses:
        return False
    return all(ipaddress.ip_address(address).is_global for address in addresses)


def _fetch_remote_image(url):
    """Descarrega apenas imagens públicas quando a configuração o permite."""
    if not getattr(settings, "ALLOW_REMOTE_AVATAR_FETCH", False):
        return None

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not _host_is_public(parsed.hostname):
        return None

    import requests

    response = requests.get(
        url,
        timeout=REMOTE_IMAGE_TIMEOUT,
        stream=True,
        allow_redirects=False,
    )
    try:
        if response.status_code != 200:
            return None
        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and not content_type.startswith("image/"):
            return None
        data = bytearray()
        for chunk in response.iter_content(8192):
            data.extend(chunk)
            if len(data) > REMOTE_IMAGE_MAX_BYTES:
                return None
    finally:
        response.close()

    try:
        from PIL import Image

        image = Image.open(io.BytesIO(bytes(data)))
        image.load()
        return image.convert("RGBA")
    except Exception:
        return None


def _normalise_reference(reference):
    raw = unquote(str(reference or "").split("?", 1)[0]).replace("\\", "/").strip()
    for prefix in ("/media/", "media/", "/sso-media/", "sso-media/"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    raw = raw.lstrip("/")
    parts = PurePosixPath(raw).parts
    if not raw or ".." in parts:
        return ""
    return "/".join(parts)


def _safe_candidate(root, relative):
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _open_local_image(path):
    if not path or not path.is_file():
        return None
    try:
        from PIL import Image

        image = Image.open(path)
        image.load()
        return image.convert("RGBA")
    except Exception:
        logger.warning("Fotografia inválida ou ilegível: %s", path)
        return None


def _local_candidates(reference, person_type):
    relative = _normalise_reference(reference)
    if not relative:
        return []

    media_root = Path(settings.MEDIA_ROOT)
    sso_root = Path(getattr(settings, "SSO_MEDIA_ROOT", media_root))
    basename = Path(relative).name
    primary = "employees" if person_type == "employee" else "workers"
    secondary = "workers" if primary == "employees" else "employees"

    specifications = (
        (sso_root, relative, "avatar_sso"),
        (media_root, relative, "media_calendar"),
        (media_root, f"photos/{primary}/{basename}", f"calendar_{primary}"),
        (sso_root, f"photos/{primary}/{basename}", f"sso_{primary}"),
        (media_root, f"photos/{secondary}/{basename}", f"calendar_{secondary}"),
        (sso_root, f"photos/{secondary}/{basename}", f"sso_{secondary}"),
        (sso_root, f"avatars/{basename}", "avatar_sso"),
    )
    candidates = []
    seen = set()
    for root, rel, source in specifications:
        path = _safe_candidate(root, rel)
        if path is not None and str(path) not in seen:
            candidates.append((path, source))
            seen.add(str(path))
    return candidates


def resolve_person_photo(*, sso_avatar=None, photo_references=()):
    """
    Resolve a fotografia por prioridade.

    ``photo_references`` contém pares ``(referência, tipo_de_pessoa)``.
    A resposta inclui a origem usada e todos os caminhos tentados, o que permite
    diagnosticar volumes incompletos sem voltar a cair silenciosamente no boneco.
    """
    attempted = []
    reference_present = bool(sso_avatar) or any(ref for ref, _kind in photo_references)

    if sso_avatar:
        avatar = str(sso_avatar)
        if avatar.lower().startswith(("http://", "https://")):
            attempted.append("avatar_remoto")
            image = _fetch_remote_image(avatar)
            if image is not None:
                return PhotoResolution(
                    image=image,
                    available=True,
                    source="avatar_remoto",
                    reference_present=True,
                    attempted=tuple(attempted),
                )
        else:
            for path, source in _local_candidates(avatar, "worker"):
                attempted.append(str(path))
                image = _open_local_image(path)
                if image is not None:
                    return PhotoResolution(
                        image=image,
                        available=True,
                        source=source,
                        reference_present=True,
                        attempted=tuple(attempted),
                    )

    for reference, person_type in photo_references:
        if not reference:
            continue
        for path, source in _local_candidates(reference, person_type):
            attempted.append(str(path))
            image = _open_local_image(path)
            if image is not None:
                return PhotoResolution(
                    image=image,
                    available=True,
                    source=source,
                    reference_present=True,
                    attempted=tuple(attempted),
                )

    return PhotoResolution(
        image=placeholder_image(),
        available=False,
        source="indisponivel",
        reference_present=reference_present,
        attempted=tuple(attempted),
    )
