"""固定序号注册表与文本容量适配的回归测试（自造样本，不依赖桌面原件）。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "xmu-ppt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import template_numbers as numbers  # noqa: E402
import text_fit  # noqa: E402


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.registry_file = Path(self.tmp.name) / "registry.json"
        self.patcher = mock.patch.object(numbers, "REGISTRY_FILE", self.registry_file)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    @staticmethod
    def _registry():
        return {
            "schema": numbers.SCHEMA,
            "rule": numbers.RULE,
            "serial_format": "三位数字",
            "builtin_range": [1, 2],
            "external_range": [3, 5],
            "next_number": 6,
            "hidden_numbers": [5],
            "entries": [
                {"number": 1, "serial": "001", "template_id": "BUILTIN-1", "name": "甲",
                 "namespace": "builtin", "source_key": None, "source_ref_hash": None, "status": "active"},
                {"number": 2, "serial": "002", "template_id": "BUILTIN-2", "name": "乙",
                 "namespace": "builtin", "source_key": None, "source_ref_hash": None, "status": "active"},
                {"number": 3, "serial": "003", "template_id": "EXT-1", "name": "丙",
                 "namespace": "external", "source_key": "EXT-003", "source_ref_hash": "hash-a", "status": "active"},
                {"number": 4, "serial": "004", "template_id": "EXT-2", "name": "丁",
                 "namespace": "external", "source_key": "EXT-004", "source_ref_hash": "hash-b", "status": "active"},
                {"number": 5, "serial": "005", "template_id": "EXT-3", "name": "戊",
                 "namespace": "external", "source_key": "EXT-005", "source_ref_hash": "hash-c", "status": "hidden"},
            ],
        }

    def test_01_serial_format_and_validation(self):
        self.assertEqual(numbers.serial(4), "004")
        self.assertEqual(numbers.validate(self._registry()), [])

    def test_02_pure_number_is_serial_not_id(self):
        r = self._registry()
        self.assertEqual(numbers.lookup(r, "004")["template_id"], "EXT-2")
        self.assertEqual(numbers.lookup(r, "4")["template_id"], "EXT-2")
        self.assertEqual(numbers.lookup(r, "EXT-1")["template_id"], "EXT-1")
        with self.assertRaisesRegex(RuntimeError, "序号"):
            numbers.lookup(r, "999")

    def test_03_duplicate_serial_is_detected(self):
        r = self._registry()
        r["entries"][1]["number"] = 1
        self.assertTrue(numbers.validate(r))

    def test_04_append_only_no_reorder_no_reuse(self):
        r = self._registry()
        self.registry_file.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        candidates = [
            {"template_id": "EXT-2", "name": "丁", "namespace": "external", "source_ref_hash": "hash-b"},
            {"template_id": "EXT-NEW", "name": "己", "namespace": "external", "source_ref_hash": "hash-new"},
            {"template_id": "EXT-NEW2", "name": "庚", "namespace": "external", "source_ref_hash": "hash-new2"},
        ]
        allocated, added = numbers.allocate_numbers(r, candidates)
        self.assertEqual(added, 2)
        by_id = {a["template_id"]: a for a in allocated}
        self.assertEqual(by_id["EXT-2"]["serial"], "004", "既有模板序号不得改变")
        self.assertEqual(by_id["EXT-NEW"]["serial"], "006")
        self.assertEqual(by_id["EXT-NEW2"]["serial"], "007")
        self.assertEqual(r["next_number"], 8)
        self.assertIn(5, r["hidden_numbers"], "被去重隐藏的序号不得回收复用")
        self.assertEqual(numbers.validate(r), [])


class TextFitTests(unittest.TestCase):
    @staticmethod
    def _plan():
        return {"schema": "template_fill_pptx_plan.v1", "slides": [
            {"source_slide": 1, "replacements": [
                {"slot_id": "s01_sh1", "text": "短短两字"},
                {"slot_id": "s01_sh2", "text": "这是一句明显超过文本框容量的长句子会横向溢出压盖相邻元素"},
            ]},
        ]}

    def test_05_validate_detects_absolute_overflow(self):
        capacity = {
            "s01_sh1": {"safe_chars": 8, "wrap": "none", "max_lines": 1, "paragraphs": 1},
            "s01_sh2": {"safe_chars": 10, "wrap": "none", "max_lines": 1, "paragraphs": 1},
        }
        problems = text_fit.validate_plan(self._plan(), capacity)
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["slot_id"], "s01_sh2")

    def test_06_enforce_shortens_without_truncating_mid_word(self):
        capacity = {
            "s01_sh1": {"safe_chars": 8, "wrap": "none", "max_lines": 1, "paragraphs": 1},
            "s01_sh2": {"safe_chars": 10, "wrap": "none", "max_lines": 1, "paragraphs": 1},
        }
        fitted, changes = text_fit.enforce_plan(self._plan(), capacity)
        self.assertEqual(len(changes), 1)
        self.assertLessEqual(len(fitted["slides"][0]["replacements"][1]["text"]), 10)
        self.assertEqual(text_fit.validate_plan(fitted, capacity), [])

    def test_07_multiline_box_splits_instead_of_truncating(self):
        capacity = {
            "s01_sh2": {"safe_chars": 8, "wrap": "square", "max_lines": 4,
                        "paragraphs": 4},
        }
        plan = {"slides": [{"source_slide": 1, "replacements": [
            {"slot_id": "s01_sh2", "text": "遵医嘱由禁食逐步过渡，少量多餐，观察耐受情况。"},
        ]}]}
        fitted, changes = text_fit.enforce_plan(plan, capacity)
        self.assertEqual(len(changes), 1)
        lines = fitted["slides"][0]["replacements"][0]["text"].split("\n")
        self.assertGreater(len(lines), 1, "可换行多段框应分行而非截断")
        self.assertTrue(all(len(line) <= 8 for line in lines))
        self.assertEqual(text_fit.validate_plan(fitted, capacity), [])

    def test_08_split_lines_preserves_full_sentence(self):
        text = "遵医嘱由禁食逐步过渡，少量多餐，观察耐受情况。"
        lines = text_fit._split_lines(text, 8, 5)
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(len(line) <= 8 for line in lines))


if __name__ == "__main__":
    unittest.main()
