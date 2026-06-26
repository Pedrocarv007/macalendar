"""
Document generation using PIL/Pillow with real PNG templates.
Templates are loaded from the shared templates_generate/ folder.
"""
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

TEMPLATES_BASE = Path(getattr(settings, 'TEMPLATES_BASE_DIR'))

TEMPLATE_FILES = {
    'birthday':       'aniversario.png',
    'welcome':        'bem_vindo.png',
    'employee_month': 'funcionario_mes.png',
}

# Paço de Arcos uses "aniversarios.png" (with s)
RESTAURANT_OVERRIDES = {
    'paço de arcos': {'birthday': 'aniversarios.png'},
    'paco de arcos': {'birthday': 'aniversarios.png'},
}


def _first_last(name):
    """Return only the first and last word of a name string."""
    if not name:
        return name
    parts = name.split()
    if len(parts) <= 2:
        return name
    return f"{parts[0]} {parts[-1]}"


def _safe_text(text):
    """Replace accented characters that basic PIL fonts can't render."""
    if not text:
        return ''
    replacements = {
        'ã': 'a', 'â': 'a', 'á': 'a', 'à': 'a', 'ä': 'a',
        'ê': 'e', 'é': 'e', 'è': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ô': 'o', 'õ': 'o', 'ò': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'Ã': 'A', 'Â': 'A', 'Á': 'A', 'À': 'A',
        'Ê': 'E', 'É': 'E', 'È': 'E',
        'Í': 'I', 'Ì': 'I',
        'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ò': 'O',
        'Ú': 'U', 'Ù': 'U',
        'Ç': 'C', 'Ñ': 'N',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def _load_font(size=40):
    """Load a light system font (falls back to regular, then PIL default)."""
    from PIL import ImageFont
    candidates = [
        'C:/Windows/Fonts/segoeuil.ttf',   # Segoe UI Light
        'C:/Windows/Fonts/seguisli.ttf',   # Segoe UI Semilight
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf',
        '/System/Library/Fonts/HelveticaNeue.ttc',
        'C:/Windows/Fonts/arial.ttf',
        'C:/Windows/Fonts/Arial.ttf',
        '/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Arial.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _fit_font(text, max_w, preferred_size, min_size=34, max_h=None):
    """Maior fonte (<= preferred_size) cujo texto cabe em max_w píxeis (e, se
    indicado, em max_h). Encolhe até min_size para o texto ficar sempre dentro
    do seu container (caixa verde)."""
    size = preferred_size
    while size >= min_size:
        font = _load_font(size)
        bbox = font.getbbox(text)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_w and (max_h is None or h <= max_h):
            return font
        size -= 4
    return _load_font(min_size)


def _apply_rounded_corners(image, radius=50):
    """Apply rounded corners to an RGBA image using a mask."""
    from PIL import Image, ImageDraw
    image = image.convert('RGBA')
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
    image.putalpha(mask)
    return image


def _get_template_image(template_name, restaurant_name):
    """Load the background template PNG for the given restaurant and template type."""
    from PIL import Image

    res_lower = (restaurant_name or '').lower()

    # Check for per-restaurant filename overrides
    override = RESTAURANT_OVERRIDES.get(res_lower, {})
    filename = override.get(template_name) or TEMPLATE_FILES.get(template_name, 'bem_vindo.png')

    # Try exact restaurant name folder first, then case-insensitive scan
    template_path = None
    if restaurant_name:
        direct = TEMPLATES_BASE / restaurant_name / filename
        if direct.exists():
            template_path = direct
        else:
            # Case-insensitive search
            try:
                for folder in TEMPLATES_BASE.iterdir():
                    if folder.is_dir() and folder.name.lower() == res_lower:
                        candidate = folder / filename
                        if candidate.exists():
                            template_path = candidate
                            break
            except Exception:
                pass

    if template_path and template_path.exists():
        return Image.open(str(template_path)).convert('RGBA')

    # Fallback: plain grey canvas
    return Image.new('RGBA', (1920, 1280), color=(60, 60, 60, 255))


# Limites/segurança para descarregar avatares remotos (defesa contra SSRF).
_REMOTE_IMAGE_MAX_BYTES = 8 * 1024 * 1024  # 8 MB
_REMOTE_IMAGE_TIMEOUT = 5                   # segundos


def _host_is_public(hostname):
    """True só se TODOS os IPs resolvidos do host forem públicos. Bloqueia
    loopback, redes privadas, link-local (ex.: 169.254.169.254 metadata),
    reservados e multicast — mitiga SSRF contra infraestrutura interna."""
    import ipaddress
    import socket

    if not hostname:
        return False
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast or addr.is_unspecified):
            return False
    return True


def _fetch_remote_image(url):
    """Descarrega uma imagem de um URL http(s) de forma segura.

    Mitigações SSRF: valida o esquema, exige host público, NÃO segue redirects
    (impede salto público→interno), limita o tamanho e exige content-type de
    imagem. Devolve um PIL.Image (RGBA) ou None se falhar/for recusado.
    """
    import io
    from urllib.parse import urlparse

    import requests
    from PIL import Image

    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return None
    if not _host_is_public(parsed.hostname):
        logger.warning('Avatar remoto recusado (host nao publico): %s', parsed.hostname)
        return None

    try:
        resp = requests.get(
            url,
            timeout=_REMOTE_IMAGE_TIMEOUT,
            allow_redirects=False,
            stream=True,
            headers={'Accept': 'image/*'},
        )
    except requests.RequestException:
        return None

    try:
        if resp.status_code != 200:
            return None
        if not resp.headers.get('Content-Type', '').lower().startswith('image/'):
            return None
        data = bytearray()
        for chunk in resp.iter_content(8192):
            data.extend(chunk)
            if len(data) > _REMOTE_IMAGE_MAX_BYTES:
                logger.warning('Avatar remoto excede %s bytes: %s',
                               _REMOTE_IMAGE_MAX_BYTES, parsed.hostname)
                return None
    finally:
        resp.close()

    try:
        return Image.open(io.BytesIO(bytes(data))).convert('RGBA')
    except Exception:
        return None


def _get_photo(photo_filename, person_type='employee', sso_avatar=None):
    """Return a PIL Image of the person's photo or a placeholder."""
    from PIL import Image, ImageDraw

    # 1. Tentar avatar SSO
    if sso_avatar:
        avatar = str(sso_avatar)
        # 1a. Avatar guardado como URL completo (ex: avatar Google) — descarregar
        #     de forma segura (ver _fetch_remote_image: bloqueia hosts internos/SSRF).
        if avatar.lower().startswith(('http://', 'https://')):
            img = _fetch_remote_image(avatar)
            if img is not None:
                return img
        else:
            # 1b. Caminho relativo no disco do SSO portal (ex: 'avatars/abel.png')
            sso_root = Path(getattr(settings, 'SSO_MEDIA_ROOT',
                                    r'I:\server_apps\Thecarv_django\media'))
            path = sso_root / avatar
            if path.exists():
                try:
                    return Image.open(str(path)).convert('RGBA')
                except Exception:
                    pass

    # 2. Tentar foto local (Mac Calendar media)
    if photo_filename:
        subfolder = 'employees' if person_type == 'employee' else 'workers'
        path = settings.MEDIA_ROOT / 'photos' / subfolder / photo_filename
        if path.exists():
            try:
                return Image.open(str(path)).convert('RGBA')
            except Exception:
                pass

    # 3. Placeholder silhouette
    ph = Image.new('RGBA', (400, 400), (160, 160, 160, 255))
    draw = ImageDraw.Draw(ph)
    draw.ellipse([100, 40, 300, 240], fill=(120, 120, 120, 255))
    draw.ellipse([60, 230, 340, 400], fill=(120, 120, 120, 255))
    return ph


def _paste_photo(fundo, photo_img, cx, cy, offset_y=-50):
    """Fit photo to 621x834, round corners, paste onto fundo."""
    from PIL import ImageDraw, ImageOps

    photo = ImageOps.fit(photo_img.convert('RGBA'), (621, 834),
                         method=0, centering=(0.5, 0.5))
    photo = _apply_rounded_corners(photo, radius=50)

    # White border
    border_draw = ImageDraw.Draw(photo)
    border_draw.rounded_rectangle([(0, 0), (620, 833)], radius=50, outline='white', width=10)

    x = cx - 621 // 2
    y = cy - 800 // 2 + offset_y
    fundo.paste(photo, (x, y), mask=photo)


def _draw_centered(draw, text, font, cy, img_width, fill=(255, 255, 255, 255)):
    """Centra o texto horizontalmente na imagem e verticalmente em cy (centro
    da caixa). cy é o CENTRO vertical, não o topo."""
    try:
        draw.text((img_width // 2, cy), text, font=font, anchor='mm', fill=fill)
    except (TypeError, ValueError):
        # Fonte bitmap (load_default) não suporta anchor — centrar manualmente.
        bbox = font.getbbox(text)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(((img_width - w) // 2, cy - h // 2), text, font=font, fill=fill)


def _norm_name(name):
    """Normaliza um nome para comparação: sem acentos, sem espaços extra, minúsculas."""
    return ' '.join(_safe_text(name or '').split()).lower()


def _sso_restaurant_id(restaurant):
    """Resolve o id do restaurante na BD do SSO (mesma lógica do BirthdayService)."""
    if not restaurant:
        return None
    sso_id = getattr(restaurant, 'sso_id', None)
    if sso_id:
        return sso_id
    from apps.workers.models import SSORestaurant
    sso_rest = SSORestaurant.objects.filter(name__iexact=restaurant.name).first()
    if not sso_rest and restaurant.name:
        sso_rest = SSORestaurant.objects.filter(
            name__icontains=restaurant.name.split()[0]
        ).first()
    return sso_rest.id if sso_rest else None


def _match_sso_worker(emp):
    """
    Encontra o Worker (crew do SSO) correspondente a um Employee, para que os
    cartões gerados a partir de Funcionários vão buscar o avatar à mesma fonte
    que o aniversário (worker.avatar).

    Ordem de match (da chave mais fiável para a menos): email → nº funcionário →
    nome, este último só dentro do mesmo restaurante e só se houver um único
    Worker com esse nome (evita match errado por homónimos). Devolve o Worker ou None.
    """
    from apps.workers.models import Worker

    if getattr(emp, 'email', ''):
        w = Worker.objects.filter(email__iexact=emp.email).first()
        if w:
            return w

    emp_number = getattr(emp, 'employee_number', '') or ''
    if emp_number:
        w = Worker.objects.filter(employee_number=emp_number).first()
        if w:
            return w

    # Fallback por nome — restrito ao mesmo restaurante e só se for único.
    # (Worker.name é uma property, não coluna → comparar em Python sobre a crew
    # do restaurante, que é um conjunto pequeno.)
    target = _norm_name(getattr(emp, 'name', ''))
    sso_id = _sso_restaurant_id(getattr(emp, 'restaurant', None))
    if target and sso_id:
        candidates = [
            w for w in Worker.objects.filter(restaurant_id=sso_id, is_active=True)
            if _norm_name(w.name) == target
        ]
        if len(candidates) == 1:
            return candidates[0]

    return None


class DocumentGenerator:

    def generate(self, template_name, data, user):
        """
        Unified entry point called from the view.

        data keys:
          name          – person display name (override)
          employee_id   – Employee pk (optional)
          worker_id     – Worker pk (optional)
          restaurant_id – Restaurant pk (falls back to user's)
          message       – extra text / month-year for employee_month
          person_type   – 'employee' | 'worker' (default 'employee')
        """
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            return {'error': 'Pillow não está instalado.'}

        if template_name not in TEMPLATE_FILES:
            return {'error': 'Template inválido.'}

        # ── Resolve person ───────────────────────────────────────────
        person_name = _safe_text(data.get('name', ''))
        photo_filename = None
        sso_avatar = None
        person_type = data.get('person_type', 'employee')
        birth_date = None
        hire_date = None

        employee_id = data.get('employee_id')
        worker_id = data.get('worker_id')

        if employee_id:
            from apps.accounts.models import Employee
            try:
                emp = Employee.objects.get(pk=employee_id)
                if not person_name:
                    person_name = _safe_text(emp.name)
                photo_filename = emp.photo_filename
                birth_date = emp.birth_date
                hire_date = emp.hire_date
                person_type = 'employee'
                # Ir buscar o avatar ao Worker do SSO — exatamente como o aniversário.
                # _get_photo tenta o avatar SSO antes da foto local.
                w = _match_sso_worker(emp)
                if w:
                    sso_avatar = w.avatar or None
                    # Fallback: se o Employee não tem foto local, usar a do Worker
                    # (que vive na pasta 'workers' → ajustar person_type em conformidade).
                    if not photo_filename and w.photo_filename:
                        photo_filename = w.photo_filename
                        person_type = 'worker'
            except Employee.DoesNotExist:
                pass
        elif worker_id:
            from apps.workers.models import Worker
            try:
                wkr = Worker.objects.get(pk=worker_id)
                if not person_name:
                    person_name = _safe_text(wkr.name)
                photo_filename = wkr.photo_filename
                sso_avatar = wkr.avatar or None  # avatar SSO (ex: 'avatars/abel.png')
                birth_date = wkr.birth_date
                hire_date = wkr.hire_date
                person_type = 'worker'
            except Worker.DoesNotExist:
                pass

        if not person_name:
            person_name = 'Colaborador'
        else:
            person_name = _first_last(person_name)

        # ── Resolve restaurant ────────────────────────────────────────
        from apps.restaurants.models import Restaurant
        restaurant_id = data.get('restaurant_id') or user.restaurant_id
        restaurant = Restaurant.objects.filter(id=restaurant_id).first()
        restaurant_name = restaurant.name if restaurant else ''

        # ── Load template ─────────────────────────────────────────────
        fundo = _get_template_image(template_name, restaurant_name)
        img_w, img_h = fundo.size
        cx = img_w // 2
        cy = img_h // 2

        draw = ImageDraw.Draw(fundo)
        name_size = max(90, img_w // 12)
        date_size = max(60, img_w // 18)

        # Geometria das caixas verdes (medida nos templates 1000x1500, em frações
        # para escalar). Caixa de texto: x 0.228–0.772 (largura ~544px).
        box_w = int(img_w * 0.46)    # largura útil dentro da caixa verde (~460px)
        name_w = int(img_w * 0.62)   # nome na área aberta acima da caixa (~620px)
        box_h = int(img_h * 0.042)   # altura útil dentro de uma caixa (~63px)
        y_name_open = int(img_h * 0.797)      # nome (aniversário/boas-vindas), área aberta
        y_box_bottom = int(img_h * 0.872)     # caixa inferior: data (aniversário)
        y_box_welcome = int(img_h * 0.857)    # boas-vindas: caixa inferior fica ~22px mais acima
        y_box_fm_top = int(img_h * 0.219)     # funcionário do mês: caixa do topo (mês/ano)
        y_box_fm_bottom = int(img_h * 0.885)  # funcionário do mês: caixa inferior (nome)

        # ── Paste photo ───────────────────────────────────────────────
        photo = _get_photo(photo_filename, person_type, sso_avatar=sso_avatar)
        photo_offset = 50 if template_name == 'employee_month' else -50
        _paste_photo(fundo, photo, cx, cy, offset_y=photo_offset)

        # ── Draw text ─────────────────────────────────────────────────
        if template_name == 'birthday':
            # Nome na área aberta acima da caixa; data centrada dentro da caixa verde.
            _draw_centered(draw, person_name, _fit_font(person_name, name_w, name_size),
                           y_name_open, img_w)
            # Birthday day/month with the event year (never the birth year)
            current_year = data.get('event_year') or datetime.now().year
            if birth_date:
                if isinstance(birth_date, str):
                    try:
                        from datetime import date
                        bd = date.fromisoformat(birth_date)
                        date_str = f"{bd.strftime('%d/%m')}/{current_year}"
                    except Exception:
                        date_str = birth_date
                else:
                    date_str = f"{birth_date.strftime('%d/%m')}/{current_year}"
            else:
                date_str = datetime.now().strftime('%d/%m/%Y')
            _draw_centered(draw, date_str, _fit_font(date_str, box_w, date_size, max_h=box_h),
                           y_box_bottom, img_w)

        elif template_name == 'welcome':
            _draw_centered(draw, person_name, _fit_font(person_name, name_w, name_size),
                           y_name_open, img_w)
            if hire_date:
                if isinstance(hire_date, str):
                    try:
                        from datetime import date
                        hd = date.fromisoformat(hire_date)
                        date_str = hd.strftime('%d/%m/%Y')
                    except Exception:
                        date_str = hire_date
                else:
                    date_str = hire_date.strftime('%d/%m/%Y')
            else:
                date_str = datetime.now().strftime('%d/%m/%Y')
            _draw_centered(draw, date_str, _fit_font(date_str, box_w, date_size, max_h=box_h),
                           y_box_bottom, img_w)

        elif template_name == 'employee_month':
            month_year = _safe_text(data.get('message', '') or datetime.now().strftime('%B %Y'))
            # Mês/ano na caixa do topo, nome na caixa inferior — ambos dentro da caixa.
            _draw_centered(draw, month_year, _fit_font(month_year, box_w, name_size, max_h=box_h),
                           y_box_fm_top, img_w)
            _draw_centered(draw, person_name, _fit_font(person_name, box_w, name_size, max_h=box_h),
                           y_box_fm_bottom, img_w)

        # ── Save ──────────────────────────────────────────────────────
        ts = int(time.time() * 1000)
        uid = uuid.uuid4().hex[:6]
        filename = f"{template_name}_{ts}_{uid}.png"
        output_dir = settings.MEDIA_ROOT / 'documents' / 'generated'
        output_dir.mkdir(parents=True, exist_ok=True)
        full_path = output_dir / filename
        fundo.save(str(full_path), 'PNG')

        # ── Save to DB ────────────────────────────────────────────────
        from .models import Document
        title_map = {
            'birthday': 'Aniversário',
            'welcome': 'Boas-Vindas',
            'employee_month': 'Funcionário do Mês',
        }
        doc = Document.objects.create(
            title=f"{title_map[template_name]} — {person_name}",
            document_type=template_name,
            template_name=template_name,
            restaurant=restaurant,
            created_by=user,
            filename=filename,
            file_path=str(full_path),
            file_size=os.path.getsize(str(full_path)),
            file_extension='.png',
            status='generated',
        )

        return {
            'id': doc.id,
            'title': doc.title,
            'filename': doc.filename,
            'file_url': f"/media/documents/generated/{filename}",
        }
