#!/usr/bin/env python3
"""Local-only user templates: onboard, list, doctor and a simple gallery.

A user template is a PPTX the user is allowed to use. It is copied (by
default) into ``~/.xmu-ppt/user-templates`` and registered with a local
``U001`` serial. Nothing is uploaded and nothing enters the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from template_fill_pptx.analyzer import analyze_pptx  # noqa: E402
import text_fit  # noqa: E402

HOME = Path.home() / ".xmu-ppt" / "user-templates"
REGISTRY = HOME / "registry.local.json"
GALLERY = HOME / "index.html"
COVER_SIZE = (960, 540)
MAX_FILE_MB = 500
WARN_FILE_MB = 200
SCHEMA = "xmu_user_template_registry.v1"
MANIFEST_SCHEMA = "xmu_user_template.v1"
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_registry() -> dict:
    current = _load(REGISTRY)
    if current is not None:
        return current
    payload = {
        "schema": SCHEMA,
        "next_serial": 1,
        "entries": [],
        "note": "本机私有模板注册表；不进入仓库、不上传。",
    }
    _write(REGISTRY, payload)
    return payload


def _entries() -> list[dict]:
    if not REGISTRY.exists():
        return []
    return list((_load(REGISTRY, {}) or {}).get("entries", []))


def lookup(selection: str) -> dict | None:
    """Resolve a U-prefixed serial or USR-* id without touching public serials."""
    value = str(selection).strip()
    serial_match = re.fullmatch(r"[Uu](\d{1,3})", value)
    if serial_match:
        serial = f"U{int(serial_match.group(1)):03d}"
        return next((e for e in _entries() if e.get("serial", "").upper() == serial), None)
    if value.upper().startswith("USR-"):
        return next((e for e in _entries() if e.get("template_id") == value), None)
    return None


def _entry_by_id(template_id: str) -> dict | None:
    return next((e for e in _entries() if e.get("template_id") == template_id), None)


def _manifest(entry: dict) -> dict | None:
    path = HOME / entry["serial"] / "user_template.json"
    return _load(path)


def source_path(template_id: str) -> Path | None:
    entry = _entry_by_id(template_id)
    if not entry:
        return None
    manifest = _manifest(entry)
    if not manifest:
        return None
    raw = manifest.get("source_path") or "source.pptx"
    path = Path(raw)
    if not path.is_absolute():
        path = HOME / entry["serial"] / path
    return path


def _fit_cover(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    canvas = Image.new("RGB", COVER_SIZE, "#FFFFFF")
    image.thumbnail(COVER_SIZE, Image.Resampling.LANCZOS)
    canvas.paste(image, ((COVER_SIZE[0] - image.width) // 2,
                         (COVER_SIZE[1] - image.height) // 2))
    return canvas


def _placeholder_cover(dest: Path, label: str) -> None:
    image = Image.new("RGB", COVER_SIZE, "#EEF2F6")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(FONT_PATH, 32)
        small = ImageFont.truetype(FONT_PATH, 18)
    except OSError:
        font = small = ImageFont.load_default()
    draw.text((COVER_SIZE[0] // 2, COVER_SIZE[1] // 2 - 22),
              label[:28], fill="#65758A", font=font, anchor="mm")
    draw.text((COVER_SIZE[0] // 2, COVER_SIZE[1] // 2 + 24),
              "我的模板 · 仅本机浏览", fill="#9AA8B8", font=small, anchor="mm")
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, "WEBP", quality=82)


def _cover_from_pptx(pptx: Path, dest: Path) -> bool:
    try:
        with zipfile.ZipFile(pptx) as archive:
            if "docProps/thumbnail.jpeg" not in archive.namelist():
                return False
            raw = archive.read("docProps/thumbnail.jpeg")
        with Image.open(io.BytesIO(raw)) as image:
            _fit_cover(image).save(dest, "WEBP", quality=84)
        return True
    except (OSError, zipfile.BadZipFile, ValueError):
        return False


ROLE_MAP = {
    "cover_candidate": "cover",
    "toc_candidate": "toc",
    "chapter_candidate": "chapter",
    "ending_candidate": "ending",
    "thanks_candidate": "ending",
}


def _page_catalog(library: dict, source: Path) -> dict:
    capacity = text_fit.build_capacity_map(source, library)
    pages = []
    for slide in library.get("slides", []):
        index = int(slide.get("slide_index") or 0)
        role = ROLE_MAP.get(str(slide.get("page_type") or ""), "content")
        shapes = [role] if role != "content" else ["content"]
        if slide.get("tables"):
            shapes.append("table")
        if slide.get("charts"):
            shapes.append("chart")
        slot_ids = [s.get("slot_id") for s in slide.get("slots", []) if s.get("slot_id")]
        slots_capacity = [capacity.get(sid) for sid in slot_ids if capacity.get(sid)]
        max_chars = max((int(c.get("safe_chars") or 0) for c in slots_capacity), default=0)
        total_chars = sum(int(c.get("safe_chars") or 0) for c in slots_capacity)
        if total_chars >= 180:
            density = "high"
        elif total_chars >= 70:
            density = "medium"
        else:
            density = "low"
        if role == "content" and len(slide.get("slots", [])) >= 5:
            shapes.append("text_heavy")
        pages.append({
            "slide": index,
            "role": role,
            "page_type": slide.get("page_type"),
            "content_shapes": sorted(set(shapes)),
            "capacity": {
                "max_slot_chars": max_chars,
                "total_safe_chars": total_chars,
            },
            "has_table": bool(slide.get("tables")),
            "has_chart": bool(slide.get("charts")),
            "image_slots": 0,
            "density": density,
            "summary": str(slide.get("text_summary") or "").replace("\n", " ")[:100],
            "confidence": 0.8 if role != "content" else 0.6,
        })
    return {
        "schema": "xmu_page_catalog.v1",
        "template_id": None,
        "pages": pages,
    }


def _gallery_html(entries: list[dict]) -> str:
    cards = []
    for entry in entries:
        cover = entry.get("cover") or "placeholder.webp"
        name = html.escape(str(entry.get("name") or "未命名模板"))
        serial = html.escape(str(entry.get("serial") or ""))
        pages = entry.get("slides") or "—"
        cards.append(
            f'<article class="card"><img src="{html.escape(cover)}" alt="{name}">'
            f'<div class="body"><div class="meta"><span>{serial}</span>'
            f'<span>仅本机</span></div><h2>{name}</h2>'
            f'<p>{pages} 页 · 原生填充</p></div></article>'
        )
    cards_html = "\n".join(cards) or (
        '<p class="empty">还没有我的模板。说“把这份 PPTX 加入我的模板”即可。</p>'
    )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>我的模板 · xmu-ppt</title>
<style>
:root {{ color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; }}
body {{ margin: 0; background: #f5f7fa; color: #172033; }}
header {{ padding: 32px 5vw 12px; }}
h1 {{ margin: 0 0 8px; font-size: 28px; }}
p.sub {{ margin: 0; color: #667085; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 18px; padding: 24px 5vw 48px; }}
.card {{ background: white; border: 1px solid #e4e9f0; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(23,32,51,.05); }}
.card img {{ width: 100%; aspect-ratio: 16/9; object-fit: cover; display: block; background: #eef2f6; }}
.body {{ padding: 14px 16px 16px; }}
.meta {{ display: flex; justify-content: space-between; color: #667085; font-size: 12px; }}
h2 {{ font-size: 17px; margin: 8px 0 6px; }}
.card p {{ color: #667085; font-size: 13px; margin: 0; }}
.empty {{ padding: 24px 5vw; color: #667085; }}
.notice {{ margin: 0 5vw; padding: 12px 14px; border: 1px solid #dce4ee; background: #fff; border-radius: 10px; color: #475467; font-size: 13px; }}
</style></head><body>
<header><h1>我的模板</h1><p class="sub">只在本机使用 · 不上传 · 不进入公开仓库</p></header>
<p class="notice">这是本机模板库。报告 U 开头的序号给 AI 即可使用；例如“用 U001 做组会汇报”。</p>
<section class="cards">{cards_html}</section>
</body></html>
"""


