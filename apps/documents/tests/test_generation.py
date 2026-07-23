from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from PIL import Image

from apps.documents.generation.backgrounds import find_template_path
from apps.documents.generation.config import get_template_definition
from apps.documents.generation.photos import resolve_person_photo
from apps.documents.generation.service import DocumentGenerator
from apps.documents.generation.text import format_date_pt, format_month_year_pt


class PortugueseFormattingTests(SimpleTestCase):
    def test_month_is_translated_to_portuguese(self):
        self.assertEqual(format_month_year_pt("July 2026"), "Julho 2026")

    def test_empty_month_uses_portuguese_name(self):
        value = format_month_year_pt(now=datetime(2026, 3, 1))
        self.assertEqual(value, "Março 2026")

    def test_date_uses_portuguese_order(self):
        self.assertEqual(format_date_pt("2026-07-23"), "23/07/2026")


class TemplateLookupTests(SimpleTestCase):
    def test_restaurant_folder_is_accent_and_case_insensitive(self):
        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            folder = base / "PAÇO DE ARCOS"
            folder.mkdir()
            expected = folder / "aniversarios.png"
            Image.new("RGB", (10, 10), "white").save(expected)

            with override_settings(TEMPLATES_BASE_DIR=base):
                result = find_template_path(
                    get_template_definition("birthday"),
                    "Paço de Arcos",
                )

            self.assertEqual(result, expected)


class PhotoResolutionTests(SimpleTestCase):
    def test_existing_worker_photo_is_resolved_from_calendar_media(self):
        with TemporaryDirectory() as calendar_media, TemporaryDirectory() as sso_media:
            photo_folder = Path(calendar_media) / "photos" / "workers"
            photo_folder.mkdir(parents=True)
            Image.new("RGB", (20, 30), "red").save(photo_folder / "worker.png")

            with override_settings(
                MEDIA_ROOT=Path(calendar_media),
                SSO_MEDIA_ROOT=Path(sso_media),
                ALLOW_REMOTE_AVATAR_FETCH=False,
            ):
                result = resolve_person_photo(
                    photo_references=(("worker.png", "worker"),),
                )

            self.assertTrue(result.available)
            self.assertEqual(result.source, "calendar_workers")
            self.assertEqual(result.image.size, (20, 30))

    def test_missing_registered_photo_is_reported(self):
        with TemporaryDirectory() as calendar_media, TemporaryDirectory() as sso_media:
            with override_settings(
                MEDIA_ROOT=Path(calendar_media),
                SSO_MEDIA_ROOT=Path(sso_media),
                ALLOW_REMOTE_AVATAR_FETCH=False,
            ):
                result = resolve_person_photo(
                    photo_references=(("missing.png", "worker"),),
                )

            self.assertFalse(result.available)
            self.assertTrue(result.reference_present)
            self.assertGreater(len(result.attempted), 0)


class GeneratedFileCleanupTests(SimpleTestCase):
    def test_database_failure_does_not_leave_orphan_file(self):
        with TemporaryDirectory() as temporary:
            person = {
                "name": "Pessoa de Teste",
                "employee": None,
                "identifier": "worker:999",
            }
            restaurant = SimpleNamespace(name="Restaurante de Teste")
            user = SimpleNamespace()

            with (
                override_settings(MEDIA_ROOT=Path(temporary)),
                patch(
                    "apps.documents.models.Document.objects.create",
                    side_effect=RuntimeError("falha simulada"),
                ),
                self.assertRaises(RuntimeError),
            ):
                DocumentGenerator._save_document(
                    background=Image.new("RGB", (20, 20), "white"),
                    definition=get_template_definition("birthday"),
                    person=person,
                    restaurant=restaurant,
                    user=user,
                    data={},
                    photo_source="teste",
                    template_path=Path("template.png"),
                )

            generated = Path(temporary) / "documents" / "generated"
            self.assertEqual(list(generated.glob("*.png")), [])
