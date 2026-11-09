"""品牌层与版式层：唯一真源、色板约束与输出契约。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/xmu-ppt/scripts"
CACHE = ROOT / ".cache"
CACHE.mkdir(exist_ok=True)
sys.path.insert(0, str(SCRIPTS))

import brand  # noqa: E402
import idea_to_ppt  # noqa: E402
from template_fill_pptx.scaffolder import scaffold_plan  # noqa: E402


class BrandLayerTests(unittest.TestCase):
    def test_validate_repo_is_clean(self):
        self.assertEqual(brand.validate_repo(), [])

    def test_every_deck_declares_its_brand(self):
        decks = sorted(p.name for p in brand.DECKS.iterdir() if p.is_dir())
        self.assertEqual(len(decks), 15)
        index = brand.brand_index()
        for deck_id in decks:
            with self.subTest(deck=deck_id):
                deck = brand.load_deck_brand(deck_id)
                self.assertIsNotNone(deck, f"{deck_id} 缺少 brand.json")
                self.assertEqual(deck["schema"], brand.SCHEMA_DECK_BRAND)
                self.assertIn(deck["brand_id"], index)
                self.assertTrue(brand.is_hex(deck["primary_color"]))

    def test_primary_color_agrees_with_deck_index(self):
        index = json.loads(
            (brand.DECKS / "decks_index.json").read_text(encoding="utf-8")
        )
        for deck_id, meta in index.items():
            with self.subTest(deck=deck_id):
                deck = brand.load_deck_brand(deck_id)
                self.assertEqual(
                    deck["primary_color"].upper(), meta["primary_color"].upper()
                )

    def test_brand_preset_matches_its_index(self):
        for brand_id, meta in brand.brand_index().items():
            with self.subTest(brand=brand_id):
                preset = brand.load_brand(brand_id)
                self.assertIsNotNone(preset)
                self.assertEqual(
                    preset["primary_color"].upper(), meta["primary_color"].upper()
                )
                self.assertTrue(brand.brand_colors(preset))

    def test_palette_covers_brand_and_deck_primary(self):
        deck_id = "厦门大学_主题_经典蓝白"
        values = set(brand.palette(deck_id))
        deck = brand.load_deck_brand(deck_id)
        preset = brand.load_brand(deck["brand_id"])
        self.assertIn(deck["primary_color"].upper(), values)
        self.assertIn(preset["primary_color"].upper(), values)

    def test_arbitrary_colour_is_rejected(self):
        deck_id = "厦门大学_主题_经典蓝白"
        self.assertTrue(brand.is_allowed_color(deck_id, "#02367B"))
        self.assertTrue(brand.is_allowed_color(deck_id, "#204080"))
        self.assertFalse(brand.is_allowed_color(deck_id, "#FF00FF"))
        self.assertFalse(brand.is_allowed_color(deck_id, "red"))
        # 未指定颜色 = 沿用原槽位，永远允许
        self.assertTrue(brand.is_allowed_color(deck_id, None))

    def test_declared_logo_matches_brand_preset(self):
        preset = brand.load_brand("厦门大学")
        expected = preset["logo"]["sha256"]
        checked = 0
        for deck_id in sorted(p.name for p in brand.DECKS.iterdir() if p.is_dir()):
            deck = brand.load_deck_brand(deck_id)
            entry = deck.get("logo") or {}
            if not entry.get("file"):
                continue
            checked += 1
            self.assertEqual(entry["sha256"], expected, deck_id)
        self.assertGreaterEqual(checked, 3)

    def test_describe_exposes_typography_and_rules(self):
        block = brand.describe("厦门大学_官方_厦园晴日")
        self.assertEqual(block["brand_id"], "厦门大学")
        self.assertEqual(block["primary_color"], "#005FA5")
        self.assertIn("title", block["typography"])
        self.assertIn("body", block["typography"])
        self.assertIn("stretch", block["logo"]["forbidden"])
        self.assertFalse(block["voice"]["emoji"])


class BrandOutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=CACHE)
        self.root = Path(self.tmp.name)
        self._old = {
            "gate": idea_to_ppt.GATE_FILE,
            "sanitized": idea_to_ppt.SANITIZED_DIR,
            "reports": idea_to_ppt.REPORT_DIR,
        }
        idea_to_ppt.GATE_FILE = self.root / ".selection.json"
        idea_to_ppt.SANITIZED_DIR = self.root / "sanitized"
        idea_to_ppt.REPORT_DIR = self.root / "checks"

    def tearDown(self):
        idea_to_ppt.GATE_FILE = self._old["gate"]
        idea_to_ppt.SANITIZED_DIR = self._old["sanitized"]
        idea_to_ppt.REPORT_DIR = self._old["reports"]
        self.tmp.cleanup()

    def test_pages_output_carries_brand_block(self):
        data = idea_to_ppt.page_layouts("014")
        block = data.get("brand")
        self.assertIsNotNone(block)
        self.assertEqual(block["brand_id"], "厦门大学")
        self.assertEqual(block["primary_color"], "#02367B")
        self.assertIn("#02367B", block["palette"])
        self.assertIn("title", block["typography"])

    def test_user_template_gets_no_borrowed_brand(self):
        data = {"template_id": "用户模板", "pages": []}
        marked = idea_to_ppt._with_brand(
            dict(data), "用户模板", {"namespace": "user"}
        )
        self.assertNotIn("brand", marked)

    def test_stray_colour_becomes_warning(self):
        plan = {
            "template_id": "厦门大学_主题_经典蓝白",
            "slides": [{"replacements": [{"slot_id": "a", "text": "x", "color": "#FF00FF"}]}],
        }
        colors = idea_to_ppt._plan_colors(plan)
        self.assertEqual(colors, ["#FF00FF"])
        allowed = set(brand.palette(plan["template_id"]))
        self.assertNotIn("#FF00FF", allowed)

    def test_build_warns_but_does_not_block_on_stray_colour(self):
        """写错颜色要报出来，但不能因此拒绝交付一份本来合格的稿子。"""
        idea_to_ppt.recommend("论文答辩", "毕业答辩", limit=6)
        idea_to_ppt.confirm("014")
        deck = "厦门大学_主题_经典蓝白"
        library = json.loads(
            (idea_to_ppt.DECKS / deck / "source.slide_library.json").read_text(
                encoding="utf-8"
            )
        )
        plan = scaffold_plan(library, [1, 4], include_empty=False)
        plan["template_id"] = "014"
        # 原文是长标题，先改短，否则会先卡在文字适配而不是品牌色
        plan["slides"][0]["replacements"][0]["text"] = "品牌层验收"
        plan["slides"][0]["replacements"][0]["color"] = "#FF00FF"
        plan_path = self.root / "plan.json"
        plan_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        result = idea_to_ppt.build(plan_path, self.root / "out.pptx")
        joined = " ".join(result["warnings"])
        self.assertIn("不在品牌色板内", joined)
        self.assertIn("#FF00FF", joined)
        self.assertTrue(result["ok"], result["errors"])


if __name__ == "__main__":
    unittest.main()
