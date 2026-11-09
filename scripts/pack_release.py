#!/usr/bin/env python3
"""Build a redistribution-safe, skill-only ZIP.

对标上游 PPT Master 在 Releases 提供的 ``ppt-master-skill-*.zip``：只把
「可以公开分发的文件」装进包里，不含任何第三方模板原件、本机路径配置、
预览截图、或含学校/第三方素材的示例 PPTX。

大白话：这个包是「会做 PPT 的技能」，不是「别人的模板」。使用者下载后，
把自己的模板目录写进 root.local.json，即可在本机得到完整能力。

判定原则：以 git 视角为准 —— tracked 文件 + 未被 .gitignore 忽略的新文件
才是候选；.gitignore 已经把本机模板原件、预览图、本机配置全部挡住了。

另外两件事：
1. 仓库里的四份「本机模板索引」带有本机 200 套模板的条目，属于本机数据而
   非技能资产。打包时只在 ZIP 内把它们重置为全新用户初始态，工作区文件
   一个字节都不改；使用者跑一次 scan 就会长成自己的索引。
2. ``tests/`` 是仓库维护测试，依赖完整仓库（含内置原件），不随技能包分发。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PREFIX = "xmu-ppt/"
NOTICES = "skills/xmu-ppt/templates/external/TEMPLATE_NOTICES.md"
BUILTIN_CATALOG = "skills/xmu-ppt/templates/decks/catalog.json"
RASTER_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif")

# 只在 ZIP 内重置，绝不改工作区：这些索引是「本机模板清单」，不是技能代码。
RESET_INDEXES = {
    "skills/xmu-ppt/templates/external/number_registry.json": "number_registry",
    "skills/xmu-ppt/templates/external/duplicates.json": "duplicates",
    "skills/xmu-ppt/templates/external/external_catalog.json": "external_catalog",
    "skills/xmu-ppt/templates/external/licenses.json": "licenses",
}
RESET_NOTE = (
    "打包时已重置为全新用户初始态；本机模板条目不随技能包分发。"
    "填入 root.local.json 后运行 external_templates.py scan 即可生成本机索引。"
)


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
    if low.startswith(("local-gallery/", "output/", "projects/", "exports/", ".workbuddy/", "dist/", "tests/")):
        return "machine-local artifact / repository maintenance test"
    if low.startswith("docs/templates/previews/"):
        return "site preview image"
    if low.startswith(("docs/", "examples/")) and low.endswith(RASTER_SUFFIXES):
        return "documentation screenshot / example preview"
    if low.startswith("skills/xmu-ppt/templates/decks/") and (
        "/assets/" in low or "/previews/" in low or low.endswith(RASTER_SUFFIXES)
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


def clean_index(rel: str) -> str:
    """Fresh-install payload for one machine-local index (ZIP content only)."""
    payload = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    kind = RESET_INDEXES[rel]
    if kind == "number_registry":
        # 保留 15 套内置模板（公开信息），让 lookup / validate / allocate_numbers
        # 有合法起点；外部模板条目清空，新人从 016 起自己追加。
        builtin = json.loads((ROOT / BUILTIN_CATALOG).read_text(encoding="utf-8"))
        payload["entries"] = [
            {
                "number": int(deck["number"]),
                "serial": f"{int(deck['number']):03d}",
                "template_id": deck["id"],
                "name": deck["name"],
                "namespace": "builtin",
                "source_key": None,
                "source_ref_hash": None,
                "status": "active",
            }
            for deck in builtin
        ]
        payload["hidden_numbers"] = []
        payload["next_number"] = 16
        payload["external_range"] = [16, 15]
        payload["builtin_range"] = [1, 15]
    elif kind == "duplicates":
        payload["groups"] = []
    elif kind == "external_catalog":
        payload["templates"] = []
        payload["counts"] = {
            key: ({} if isinstance(value, dict) else 0)
            for key, value in (payload.get("counts") or {}).items()
        }
        payload["fingerprint_note"] = ""
        payload["rights_warning"] = "外部模板由使用者自备，权利状态由使用者自行核验。"
    else:  # licenses
        payload["entries"] = []
        payload["counts"] = {"total": 0, "unknown": 0}
    payload["generated_on"] = date.today().isoformat()
    payload["reset_note"] = RESET_NOTE
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def audit(kept: list[str]) -> list[str]:
    problems: list[str] = []
    for rel in kept:
        reason = exclusion(rel)
        if reason:
            problems.append(f"excluded file leaked ({reason}): {rel}")
        elif "local-gallery/" in rel.lower() or "source_map" in rel.lower():
            problems.append(f"local config/asset leaked: {rel}")
    if NOTICES not in kept:
        problems.append(f"missing rights declaration: {NOTICES}")
    if BUILTIN_CATALOG not in kept:
        problems.append(f"missing builtin catalog: {BUILTIN_CATALOG}")
    for rel, kind in RESET_INDEXES.items():
        if rel not in kept:
            problems.append(f"missing index to reset: {rel}")
            continue
        try:
            payload = json.loads(clean_index(rel))
        except (OSError, ValueError, KeyError) as exc:
            problems.append(f"cannot build clean index {rel}: {exc}")
            continue
        if kind == "number_registry":
            if any(e["namespace"] == "external" for e in payload["entries"]):
                problems.append(f"local template entries leaked into {rel}")
            if payload["next_number"] != 16:
                problems.append(f"registry does not start at 016: {rel}")
        elif payload.get({"duplicates": "groups",
                          "external_catalog": "templates",
                          "licenses": "entries"}[kind]):
            problems.append(f"local template entries leaked into {rel}")
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
    lines += ["", "Reset to fresh-install state (ZIP content only):"]
    lines += [f"  - {rel}" for rel in RESET_INDEXES]
    lines += [
        "",
        "This package contains code, docs, SVG layout definitions, runtime",
        "image assets and index schemas. It contains NO external .pptx",
        "originals, NO display screenshots, NO template bitmaps,",
        "NO machine-local paths and NO machine-local template list.",
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
    print(f"  reset to fresh state: {len(RESET_INDEXES)} indexes")

    if args.check:
        print("audit OK - package boundary is clean")
        return 0

    out = args.out or DIST / f"xmu-ppt-skill-{date.today().strftime('%Y%m%d')}.zip"
    out = out if out.is_absolute() else ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr(PREFIX + "PACK_MANIFEST.txt", manifest_text(kept, skipped))
        for rel in kept:
            if rel in RESET_INDEXES:
                zf.writestr(PREFIX + rel, clean_index(rel))
            else:
                zf.write(ROOT / rel, PREFIX + rel)
    print(f"wrote: {out} ({out.stat().st_size / 1024 / 1024:.1f} MiB)")
    # 稳定别名：README 固定指向 releases/latest/download/xmu-ppt-skill.zip，
    # 避免每次重建日期变化导致下载链接失效。发布时两个文件一并上传。
    alias = DIST / "xmu-ppt-skill.zip"
    if out.resolve() != alias.resolve():
        alias.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, alias)
        print(f"wrote: {alias} ({alias.stat().st_size / 1024 / 1024:.1f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
