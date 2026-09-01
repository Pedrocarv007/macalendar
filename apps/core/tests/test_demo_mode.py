from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class DemoModeContractTests(SimpleTestCase):
    def test_navigation_loads_shared_demo_privacy_mode(self):
        root = Path(settings.BASE_DIR)
        template = (root / "templates" / "base.html").read_text(encoding="utf-8")
        script = (root / "static" / "js" / "demo-mode.js").read_text(encoding="utf-8")

        self.assertIn("data-demo-toggle", template)
        self.assertIn("js/demo-mode.js", template)
        self.assertIn("Domain=.thecarv.com", script)
        self.assertIn("pedro lopes campos de carvalho", script)