def write_gallery() -> Path:
    HOME.mkdir(parents=True, exist_ok=True)
    entries = _entries()
    (HOME / "index.html").write_text(_gallery_html(entries), encoding="utf-8")
    if not (HOME / "placeholder.webp").exists():
        _placeholder_cover(HOME / "placeholder.webp", "暂无封面")
    return HOME / "index.html"


def gallery_uri() -> str | None:
    path = HOME / "index.html"
    return path.resolve().as_uri() if path.is_file() else None


def onboard(pptx: Path, *, name: str | None = None, link: bool = False,
            force: bool = False, rights_confirmed: bool = False) -> dict:
    source = Path(pptx).expanduser()
    if not rights_confirmed:
        raise RuntimeError(
            "请先确认你合法持有或有权使用这份模板；模板只会在本机使用，不会上传或进入公开仓库。"
            "确认后加 --rights-confirmed。"
        )
    if not source.is_file():
        raise RuntimeError(f"文件不存在：{source}")
    if source.suffix.lower() == ".pptm":
        raise RuntimeError("不支持 .pptm 宏模板；请先另存为 .pptx。")
    if source.suffix.lower() != ".pptx":
        raise RuntimeError("只支持 .pptx 文件；.ppt 请先另存为 .pptx。")
    size_mb = source.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise RuntimeError(f"文件过大：{size_mb:.0f} MB（上限 {MAX_FILE_MB} MB）。")
    digest = _sha256(source)
    existing = next((e for e in _entries() if e.get("source_sha256") == digest), None)
    if existing and not force:
        if source_path(existing["template_id"]) and source_path(existing["template_id"]).is_file():
            return {"already_exists": True, **_summary(existing)}

    try:
        library = analyze_pptx(source)
    except Exception as exc:
        raise RuntimeError(f"无法解析这个 PPTX：{exc}") from exc
    if not library.get("slides"):
        raise RuntimeError("这个 PPTX 没有可分析的页面。")

    registry = ensure_registry()
    if existing and force:
        serial = existing["serial"]
        folder = HOME / serial
        if source.resolve().is_relative_to(folder.resolve()):
            raise RuntimeError("不能直接覆盖模板库内的源文件；请用原始文件重新入库。")
        shutil.rmtree(folder, ignore_errors=True)
    else:
        serial = f"U{int(registry.get('next_serial', 1)):03d}"
        folder = HOME / serial
        while folder.exists() or any(e.get("serial") == serial for e in registry["entries"]):
            registry["next_serial"] = int(registry.get("next_serial", 1)) + 1
            serial = f"U{int(registry['next_serial']):03d}"
        registry["next_serial"] = int(registry.get("next_serial", 1)) + 1
    folder.mkdir(parents=True, exist_ok=True)

    template_id = existing["template_id"] if existing else f"USR-{digest[:8]}"
    try:
        if link:
            source_mode = "link"
            source_path_value = str(source.resolve())
            analysis_source = source
        else:
            source_mode = "copy"
            target = folder / "source.pptx"
            shutil.copy2(source, target)
            source_path_value = "source.pptx"
            analysis_source = target
        library = analyze_pptx(analysis_source)
        (folder / "source.slide_library.json").write_text(
            json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        page_catalog = _page_catalog(library, analysis_source)
        page_catalog["template_id"] = template_id
        (folder / "page_catalog.json").write_text(
            json.dumps(page_catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cover = folder / "previews" / "cover.webp"
        if not _cover_from_pptx(analysis_source, cover):
            _placeholder_cover(cover, name or source.stem)
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "template_id": template_id,
            "serial": serial,
            "name": name or source.stem,
            "source_path": source_path_value,
            "source_mode": source_mode,
            "source_sha256": digest,
            "slides": len(library.get("slides", [])),
            "canvas": library.get("canvas_px"),
            "rights_confirmed_at": _now(),
            "created_at": _now(),
            "page_catalog": "page_catalog.json",
            "preview": "previews/cover.webp",
            "status": "active",
        }
        _write(folder / "user_template.json", manifest)
        entry = {
            "serial": serial,
            "template_id": template_id,
            "name": manifest["name"],
            "source_path": source_path_value,
            "source_sha256": digest,
            "slides": manifest["slides"],
            "status": "active",
            "rights_confirmed_at": manifest["rights_confirmed_at"],
            "created_at": manifest["created_at"],
            "cover": f"{serial}/previews/cover.webp",
        }
        registry["entries"] = [e for e in registry["entries"] if e.get("template_id") != template_id]
        registry["entries"].append(entry)
        registry["entries"].sort(key=lambda e: e.get("serial", ""))
        _write(REGISTRY, registry)
        write_gallery()
        return {
            "already_exists": False,
            "serial": serial,
            "template_id": template_id,
            "name": manifest["name"],
            "slides": manifest["slides"],
            "gallery": str(HOME / "index.html"),
            "warnings": [f"文件较大：{size_mb:.0f} MB"] if size_mb > WARN_FILE_MB else [],
        }
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise


def _summary(entry: dict) -> dict:
    return {
        "serial": entry.get("serial"),
        "template_id": entry.get("template_id"),
        "name": entry.get("name"),
        "slides": entry.get("slides"),
        "gallery": str(HOME / "index.html"),
    }


def list_templates() -> list[dict]:
    result = []
    for entry in _entries():
        path = source_path(entry["template_id"])
        result.append({
            **entry,
            "source_ok": bool(path and path.is_file()),
            "source_path_resolved": str(path) if path else None,
        })
    return result


def doctor() -> dict:
    errors, warnings = [], []
    for entry in _entries():
        path = source_path(entry["template_id"])
        if not path or not path.is_file():
            errors.append(f"{entry.get('serial')}：原件不存在")
            continue
        if entry.get("source_sha256") and _sha256(path) != entry["source_sha256"]:
            warnings.append(f"{entry.get('serial')}：原件内容已变化，建议重新入库")
        if not (HOME / entry["serial"] / "page_catalog.json").is_file():
            warnings.append(f"{entry.get('serial')}：缺少页面目录")
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "count": len(_entries()), "root": str(HOME)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="本机私有模板入库（只在本机使用，不上传）")
    sub = parser.add_subparsers(dest="command", required=True)
    on = sub.add_parser("onboard", help="把一个 PPTX 加入我的模板")
    on.add_argument("pptx")
    on.add_argument("--name")
    on.add_argument("--link", action="store_true", help="只登记原路径，不复制文件")
    on.add_argument("--force", action="store_true", help="覆盖同一模板的旧副本")
    on.add_argument("--rights-confirmed", action="store_true",
                    help="确认你合法持有或有权使用该模板")
    sub.add_parser("list", help="列出我的模板")
    sub.add_parser("doctor", help="检查我的模板原件与目录")
    sub.add_parser("gallery", help="重新生成本机模板画廊")
    args = parser.parse_args(argv)
    try:
        if args.command == "onboard":
            result = onboard(Path(args.pptx), name=args.name, link=args.link,
                             force=args.force, rights_confirmed=args.rights_confirmed)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result.get("warnings"):
                for warning in result["warnings"]:
                    print(f"警告：{warning}", file=sys.stderr)
            return 0
        if args.command == "list":
            print(json.dumps(list_templates(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "doctor":
            result = doctor()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 1
        if args.command == "gallery":
            print(write_gallery())
            return 0
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
