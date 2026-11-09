"""内容策划案：结构校验、确认状态和出稿门禁。"""
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

import content_brief  # noqa: E402
import idea_to_ppt  # noqa: E402


def sample_brief() -> dict:
    brief = content_brief.new_brief(
        "本次组会汇报", "课题组组会", "导师和同组同学", 15, 3, "组会汇报")
    brief["sections"] = [{"id": "S1", "title": "实验结果", "purpose": "说明结果"}]
    brief["pages"] = [
        {
            "page_no": 1,
            "section_id": "S1",
            "purpose": "封面",
            "key_message": "本次组会汇报",
            "content_shape": ["cover"],
            "evidence": [],
            "data_status": "not_applicable",
        },
        {
            "page_no": 2,
            "section_id": "S1",
            "purpose": "说明实验设置",
            "key_message": "三组对照，统一数据划分",
            "content_shape": ["comparison", "table"],
            "evidence": [{"type": "file", "ref": "实验记录.md", "status": "provided"}],
            "data_status": "provided",
        },
    ]
    return brief


class ContentBriefTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=CACHE)
        self.root = Path(self.tmp.name)
        self._old_gate = idea_to_ppt.GATE_FILE
        idea_to_ppt.GATE_FILE = self.root / ".selection.json"

    def tearDown(self):
        idea_to_ppt.GATE_FILE = self._old_gate
        self.tmp.cleanup()

    def test_draft_can_be_empty_but_confirmed_cannot(self):
        draft = content_brief.new_brief("组会汇报", "课题组组会")
        self.assertEqual(draft["status"], "draft")
        self.assertEqual(content_brief.validate(draft), [])
        with self.assertRaisesRegex(ValueError, "至少需要一页"):
            content_brief.confirm(draft)

    def test_confirm_valid_brief_and_hash_is_stable(self):
        brief = sample_brief()
        before = content_brief.content_hash(brief)
        confirmed = content_brief.confirm(brief)
        self.assertEqual(confirmed["status"], "confirmed")
        self.assertTrue(confirmed["confirmed_at"])
        self.assertEqual(content_brief.content_hash(confirmed), before)
        self.assertEqual(content_brief.validate(confirmed, require_confirmed=True), [])

    def test_rejects_invalid_shape_and_duplicate_page(self):
        brief = sample_brief()
        brief["pages"][1]["content_shape"] = ["not-a-shape"]
        brief["pages"].append(dict(brief["pages"][0]))
        errors = content_brief.validate(brief, require_confirmed=True)
        self.assertTrue(any("未知类型" in error for error in errors), errors)
        self.assertTrue(any("重复" in error for error in errors), errors)

    def test_recommend_records_brief_hash_and_build_gate_checks_it(self):
        brief = content_brief.confirm(sample_brief())
        brief_path = self.root / "brief.json"
        content_brief.write(brief_path, brief)
        gate = idea_to_ppt.recommend("", "", limit=8, brief_path=brief_path)
        self.assertEqual(gate["brief_sha256"], content_brief.content_hash(brief))
        self.assertIn("内容策划案", gate["markdown"])
        # 模拟已确认模板；plan 缺 hash 或 hash 不一致都必须拒绝。
        idea_to_ppt._write(idea_to_ppt.GATE_FILE, {
            "status": "confirmed", "route": "native",
            "template_id": "测试模板", "serial": "001",
            "brief_sha256": gate["brief_sha256"],
        })
        with self.assertRaisesRegex(RuntimeError, "必须包含 brief_sha256"):
            idea_to_ppt.require_confirmed({"template_id": "测试模板"})
        with self.assertRaisesRegex(RuntimeError, "不一致"):
            idea_to_ppt.require_confirmed({
                "template_id": "测试模板",
                "brief_sha256": "wrong",
            })
        self.assertEqual(
            idea_to_ppt.require_confirmed({
                "template_id": "测试模板",
                "brief_sha256": gate["brief_sha256"],
            })["status"], "confirmed")

    def test_render_markdown_contains_page_purpose_and_gap(self):
        brief = sample_brief()
        brief["gaps"] = ["测试集结果尚未整理"]
        markdown = content_brief.render_markdown(brief)
        self.assertIn("说明实验设置", markdown)
        self.assertIn("测试集结果尚未整理", markdown)
        self.assertIn("待确认", markdown)


if __name__ == "__main__":
    unittest.main()
