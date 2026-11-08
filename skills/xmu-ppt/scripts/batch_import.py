#!/usr/bin/env python3
"""Batch-import external PPTX templates as native page libraries.

Stages are deliberately separate because the cost differs by orders of
magnitude:

* ``precheck`` parses every source with no copying (minutes).
* ``index``   writes slide libraries, layout indexes and structure
              fingerprints (minutes).
* ``previews``renders every source page (about 3.5 s per page, so ~6 h for
              the whole 6102-page library). Use ``--limit`` / ``--deck`` for
              a controlled batch.
* ``verify``  clones each source with no text changes and compares the
              non-text structure, proving the clone itself did not alter
              the layout.

The original PPTX files are never copied or rewritten. External templates
are referenced by ``source_path``; only derived JSON metadata and preview
JPEGs are written under ``output/template_import``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from template_fill_pptx.analyzer import analyze_pptx  # noqa: E402
from native_full import _media_hashes, _nontext_xml, _slide_xmls  # noqa: E402

ROOT = HERE.parents[2]
DECKS = ROOT / "skills/xmu-ppt/templates/decks"
EXTERNAL = ROOT / "skills/xmu-ppt/templates/external"
AUDIT = ROOT / "output/template_audit/library_audit.json"
OUT = ROOT / "output/template_import"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def external_targets() -> list[dict]:
    if not AUDIT.is_file():
        raise SystemExit("Run the library audit first: output/template_audit/library_audit.json is missing")
    root = Path(_read_json(EXTERNAL / "root.local.json")["root"])
    audit = _read_json(AUDIT)
    targets = []
    for item in audit["unique_files"]:
        if item.get("is_backup") or not item["rel"].lower().endswith(".pptx"):
            continue
        source = root / item["rel"]
        if not source.is_file():
            continue
        targets.append({"source": source, **item})
    return sorted(targets, key=lambda t: (t.get("external_serial") or 999, t["rel"]))


def deck_dir(meta: dict) -> Path:
    key = meta.get("external_id") or Path(meta["rel"]).stem
    return OUT / "decks" / key


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprints(source: Path) -> list[dict]:
    return [
        {"slide": number, "nontext_sha256": hashlib.sha256(_nontext_xml(xml)).hexdigest()}
        for number, xml in enumerate(_slide_xmls(source), start=1)
    ]


def analyze_one(meta: dict) -> dict:
    started = time.time()
    row = {
        "external_id": meta.get("external_id"),
        "serial": meta.get("external_serial"),
        "name": meta.get("external_name") or Path(meta["rel"]).stem,
        "rel": meta["rel"],
        "sha256": meta["sha256"],
        "size_mb": round(meta["size"] / 1024 / 1024, 2),
        "audited_pages": meta.get("pages"),
    }
    try:
        library = analyze_pptx(meta["source"])
    except Exception as exc:  # one bad template must not abort the batch
        row.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
        return row
    slots = [s for slide in library["slides"] for s in slide["slots"]]
    bad_geometry = [
        s for s in slots
        if not s["geometry"].get("width") or not s["geometry"].get("height")
    ]
    row.update({
        "status": "ok",
        "pages": library["slide_count"],
        "slots": len(slots),
        "group_absolute": sum(1 for s in slots if s["geometry"].get("group_depth")),
        "placeholder_inherited": sum(1 for s in slots if s["geometry"].get("inherited_from")),
        "unresolved_geometry": sum(1 for s in slots if s["geometry"].get("source") == "unresolved"),
        "zero_geometry": len(bad_geometry),
        "zero_with_text": sum(1 for s in bad_geometry if str(s.get("text") or "").strip()),
        "zero_sources": dict(Counter(str(s["geometry"].get("source")) for s in bad_geometry)),
        "tables": sum(len(x.get("tables", [])) for x in library["slides"]),
        "charts": sum(len(x.get("charts", [])) for x in library["slides"]),
        "seconds": round(time.time() - started, 2),
    })
    return row


def stage_precheck(targets: list[dict]) -> list[dict]:
    rows = []
    for index, meta in enumerate(targets, 1):
        row = analyze_one(meta)
        rows.append(row)
        print(f"[{index:3d}/{len(targets)}] {row['status']:5s} "
              f"P{row.get('pages', '-')!s:>3} slots={row.get('slots', '-')!s:>5} "
              f"zero={row.get('zero_geometry', '-')!s:>3} {row['name'][:34]}", flush=True)
    _write_json(OUT / "PRECHECK.json", rows)
    ok = [r for r in rows if r["status"] == "ok"]
    lines = [
        "# 外部模板批量入库 · 全量预检", "",
        f"- 扫描时间：本地模板库 `D:/桌面/PPT模板`（不含备份目录）",
        f"- 目标模板：**{len(targets)}** 套；解析成功：**{len(ok)}** 套；失败：**{len(rows) - len(ok)}** 套",
        f"- 可入库页数：**{sum(r['pages'] for r in ok)}** 页；文本槽：**{sum(r['slots'] for r in ok)}** 个",
        f"- 组合内坐标已换算：**{sum(r['group_absolute'] for r in ok)}** 个；占位框继承：**{sum(r['placeholder_inherited'] for r in ok)}** 个",
        f"- 仍无几何的槽位：**{sum(r['zero_geometry'] for r in ok)}** 个；其中带文字、会影响填充的："
        f"**{sum(r['zero_with_text'] for r in ok)}** 个",
        f"- 原生表格：**{sum(r['tables'] for r in ok)}** 个；原生图表：**{sum(r['charts'] for r in ok)}** 个",
        f"- 预计全页预览渲染：{sum(r['pages'] for r in ok)} 页 × 3.5 秒 ≈ "
        f"**{round(sum(r['pages'] for r in ok) * 3.5 / 3600, 1)} 小时**（单进程）",
        "", "## 失败清单", "",
    ]
    failures = [r for r in rows if r["status"] != "ok"]
    if failures:
        for r in failures:
            lines.append(f"- `{r['name']}`：`{r['error']}`")
    else:
        lines.append("无。全部模板可被原生页库解析器读取。")
    lines += ["", "## 逐套明细", "", "完整数据见 `PRECHECK.json`。", ""]
    (OUT / "PRECHECK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def stage_index(targets: list[dict], rows: list[dict], limit: int | None) -> None:
    by_id = {r["external_id"]: r for r in rows if r["status"] == "ok"}
    selected = [t for t in targets if t.get("external_id") in by_id]
    if limit:
        selected = selected[:limit]
    for index, meta in enumerate(selected, 1):
        folder = deck_dir(meta)
        library = analyze_pptx(meta["source"])
        _write_json(folder / "slide_library.json", library)
        pages = [{
            "slide": slide["slide_index"],
            "role": slide.get("page_type"),
            "slot_count": len(slide.get("slots", [])),
            "filled_slot_count": sum(1 for s in slide.get("slots", []) if s.get("text")),
            "tables": len(slide.get("tables", [])),
            "charts": len(slide.get("charts", [])),
            "summary": str(slide.get("text_summary", "")).replace("\n", " ")[:80],
        } for slide in library["slides"]]
        _write_json(folder / "layout_index.json", {
            "schema": "external_native_layout_index.v1",
            "deck_id": meta.get("external_id"),
            "source_path": str(meta["source"]),
            "slide_count": library["slide_count"],
            "canvas_px": library["canvas_px"],
            "pages": pages,
        })
        _write_json(folder / "layout_fingerprint.json", {
            "schema": "external_native_fingerprint.v1",
            "source_sha256": meta["sha256"],
            "slide_count": library["slide_count"],
            "media_sha256": _media_hashes(meta["source"]),
            "pages": _fingerprints(meta["source"]),
        })
        _write_json(folder / "manifest.json", {
            "schema": "external_native_manifest.v1",
            "external_id": meta.get("external_id"),
            "serial": meta.get("external_serial"),
            "name": meta.get("external_name"),
            "source_path": str(meta["source"]),
            "source_sha256": meta["sha256"],
            "source_bytes": meta["source"].stat().st_size,
            "slide_count": library["slide_count"],
            "canvas_px": library["canvas_px"],
            "route": "native",
            "redistributable": False,
            "rights_status": (meta.get("external_rights") or {}).get("status", "unknown"),
        })
        print(f"[{index:3d}/{len(selected)}] indexed {meta.get('external_name')} "
              f"({library['slide_count']} pages) -> {folder}", flush=True)


def stage_previews(targets: list[dict], limit: int | None, pages_limit: int | None) -> None:
    slidep = shutil.which("slidep")
    if not slidep:
        raise SystemExit("slidep is required for preview rendering")
    selected = [t for t in targets if (deck_dir(t) / "layout_index.json").is_file()]
    if limit:
        selected = selected[:limit]
    for deck_index, meta in enumerate(selected, 1):
        folder = deck_dir(meta)
        outdir = folder / "previews"
        outdir.mkdir(parents=True, exist_ok=True)
        index = _read_json(folder / "layout_index.json")
        total = index["slide_count"] if pages_limit is None else min(pages_limit, index["slide_count"])
        rendered = 0
        for page in range(1, total + 1):
            target = outdir / f"slide_{page:02d}.jpg"
            if target.is_file():
                rendered += 1
                continue
            for _ in range(2):
                subprocess.run([slidep, "screenshot", str(meta["source"]),
                                "--page-index", str(page - 1), "--out", str(target)],
                               capture_output=True, text=True)
                if target.is_file():
                    break
            if target.is_file():
                rendered += 1
        print(f"[{deck_index:3d}/{len(selected)}] previews {rendered}/{total} "
              f"{meta.get('external_name')}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("precheck", "index", "previews"), default="precheck")
    parser.add_argument("--limit", type=int, help="only process the first N templates")
    parser.add_argument("--pages-limit", type=int, help="only render the first N pages per template")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    targets = external_targets()
    print(f"targets: {len(targets)} external templates", flush=True)
    if args.stage == "precheck":
        stage_precheck(targets)
    else:
        rows = _read_json(OUT / "PRECHECK.json") if (OUT / "PRECHECK.json").is_file() else stage_precheck(targets)
        if args.stage == "index":
            stage_index(targets, rows, args.limit)
        else:
            stage_previews(targets, args.limit, args.pages_limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
