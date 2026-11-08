#!/usr/bin/env python3
"""Local-only external template bridge for the confirm_ui gallery.

大白话：把「本机画廊」里已经渲染好的外部模板，接进制作流程的选择页。
原件一个字节都不复制 —— 只读取本机索引、预览图和原件路径；这些文件全部
被 .gitignore 挡住，永远不进公开仓库。

公开页（docs/templates）不读这里的数据，仍然只显示 15 套内置模板。

纯技能包里的四份索引会被重置为「全新用户初始态」，所以 source_key 必须以
``external_catalog.json``（每次 scan 都会重写）为准；固定序号注册表只是
补充展示名与序号，不能作为定位原件的唯一来源。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GALLERY = ROOT / "local-gallery"
EXTERNAL = ROOT / "skills" / "xmu-ppt" / "templates" / "external"
IMPORTED = ROOT / "output" / "template_import" / "decks"
CATALOG_JS = GALLERY / "catalog.js"
REGISTRY = EXTERNAL / "number_registry.json"
EXTERNAL_CATALOG = EXTERNAL / "external_catalog.json"
ROOT_LOCAL = EXTERNAL / "root.local.json"
SOURCE_MAP = EXTERNAL / "source_map.local.json"


def _read_json(path: Path, default=None):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _gallery_catalog() -> dict | None:
    """Parse ``window.LOCAL_CATALOG = {...};`` without executing JS."""
    if not CATALOG_JS.is_file():
        return None
    try:
        text = CATALOG_JS.read_text(encoding="utf-8")
        start = text.find("=")
        if start < 0:
            return None
        data = json.loads(text[start + 1:].strip().rstrip(";"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _catalog_source_keys() -> dict[str, str]:
    """Authoritative template_id -> source_key map, rebuilt by every scan."""
    data = _read_json(EXTERNAL_CATALOG, {}) or {}
    return {
        item["id"]: item["source_key"]
        for item in data.get("templates", [])
        if item.get("id") and item.get("source_key")
    }


def available() -> bool:
    """No local gallery (fresh clone) -> graceful degradation to 15 built-ins."""
    return _gallery_catalog() is not None


def decks() -> list[dict]:
    """External decks in the same shape as ``template_selection.catalog()``."""
    data = _gallery_catalog()
    if not data:
        return []
    registry = _read_json(REGISTRY, {}) or {}
    by_id = {e["template_id"]: e for e in registry.get("entries", [])}
    catalog_keys = _catalog_source_keys()
    result = []
    for item in data.get("templates", []):
        if item.get("namespace") == "builtin":
            continue
        reg = by_id.get(item["id"], {})
        number = int(item["number"])
        result.append({
            "number": number,
            "id": item["id"],
            "name": item.get("name") or item["id"],
            "style": item.get("style", ""),
            "tags": item.get("tags", []),
            "serial": item.get("serial") or reg.get("serial"),
            # strict-native in the local gallery maps to the 'native' route here.
            "routes": ["native"],
            "preview": f"previews/external/{number}.webp",
            "namespace": "external",
            "rights": item.get("rights", ""),
            "page_count": int(item.get("pages") or 0),
            "source_key": reg.get("source_key") or catalog_keys.get(item["id"]),
        })
    return result


def find(number: int) -> dict | None:
    return next((d for d in decks() if d["number"] == number), None)


def find_by_id(template_id: str) -> dict | None:
    return next((d for d in decks() if d["id"] == template_id), None)


def cover(number: int) -> Path | None:
    deck = find(number)
    if not deck:
        return None
    path = GALLERY / "covers" / f"{deck['id']}.webp"
    return path if path.is_file() else None


def page_image(number: int, page: int) -> Path | None:
    deck = find(number)
    if not deck:
        return None
    path = GALLERY / "pages" / deck["id"] / f"{page:02d}.webp"
    return path if path.is_file() else None


def pages(number: int) -> dict:
    """Same contract as ``/api/deck-pages/<n>`` for built-in decks."""
    deck = find(number)
    empty = {"available": False, "reason": "unknown_external_deck",
             "source_page_count": 0, "preview_count": 0, "complete": False, "pages": []}
    if not deck:
        return empty
    index_file = IMPORTED / deck["id"] / "layout_index.json"
    index = _read_json(index_file, {}) or {}
    source_pages = index.get("pages", [])
    total = int(index.get("slide_count") or deck["page_count"] or 0)
    if not source_pages:
        # Fresh clone: layout index is a local build artifact. Fall back to
        # whatever previews the user rendered, so the gallery still works.
        folder = GALLERY / "pages" / deck["id"]
        names = sorted(folder.glob("*.webp")) if folder.is_dir() else []
        source_pages = [{"slide": i} for i in range(1, len(names) + 1)]
        total = total or len(names)
    out = []
    for pos, item in enumerate(source_pages, 1):
        slide = int(item.get("slide", pos))
        has_preview = page_image(number, slide) is not None
        out.append({
            "slide": slide,
            "role": item.get("role"),
            "layout": item.get("layout"),
            "slot_count": item.get("slot_count", 0),
            "filled_slot_count": item.get("filled_slot_count", 0),
            "tables": item.get("tables", 0),
            "charts": item.get("charts", 0),
            "type_scale_px": item.get("type_scale_px", []),
            "summary": item.get("summary", ""),
            "preview": f"previews/external/{number}/{slide:02d}.webp" if has_preview else None,
        })
    preview_count = sum(1 for p in out if p["preview"])
    return {
        "available": True,
        "source_page_count": total,
        "preview_count": preview_count,
        "complete": total > 0 and preview_count == total,
        "pages": out,
    }


def source_path(template_id: str) -> Path | None:
    """Resolve the original PPTX on this machine, never copying it."""
    manifest = _read_json(IMPORTED / template_id / "manifest.json", {}) or {}
    cached = manifest.get("source_path")
    if cached and Path(cached).is_file():
        return Path(cached)
    root_cfg = _read_json(ROOT_LOCAL, {}) or {}
    mapping = _read_json(SOURCE_MAP, {}) or {}
    deck = find_by_id(template_id)
    key = (deck.get("source_key") if deck else None) or _catalog_source_keys().get(template_id)
    rel = (mapping.get("paths") or {}).get(key) if key else None
    root = root_cfg.get("root")
    if root and rel:
        candidate = Path(root) / rel
        if candidate.is_file():
            return candidate
    return None
