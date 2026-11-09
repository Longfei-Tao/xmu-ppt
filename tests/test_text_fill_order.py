"""回归：空表格单元格写入文字后，a:r 必须排在 a:endParaRPr 之前。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/xmu-ppt/scripts"
sys.path.insert(0, str(SCRIPTS))

from template_fill_pptx.ooxml import NS  # noqa: E402
from template_fill_pptx.text_fill import _set_container_text  # noqa: E402


class TextFillOrderTests(unittest.TestCase):
    def test_empty_cell_run_is_inserted_before_end_marker(self):
        xml = (
            '<a:tc xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            "<a:txBody><a:p><a:pPr algn=\"ctr\" /><a:endParaRPr lang=\"zh-CN\" />"
            "</a:p></a:txBody></a:tc>"
        )
        container = ET.fromstring(xml)
        _set_container_text(container, "可用", "#172033")
        paragraph = container.find(".//a:p", NS)
        tags = [child.tag.rsplit("}", 1)[-1] for child in list(paragraph)]
        self.assertIn("r", tags)
        self.assertLess(tags.index("r"), tags.index("endParaRPr"))
        self.assertEqual(paragraph.find("a:r/a:t", NS).text, "可用")


if __name__ == "__main__":
    unittest.main()
