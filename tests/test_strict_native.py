"""strict-native 严格保真路线的回归测试。

测试用 python-pptx 在临时目录自造一个 3 页 PPTX 作为样本，不依赖桌面上的
外部模板原件，也不会写入项目目录。样本里刻意放入：图片、未被引用的媒体部件、
页面切换效果 —— 这些正是"完整保留"最容易丢失的东西。
"""
from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.util import Inches

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "xmu-ppt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import strict_native as sn  # noqa: E402

FLAGS_ON = {"strict_native": True, "image_replace": True}
FLAGS_NO_IMAGE = {"strict_native": True, "image_replace": False}
FLAGS_OFF = {"strict_native": False}

SLIDE_RE = re.compile(r"ppt/slides/slide(\d+)\.xml$")
A_T_RE = re.compile(r"<a:t(?:\s[^>]*)?>(.*?)</a:t>", re.S)


def _png(color: tuple[int, int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buffer, "PNG")
    return buffer.getvalue()


def _build_fixture(path: Path) -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    for index in range(3):
        slide = prs.slides.add_slide(blank)
        title = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(1))
        title.text_frame.text = f"标题 {index + 1}"
        body = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(6), Inches(2))
        body.text_frame.text = f"说明 {index + 1}"
        if index == 0:
            slide.shapes.add_picture(str(path.parent / "pic.png"), Inches(8), Inches(2), width=Inches(2))
    prs.save(str(path))

    # 追加：页面切换效果 + 未被引用的媒体/备注部件（验证绝不被 GC 掉）
    with zipfile.ZipFile(path) as zf:
        data = {i.filename: zf.read(i.filename) for i in zf.infolist() if not i.is_dir()}
    first = data["ppt/slides/slide1.xml"]
    assert b"</p:sld>" in first
    data["ppt/slides/slide1.xml"] = first.replace(
        b"</p:sld>", b'<p:transition spd="med"><p:fade/></p:transition></p:sld>', 1
    )
    data["ppt/media/unused.png"] = _png((10, 20, 30))
    data["ppt/notesSlides/notesSlideUnused.xml"] = b'<?xml version="1.0" encoding="UTF-8"?><p:notes xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in data.items():
            zf.writestr(name, payload)


def _plan(*slides: dict) -> dict:
    return {
        "schema": sn.PLAN_SCHEMA,
        "template_id": "FIXTURE",
        "keep_all_slides": True,
        "slides": list(slides),
    }


