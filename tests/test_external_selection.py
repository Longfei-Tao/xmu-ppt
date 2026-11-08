"""Local-only external decks in the picker: grouping, previews, Native gate.

These tests skip themselves on a fresh clone (no ``local-gallery/``), which is
exactly the public, redistributable state of the repository.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/xmu-ppt/scripts"
CACHE = ROOT / ".cache"
CACHE.mkdir(exist_ok=True)
sys.path.insert(0, str(SCRIPTS))

import external_selection as ext  # noqa: E402

HAS_GALLERY = ext.available()


@unittest.skipUnless(HAS_GALLERY, "本机画廊未生成（全新 clone 的正常状态）")
class ExternalSelectionTests(unittest.TestCase):
    def test_01_decks_are_local_only_native(self):
        decks = ext.decks()
        self.assertEqual(len(decks), 188)
        self.assertTrue(all(d["namespace"] == "external" for d in decks))
        self.assertTrue(all(d["routes"] == ["native"] for d in decks))
        self.assertTrue(all(d["preview"].startswith("previews/external/") for d in decks))
        self.assertEqual(min(d["number"] for d in decks), 16)
        self.assertEqual(len({d["number"] for d in decks}), len(decks))

    def test_02_ids_match_number_registry(self):
        registry = json.loads(ext.REGISTRY.read_text(encoding="utf-8"))
        known = {e["template_id"] for e in registry["entries"]
                 if e["namespace"] == "external"}
        self.assertTrue({d["id"] for d in ext.decks()} <= known)

    def test_03_first_deck_has_complete_page_previews(self):
        number = ext.decks()[0]["number"]
        data = ext.pages(number)
        self.assertTrue(data["available"])
        self.assertTrue(data["complete"], data)
        self.assertEqual(data["source_page_count"], data["preview_count"])
        self.assertTrue(data["pages"][0]["preview"].startswith(
            f"previews/external/{number}/"))
        self.assertIsNotNone(ext.cover(number))
        self.assertIsNotNone(ext.page_image(number, 1))

    def test_04_source_path_points_to_existing_original(self):
        deck = ext.decks()[0]
        path = ext.source_path(deck["id"])
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file(), path)
        self.assertEqual(path.suffix.lower(), ".pptx")

    def test_05_selection_gate_accepts_external_native_only(self):
        from template_selection import _validate
        deck = ext.decks()[0]
        resolved = _validate(deck["id"], "native")
        self.assertEqual(resolved["namespace"], "external")
        with self.assertRaises(ValueError):
            _validate(deck["id"], "svg")

    def test_06_public_catalog_still_has_only_15_decks(self):
        public = json.loads((ROOT / "docs/templates/catalog.json").read_text(
            encoding="utf-8"))
        self.assertEqual(len(public), 15)

    def test_10_source_key_comes_from_scanned_catalog_even_with_empty_registry(self):
        """纯技能包会重置注册表；定位原件不能依赖旧条目碰巧命中。"""
        self.assertTrue(ext._catalog_source_keys())
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            empty = Path(tmp) / "number_registry.json"
            empty.write_text(json.dumps({"schema": "template_number_registry.v1",
                                         "entries": []}), encoding="utf-8")
            with mock.patch.object(ext, "REGISTRY", empty):
                decks = ext.decks()
                self.assertTrue(decks)
                self.assertTrue(all(d["source_key"] for d in decks))

    def test_11_source_path_survives_empty_registry(self):
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            empty = Path(tmp) / "number_registry.json"
            empty.write_text(json.dumps({"schema": "template_number_registry.v1",
                                         "entries": []}), encoding="utf-8")
            deck = ext.decks()[0]
            with mock.patch.object(ext, "REGISTRY", empty), \
                    mock.patch.object(ext, "IMPORTED", Path(tmp) / "no-import-cache"):
                path = ext.source_path(deck["id"])
                self.assertIsNotNone(path)
                self.assertTrue(path.is_file(), path)


@unittest.skipUnless(HAS_GALLERY, "本机画廊未生成（全新 clone 的正常状态）")
class ExternalGalleryAPITests(unittest.TestCase):
    def setUp(self):
        from confirm_ui.server import create_app
        from template_selection import prepare
        self.tmp = tempfile.TemporaryDirectory(dir=CACHE)
        self.project = Path(self.tmp.name)
        prepare(self.project)
        self.client = create_app(str(self.project), idle_timeout=0).test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_07_templates_api_groups_builtin_and_local(self):
        data = self.client.get("/api/templates").get_json()
        builtin = [d for d in data if d["namespace"] == "builtin"]
        external = [d for d in data if d["namespace"] == "external"]
        self.assertEqual(len(builtin), 15)
        self.assertEqual(len(external), 188)

    def test_08_external_pages_and_images_are_served(self):
        number = ext.decks()[0]["number"]
        data = self.client.get(f"/api/deck-pages/{number}").get_json()
        self.assertTrue(data["available"])
        self.assertTrue(data["complete"])
        cover = self.client.get(f"/previews/external/{number}.webp")
        self.assertEqual(cover.status_code, 200)
        self.assertEqual(cover.mimetype, "image/webp")
        cover.close()
        page = self.client.get(f"/previews/external/{number}/01.webp")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.mimetype, "image/webp")
        page.close()

    def test_09_confirm_external_records_original_path(self):
        deck = ext.decks()[0]
        rid = self.client.get("/api/recommendations").get_json()["request_id"]
        response = self.client.post("/api/template-confirm", json={
            "request_id": rid, "template_id": deck["id"], "route": "native"})
        self.assertEqual(response.status_code, 200, response.get_json())
        result = json.loads((self.project / "confirm_ui/result.json").read_text(
            encoding="utf-8"))
        self.assertEqual(result["namespace"], "external")
        self.assertEqual(result["template_id"], deck["id"])
        self.assertTrue(Path(result["source_path"]).is_file())


class SkillOnlyPackageTests(unittest.TestCase):
    """A release ZIP has no built-in originals/covers; the picker must survive."""

    def test_catalog_skips_decks_without_covers(self):
        import template_selection
        from unittest import mock
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            with mock.patch.object(template_selection, "DECKS", Path(tmp)):
                self.assertEqual(template_selection.catalog(), [])


if __name__ == "__main__":
    unittest.main()
