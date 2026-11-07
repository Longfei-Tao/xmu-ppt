"""段落内多行文本必须写成 <a:br/>，不能塞进同一个 <a:t>。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "xmu-ppt" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from template_fill_pptx.ooxml import NS  # noqa: E402
from template_fill_pptx.text_fill import _set_paragraph_text  # noqa: E402

A = NS["a"]


def paragraph() -> ET.Element:
    return ET.fromstring(
        f'<a:p xmlns:a="{A}">'
        '<a:pPr algn="l"/>'
        '<a:r><a:rPr sz="2400" b="1"/><a:t>原始文字</a:t></a:r>'
        '<a:endParaRPr sz="2400"/>'
        "</a:p>"
    )


class ParagraphTextTests(unittest.TestCase):
    def test_single_line_keeps_one_run(self):
        p = paragraph()
        _set_paragraph_text(p, "单行文案")
        self.assertEqual(len(p.findall("a:r", NS)), 1)
        self.assertEqual(p.find("a:r/a:t", NS).text, "单行文案")
        self.assertEqual(len(p.findall("a:br", NS)), 0)

    def test_multi_line_inserts_real_breaks(self):
        p = paragraph()
        _set_paragraph_text(p, "第一行\n第二行\n第三行")
        self.assertEqual(len(p.findall("a:br", NS)), 2, "三行应有两次换行")
        texts = [node.text for node in p.findall("a:r/a:t", NS)]
        self.assertEqual(texts, ["第一行", "第二行", "第三行"])
        self.assertEqual(len(p.findall("a:r", NS)), 3)

    def test_run_properties_are_reused(self):
        p = paragraph()
        _set_paragraph_text(p, "粗体一\n粗体二")
        for run in p.findall("a:r", NS):
            props = run.find("a:rPr", NS)
            self.assertIsNotNone(props, "换行后的 run 必须保留原字号与字重")
            self.assertEqual(props.get("sz"), "2400")
            self.assertEqual(props.get("b"), "1")

    def test_end_paragraph_properties_stay_last(self):
        p = paragraph()
        _set_paragraph_text(p, "上\n下")
        self.assertEqual(p[-1].tag, f"{{{A}}}endParaRPr", "endParaRPr 必须留在段落末尾")

    def test_creates_text_node_when_missing(self):
        p = ET.fromstring(f'<a:p xmlns:a="{A}"><a:pPr algn="ctr"/></a:p>')
        _set_paragraph_text(p, "补写\n第二行")
        self.assertEqual([n.text for n in p.findall("a:r/a:t", NS)], ["补写", "第二行"])

    def test_empty_paragraph_inherits_fallback_properties(self):
        p = ET.fromstring(f'<a:p xmlns:a="{A}"><a:pPr algn="l"/></a:p>')
        fallback = ET.fromstring(
            f'<a:rPr xmlns:a="{A}" sz="2000"><a:solidFill><a:srgbClr val="1F4E79"/></a:solidFill></a:rPr>'
        )
        _set_paragraph_text(p, "第一行\n第二行", fallback)
        for run in p.findall("a:r", NS):
            props = run.find("a:rPr", NS)
            self.assertIsNotNone(props, "空段落必须继承同形状首个 run 的格式")
            self.assertEqual(props.get("sz"), "2000")
            self.assertIsNotNone(props.find("a:solidFill", NS))

    def test_color_override_replaces_existing_fill(self):
        p = paragraph()
        _set_paragraph_text(p, "深色背景上的白字", color="#FFFFFF")
        color = p.find("a:r/a:rPr/a:solidFill/a:srgbClr", NS)
        self.assertIsNotNone(color)
        self.assertEqual(color.get("val"), "FFFFFF")

    def test_color_applies_to_every_wrapped_line(self):
        p = paragraph()
        _set_paragraph_text(p, "第一行\n第二行\n第三行", color="1F4E79")
        for run in p.findall("a:r", NS):
            color = run.find("a:rPr/a:solidFill/a:srgbClr", NS)
            self.assertIsNotNone(color, "每一行都必须带上指定颜色")
            self.assertEqual(color.get("val"), "1F4E79")


if __name__ == "__main__":
    unittest.main()
