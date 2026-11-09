"""本机用户模板入库与出稿链路。"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/xmu-ppt/scripts"
CACHE = ROOT / ".cache"
CACHE.mkdir(exist_ok=True)
sys.path.insert(0, str(SCRIPTS))

import idea_to_ppt  # noqa: E402
import user_templates  # noqa: E402
from template_fill_pptx.scaffolder import scaffold_plan  # noqa: E402


def make_pptx(path: Path) -> None:
    from pptx import Presentation

    prs = Presentation()
    for index, title in enumerate(("封面标题", "实验结果", "下一步"), start=1):
        layout = prs.slide_layouts[1] if index > 1 else prs.slide_layouts[0]
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = title
        if index > 1:
            body = slide.placeholders[1].text_frame
            body.text = f"第 {index} 页正文"
    prs.save(path)


class UserTemplateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=CACHE)
        self.root = Path(self.tmp.name)
        self.home = self.root / "user-templates"
        self._old = {
            "home": user_templates.HOME,
            "registry": user_templates.REGISTRY,
            "gallery": user_templates.GALLERY,
            "gate": idea_to_ppt.GATE_FILE,
            "sanitized": idea_to_ppt.SANITIZED_DIR,
            "reports": idea_to_ppt.REPORT_DIR,
        }
        user_templates.HOME = self.home
        user_templates.REGISTRY = self.home / "registry.local.json"
        user_templates.GALLERY = self.home / "index.html"
        idea_to_ppt.GATE_FILE = self.root / ".selection.json"
        idea_to_ppt.SANITIZED_DIR = self.root / "sanitized"
        idea_to_ppt.REPORT_DIR = self.root / "checks"
        self.pptx = self.root / "我的模板.pptx"
        make_pptx(self.pptx)

    def tearDown(self):
        user_templates.HOME = self._old["home"]
        user_templates.REGISTRY = self._old["registry"]
        user_templates.GALLERY = self._old["gallery"]
        idea_to_ppt.GATE_FILE = self._old["gate"]
        idea_to_ppt.SANITIZED_DIR = self._old["sanitized"]
        idea_to_ppt.REPORT_DIR = self._old["reports"]
        self.tmp.cleanup()

    def test_onboard_requires_rights_confirmation(self):
        with self.assertRaisesRegex(RuntimeError, "合法持有"):
            user_templates.onboard(self.pptx, name="我的模板", rights_confirmed=False)

    def test_rejects_macro_template(self):
        macro = self.root / "宏模板.pptm"
        macro.write_bytes(b"not a real pptm")
        with self.assertRaisesRegex(RuntimeError, "pptm"):
            user_templates.onboard(macro, rights_confirmed=True)

    def test_onboard_copies_registers_and_builds_gallery(self):
        result = user_templates.onboard(
            self.pptx, name="我的模板", rights_confirmed=True)
        self.assertEqual(result["serial"], "U001")
        self.assertEqual(result["slides"], 3)
        self.assertTrue((self.home / "U001" / "source.pptx").is_file())
        self.assertTrue((self.home / "U001" / "page_catalog.json").is_file())
        self.assertTrue((self.home / "index.html").is_file())
        self.assertEqual(user_templates.lookup("U001")["name"], "我的模板")
        self.assertEqual(user_templates.source_path(result["template_id"]).name, "source.pptx")

    def test_duplicate_does_not_create_u002(self):
        first = user_templates.onboard(self.pptx, name="我的模板", rights_confirmed=True)
        second = user_templates.onboard(self.pptx, name="重复", rights_confirmed=True)
        self.assertTrue(second["already_exists"])
        self.assertEqual(second["serial"], first["serial"])
        self.assertEqual(len(user_templates.list_templates()), 1)

    def test_onboard_preserves_embedded_thumbnail(self):
        thumbnail = io.BytesIO()
        Image.new("RGB", (960, 540), "red").save(thumbnail, "JPEG")
        with zipfile.ZipFile(self.pptx) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        entries["docProps/thumbnail.jpeg"] = thumbnail.getvalue()
        with zipfile.ZipFile(self.pptx, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries.items():
                archive.writestr(name, data)

        result = user_templates.onboard(self.pptx, rights_confirmed=True)

        with Image.open(self.home / result["serial"] / "previews" / "cover.webp") as cover:
            red, green, blue = cover.convert("RGB").getpixel((0, 0))
        self.assertGreater(red, 240)
        self.assertLess(green, 20)
        self.assertLess(blue, 20)

    def test_link_mode_keeps_original_path(self):
        result = user_templates.onboard(
            self.pptx, name="链接模板", link=True, rights_confirmed=True)
        self.assertEqual(result["serial"], "U001")
        self.assertFalse((self.home / "U001" / "source.pptx").exists())
        self.assertEqual(user_templates.source_path(result["template_id"]).resolve(),
                         self.pptx.resolve())

    def test_doctor_reports_missing_source(self):
        result = user_templates.onboard(self.pptx, name="我的模板", rights_confirmed=True)
        (self.home / "U001" / "source.pptx").unlink()
        report = user_templates.doctor()
        self.assertFalse(report["ok"])
        self.assertIn(result["serial"], report["errors"][0])

    def test_user_template_enters_recommend_confirm_and_build(self):
        result = user_templates.onboard(
            self.pptx, name="我的模板", rights_confirmed=True)
        gate = idea_to_ppt.recommend("组会汇报", "课题组组会", limit=8)
        self.assertIn(result["template_id"], gate["candidates"])
        confirmed = idea_to_ppt.confirm("U001")
        self.assertEqual(confirmed["template_id"], result["template_id"])
        self.assertEqual(confirmed["serial"], "U001")
        self.assertEqual(idea_to_ppt.page_layouts("U001")["slide_count"], 3)

        library = json.loads(
            (self.home / "U001" / "source.slide_library.json").read_text(encoding="utf-8"))
        plan = scaffold_plan(library, [1], include_empty=False)
        plan["template_id"] = result["template_id"]
        plan["slides"][0]["replacements"] = [
            {**replacement, "text": "测试标题"}
            for replacement in plan["slides"][0]["replacements"][:1]
        ]
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        built = idea_to_ppt.build(plan_path, self.root / "out.pptx")
        self.assertTrue(built["ok"], built)
        self.assertEqual(built["serial"], "U001")
        self.assertTrue((self.root / "out.pptx").is_file())
