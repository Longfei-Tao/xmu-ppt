#!/usr/bin/env python3
"""Refresh the deck asset manifest (hashes and coverage).

Reads the built-in deck catalogue and the serial registry, then rewrites
``skills/xmu-ppt/templates/decks/assets_manifest.json``.

Human-owned fields are preserved:

* ``license_status``
* ``allowed_uses``
* ``license`` / ``evidence`` / ``verified_on`` / ``notes``

Only machine-owned fields are refreshed: paths, hashes, serials and the
``generated_on`` date. Run ``scripts/check_assets.py`` afterwards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECKS = ROOT / "skills" / "xmu-ppt" / "templates" / "decks"
CATALOG = DECKS / "catalog.json"
REGISTRY = ROOT / "skills" / "xmu-ppt" / "templates" / "external" / "number_registry.json"
LICENSES = ROOT / "skills" / "xmu-ppt" / "templates" / "external" / "licenses.json"
MANIFEST = DECKS / "assets_manifest.json"

SCHEMA = "xmu_ppt_asset_manifest.v1"
ALLOWED_USES = ["local", "public", "commercial"]
LICENSE_STATUS = ["project", "licensed", "unknown", "prohibited"]

DEFAULT_SURFACES = [
    {
        "path": "examples/quickstart/",
        "kind": "sample_deck",
        "license_status": "project",
        "allowed_uses": ["public", "commercial"],
        "evidence": "docs/assets.md",
        "notes": "自写文本与几何图形，无外部图片",
    },
    {
        "path": "examples/",
        "kind": "sample_deck",
        "license_status": "unknown",
        "allowed_uses": ["local"],
        "evidence": "docs/assets.md",
        "notes": "含学校或第三方素材的示例成品",
    },
    {
        "path": "docs/templates/previews/",
        "kind": "derived_preview",
        "license_status": "unknown",
        "allowed_uses": ["local"],
        "evidence": "docs/assets.md",
        "notes": "由模板源文件导出的预览图",
    },
    {
        "path": "docs/assets/screenshots/",
        "kind": "derived_screenshot",
        "license_status": "unknown",
        "allowed_uses": ["local"],
        "evidence": "docs/assets.md",
        "notes": "README 展示图，取自真实成品",
    },
]


def load(path: Path, default=None):
    if not path.exists():
        if default is None:
            raise SystemExit(f"missing file: {path}")
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build() -> dict:
    catalog = load(CATALOG)
    registry = {e["template_id"]: e for e in load(REGISTRY)["entries"]}
    previous = load(MANIFEST, {"decks": [], "surfaces": []})
    prior = {d["deck_id"]: d for d in previous.get("decks", [])}
    prior_surfaces = {s["path"]: s for s in previous.get("surfaces", [])}

    decks = []
    for item in catalog:
        deck_id = item["id"]
        entry = prior.get(deck_id, {})
        source = DECKS / deck_id / "source.pptx"
        decks.append({
            "deck_id": deck_id,
            "serial": registry.get(deck_id, {}).get("serial", f"{int(item['number']):03d}"),
            "name": item.get("name", deck_id),
            "source_pptx": source.relative_to(ROOT).as_posix() if source.is_file() else None,
            "source_sha256": digest(source) if source.is_file() else None,
            "license_status": entry.get("license_status", "unknown"),
            "allowed_uses": entry.get("allowed_uses", ["local"]),
            "license": entry.get("license"),
            "evidence": entry.get("evidence", "docs/assets.md"),
            "verified_on": entry.get("verified_on", "2026-11-07"),
            "notes": entry.get("notes", "来源与再分发条件待核验"),
        })

    surfaces = []
    for default in DEFAULT_SURFACES:
        saved = prior_surfaces.get(default["path"], {})
        merged = dict(default)
        for key in ("license_status", "allowed_uses", "license", "evidence", "verified_on", "notes"):
            if key in saved:
                merged[key] = saved[key]
        surfaces.append(merged)

    licenses = load(LICENSES)["entries"]
    external = {
        "catalog": "skills/xmu-ppt/templates/external/external_catalog.json",
        "license_registry": "skills/xmu-ppt/templates/external/licenses.json",
        "entries": len(licenses),
        "redistributable_true": sum(1 for e in licenses if e.get("redistributable")),
        "default_status": "unknown",
        "policy": "原件、预览与衍生截图不入库；仅本机离线索引。",
    }

    return {
        "schema": SCHEMA,
        "generated_on": date.today().isoformat(),
        "allowed_uses_vocabulary": ALLOWED_USES,
        "license_status_vocabulary": LICENSE_STATUS,
        "decks": decks,
        "surfaces": surfaces,
        "external_library": external,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只比较，不写回")
    args = parser.parse_args(argv)

    data = build()
    current = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    unchanged = False
    if current is not None:
        left, right = dict(current), dict(data)
        left.pop("generated_on", None)
        right.pop("generated_on", None)
        unchanged = left == right

    if args.check:
        if not unchanged:
            print("manifest is stale; run scripts/build_asset_manifest.py", file=sys.stderr)
            return 1
        print("manifest is up to date")
        return 0

    if unchanged:
        print("manifest unchanged")
        return 0

    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    MANIFEST.write_text(payload, encoding="utf-8")
    print(f"wrote {MANIFEST.relative_to(ROOT)} | decks={len(data['decks'])} surfaces={len(data['surfaces'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
