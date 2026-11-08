#!/usr/bin/env python3
"""Native full-page acceptance pipeline.

This is the reference implementation for a single template:
  prepare  original.pptx -> package/source.pptx + slide_library + layout_index + fingerprint
  build    package/ + fill_plan.json -> output.pptx + page_map + fidelity report
  verify   source.pptx vs output.pptx -> per-page structural proof

It deliberately does NOT create SVG pages. The output is cloned from the
original PPTX and only text / table / chart data are edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pptx import Presentation  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE_TYPE  # noqa: E402

from template_fill_pptx.analyzer import analyze_pptx  # noqa: E402
from template_fill_pptx.applier import apply_plan  # noqa: E402
from template_fill_pptx.checker import check_plan  # noqa: E402
from template_fill_pptx.ooxml import _parse_slide_refs  # noqa: E402

PLACEHOLDERS = (
    "单击此处", "单击添加", "YOUR CONPANY", "输入医院名称",
    "请替换文字内容", "模板所有页面均有动画", "替换文字内容",
)
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _slide_xmls(path: Path) -> list[bytes]:
    with zipfile.ZipFile(path) as zf:
        return [zf.read(ref.part_name) for ref in _parse_slide_refs(zf)]


def _nontext_xml(xml: bytes) -> bytes:
    """Layout signature: drop text runs/breaks but keep shape and paragraph properties."""
    root = ET.fromstring(xml)
    drop = {A_NS + "r", A_NS + "br", A_NS + "fld", A_NS + "t"}
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag in drop:
                parent.remove(child)
    text = ET.tostring(root, encoding="unicode")
    return ET.canonicalize(text, strip_text=True).encode("utf-8")


def _walk_shapes(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _walk_shapes(shape.shapes)


def _shape_signature(slide) -> list[list]:
    rows = []
    for shape in _walk_shapes(slide.shapes):
        rows.append([
            str(shape.shape_type),
            int(shape.shape_id),
            shape.name,
            shape.left,
            shape.top,
            shape.width,
            shape.height,
            float(shape.rotation),
            bool(getattr(shape, "has_text_frame", False)),
            bool(getattr(shape, "has_table", False)),
            bool(getattr(shape, "has_chart", False)),
        ])
    return rows


def _media_hashes(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return sorted(hashlib.sha256(zf.read(n)).hexdigest() for n in zf.namelist() if n.startswith("ppt/media/"))


def _slide_text(path: Path) -> list[str]:
    prs = Presentation(str(path))
    texts = []
    for slide in prs.slides:
        parts = [shape.text for shape in slide.shapes if getattr(shape, "has_text_frame", False)]
        texts.append("\n".join(parts))
    return texts


def prepare(source: Path, package: Path, template_id: str) -> dict:
    package.mkdir(parents=True, exist_ok=True)
    source_copy = package / "source.pptx"
    shutil.copy2(source, source_copy)
    library = analyze_pptx(source_copy)
    _write(package / "slide_library.json", library)

    pages = []
    for slide in library["slides"]:
        pages.append({
            "slide": slide["slide_index"],
            "role": slide.get("page_type"),
            "slot_count": len(slide.get("slots", [])),
            "tables": len(slide.get("tables", [])),
            "charts": len(slide.get("charts", [])),
            "summary": str(slide.get("text_summary", "")).replace("\n", " ")[:80],
        })
    _write(package / "layout_index.json", {
        "schema": "native_full_layout_index.v1",
        "deck_id": template_id,
        "source": "source.pptx",
        "slide_count": library["slide_count"],
        "canvas_px": library["canvas_px"],
        "pages": pages,
    })

    xmls = _slide_xmls(source_copy)
    prs = Presentation(str(source_copy))
    fingerprints = []
    for index, xml in enumerate(xmls, start=1):
        fingerprints.append({
            "slide": index,
            "nontext_sha256": hashlib.sha256(_nontext_xml(xml)).hexdigest(),
            "shape_signature": _shape_signature(prs.slides[index - 1]),
        })
    _write(package / "layout_fingerprint.json", {
        "schema": "native_full_fingerprint.v1",
        "source_sha256": _sha256(source_copy),
        "slide_count": len(xmls),
        "media_sha256": _media_hashes(source_copy),
        "pages": fingerprints,
    })

    manifest = {
        "schema": "native_full_manifest.v1",
        "template_id": template_id,
        "source": "source.pptx",
        "source_sha256": _sha256(source_copy),
        "source_bytes": source_copy.stat().st_size,
        "slide_count": library["slide_count"],
        "canvas_px": library["canvas_px"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "route": "native",
        "full_page_previews": 0,
    }
    _write(package / "manifest.json", manifest)
    return manifest


def render_previews(package: Path, outdir: Path | None = None) -> dict:
    manifest = _load(package / "manifest.json")
    source = package / manifest["source"]
    outdir = outdir or package / "previews"
    outdir.mkdir(parents=True, exist_ok=True)
    slidep = shutil.which("slidep")
    if not slidep:
        raise RuntimeError("slidep is required to render full-page previews")
    rendered = 0
    for index in range(manifest["slide_count"]):
        target = outdir / f"slide_{index + 1:02d}.png"
        for _ in range(2):
            subprocess.run(
                [slidep, "screenshot", str(source), "--page-index", str(index), "--out", str(target)],
                capture_output=True, text=True,
            )
            if target.is_file():
                break
        if not target.is_file():
            raise RuntimeError(f"preview render failed for page {index + 1}")
        rendered += 1
    manifest["full_page_previews"] = rendered
    manifest["previews_dir"] = str(outdir.relative_to(package)) if outdir.is_relative_to(package) else str(outdir)
    _write(package / "manifest.json", manifest)
    return {"previews": rendered, "dir": str(outdir)}


def _picture_hashes(slide) -> set[str]:
    hashes = set()
    for shape in _walk_shapes(slide.shapes):
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            hashes.add(hashlib.sha256(shape.image.blob).hexdigest())
    return hashes


def verify(source: Path, output: Path, page_map: list[int] | None = None) -> dict:
    src = Presentation(str(source))
    dst = Presentation(str(output))
    src_xml = _slide_xmls(source)
    out_xml = _slide_xmls(output)
    implicit_map = page_map is None
    if implicit_map:
        page_map = list(range(1, len(src.slides) + 1))
    reports = []
    errors = []
    if len(page_map) != len(dst.slides):
        errors.append(f"page map {len(page_map)} != output {len(dst.slides)}")
    if implicit_map and len(src.slides) != len(dst.slides):
        errors.append(f"page count {len(src.slides)} -> {len(dst.slides)}")
    source_media = set()
    for source_index in page_map:
        if 1 <= source_index <= len(src.slides):
            source_media |= _picture_hashes(src.slides[source_index - 1])
    output_media = set()
    for slide in dst.slides:
        output_media |= _picture_hashes(slide)
    for index, source_index in enumerate(page_map, start=1):
        if not (1 <= source_index <= len(src.slides)):
            errors.append(f"P{index:02d}: source page {source_index} out of range")
            continue
        a = src.slides[source_index - 1]
        if index - 1 >= len(dst.slides):
            errors.append(f"P{index:02d}: output page missing (output has {len(dst.slides)} pages)")
            continue
        b = dst.slides[index - 1]
        sig_a = _shape_signature(a)
        sig_b = _shape_signature(b)
        xml_a = src_xml[source_index - 1]
        xml_b = out_xml[index - 1] if index - 1 < len(out_xml) else b""
        nontext_equal = bool(xml_a) and bool(xml_b) and _nontext_xml(xml_a) == _nontext_xml(xml_b)
        shape_equal = sig_a == sig_b
        if not shape_equal:
            errors.append(f"P{index:02d}: shape signature differs from source P{source_index:02d}")
        if not nontext_equal:
            errors.append(f"P{index:02d}: non-text XML differs from source P{source_index:02d}")
        reports.append({
            "output_slide": index,
            "source_slide": source_index,
            "shape_count_source": len(sig_a),
            "shape_count_output": len(sig_b),
            "shape_signature_equal": shape_equal,
            "nontext_xml_equal": nontext_equal,
        })
    missing_media = sorted(source_media - output_media)
    if missing_media:
        errors.append(f"media missing: {len(missing_media)}")
    # Any remaining template prompt is a hard failure.
    for i, text in enumerate(_slide_text(output), start=1):
        hits = [p for p in PLACEHOLDERS if p in text]
        if hits:
            errors.append(f"P{i:02d}: placeholder remains: {hits}")
    return {
        "ok": not errors,
        "errors": errors,
        "source": str(source),
        "output": str(output),
        "page_count": len(dst.slides),
        "media_missing": len(missing_media),
        "pages": reports,
    }


def build(package: Path, plan_path: Path, output: Path) -> dict:
    manifest = _load(package / "manifest.json")
    source = package / manifest["source"]
    if _sha256(source) != manifest["source_sha256"]:
        raise RuntimeError("Template source SHA256 changed; refuse to build")
    plan = _load(plan_path)
    library = analyze_pptx(source)
    check = check_plan(library, plan)
    if check["summary"]["error"]:
        raise RuntimeError(f"Plan has {check['summary']['error']} hard errors")
    apply_plan(source, plan, output, transition="keep")
    page_map = [
        {"output_slide": i, "source_slide": int(item["source_slide"])}
        for i, item in enumerate(plan.get("slides", []), start=1)
    ]
    report = verify(source, output, [item["source_slide"] for item in page_map])
    report["plan_check"] = check["summary"]
    report["page_map"] = page_map
    _write(package / "page_map.json", page_map)
    _write(package / "fidelity_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prepare")
    prep.add_argument("source", type=Path)
    prep.add_argument("package", type=Path)
    prep.add_argument("--template-id", default="厦门大学_主题_厦大蓝")

    prev = sub.add_parser("previews")
    prev.add_argument("package", type=Path)
    prev.add_argument("--out", type=Path)

    build_p = sub.add_parser("build")
    build_p.add_argument("package", type=Path)
    build_p.add_argument("plan", type=Path)
    build_p.add_argument("-o", "--output", type=Path, required=True)

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("source", type=Path)
    verify_p.add_argument("output", type=Path)
    verify_p.add_argument("--page-map", type=Path,
                          help="page_map.json written by `build`; required when the output "
                               "uses a subset of source pages")

    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.source, args.package, args.template_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "previews":
        result = render_previews(args.package, args.out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "build":
        result = build(args.package, args.plan, args.output)
        print(json.dumps({k: result[k] for k in ("ok", "errors", "page_count", "media_missing")}, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    if args.command == "verify":
        explicit_map = None
        if args.page_map:
            payload = json.loads(args.page_map.read_text(encoding="utf-8"))
            explicit_map = [int(item["source_slide"]) for item in payload]
        result = verify(args.source, args.output, explicit_map)
        print(json.dumps({k: result[k] for k in ("ok", "errors", "page_count", "media_missing")}, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
