#!/usr/bin/env python3
"""Offline asset/capability audit. No PowerPoint, network or API key required."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

PROTOTYPES = ("01_cover.svg", "02_toc.svg", "02_chapter.svg",
              "03_content.svg", "04_ending.svg")
NATIVE = ("source.pptx", "source.slide_library.json", "layout_index.json")


def audit(root: Path) -> dict:
    report = {"decks": [], "errors": [], "warnings": []}
    decks = sorted(p for p in root.glob("厦门大学_*") if p.is_dir())
    if not decks:
        report["errors"].append(f"No XMU templates found: {root}")
    for deck in decks:
        errors = report["errors"]
        for name in (*PROTOTYPES, "design_spec.md"):
            if not (deck / name).is_file():
                errors.append(f"{deck.name}: missing {name}")
        for name in PROTOTYPES:
            svg = deck / name
            if not svg.is_file():
                continue
            try:
                tree = ET.parse(svg)
                if tree.getroot().get("viewBox") != "0 0 1280 720":
                    errors.append(f"{deck.name}/{name}: expected 1280x720 canvas")
                for el in tree.iter():
                    if el.tag.rsplit("}", 1)[-1] != "image":
                        continue
                    href = el.get("href") or el.get("{http://www.w3.org/1999/xlink}href", "")
                    if href.startswith("data:image/"):
                        continue
                    asset = (deck / href).resolve()
                    if not href or not asset.is_relative_to(deck.resolve()) or not asset.is_file():
                        errors.append(f"{deck.name}/{name}: missing or non-portable image {href}")
            except (ET.ParseError, OSError) as exc:
                errors.append(f"{deck.name}/{name}: {exc}")
        native = all((deck / name).is_file() for name in NATIVE)
        if not native:
            if any((deck / name).exists() for name in NATIVE):
                errors.append(f"{deck.name}: incomplete native-fill assets")
            else:
                report["warnings"].append(f"{deck.name}: SVG only; do not route to native fill")
        else:
            try:
                library = json.loads((deck / NATIVE[1]).read_text(encoding="utf-8"))
                index = json.loads((deck / NATIVE[2]).read_text(encoding="utf-8"))
                with zipfile.ZipFile(deck / NATIVE[0]) as archive:
                    bad = archive.testzip()
                    if bad:
                        errors.append(f"{deck.name}: corrupt ZIP member {bad}")
                    pres = ET.fromstring(archive.read("ppt/presentation.xml"))
                    count = len(pres.findall(".//{http://schemas.openxmlformats.org/presentationml/2006/main}sldId"))
                if not (count == library["slide_count"] == len(library["slides"])
                        == index["slide_count"] == len(index["pages"])):
                    errors.append(f"{deck.name}: source/index/library page counts disagree")
            except (OSError, ValueError, KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
                errors.append(f"{deck.name}: invalid native assets: {exc}")
        report["decks"].append({"id": deck.name, "svg": True, "native": native})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "templates/decks")
    parser.add_argument("--check-svg", action="store_true", help="Also run canonical SVG quality checks")
    parser.add_argument("--json", type=Path, help="Save a machine-readable capability report")
    args = parser.parse_args()
    report = audit(args.root)
    if args.check_svg:
        for deck in report["decks"]:
            result = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).with_name("svg_quality_checker.py")),
                                     str(args.root / deck["id"]), "--template-mode", "--canonical-authoring"],
                                    capture_output=True)
            if result.returncode:
                details = (result.stderr or result.stdout).decode("utf-8", errors="replace")[-2000:]
                report["errors"].append(f"{deck['id']}: SVG quality check failed: {details}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
