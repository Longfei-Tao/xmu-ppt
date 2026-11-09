"""隐私门禁：仓库内不得残留真实姓名、邮箱、手机号与证件号。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_privacy as privacy  # noqa: E402


class PrivacyCheckTests(unittest.TestCase):
    def test_repository_has_no_personal_data(self):
        result = privacy.check()
        self.assertEqual(result["findings"], [], result["findings"])
        self.assertTrue(result["ok"])
        self.assertGreater(result["scanned"], 100)

    def test_name_label_is_detected(self):
        sample = "答辩人：" + "赵" + "六"
        findings = privacy.scan_text(sample, "sample", ())
        self.assertTrue([f for f in findings if f["kind"] == "name"], findings)

    def test_placeholder_name_is_allowed(self):
        for value in ("XXX", "小夏", "示例", "甲乙丙", "待定"):
            findings = privacy.scan_text("答辩人：" + value, "sample", ())
            self.assertEqual(findings, [], value)

    def test_email_is_detected(self):
        sample = "contact " + "someone" + "@" + "corp.example"
        findings = privacy.scan_text(sample, "sample", ())
        self.assertTrue([f for f in findings if f["kind"] == "email"], findings)

    def test_phone_is_detected(self):
        sample = "tel " + "139" + "0000" + "0000"
        findings = privacy.scan_text(sample, "sample", ())
        self.assertTrue([f for f in findings if f["kind"] == "phone"], findings)

    def test_explicit_term_is_detected(self):
        term = "某" + "某同学"
        findings = privacy.scan_text("汇报人：" + term, "sample", (term,))
        self.assertTrue([f for f in findings if f["kind"] == "term"], findings)

    def test_local_absolute_path_is_detected(self):
        findings = privacy.scan_text("原件在 " + "D" + ":/桌面/模板库 下", "sample", ())
        self.assertTrue([f for f in findings if f["kind"] == "path"], findings)

    def test_documented_example_path_is_allowed(self):
        for sample in ("把 D:\\我的模板\\组会模板.pptx 加入我的模板",
                       "font: C:/Windows/Fonts/msyh.ttc",
                       "root 例如 D:/path/to/templates"):
            findings = privacy.scan_text(sample, "sample", ())
            self.assertEqual(findings, [], sample)


if __name__ == "__main__":
    unittest.main()
