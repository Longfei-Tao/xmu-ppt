"""模板包 build -> import 闭环：指纹校验、zip-slip 拒绝、冲突处理。"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/xmu-ppt/scripts"
CACHE = ROOT / ".cache"
CACHE.mkdir(exist_ok=True)
sys.path.insert(0, str(SCRIPTS))

import external_templates as ext  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rewrite_member(pack: Path, member: str, data: bytes) -> None:
    with zipfile.ZipFile(pack) as zf:
        items = {name: zf.read(name) for name in zf.namelist()}
    items[member] = data
    with zipfile.ZipFile(pack, "w") as zf:
        for name, value in items.items():
            zf.writestr(name, value)


class TemplatePackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=CACHE)
        self.base = Path(self.tmp.name)
        self.root = self.base / "source"
        (self.root / "汇报").mkdir(parents=True)
        records = []
        for seq, stem in ((1, "汇报_甲"), (2, "临床_乙")):
            source = self.root / "汇报" / f"{stem}_{seq:03d}.pptx"
            source.write_bytes(f"dummy-pptx-{seq}".encode())
            rel = source.relative_to(self.root).as_posix()
            records.append({
                "id": f"MED-{seq:03d}",
                "number": seq,
                "serial": f"EXT-{seq:03d}",
                "source_key": f"EXT-{seq:03d}",
                "name": stem,
                "primary_category": "report",
                "sha256": sha256(source),
                "size_bytes": source.stat().st_size,
                "_rel": rel,
            })
        self.catalog = {"templates": records}
        self.source_map = self.base / "source_map.local.json"
        self.source_map.write_text(json.dumps({
            "schema": "external_source_map.v1",
            "paths": {r["source_key"]: r.pop("_rel") for r in records},
        }, ensure_ascii=False), encoding="utf-8")

        for attr, value in (
            ("SOURCE_MAP", self.source_map),
            ("ROOT_LOCAL", self.base / "root.local.json"),
        ):
            patcher = mock.patch.object(ext, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def build(self) -> Path:
        pack = self.base / "pack.zip"
        ext.build_template_pack(self.root, pack, catalog=self.catalog)
        return pack

    def test_01_pack_then_import_roundtrip(self):
        pack = self.build()
        dest = self.base / "imported"
        result = ext.import_template_pack(pack, dest, scan=False)
        self.assertEqual(result["count"], 2)
        for record in self.catalog["templates"]:
            target = dest / self._rel(record)
            self.assertTrue(target.is_file(), target)
            self.assertEqual(sha256(target), record["sha256"])
        root_cfg = json.loads((self.base / "root.local.json").read_text(encoding="utf-8"))
        self.assertEqual(root_cfg["root"], dest.resolve().as_posix())

    def _rel(self, record) -> str:
        mapping = json.loads(self.source_map.read_text(encoding="utf-8"))["paths"]
        return mapping[record["source_key"]]

    def test_02_pack_rejects_fingerprint_mismatch(self):
        source = self.root / "汇报" / "汇报_甲_001.pptx"
        source.write_bytes(b"changed-after-scan")
        with self.assertRaises(SystemExit):
            self.build()

    def test_03_import_rejects_tampered_content(self):
        pack = self.build()
        rewrite_member(pack, "templates/汇报/汇报_甲_001.pptx", b"tampered")
        with self.assertRaises(SystemExit):
            ext.import_template_pack(pack, self.base / "imported", scan=False)

    def test_04_import_rejects_zip_slip(self):
        pack = self.base / "evil.zip"
        manifest = {
            "schema": ext.PACK_SCHEMA,
            "count": 1,
            "templates": [{
                "file": "templates/../../evil.pptx",
                "sha256": "0" * 64,
            }],
        }
        with zipfile.ZipFile(pack, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("templates/../../evil.pptx", b"x")
        with self.assertRaises(SystemExit):
            ext.import_template_pack(pack, self.base / "imported", scan=False)
        self.assertFalse((self.base / "evil.pptx").exists())

    def test_05_conflict_requires_force(self):
        pack = self.build()
        dest = self.base / "imported"
        ext.import_template_pack(pack, dest, scan=False)
        target = dest / self._rel(self.catalog["templates"][0])
        target.write_bytes(b"user-edited")
        with self.assertRaises(SystemExit):
            ext.import_template_pack(pack, dest, scan=False)
        self.assertEqual(target.read_bytes(), b"user-edited")
        ext.import_template_pack(pack, dest, force=True, scan=False)
        self.assertEqual(sha256(target), self.catalog["templates"][0]["sha256"])


class GalleryStepTests(unittest.TestCase):
    """导入后自动生成离线画廊；失败不能影响导入本身。"""

    def test_01_missing_builder_is_skipped(self):
        with mock.patch.object(ext, "GALLERY_BUILDER", Path("does-not-exist.py")):
            self.assertFalse(ext.build_local_gallery())

    def test_02_builder_failure_is_not_fatal(self):
        with mock.patch.object(ext.subprocess, "run",
                               return_value=mock.Mock(returncode=1)):
            self.assertFalse(ext.build_local_gallery())

    def test_03_builder_runs_in_repo_root(self):
        with mock.patch.object(ext.subprocess, "run",
                               return_value=mock.Mock(returncode=0)) as run:
            self.assertTrue(ext.build_local_gallery())
        self.assertEqual(run.call_args.kwargs["cwd"], str(ext.REPO_ROOT))

    def _args(self, tmp: Path, **overrides):
        values = {
            "pack": str(tmp / "pack.zip"),
            "dest": str(tmp / "imported"),
            "url": None,
            "force": False,
            "skip_scan": False,
            "skip_gallery": False,
        }
        values.update(overrides)
        return mock.Mock(**values)

    def test_04_run_import_builds_gallery_after_scan(self):
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            base = Path(tmp)
            (base / "pack.zip").write_bytes(b"x")
            with mock.patch.object(ext, "import_template_pack",
                                   return_value={"count": 2, "root": "d"}), \
                    mock.patch.object(ext, "build_local_gallery",
                                      return_value=True) as gallery:
                self.assertEqual(ext.run_import(self._args(base)), 0)
                gallery.assert_called_once()

    def test_05_run_import_can_skip_gallery(self):
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            base = Path(tmp)
            (base / "pack.zip").write_bytes(b"x")
            with mock.patch.object(ext, "import_template_pack",
                                   return_value={"count": 2, "root": "d"}), \
                    mock.patch.object(ext, "build_local_gallery") as gallery:
                self.assertEqual(
                    ext.run_import(self._args(base, skip_gallery=True)), 0)
                gallery.assert_not_called()

    def test_06_run_import_skips_gallery_when_scan_skipped(self):
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            base = Path(tmp)
            (base / "pack.zip").write_bytes(b"x")
            with mock.patch.object(ext, "import_template_pack",
                                   return_value={"count": 2, "root": "d"}), \
                    mock.patch.object(ext, "build_local_gallery") as gallery:
                self.assertEqual(
                    ext.run_import(self._args(base, skip_scan=True)), 0)
                gallery.assert_not_called()


class NumberSeedingTests(unittest.TestCase):
    """模板包自带的序号必须在全新机器上原样沿用。"""

    def _write(self, path: Path, entries, next_number=16):
        path.write_text(json.dumps({
            "schema": "template_number_registry.v1",
            "entries": entries,
            "next_number": next_number,
        }, ensure_ascii=False), encoding="utf-8")

    def _builtin(self, number=15):
        return {"number": number, "serial": f"{number:03d}",
                "template_id": "builtin-x", "name": "x", "namespace": "builtin",
                "source_key": None, "source_ref_hash": None, "status": "active"}

    def test_01_pack_serials_are_preserved(self):
        import template_numbers as tn
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            path = Path(tmp) / "number_registry.json"
            self._write(path, [self._builtin()])
            with mock.patch.object(tn, "REGISTRY_FILE", path):
                added = ext._seed_numbers([
                    {"id": "MED-001", "serial": "016", "name": "a",
                     "file": "templates/甲/MED-001.pptx"},
                    {"id": "MED-003", "serial": "018", "name": "b",
                     "file": "templates/乙/MED-003.pptx"},
                ])
            self.assertEqual(added, 2)
            data = json.loads(path.read_text(encoding="utf-8"))
            numbers = {e["template_id"]: e["number"] for e in data["entries"]}
            self.assertEqual(numbers["MED-003"], 18)
            self.assertEqual(data["next_number"], 19)

    def test_02_existing_external_numbers_are_never_renumbered(self):
        import template_numbers as tn
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            path = Path(tmp) / "number_registry.json"
            existing = {**self._builtin(), "number": 17, "serial": "017",
                        "template_id": "MED-003", "namespace": "external"}
            self._write(path, [self._builtin(), existing], next_number=18)
            with mock.patch.object(tn, "REGISTRY_FILE", path):
                added = ext._seed_numbers([
                    {"id": "MED-003", "serial": "018", "name": "b",
                     "file": "templates/乙/MED-003.pptx"},
                ])
            self.assertEqual(added, 0)
            data = json.loads(path.read_text(encoding="utf-8"))
            numbers = {e["template_id"]: e["number"] for e in data["entries"]}
            self.assertEqual(numbers["MED-003"], 17)


if __name__ == "__main__":
    unittest.main()
