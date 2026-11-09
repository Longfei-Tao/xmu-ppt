"""文本容量应按演示文稿页序读取 XML 元数据。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/xmu-ppt/scripts"
CACHE = ROOT / ".cache"
CACHE.mkdir(exist_ok=True)
sys.path.insert(0, str(SCRIPTS))

from template_fill_pptx.analyzer import analyze_pptx  # noqa: E402
from template_fill_pptx.applier import apply_plan  # noqa: E402
import text_fit  # noqa: E402


class CapacitySlideOrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=CACHE)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.pptx"
        self.presentation = Presentation()
        for word_wrap in (False, True):
            slide = self.presentation.slides.add_slide(self.presentation.slide_layouts[6])
            box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
            box.text_frame.word_wrap = word_wrap
            box.text_frame.text = "Source text"
            box.text_frame.paragraphs[0].runs[0].font.size = Pt(24)

    def test_reordered_slides_keep_their_own_wrap_metadata(self):
        slide_ids = self.presentation.slides._sldIdLst
        slide_ids.insert(0, slide_ids[-1])
        self.presentation.save(self.source)

        capacity = text_fit.build_capacity_map(self.source, analyze_pptx(self.source))

        self.assertEqual(capacity["s01_sh2"]["wrap"], "square")
        self.assertEqual(capacity["s02_sh2"]["wrap"], "none")
        self.assertEqual(capacity["s02_sh2"]["max_lines"], 1)

    def test_cloned_slide_uses_its_referenced_part_metadata(self):
        self.presentation.save(self.source)
        output = self.root / "cloned.pptx"
        apply_plan(self.source, {"slides": [{"source_slide": 1}]}, output)

        capacity = text_fit.build_capacity_map(output, analyze_pptx(output))

        self.assertEqual(capacity["s01_sh2"]["wrap"], "none")
        self.assertEqual(capacity["s01_sh2"]["max_lines"], 1)
        plan = {"slides": [{"source_slide": 1, "replacements": [
            {"slot_id": "s01_sh2", "text": "A" * 60},
        ]}]}
        with self.assertRaises(text_fit.TextOverflowError):
            text_fit.enforce_plan(plan, capacity)


if __name__ == "__main__":
    unittest.main()
