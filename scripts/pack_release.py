#!/usr/bin/env python3
"""Build a redistribution-safe, skill-only ZIP.

对标上游 PPT Master 在 Releases 提供的 ``ppt-master-skill-*.zip``：只把
「可以公开分发的文件」装进包里，不含任何第三方模板原件、本机路径配置、
预览截图、或含学校/第三方素材的示例 PPTX。

大白话：这个包是「会做 PPT 的技能」，不是「别人的模板」。使用者下载后，
把自己的模板目录写进 root.local.json，即可在本机得到完整能力。

判定原则：以 git 视角为准 —— tracked 文件 + 未被 .gitignore 忽略的新文件
才是候选；.gitignore 已经把本机模板原件、预览图、本机配置全部挡住了。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PREFIX = "xmu-ppt/"
NOTICES = "skills/xmu-ppt/templates/external/TEMPLATE_NOTICES.md"


def candidates() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    )
    raw = result.stdout.decode("utf-8", errors="replace").split("\0")
    return sorted({p.replace("\\", "/") for p in raw if p.strip()})


def exclusion(rel: str) -> str | None:
    low = rel.lower()
    if low.endswith((".pptx", ".ppt")):
        return "template original / example deck (not covered by MIT)"
    if low.endswith(".local.json") or low.endswith("path_status.json"):
        return "machine-local config"
    if low.startswith(("local-gallery/", "output/", "projects/", "exports/", ".workbuddy/", "dist/")):
        return "machine-local artifact"
    if low.startswith("docs/templates/previews/"):
        return "site preview image"
    if low.startswith("skills/xmu-ppt/templates/decks/") and (
        "/assets/" in low or "/previews/" in low or low.endswith("/preview.png")
    ):
        return "bundled photo / thumbnail"
    if "xmu_logo" in low and low.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg")):
        return "school visual identity mark"
    return None


def select() -> tuple[list[str], dict[str, int]]:
    kept: list[str] = []
    skipped: dict[str, int] = {}
    for rel in candidates():
        reason = exclusion(rel)
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        if not (ROOT / rel).is_file():
            continue
        kept.append(rel)
    return kept, skipped


def audit(kept: list[str]) -> list[str]:
    problems: list[str] = []
    for rel in kept:
        low = rel.lower()
        if low.endswith((".pptx", ".ppt")):
            problems.append(f"original deck leaked: {rel}")
        if low.endswith(".local.json") or "local-gallery/" in low or "source_map" in low:
            problems.append(f"local config/asset leaked: {rel}")
    if NOTICES not in kept:
        problems.append(f"missing rights declaration: {NOTICES}")
    return problems


def manifest_text(kept: list[str], skipped: dict[str, int]) -> str:
    lines = [
        "xmu-ppt skill-only package",
        f"built_on: {date.today().isoformat()}",
        "source: git ls-files --cached --others --exclude-standard (gitignore-aware)",
        f"files: {len(kept)}",
        "",
        "Excluded (not redistributable / machine-local):",
    ]
    lines += [f"  - {reason}: {count}" for reason, count in sorted(skipped.items())]
    lines += [
        "",
        "This package contains code, docs, SVG layout definitions and the",
        "external-template INDEX METADATA only. It contains NO external .pptx",
        "originals, NO preview screenshots and NO machine-local paths.",
        "",
        "Rights boundary: LICENSE-ASSETS",
        "External template notices: " + NOTICES,
        "To use your own templates, copy root.example.json to root.local.json,",
        "set your template folder, then run external_templates.py scan.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="output zip path")
    parser.add_argument("--check", action="store_true",
                        help="audit only, do not write a zip")
    args = parser.parse_args(argv)

    kept, skipped = select()
    problems = audit(kept)
    if problems:
        for item in problems:
            print("ERROR:", item, file=sys.stderr)
        return 1

    print(f"candidates kept: {len(kept)}")
    for reason, count in sorted(skipped.items()):
        print(f"  excluded {reason}: {count}")

    if args.check:
        print("audit OK - package boundary is clean")
        return 0

    out = args.out or DIST / f"xmu-ppt-skill-{date.today().strftime('%Y%m%d')}.zip"
    out = out if out.is_absolute() else ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr(PREFIX + "PACK_MANIFEST.txt", manifest_text(kept, skipped))
        for rel in kept:
            zf.write(ROOT / rel, PREFIX + rel)
    print(f"wrote: {out} ({out.stat().st_size / 1024 / 1024:.1f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
