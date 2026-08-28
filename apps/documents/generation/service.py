"""Serviço principal de geração de cartões."""

import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

from django.conf import settings

from .backgrounds import load_template_image
from .config import get_template_definition
from .layout import paste_photo
from .people import match_sso_worker
from .photos import resolve_person_photo
from .text import (
    draw_centered,
    first_last,
    fit_font,
    format_date_pt,
    format_month_year_pt,
    safe_text,
)


logger = logging.getLogger(__name__)


class DocumentGenerator:
    """Gera um documento a partir da configuração central do modelo."""

    def photo_status(self, data):
        """Valida a fotografia sem criar qualquer documento."""
        person = self._resolve_person(data)
        if person.get("error"):
            return person
        photo = resolve_person_photo(
            sso_avatar=person["sso_avatar"],
            photo_references=person["photo_references"],
        )
        return {
            "available": photo.available,
            "status": "disponivel" if photo.available else "indisponivel",
            "source": photo.source if photo.available else None,
            "reference_present": photo.reference_present,
        }

    def generate(self, template_name, data, user):
        try:
            from PIL import ImageDraw
        except ImportError:
            return {"error": "A biblioteca de imagens não está instalada.", "code": "pillow_missing"}

        definition = get_template_definition(template_name)
        if definition is None:
            return {"error": "O modelo selecionado não existe.", "code": "invalid_template"}

        person = self._resolve_person(data)
        if person.get("error"):
            return person

        restaurant = self._resolve_restaurant(data, user, person)
        if restaurant is None:
            return {
                "error": (
                    "A pessoa selecionada não tem um restaurante de destino "
                    "válido. Confirme a associação no Portal."
                ),
                "code": "restaurant_required",
            }
        if (
            getattr(user, "role", None) not in settings.SUPER_ROLES
            and restaurant.id != getattr(user, "restaurant_id", None)
        ):
            return {
                "error": "Só pode gerar templates para o seu restaurante.",
                "code": "target_restaurant_forbidden",
            }

        background, template_path = load_template_image(definition, restaurant.name)
        if background is None:
            return {
                "error": f'Não existe o modelo “{definition.label}” para {restaurant.name}.',
                "code": "template_file_missing",
            }

        photo = resolve_person_photo(
            sso_avatar=person["sso_avatar"],
            photo_references=person["photo_references"],
        )
        if not photo.available:
            if photo.reference_present:
                message = (
                    "A fotografia está registada, mas o ficheiro não existe neste "
                    "ambiente local. Volte a carregar a fotografia da pessoa."
                )
            else:
                message = (
                    "Esta pessoa não tem uma fotografia disponível. "
                    "Carregue uma fotografia antes de gerar o cartão."
                )
            logger.warning(
                "Geração sem fotografia bloqueada: pessoa=%s tentativas=%s",
                person["identifier"],
                photo.attempted,
            )
            return {
                "error": message,
                "code": "photo_unavailable",
                "photo_status": "indisponivel",
            }

        image_width, image_height = background.size
        center_x = image_width // 2
        center_y = image_height // 2
        paste_photo(
            background,
            photo.image,
            center_x,
            center_y,
            offset_y=definition.photo_offset,
        )

        self._draw_text(
            background,
            definition.key,
            person,
            data,
        )
        return self._save_document(
            background=background,
            definition=definition,
            person=person,
            restaurant=restaurant,
            user=user,
            data=data,
            photo_source=photo.source,
            template_path=template_path,
        )

    @staticmethod
    def _resolve_person(data):
        from apps.accounts.models import Employee
        from apps.workers.models import Worker

        person_name = safe_text(data.get("name", ""))
        birth_date = None
        hire_date = None
        employee = None
        worker = None
        references = []

        employee_id = data.get("employee_id")
        worker_id = data.get("worker_id")
        try:
            if employee_id:
                employee = Employee.objects.get(pk=employee_id)
                person_name = person_name or safe_text(employee.name)
                birth_date = employee.birth_date
                hire_date = employee.hire_date
                if employee.photo_filename:
                    references.append((employee.photo_filename, "employee"))
                worker = match_sso_worker(employee)
                if worker and worker.photo_filename:
                    references.append((worker.photo_filename, "worker"))
            elif worker_id:
                worker = Worker.objects.get(pk=worker_id)
                person_name = person_name or safe_text(worker.name)
                birth_date = worker.birth_date
                hire_date = worker.hire_date
                if worker.photo_filename:
                    references.append((worker.photo_filename, "worker"))
            else:
                return {
                    "error": "Selecione a pessoa para quem pretende gerar o cartão.",
                    "code": "person_required",
                }
        except (Employee.DoesNotExist, Worker.DoesNotExist):
            return {
                "error": "A pessoa selecionada já não existe.",
                "code": "person_not_found",
            }

        return {
            "name": first_last(person_name) or "Colaborador",
            "birth_date": birth_date,
            "hire_date": hire_date,
            "employee": employee,
            "worker": worker,
            "sso_avatar": getattr(worker, "avatar", None) if worker else None,
            "photo_references": tuple(references),
            "identifier": (
                f"employee:{employee.pk}" if employee else f"worker:{worker.pk}"
            ),
        }

    @staticmethod
    def _resolve_restaurant(data, user, person=None):
        from apps.restaurants.models import Restaurant
        from apps.restaurants.services import get_local_restaurant_for_sso_id

        person = person or {}
        worker = person.get("worker")
        if worker and getattr(worker, "restaurant_id", None):
            # Worker restaurant IDs come from the SSO database, so they must be
            # mapped to the local Restaurant row used by Document.restaurant.
            return get_local_restaurant_for_sso_id(worker.restaurant_id)

        employee = person.get("employee")
        if employee and getattr(employee, "restaurant_id", None):
            return employee.restaurant

        restaurant_id = data.get("restaurant_id") or getattr(user, "restaurant_id", None)
        if not restaurant_id:
            return None
        return Restaurant.objects.filter(id=restaurant_id).first()

    @staticmethod
    def _draw_text(background, template_key, person, data):
        from PIL import ImageDraw

        width, height = background.size
        draw = ImageDraw.Draw(background)
        name_size = max(90, width // 12)
        date_size = max(60, width // 18)
        box_width = int(width * 0.46)
        name_width = int(width * 0.62)
        box_height = int(height * 0.042)
        name_y = int(height * 0.797)
        bottom_y = int(height * 0.872)
        month_y = int(height * 0.219)
        employee_name_y = int(height * 0.885)

        if template_key == "birthday":
            draw_centered(
                draw,
                person["name"],
                fit_font(person["name"], name_width, name_size),
                name_y,
                width,
            )
            current_year = int(data.get("event_year") or datetime.now().year)
            birth_date = person["birth_date"]
            if birth_date:
                formatted = format_date_pt(birth_date)
                date_text = f"{formatted[:5]}/{current_year}"
            else:
                date_text = format_date_pt(None)
            draw_centered(
                draw,
                date_text,
                fit_font(date_text, box_width, date_size, max_h=box_height),
                bottom_y,
                width,
            )
            return

        if template_key == "welcome":
            lift = round(height * 10 / 1500)
            date_lift = lift + round(height * 5 / 1500)
            draw_centered(
                draw,
                person["name"],
                fit_font(person["name"], name_width, name_size),
                name_y - lift,
                width,
            )
            date_text = format_date_pt(person["hire_date"])
            draw_centered(
                draw,
                date_text,
                fit_font(date_text, box_width, date_size, max_h=box_height),
                bottom_y - date_lift,
                width,
            )
            return

        month_text = format_month_year_pt(data.get("message"))
        draw_centered(
            draw,
            month_text,
            fit_font(month_text, box_width, name_size, max_h=box_height),
            month_y,
            width,
        )
        draw_centered(
            draw,
            person["name"],
            fit_font(person["name"], box_width, name_size, max_h=box_height),
            employee_name_y,
            width,
        )

    @staticmethod
    def _save_document(
        *,
        background,
        definition,
        person,
        restaurant,
        user,
        data,
        photo_source,
        template_path,
    ):
        from apps.documents.models import Document

        timestamp = int(time.time() * 1000)
        token = uuid.uuid4().hex[:6]
        filename = f"{definition.key}_{timestamp}_{token}.png"
        output_dir = Path(settings.MEDIA_ROOT) / "documents" / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)
        full_path = output_dir / filename
        background.save(full_path, "PNG")

        try:
            document = Document.objects.create(
                title=f"{definition.label} — {person['name']}",
                document_type=definition.key,
                template_name=definition.key,
                employee=person["employee"],
                worker=person.get("worker"),
                restaurant=restaurant,
                created_by=user,
                filename=filename,
                file_path=str(full_path),
                file_size=os.path.getsize(full_path),
                file_extension=".png",
                tags=safe_text(
                    data.get("document_key") or person["identifier"]
                )[:500],
                status="generated",
            )
        except Exception:
            full_path.unlink(missing_ok=True)
            raise

        return {
            "id": document.id,
            "title": document.title,
            "filename": document.filename,
            "file_url": f"/media/documents/generated/{filename}",
            "template_label": definition.label,
            "restaurant_id": restaurant.id,
            "restaurant_name": restaurant.name,
            "photo_status": "disponivel",
            "photo_source": photo_source,
            "template_file": template_path.name,
        }
