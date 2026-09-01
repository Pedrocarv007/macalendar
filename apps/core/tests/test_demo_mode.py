from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class DemoModeContractTests(SimpleTestCase):
    def test_navigation_loads_shared_demo_privacy_mode_without_exposing_control(self):
        root = Path(settings.BASE_DIR)
        template = (root / "templates" / "base.html").read_text(encoding="utf-8")
        script = (root / "static" / "js" / "demo-mode.js").read_text(encoding="utf-8")

        self.assertNotIn("data-demo-toggle", template)
        self.assertIn("js/demo-mode.js", template)
        self.assertIn("thecarv_demo_mode", script)
        self.assertIn("pedro lopes campos de carvalho", script)
        notifications = (root / "templates" / "notifications" / "index.html").read_text(encoding="utf-8")
        calendar_script = (root / "static" / "js" / "modules" / "calendar.js").read_text(encoding="utf-8")
        documents_script = (root / "static" / "js" / "modules" / "documents.js").read_text(encoding="utf-8")
        self.assertIn("data-demo-private", notifications)
        self.assertIn("demoPrivate", calendar_script)
        self.assertIn("isPersonDocument", documents_script)
