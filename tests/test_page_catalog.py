"""页面语义目录与内容策划案的页面匹配。"""
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
import page_catalog  # noqa: E402

ITEM = {
    "id": "厦门大学_官方_厦园晴日",
    "namespace": "builtin",
}


def brief() -> dict:
    data = content_brief.new_brief("组会汇报", "课题组组会", "导师", 15, 2)
    data["pages"] = [
        {
            "page_no": 1,
            "purpose": "说明背景",
            "key_message": "研究问题",
            "content_shape": ["context"],
            "evidence": [],
            "data_status": "not_applicable",
        },
        {
            "page_no": 2,
            "purpose": "展示表格结果",
            "key_message": "结果表",
            "content_shape": ["table"],
            "evidence": [],
            "data_status": "provided",
        },
    ]
    return content_brief.confirm(data)


class PageCatalogTests(unittest.TestCase):
    def test_builtin_catalog_has_roles_and_shapes(self):
        catalog = page_catalog.for_item(ITEM)
        self.assertIsNotNone(catalog)
        self.assertEqual(catalog["pages"][0]["page_type"], "cover_candidate")
        self.assertIn("cover", catalog["pages"][0]["content_shapes"])
        rich = page_catalog.for_item({
            "id": "厦门大学_主题_经典蓝白", "namespace": "builtin"})
        self.assertTrue(any("table" in page["content_shapes"] or
                            "chart" in page["content_shapes"]
                            for page in rich["pages"]))

    def test_suggest_matches_context_and_falls_back_for_missing_table(self):
        catalog = page_catalog.for_item(ITEM)
        context_matches = page_catalog.suggest(catalog, brief()["pages"][0])
        self.assertTrue(context_matches)
        self.assertGreater(context_matches[0]["score"], 0)
        table_matches = page_catalog.suggest(catalog, brief()["pages"][1])
        self.assertTrue(table_matches)
        self.assertTrue(all(item["score"] == 0 for item in table_matches))
        self.assertIn("没有精确匹配", table_matches[0]["reason"])

    def test_with_brief_adds_page_suggestions(self):
        data = page_catalog.with_brief(page_catalog.for_item(ITEM), brief())
        self.assertEqual(len(data["brief_suggestions"]), 2)
        self.assertTrue(data["brief_suggestions"][0]["suggested_pages"])

    def test_pages_cli_data_contains_brief_suggestions(self):
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            path = Path(tmp) / "brief.json"
            content_brief.write(path, brief())
            old_gate = idea_to_ppt.GATE_FILE
            idea_to_ppt.GATE_FILE = Path(tmp) / ".selection.json"
            try:
                data = idea_to_ppt.page_layouts("001", path)
            finally:
                idea_to_ppt.GATE_FILE = old_gate
        self.assertEqual(data["template_id"], "厦门大学_官方_厦园晴日")
        self.assertIn("brief_suggestions", data)
        self.assertEqual(data["pages"][0]["page_type"], "cover_candidate")

    def test_recommend_surfaces_table_capable_template(self):
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            path = Path(tmp) / "brief.json"
            content_brief.write(path, brief())
            old_gate = idea_to_ppt.GATE_FILE
            idea_to_ppt.GATE_FILE = Path(tmp) / ".selection.json"
            try:
                gate = idea_to_ppt.recommend("", "", limit=8, brief_path=path)
            finally:
                idea_to_ppt.GATE_FILE = old_gate
        self.assertIn("厦门大学_主题_经典蓝白", gate["candidates"])


if __name__ == "__main__":
    unittest.main()