def _read(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as zf:
        return {i.filename: zf.read(i.filename) for i in zf.infolist() if not i.is_dir()}


class StrictNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        (cls.root / "pic.png").write_bytes(_png((200, 30, 30)))
        (cls.root / "new.png").write_bytes(_png((30, 200, 30)))
        cls.source = cls.root / "fixture.pptx"
        _build_fixture(cls.source)
        slots = sn.inspect_slots(cls.source)["slides"]
        cls.first_slot = slots[0]["slots"][0]["slot_id"]
        cls.second_slot = slots[0]["slots"][1]["slot_id"]
        with zipfile.ZipFile(cls.source) as zf:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(zf.read("ppt/slides/slide1.xml"))
        cls.pic_shape_id = next(
            nv.get("id")
            for pic in root.iter(sn.qn("p", "pic"))
            for nv in [pic.find(".//" + sn.qn("p", "cNvPr"))]
            if nv is not None
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _apply(self, plan: dict, name: str = "out.pptx", **kwargs):
        output = self.root / name
        audit = sn.apply_strict(self.source, plan, output, flags=FLAGS_NO_IMAGE, **kwargs)
        return output, audit

    # ------------------------------------------------------------------
    def test_01_only_text_changed_everything_else_byte_identical(self):
        output, audit = self._apply(_plan({"slide": 1, "replacements": [
            {"slot_id": self.first_slot, "text": "新的年度汇报标题"}
        ]}))
        report = sn.verify_strict(self.source, output, audit)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["slide_count"], 3)
        self.assertTrue(report["slide_order_identical"])
        self.assertEqual(report["parts_changed"], 1)
        self.assertEqual(report["changed_parts"], ["ppt/slides/slide1.xml"])

        before, after = _read(self.source), _read(output)
        self.assertEqual(set(before), set(after), "部件集合不能被删减或新增")
        # 未被引用的媒体、备注部件、切换效果全部原样
        self.assertEqual(before["ppt/media/unused.png"], after["ppt/media/unused.png"])
        self.assertEqual(before["ppt/notesSlides/notesSlideUnused.xml"],
                         after["ppt/notesSlides/notesSlideUnused.xml"])
        self.assertEqual(before["ppt/presentation.xml"], after["ppt/presentation.xml"])
        self.assertEqual(before["[Content_Types].xml"], after["[Content_Types].xml"])
        self.assertEqual(before["ppt/slides/slide2.xml"], after["ppt/slides/slide2.xml"])
        self.assertEqual(before["ppt/slides/slide3.xml"], after["ppt/slides/slide3.xml"])
        self.assertIn(b"p:transition", after["ppt/slides/slide1.xml"])

        texts = A_T_RE.findall(after["ppt/slides/slide1.xml"].decode("utf-8"))
        self.assertIn("新的年度汇报标题", texts)
        self.assertIn("说明 1", texts, "未点名的文本框必须保留原示例文字")
        self.assertEqual(len(A_T_RE.findall(before["ppt/slides/slide1.xml"].decode("utf-8"))),
                         len(texts), "不得新增或删除文本节点")
        self.assertEqual(sn._canonical(before["ppt/slides/slide1.xml"]),
                         sn._canonical(after["ppt/slides/slide1.xml"]),
                         "除 <a:t> 内容外必须字节全等")

    def test_02_forbidden_plans_are_rejected(self):
        good_slide = {"slide": 1, "replacements": [{"slot_id": self.first_slot, "text": "X"}]}
        cases = {
            "关闭全页保留": {**_plan(good_slide), "keep_all_slides": False},
            "删页字段": {**_plan(good_slide), "remove_slides": [3]},
            "重排字段": {**_plan(good_slide), "slide_order": [3, 2, 1]},
            "复用页字段": {**_plan(good_slide), "duplicate_slides": [1]},
            "改切换效果": {**_plan(good_slide), "transition": "fade"},
            "页码乱序": _plan({"slide": 2, "replacements": []}, {"slide": 1, "replacements": []}),
            "页码越界": _plan({"slide": 9, "replacements": []}),
            "改备注": _plan({"slide": 1, "replacements": [], "notes": "hi"}),
            "replacement 夹带私货": _plan({"slide": 1, "replacements": [
                {"slot_id": self.first_slot, "text": "X", "table_edits": []}
            ]}),
            "schema 不对": {**_plan(good_slide), "schema": "template_fill_pptx_plan.v1"},
        }
        for label, plan in cases.items():
            with self.subTest(label), self.assertRaises(RuntimeError):
                self._apply(plan, f"bad-{label}.pptx")

    def test_03_image_replace_requires_all_three_gates(self):
        image_spec = {
            "shape_id": self.pic_shape_id,
            "asset": str(self.root / "new.png"),
            "user_specified": True,
        }
        plan = _plan({"slide": 1, "replacements": [], "image_replacements": [image_spec]})
        # 闸门 1：未给 CLI 授权
        with self.assertRaises(RuntimeError):
            self._apply(plan, "img-denied.pptx")
        # 闸门 2：feature flag 关闭
        with self.assertRaises(RuntimeError):
            sn.apply_strict(self.source, plan, self.root / "img-flag.pptx",
                            allow_image_replace=True, flags=FLAGS_NO_IMAGE)
        # 闸门 3：plan 未标注 user_specified
        bad = _plan({"slide": 1, "replacements": [], "image_replacements": [
            {**image_spec, "user_specified": False}
        ]})
        with self.assertRaises(RuntimeError):
            sn.apply_strict(self.source, bad, self.root / "img-noflag.pptx",
                            allow_image_replace=True, flags=FLAGS_ON)
        # 素材不存在 / 格式不一致也要拒绝
        missing = _plan({"slide": 1, "replacements": [], "image_replacements": [
            {**image_spec, "asset": str(self.root / "nope.png")}
        ]})
        with self.assertRaises(RuntimeError):
            sn.apply_strict(self.source, missing, self.root / "img-missing.pptx",
                            allow_image_replace=True, flags=FLAGS_ON)

    def test_04_authorized_image_replace_changes_only_that_media(self):
        plan = _plan({"slide": 1, "replacements": [], "image_replacements": [{
            "shape_id": self.pic_shape_id,
            "asset": str(self.root / "new.png"),
            "user_specified": True,
        }]})
        output = self.root / "img-ok.pptx"
        audit = sn.apply_strict(self.source, plan, output,
                                allow_image_replace=True, flags=FLAGS_ON)
        report = sn.verify_strict(self.source, output, audit)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(len(audit["changed_media"]), 1)
        self.assertEqual(audit["layout_adjusted_slides"], [])
        before, after = _read(self.source), _read(output)
        changed = {k for k in before if before[k] != after[k]}
        self.assertEqual(changed, set(audit["changed_media"]),
                         "档 1 原位换图：slide XML 与其它部件一律不得变化")
        self.assertEqual(before["ppt/media/unused.png"], after["ppt/media/unused.png"])
        self.assertEqual(after[audit["changed_media"][0]], (self.root / "new.png").read_bytes())

    def test_05_layout_adjustment_needs_extra_authorization(self):
        spec = {
            "shape_id": self.pic_shape_id,
            "asset": str(self.root / "new.png"),
            "user_specified": True,
            "layout_adjustment": {"x": "1000000", "y": "2000000"},
        }
        plan = _plan({"slide": 1, "replacements": [], "image_replacements": [spec]})
        with self.assertRaises(RuntimeError):
            sn.apply_strict(self.source, plan, self.root / "layout-denied.pptx",
                            allow_image_replace=True, flags=FLAGS_ON)
        output = self.root / "layout-ok.pptx"
        audit = sn.apply_strict(self.source, plan, output, allow_image_replace=True,
                                allow_layout_adjust=True, flags=FLAGS_ON)
        report = sn.verify_strict(self.source, output, audit)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(audit["layout_adjusted_slides"], [1])
        after = _read(output)
        self.assertIn(b'x="1000000"', after["ppt/slides/slide1.xml"])

    def test_06_multiline_never_adds_elements(self):
        plan = _plan({"slide": 1, "replacements": [
            {"slot_id": self.first_slot, "text": "第一行\n第二行\n第三行\n第四行"}
        ]})
        output, audit = self._apply(plan, "multiline.pptx")
        before, after = _read(self.source), _read(output)
        self.assertEqual(len(A_T_RE.findall(before["ppt/slides/slide1.xml"].decode("utf-8"))),
                         len(A_T_RE.findall(after["ppt/slides/slide1.xml"].decode("utf-8"))))
        self.assertEqual(sn._canonical(before["ppt/slides/slide1.xml"]),
                         sn._canonical(after["ppt/slides/slide1.xml"]))
        self.assertTrue(any("超出原文本节点数" in w for w in audit["warnings"]))

    def test_07_flag_off_disables_route(self):
        with self.assertRaises(RuntimeError):
            sn.apply_strict(self.source,
                            _plan({"slide": 1, "replacements": []}),
                            self.root / "off.pptx", flags=FLAGS_OFF)

    def test_08_verify_detects_unauthorized_tampering(self):
        output, audit = self._apply(_plan({"slide": 1, "replacements": [
            {"slot_id": self.first_slot, "text": "正常文案"}
        ]}), "tamper.pptx")
        # 伪造一个"顺手删掉未引用素材"的回归
        with zipfile.ZipFile(output) as zf:
            data = {i.filename: zf.read(i.filename) for i in zf.infolist() if not i.is_dir()}
        data.pop("ppt/media/unused.png")
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, payload in data.items():
                zf.writestr(name, payload)
        report = sn.verify_strict(self.source, output, audit)
        self.assertFalse(report["ok"])
        self.assertTrue(any("丢失" in e for e in report["errors"]))

    def test_09_scaffold_lists_all_slides_with_no_writes(self):
        plan = sn.scaffold_plan(self.source, "FIXTURE")
        self.assertEqual(plan["schema"], sn.PLAN_SCHEMA)
        self.assertTrue(plan["keep_all_slides"])
        self.assertEqual(len(plan["slides"]), 3)
        self.assertTrue(all(s["replacements"] == [] for s in plan["slides"]))
        output, audit = self._apply(plan, "noop.pptx")
        before, after = _read(self.source), _read(output)
        self.assertEqual(before, after, "空 plan 必须产出与原文件逐字节相同的 PPTX")
        self.assertEqual(audit["changed_slides"], [])


if __name__ == "__main__":
    unittest.main()
