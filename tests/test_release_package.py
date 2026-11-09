"""The skill-only release excludes display and template bitmaps."""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pack_release  # noqa: E402


class ReleasePackageTests(unittest.TestCase):
    def test_display_and_template_bitmaps_are_excluded(self):
        paths = (
            "docs/assets/screenshots/defense-cover.webp",
            "docs/preview/defense/01.webp",
            "docs/preview/group/01.webp",
            "docs/preview/native/01.webp",
            "examples/quickstart/preview/overview.png",
            "examples/厦大PPT模板总览.png",
            "skills/xmu-ppt/templates/decks/厦门大学_官方_厦园晴日/campus_bg.jpg",
            "skills/xmu-ppt/templates/decks/厦门大学_官方_南强蔚蓝/building.png",
            "skills/xmu-ppt/templates/decks/厦门大学_官方_凤栖青橙/paper_bg.jpg",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNotNone(pack_release.exclusion(path))

    def test_code_layouts_and_runtime_images_are_retained(self):
        paths = (
            "docs/quickstart.md",
            "examples/quickstart/svg_output/01_cover.svg",
            "skills/xmu-ppt/templates/decks/厦门大学_官方_厦园晴日/01_cover.svg",
            "skills/xmu-ppt/scripts/assets/bg_48.png",
            "skills/xmu-ppt/scripts/assets/bg_96.png",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNone(pack_release.exclusion(path))

    def test_selected_files_contain_no_display_or_template_bitmaps(self):
        kept, _ = pack_release.select()
        forbidden = [
            path for path in kept
            if path.startswith(("docs/", "examples/", "skills/xmu-ppt/templates/decks/"))
            and Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        ]
        self.assertEqual(forbidden, [])

    def test_audit_rejects_display_and_template_bitmaps(self):
        kept, _ = pack_release.select()
        for path in (
            "docs/assets/screenshots/defense-cover.webp",
            "skills/xmu-ppt/templates/decks/厦门大学_官方_南强蔚蓝/building.png",
        ):
            with self.subTest(path=path):
                problems = pack_release.audit(kept + [path])
                self.assertTrue(any(path in problem for problem in problems))

    def test_audit_preserves_nested_local_gallery_protection(self):
        kept, _ = pack_release.select()
        path = "nested/local-gallery/preview.png"
        problems = pack_release.audit(kept + [path])
        self.assertTrue(any(path in problem for problem in problems))

    def test_custom_output_creates_missing_alias_directory(self):
        required = [
            pack_release.NOTICES,
            pack_release.BUILTIN_CATALOG,
            *pack_release.RESET_INDEXES,
        ]
        with tempfile.TemporaryDirectory() as folder:
            dist = Path(folder) / "dist"
            output = Path(folder) / "custom" / "release.zip"
            with (
                patch.object(pack_release, "DIST", dist),
                patch.object(pack_release, "candidates", return_value=required),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(pack_release.main(["--out", str(output)]), 0)
            self.assertEqual(output.read_bytes(), (dist / "xmu-ppt-skill.zip").read_bytes())


if __name__ == "__main__":
    unittest.main()
