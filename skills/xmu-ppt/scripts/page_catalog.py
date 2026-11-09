#!/usr/bin/env python3
"""Semantic page catalogue and content-aware page suggestions.

The catalogue is deliberately small: role, content shapes, density and
capacity. It does not claim to understand visual quality; it only helps the
agent avoid choosing a cover page for a comparison or a table page for prose.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "xmu_page_catalog.v1"
DECKS = Path(__file__).resolve().parents[1] / "templates" / "decks"

ROLE_MAP = {
    "cover_candidate": "cover",
    "toc_candidate": "toc",
    "chapter_candidate": "chapter",
    "ending_candidate": "ending",
    "thanks_candidate": "ending",
}
ROLE_SHAPES = {
    "cover": "cover",
    "toc": "toc",
    "chapter": "chapter",
    "content": "context",
    "ending": "ending",
}
LAYOUT_SHAPES = {
    "cover": ["cover"],
    "toc": ["toc"],
    "chapter-divider": ["chapter"],
    "ending": ["ending"],
    "hero-statement": ["context"],
    "list": ["context"],
    "multi-block": ["comparison"],
    "two-block": ["comparison"],
    "numbered-cards": ["kpi"],
    "content": ["context"],
}


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _density(slot_count: int, role: str) -> str:
    if role in {"cover", "toc", "chapter", "ending"} and slot_count <= 30:
        return "low"
    if slot_count <= 6:
        return "low"
    if slot_count <= 20:
        return "medium"
    return "high"


def from_layout_index(deck_id: str, data: dict) -> dict:
    pages = []
    for page in data.get("pages", []):
        page_type = str(page.get("role") or "content_candidate")
        role = ROLE_MAP.get(page_type, "content")
        layout = str(page.get("layout") or "")
        shapes = set(LAYOUT_SHAPES.get(layout, [ROLE_SHAPES.get(role, "context")]))
        if role == "chapter":
            shapes.discard("context")
            shapes.add("chapter")
        if page.get("tables"):
            shapes.add("table")
        if page.get("charts"):
            shapes.add("chart")
        # 编号卡片页通常用来放 3–4 个并列要点/指标。
        if layout == "numbered-cards" and "kpi" not in shapes:
            shapes.add("kpi")
        pages.append({
            "slide": int(page.get("slide") or 0),
            "source_slide": int(page.get("slide") or 0),
            "text_slots": int(page.get("slot_count") or 0),
            "role": role,
            "page_type": page_type,
            "layout": layout,
            "content_shapes": sorted(shapes),
            "capacity": {
                "slot_count": int(page.get("slot_count") or 0),
                "type_scale_px": page.get("type_scale_px") or [],
            },
            "has_table": bool(page.get("tables")),
            "has_chart": bool(page.get("charts")),
            "image_slots": 0,
            "density": _density(int(page.get("slot_count") or 0), role),
            "summary": str(page.get("summary") or "").replace("\n", " ")[:100],
            "confidence": 0.8 if role != "content" else 0.65,
        })
    return {"schema": SCHEMA, "template_id": deck_id, "pages": pages}


def from_user_catalog(template_id: str, path: Path) -> dict | None:
    if not path.is_file():
        return None
    data = _read(path)
    if data.get("schema") != SCHEMA:
        return None
    data["template_id"] = template_id
    for page in data.get("pages", []):
        page.setdefault("source_slide", page.get("slide"))
        page.setdefault("text_slots", (page.get("capacity") or {}).get("slot_count", 0))
    return data


def for_item(item: dict) -> dict | None:
    """Return a semantic catalogue for a built-in or local user template."""
    namespace = item.get("namespace")
    template_id = item.get("id")
    if namespace == "builtin":
        path = DECKS / template_id / "layout_index.json"
        if path.is_file():
            return from_layout_index(template_id, _read(path))
        return None
    if namespace == "user":
        try:
            from user_templates import source_path
            source = source_path(template_id)
        except (ImportError, OSError, ValueError):
            return None
        if not source:
            return None
        return from_user_catalog(template_id, source.parent / "page_catalog.json")
    # External/local scan templates currently have no semantic catalogue; do not
    # guess from filenames or force an expensive analysis on every recommend.
    return None


def _shape_score(page: dict, desired: set[str]) -> int:
    shapes = set(page.get("content_shapes") or [])
    score = 5 * len(desired & shapes)
    if "table" in desired and page.get("has_table"):
        score += 2
    if "chart" in desired and page.get("has_chart"):
        score += 2
    role = page.get("role")
    if role in desired:
        score += 3
    if "cover" in desired and role == "cover":
        score += 3
    if "ending" in desired and role == "ending":
        score += 3
    return score


def suggest(catalog: dict | None, brief_page: dict, limit: int = 3) -> list[dict]:
    if not catalog:
        return []
    desired = set(brief_page.get("content_shape") or [])
    ranked = []
    for page in catalog.get("pages", []):
        score = _shape_score(page, desired)
        if score <= 0:
            continue
        matched = sorted(desired & set(page.get("content_shapes") or []))
        reason = "匹配：" + "、".join(matched) if matched else "角色匹配"
        ranked.append({
            "source_slide": page.get("slide"),
            "role": page.get("role"),
            "content_shapes": page.get("content_shapes") or [],
            "density": page.get("density"),
            "summary": page.get("summary"),
            "score": score,
            "reason": reason,
        })
    ranked.sort(key=lambda item: (-item["score"], item["source_slide"] or 0))
    if not ranked:
        # 没有精确匹配时，给出容量较大的内容页作为备选，并明确说明不匹配。
        fallback = [
            page for page in catalog.get("pages", [])
            if page.get("role") == "content"
        ]
        fallback.sort(key=lambda page: (-(page.get("capacity") or {}).get("slot_count", 0),
                                        page.get("slide") or 0))
        return [
            {
                "source_slide": page.get("slide"),
                "role": page.get("role"),
                "content_shapes": page.get("content_shapes") or [],
                "density": page.get("density"),
                "summary": page.get("summary"),
                "score": 0,
                "reason": "没有精确匹配，这是容量较大的备选；可能需要调整版式或另选模板",
            }
            for page in fallback[:limit]
        ]
    return ranked[:limit]


def coverage(catalog: dict | None, brief: dict, limit: int = 3) -> int:
    """How well a template's pages cover the brief's requested shapes."""
    if not catalog:
        return 0
    total = 0
    for page in brief.get("pages", []):
        total += sum(item["score"] for item in suggest(catalog, page, limit=limit))
    return total


def with_brief(catalog: dict | None, brief: dict) -> dict:
    pages = []
    for page in (catalog or {}).get("pages", []):
        pages.append(page)
    suggestions = []
    for brief_page in brief.get("pages", []):
        suggestions.append({
            "page_no": brief_page.get("page_no"),
            "purpose": brief_page.get("purpose"),
            "content_shape": brief_page.get("content_shape") or [],
            "suggested_pages": suggest(catalog, brief_page),
        })
    return {
        "schema": SCHEMA,
        "template_id": (catalog or {}).get("template_id"),
        "pages": pages,
        "brief_suggestions": suggestions,
    }
