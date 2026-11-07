"""默认出稿流程与净化的回归测试（自造样本，不依赖桌面模板原件）。"""
from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from PIL import Image
from pptx import Presentation
from pptx.util import Inches

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "xmu-ppt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import idea_to_ppt as flow  # noqa: E402
import sanitize_pptx as sp  # noqa: E402


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (20, 90, 160)).save(buf, "PNG")
    return buf.getvalue()


def _fixture(path: Path) -> None:
    """造一个 3 页 PPTX，并注入音乐部件、音频关系与自动换片设置。"""
    prs = Presentation()
    blank = prs.slide_layouts[6]
    for i in range(3):
        slide = prs.slides.add_slide(blank)
        box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
        box.text_frame.text = f"标题 {i + 1}"
        slide.shapes.add_picture(str(path.parent / "pic.png"), Inches(6), Inches(2), width=Inches(1))
    prs.save(str(path))

    with zipfile.ZipFile(path) as zf:
        data = {i.filename: zf.read(i.filename) for i in zf.infolist() if not i.is_dir()}

    first = data["ppt/slides/slide1.xml"]
    assert b"</p:sld>" in first
    data["ppt/slides/slide1.xml"] = first.replace(
        b"</p:sld>", b'<p:transition spd="med" advTm="5000"/></p:sld>', 1
    )
    data["ppt/media/audio1.wav"] = b"RIFF\x00\x00\x00\x00WAVEfake"
    rels_name = "ppt/slides/_rels/slide1.xml.rels"
    rels = data.get(rels_name, b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
    rels = rels.replace(
        b"</Relationships>",
        b'<Relationship Id="rIdAudio" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/audio" Target="../media/audio1.wav"/>'
        b'<Relationship Id="rIdMedia" Type="http://schemas.microsoft.com/office/2007/relationships/media" Target="../media/audio1.wav"/>'
        b"</Relationships>",
    )
    data[rels_name] = rels
    ct = data["[Content_Types].xml"]
    data["[Content_Types].xml"] = ct.replace(
        b"</Types>", b'<Default Extension="wav" ContentType="audio/x-wav"/></Types>', 1
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in data.items():
            zf.writestr(name, payload)


class SanitizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        (cls.root / "pic.png").write_bytes(_png())
        cls.source = cls.root / "dirty.pptx"
        _fixture(cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_01_fixture_is_dirty(self):
        report = sp.scan(self.source)
        self.assertFalse(report["clean"])
        self.assertEqual(report["audio_parts"], 1)
        self.assertGreaterEqual(report["audio_relationships"], 1)
        self.assertGreaterEqual(report["auto_advance"], 1)

    def test_02_sanitize_removes_music_and_auto_advance_but_keeps_layout(self):
        out = self.root / "clean.pptx"
        result = sp.sanitize(self.source, out)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["after"]["clean"])
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            self.assertNotIn("ppt/media/audio1.wav", names)
            xml = zf.read("ppt/slides/slide1.xml").decode("utf-8")
            self.assertNotIn("advTm", xml)
            self.assertNotIn("rIdAudio", zf.read("ppt/slides/_rels/slide1.xml.rels").decode("utf-8"))
            self.assertIn("标题 1", xml)
        before = Presentation(str(self.source))
        after = Presentation(str(out))
        self.assertEqual(len(after.slides), 3)
        for i in range(3):
            self.assertEqual(len(before.slides[i].shapes), len(after.slides[i].shapes),
                             "净化不得增删页面元素")
        self.assertIn("p:transition", xml, "切换动画应保留，只去掉自动换片时间")

    def test_03_clean_text_handles_all_music_patterns(self):
        xml = (
            '<p:sld><p:transition spd="med" advTm="6121"/>'
            '<p:timing><p:audio><p:cMediaNode/></p:audio></p:timing>'
            '<a:audioFile r:link="rId2"/>'
            '<p:ext><p14:media r:embed="rId3"/></p:ext>'
            '<a:hlinkClick r:id="" action="ppaction://media"/>'
            '<p:showPr loop="1" useTimings="1"/></p:sld>'
        )
        stats = {k: 0 for k in (
            "audio_relationships", "audio_defaults", "audio_nodes", "audio_refs",
            "media_ext", "media_refs", "media_actions", "sound_actions",
            "sound_nodes", "media_controls", "auto_advance",
            "forced_auto", "show_timings", "parts_changed",
        )}
        out = sp.clean_text("ppt/slides/slide1.xml", xml, stats)
        for token in ("advTm", "<p:audio", "<a:audioFile", "<p14:media", "ppaction://media"):
            self.assertNotIn(token, out, token)
        self.assertIn("p:transition", out)
        self.assertGreaterEqual(stats["auto_advance"], 1)
        self.assertGreaterEqual(stats["audio_nodes"], 1)

    def test_04_in_place_skips_when_already_clean(self):
        clean = self.root / "clean.pptx"
        before = clean.read_bytes()
        result = sp.sanitize(clean, clean, in_place=True)
        self.assertTrue(result.get("unchanged"))
        self.assertEqual(clean.read_bytes(), before, "已干净时不得重写二进制")


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gate = Path(self.tmp.name) / "gate.json"
        self.patcher = mock.patch.object(flow, "GATE_FILE", self.gate)
        self.patcher.start()
        # addCleanup 保证即使断言失败也会还原模块常量，避免污染其它测试
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_05_recommend_is_waiting_and_has_clickable_links(self):
        gate = flow.recommend("癌症科普", "医护健康科普", limit=6)
        self.assertEqual(gate["status"], "waiting")
        self.assertGreater(len(gate["candidates"]), 0)
        self.assertIn("file://", gate["markdown"])
        self.assertIn("看每一页", gate["markdown"])
        self.assertEqual(json.loads(self.gate.read_text(encoding="utf-8"))["status"], "waiting")

    def test_06_build_is_blocked_until_user_confirms(self):
        flow.recommend("癌症科普", "医护健康科普", limit=6)
        with self.assertRaisesRegex(RuntimeError, "门禁"):
            flow.require_confirmed({"template_id": "MED-001"})

    def test_07_confirm_allows_gallery_choice_outside_candidates(self):
        flow.recommend("癌症科普", "医护健康科普", limit=6)
        # 004 是真实固定序号（光影厦大），且不在本次候选里：验证清单外仍可选
        with mock.patch.object(flow, "resolve_source", return_value=(
            {"name": "光影厦大", "pages": 9}, Path("dummy.pptx")
        )):
            gate = flow.confirm("004")
        self.assertEqual(gate["status"], "confirmed")
        self.assertEqual(gate["serial"], "004")
        self.assertTrue(gate["outside_candidates"])
        self.assertEqual(flow.require_confirmed({"template_id": "004"})["status"], "confirmed")
        with self.assertRaisesRegex(RuntimeError, "不一致"):
            flow.require_confirmed({"template_id": "MED-001"})

    def test_08_page_layouts_are_grouped_by_role(self):
        # 只用内存 library 验证版式清单结构，不依赖桌面原件；004 走权威序号解析
        with mock.patch.object(flow, "resolve_source", return_value=({}, Path("x"))), \
             mock.patch.object(flow, "analyze_pptx", return_value={
                 "slides": [
                     {"slide_index": 1, "page_type": "cover_candidate", "slots": [], "text_summary": "封面"},
                     {"slide_index": 2, "page_type": "content_candidate", "slots": [{}], "text_summary": "正文"},
                 ]
             }):
            data = flow.page_layouts("004")
        self.assertEqual(data["slide_count"], 2)
        self.assertEqual(data["pages"][0]["page_type"], "cover_candidate")

    def test_09_non_medical_topic_avoids_medical_decks(self):
        gate = flow.recommend(
            "大学生职业规划，包含自我认知、行业与岗位分析、目标设定与行动计划",
            "大学生职业规划课程", limit=8,
        )
        ids = gate["candidates"]
        self.assertFalse([i for i in ids if i.startswith("MED-")], ids)
        self.assertGreaterEqual(
            sum(1 for i in ids if i.startswith("厦门大学_")), 6,
            f"非医学主题应以厦大校园模板为主：{ids}",
        )

    def test_10_medical_topic_still_returns_clinical_decks(self):
        gate = flow.recommend("胃癌术后护理与随访", "临床医护", limit=5)
        self.assertTrue(any(i.startswith("MED-") for i in gate["candidates"]))


if __name__ == "__main__":
    unittest.main()
