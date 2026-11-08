"""The template picker must show every real source page, not three SVG prototypes."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/xmu-ppt/scripts"
STATIC = SCRIPTS / "confirm_ui/static"
CACHE = ROOT / ".cache"
CACHE.mkdir(exist_ok=True)
sys.path.insert(0, str(SCRIPTS))


class FullPagePreviewTests(unittest.TestCase):
    def setUp(self):
        from confirm_ui.server import create_app
        from template_selection import prepare

        self.tmp = tempfile.TemporaryDirectory(dir=CACHE)
        project = Path(self.tmp.name)
        prepare(project)
        self.client = create_app(str(project), idle_timeout=0).test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_baseline_deck_exposes_every_real_page(self):
        response = self.client.get("/api/deck-pages/6")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["available"])
        self.assertEqual(data["source_page_count"], 15)
        self.assertEqual(data["preview_count"], 15)
        self.assertTrue(data["complete"])
        self.assertEqual(len(data["pages"]), 15)
        self.assertTrue(all(page["preview"] for page in data["pages"]))
        self.assertEqual(data["pages"][0]["slide"], 1)
        self.assertEqual(data["pages"][-1]["slide"], 15)
        # The gallery must be able to describe capacity and non-text content.
        for page in data["pages"]:
            self.assertIn("slot_count", page)
            self.assertIn("tables", page)
            self.assertIn("charts", page)
            self.assertIn("layout", page)

    def test_full_page_preview_image_is_served(self):
        response = self.client.get("/previews/full/06/01.jpg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/jpeg")
        self.assertGreater(len(response.data), 10_000)
        self.assertEqual(response.data[:2], b"\xff\xd8")
        response.close()

    def test_deck_without_native_index_is_reported_honestly(self):
        response = self.client.get("/api/deck-pages/3")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["available"])
        self.assertEqual(data["reason"], "no_native_page_index")
        self.assertFalse(data["complete"])

    def test_every_native_deck_has_full_page_previews(self):
        from template_selection import catalog
        checked = 0
        for deck in catalog():
            if "native" not in deck["routes"]:
                continue
            data = self.client.get(f"/api/deck-pages/{deck['number']}").get_json()
            self.assertTrue(
                data["complete"],
                f"{deck['name']}: {data['preview_count']}/{data['source_page_count']} previews",
            )
            self.assertGreater(data["source_page_count"], 0)
            checked += 1
        self.assertEqual(checked, 14)

    def test_unknown_template_is_rejected(self):
        self.assertEqual(self.client.get("/api/deck-pages/999").status_code, 404)
        self.assertEqual(self.client.get("/previews/full/999/01.jpg").status_code, 404)

    def test_gallery_locks_native_route_and_uses_full_pages(self):
        js = (STATIC / "gallery.js").read_text(encoding="utf-8")
        self.assertIn("/api/deck-pages/", js)
        self.assertIn("nativeReady ? 'native'", js)
        self.assertIn("LAYOUT_LABELS[page.layout]", js)
        self.assertNotIn("$('route').value = 'svg'", js)
        html = (STATIC / "gallery.html").read_text(encoding="utf-8")
        self.assertIn('id="pages"', html)
        self.assertIn('value="native"', html)
        self.assertNotIn("比较封面与正文", html)


if __name__ == "__main__":
    unittest.main()
