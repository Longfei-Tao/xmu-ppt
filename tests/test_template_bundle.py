import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/ppt-master/scripts"
DECKS = ROOT / "skills/ppt-master/templates/decks"


class BundleTests(unittest.TestCase):
    def test_checker_handles_non_utf8_piped_output(self):
        env = dict(os.environ, PYTHONIOENCODING="ascii")
        result = subprocess.run([sys.executable, str(SCRIPTS / "svg_quality_checker.py"),
                                 str(DECKS / "厦门大学_主题_凤凰花开"),
                                 "--template-mode", "--canonical-authoring"],
                                env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode("ascii", errors="replace"))

    def test_installable_skill_keeps_license_and_asset_notice(self):
        skill = ROOT / "skills/ppt-master"
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            self.assertEqual((ROOT / name).read_bytes(), (skill / name).read_bytes())

    def audit(self, root):
        spec = importlib.util.spec_from_file_location("audit_xmu", SCRIPTS / "audit_xmu.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.audit(root)

    def test_shipped_bundle(self):
        report = self.audit(DECKS)
        self.assertEqual(report["errors"], [])
        self.assertEqual(len(report["decks"]), 14)
        self.assertEqual(sum(d["native"] for d in report["decks"]), 13)

    def test_missing_image_blocks_delivery(self):
        cache = ROOT / ".cache"
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            deck = Path(tmp) / "厦门大学_test"
            shutil.copytree(DECKS / "厦门大学_官方_南强蔚蓝", deck)
            (deck / "xmu_logo.png").unlink()
            self.assertTrue(any("xmu_logo.png" in e for e in self.audit(Path(tmp))["errors"]))

    def test_empty_library_is_an_error(self):
        cache = ROOT / ".cache"
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            self.assertTrue(self.audit(Path(tmp))["errors"])
