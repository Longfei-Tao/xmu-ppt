"""素材边界：台账覆盖、发布声明与外部模板隔离。"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_assets as assets  # noqa: E402


class AssetBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(assets.MANIFEST.read_text(encoding="utf-8"))
        cls.catalogue = json.loads(assets.CATALOG.read_text(encoding="utf-8"))
        cls.result = assets.check(verify_hashes=False)

    def test_01_boundary_check_has_no_errors(self):
        self.assertEqual(self.result["errors"], [])
        self.assertTrue(self.result["ok"])

    def test_02_every_catalogue_deck_is_registered(self):
        manifest_ids = {d["deck_id"] for d in self.manifest["decks"]}
        catalogue_ids = {d["id"] for d in self.catalogue}
        self.assertEqual(manifest_ids, catalogue_ids)
        self.assertEqual(len(self.manifest["decks"]), 15)

    def test_03_serials_are_unique_and_complete(self):
        serials = [d["serial"] for d in self.manifest["decks"]]
        self.assertEqual(len(serials), len(set(serials)))
        self.assertTrue(all(len(s) == 3 and s.isdigit() for s in serials))

    def test_04_public_claim_requires_a_license(self):
        for deck in self.manifest["decks"]:
            uses = set(deck["allowed_uses"])
            if uses & {"public", "commercial"}:
                self.assertNotEqual(deck["license_status"], "unknown", deck["deck_id"])
                self.assertTrue(deck.get("license"), deck["deck_id"])
        for surface in self.manifest["surfaces"]:
            if set(surface["allowed_uses"]) & {"public", "commercial"}:
                self.assertNotEqual(surface["license_status"], "unknown", surface["path"])

    def test_05_external_library_is_not_redistributable(self):
        entries = json.loads(assets.LICENSES.read_text(encoding="utf-8"))["entries"]
        self.assertEqual(len(entries), 200)
        self.assertEqual([e["id"] for e in entries if e.get("redistributable")], [])
        self.assertEqual(assets.tracked_external_pptx(), [])

    def test_06_license_boundary_files_exist(self):
        self.assertIn("MIT License", assets.LICENSE.read_text(encoding="utf-8"))
        boundary = assets.ASSET_BOUNDARY.read_text(encoding="utf-8")
        for token in ("Not covered by MIT", "allowed_uses", "commercial"):
            self.assertIn(token, boundary)

    def test_07_source_hashes_match(self):
        result = assets.check(verify_hashes=True)
        self.assertEqual(result["errors"], [], result["errors"])


if __name__ == "__main__":
    unittest.main()
