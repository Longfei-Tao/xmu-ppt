#!/usr/bin/env python3
"""Validate the asset boundary: manifest coverage, hashes and publish flags.

Read-only. It never touches the build pipeline. Exit code 1 means a structural
boundary violation (missing deck entry, hash drift, external original committed,
or a ``public``/``commercial`` claim without a license).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECKS = ROOT / "skills" / "xmu-ppt" / "templates" / "decks"
CATALOG = DECKS / "catalog.json"
MANIFEST = DECKS / "assets_manifest.json"
EXTERNAL = ROOT / "skills" / "xmu-ppt" / "templates" / "external"
LICENSES = EXTERNAL / "licenses.json"
LICENSE = ROOT / "LICENSE"
ASSET_BOUNDARY = ROOT / "LICENSE-ASSETS"

ALLOWED_USES = {"local", "public", "commercial"}
LICENSE_STATUS = {"project", "licensed", "unknown", "prohibited"}
PUBLIC_CLAIMS = {"public", "commercial"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tracked_external_pptx() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "skills/xmu-ppt/templates/external"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except OSError:
        return []
    if out.returncode != 0:
        return []
    return [line for line in out.stdout.splitlines() if line.lower().endswith((".pptx", ".ppt"))]


def check(verify_hashes: bool = True) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    for path in (CATALOG, MANIFEST, LICENSES, LICENSE, ASSET_BOUNDARY):
        if not path.exists():
            errors.append(f"missing file: {path.relative_to(ROOT).as_posix()}")
    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings, "stats": {}}

    manifest = load(MANIFEST)
    catalogue = {item["id"]: item for item in load(CATALOG)}
    licenses = load(LICENSES).get("entries", [])

    if manifest.get("schema") != "xmu_ppt_asset_manifest.v1":
        errors.append("manifest schema mismatch (expected xmu_ppt_asset_manifest.v1)")

    entries = manifest.get("decks", [])
    seen_ids: set[str] = set()
    seen_serials: set[str] = set()
    for entry in entries:
        deck_id = entry.get("deck_id")
        serial = entry.get("serial")
        if deck_id in seen_ids:
            errors.append(f"duplicate deck_id in manifest: {deck_id}")
        if serial in seen_serials:
            errors.append(f"duplicate serial in manifest: {serial}")
        seen_ids.add(deck_id)
        seen_serials.add(serial)

        uses = set(entry.get("allowed_uses") or [])
        status = entry.get("license_status")
        if not uses or not uses <= ALLOWED_USES:
            errors.append(f"{deck_id}: invalid allowed_uses {sorted(uses)}")
        if status not in LICENSE_STATUS:
            errors.append(f"{deck_id}: invalid license_status {status!r}")
        if uses & PUBLIC_CLAIMS and status == "unknown":
            errors.append(f"{deck_id}: public/commercial claimed while license is unknown")
        if status == "licensed" and not entry.get("license"):
            errors.append(f"{deck_id}: status licensed but no license name")

        source = entry.get("source_pptx")
        expected = entry.get("source_sha256")
        if source:
            path = ROOT / source
            if not path.is_file():
                errors.append(f"{deck_id}: source missing: {source}")
            elif verify_hashes:
                actual = digest(path)
                if actual != expected:
                    errors.append(f"{deck_id}: source hash drift ({actual[:12]} != {str(expected)[:12]})")

    catalog_ids = set(catalogue)
    missing = sorted(catalog_ids - seen_ids)
    extra = sorted(seen_ids - catalog_ids)
    if missing:
        errors.append(f"deck(s) missing from manifest: {missing}")
    if extra:
        errors.append(f"manifest entries not in catalogue: {extra}")

    for directory in sorted(DECKS.iterdir()):
        if directory.is_dir() and (directory / "source.pptx").is_file() and directory.name not in seen_ids:
            errors.append(f"deck directory not registered: {directory.name}")

    for surface in manifest.get("surfaces", []):
        path = ROOT / surface.get("path", "")
        if not path.exists():
            errors.append(f"surface missing: {surface.get('path')}")
        uses = set(surface.get("allowed_uses") or [])
        status = surface.get("license_status")
        if not uses or not uses <= ALLOWED_USES:
            errors.append(f"surface {surface.get('path')}: invalid allowed_uses {sorted(uses)}")
        if status not in LICENSE_STATUS:
            errors.append(f"surface {surface.get('path')}: invalid license_status {status!r}")
        if uses & PUBLIC_CLAIMS and status == "unknown":
            errors.append(f"surface {surface.get('path')}: public/commercial claimed while unknown")

    redistributable = [e for e in licenses if e.get("redistributable")]
    for entry in redistributable:
        if not entry.get("license"):
            errors.append(f"external {entry.get('id')}: redistributable without a license")
    if redistributable:
        warnings.append(f"{len(redistributable)} external template(s) marked redistributable")

    committed = tracked_external_pptx()
    if committed:
        errors.append(f"external originals committed: {committed[:3]}")

    unknown_decks = [e["deck_id"] for e in entries
                     if e.get("license_status") == "unknown" and "local" in (e.get("allowed_uses") or [])]
    if unknown_decks:
        warnings.append(f"{len(unknown_decks)} deck(s) remain local-only with unknown provenance")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "decks": len(entries),
            "surfaces": len(manifest.get("surfaces", [])),
            "external_entries": len(licenses),
            "external_redistributable": len(redistributable),
            "tracked_external_originals": len(committed),
            "hashes_verified": bool(verify_hashes),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="机器可读输出")
    parser.add_argument("--no-hash", action="store_true", help="跳过 184 MB 源文件哈希校验")
    parser.add_argument("--strict", action="store_true", help="warning 也算失败")
    args = parser.parse_args(argv)

    result = check(verify_hashes=not args.no_hash)
    if args.strict and result["warnings"]:
        result["ok"] = False
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        stats = result["stats"]
        print(f"decks={stats.get('decks')} surfaces={stats.get('surfaces')} "
              f"external={stats.get('external_entries')} hashes={stats.get('hashes_verified')}")
        for item in result["errors"]:
            print("ERROR", item)
        for item in result["warnings"]:
            print("WARN ", item)
        print("OK" if result["ok"] else "FAILED")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
