#!/usr/bin/env python3
"""Brand and layout layers for the built-in XMU decks.

Two small layers, not four:

* ``brands/<brand_id>/brand.json`` — identity only: palette, typography, logo
  rules, voice. One file, shared by every deck of that brand.
* ``decks/<deck_id>/brand.json`` — this deck's brand binding: which brand it
  belongs to and which colour it actually uses for its primary.
* ``decks/<deck_id>/layout_index.json`` — already exists: page roles and
  layouts. This module only validates it, it does not duplicate it.

The purpose is narrow on purpose: give the fill step a closed set of legal
colours and a font stack, instead of letting any hex value through.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SCHEMA_BRAND = "xmu_ppt_brand.v1"
SCHEMA_DECK_BRAND = "xmu_ppt_deck_brand.v1"

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
BRANDS = TEMPLATES / "brands"
DECKS = TEMPLATES / "decks"

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

ROLE_VOCABULARY = {
    "cover_candidate",
    "toc_candidate",
    "chapter_candidate",
    "content_candidate",
    "ending_candidate",
    "thanks_candidate",
}

LAYOUT_VOCABULARY = {
    "cover",
    "toc",
    "chapter-divider",
    "ending",
    "hero-statement",
    "list",
    "multi-block",
    "two-block",
    "numbered-cards",
    "content",
    "table",
    "chart",
}


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _clean(color: str) -> str:
    return color.strip().upper()


def is_hex(value: object) -> bool:
    return isinstance(value, str) and bool(HEX_RE.match(value.strip()))


def brand_index() -> dict:
    return _read(BRANDS / "brands_index.json") or {}


def load_brand(brand_id: str | None = None) -> dict | None:
    """Load a brand identity preset by id. No id means no brand — never guess."""
    if not brand_id:
        return None
    data = _read(BRANDS / brand_id / "brand.json")
    if not data or data.get("schema") != SCHEMA_BRAND:
        return None
    data["brand_id"] = brand_id
    return data


def load_deck_brand(deck_id: str) -> dict | None:
    data = _read(DECKS / deck_id / "brand.json")
    if not data or data.get("schema") != SCHEMA_DECK_BRAND:
        return None
    data["deck_id"] = deck_id
    return data


def brand_colors(brand: dict | None) -> dict[str, str]:
    if not brand:
        return {}
    colors: dict[str, str] = {}
    raw = brand.get("colors") or {}
    if isinstance(raw, dict):
        for role, entry in raw.items():
            value = entry.get("value") if isinstance(entry, dict) else entry
            if is_hex(value):
                colors[role] = _clean(value)
    primary = brand.get("primary_color")
    if is_hex(primary):
        colors.setdefault("primary", _clean(primary))
    return colors


def palette(deck_id: str) -> list[str]:
    """Closed set of colours this deck may use for explicit text colours."""
    deck = load_deck_brand(deck_id)
    brand = load_brand(deck.get("brand_id") if deck else None)
    values = set(brand_colors(brand).values())
    if deck and is_hex(deck.get("primary_color")):
        values.add(_clean(deck["primary_color"]))
    return sorted(values)


def is_allowed_color(deck_id: str, color: str | None) -> bool:
    """An explicit colour must come from the deck palette, not from thin air."""
    if not color:
        return True
    if not is_hex(color):
        return False
    values = palette(deck_id)
    if not values:
        return True
    return _clean(color) in values


def describe(deck_id: str) -> dict:
    """Compact brand block for the `pages` output the agent reads."""
    deck = load_deck_brand(deck_id) or {}
    brand = load_brand(deck.get("brand_id")) or {}
    typography = brand.get("typography") or {}
    logo = brand.get("logo") or {}
    deck_logo = deck.get("logo") or {}
    return {
        "brand_id": deck.get("brand_id") or brand.get("brand_id"),
        "primary_color": deck.get("primary_color") or brand.get("primary_color"),
        "palette": palette(deck_id),
        "typography": {
            key: value.get("stack")
            for key, value in typography.items()
            if isinstance(value, dict) and value.get("stack")
        },
        "logo": {
            "file": deck_logo.get("file") or logo.get("file"),
            "placement": logo.get("placement") or {},
            "forbidden": logo.get("forbidden") or [],
        },
        "voice": brand.get("voice") or {},
    }


def font_for(deck_id: str, role: str = "body") -> list[str]:
    brand = load_brand((load_deck_brand(deck_id) or {}).get("brand_id")) or {}
    typography = brand.get("typography") or {}
    entry = typography.get(role) or typography.get("body") or {}
    return list(entry.get("stack") or [])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_repo() -> list[str]:
    """Return human-readable problems; empty list means the layers agree."""
    problems: list[str] = []
    index = brand_index()
    if not index:
        problems.append("brands_index.json 缺失或为空")

    for brand_id in index:
        data = _read(BRANDS / brand_id / "brand.json")
        if data is None:
            problems.append(f"品牌 {brand_id} 缺少 brand.json")
            continue
        if data.get("schema") != SCHEMA_BRAND:
            problems.append(f"品牌 {brand_id} 的 schema 不是 {SCHEMA_BRAND}")
        if not (BRANDS / brand_id / "design_spec.md").is_file():
            problems.append(f"品牌 {brand_id} 缺少 design_spec.md")
        primary = data.get("primary_color")
        if not is_hex(primary):
            problems.append(f"品牌 {brand_id} 的 primary_color 不是 #RRGGBB：{primary!r}")
        elif index.get(brand_id, {}).get("primary_color") and (
            _clean(index[brand_id]["primary_color"]) != _clean(primary)
        ):
            problems.append(
                f"品牌 {brand_id} 的 primary_color 与 brands_index.json 不一致："
                f"{primary} vs {index[brand_id]['primary_color']}"
            )
        for role, entry in (data.get("colors") or {}).items():
            value = entry.get("value") if isinstance(entry, dict) else entry
            if not is_hex(value):
                problems.append(f"品牌 {brand_id} 的颜色 {role} 不是 #RRGGBB：{value!r}")
        logo = data.get("logo") or {}
        logo_file = logo.get("file")
        if logo_file:
            path = BRANDS / brand_id / logo_file
            if not path.is_file():
                problems.append(f"品牌 {brand_id} 声明的校徽不存在：{logo_file}")
            elif logo.get("sha256") and _sha256(path) != logo["sha256"]:
                problems.append(f"品牌 {brand_id} 的校徽哈希与 brand.json 不符")

    decks_index = _read(DECKS / "decks_index.json") or {}
    catalog = {c["id"]: c for c in (_read(DECKS / "catalog.json") or [])}
    deck_dirs = sorted(p.name for p in DECKS.iterdir() if p.is_dir())

    for deck_id in deck_dirs:
        deck = _read(DECKS / deck_id / "brand.json")
        if deck is None:
            problems.append(f"模板 {deck_id} 缺少 brand.json")
            continue
        if deck.get("schema") != SCHEMA_DECK_BRAND:
            problems.append(f"模板 {deck_id} 的 schema 不是 {SCHEMA_DECK_BRAND}")
        brand_id = deck.get("brand_id")
        if brand_id not in index:
            problems.append(f"模板 {deck_id} 指向未知品牌 {brand_id!r}")
        if deck.get("deck_id") != deck_id:
            problems.append(f"模板 {deck_id} 的 deck_id 与目录名不一致")
        if deck_id in catalog and deck.get("serial") != catalog[deck_id].get("serial"):
            problems.append(
                f"模板 {deck_id} 的 serial 与 catalog.json 不一致："
                f"{deck.get('serial')} vs {catalog[deck_id].get('serial')}"
            )
        primary = deck.get("primary_color")
        if not is_hex(primary):
            problems.append(f"模板 {deck_id} 的 primary_color 不是 #RRGGBB：{primary!r}")
        elif deck_id in decks_index and (
            _clean(decks_index[deck_id].get("primary_color", "")) != _clean(primary)
        ):
            problems.append(
                f"模板 {deck_id} 的 primary_color 与 decks_index.json 不一致："
                f"{primary} vs {decks_index[deck_id].get('primary_color')}"
            )
        logo = deck.get("logo") or {}
        logo_file = logo.get("file")
        if logo_file:
            path = DECKS / deck_id / logo_file
            if not path.is_file():
                problems.append(f"模板 {deck_id} 声明的校徽不存在：{logo_file}")
            elif logo.get("sha256"):
                brand = _read(BRANDS / str(brand_id) / "brand.json") or {}
                expected = (brand.get("logo") or {}).get("sha256")
                actual = _sha256(path)
                if actual != logo["sha256"]:
                    problems.append(f"模板 {deck_id} 的校徽哈希与 brand.json 不符")
                if expected and actual != expected:
                    problems.append(
                        f"模板 {deck_id} 的校徽与品牌层不是同一文件：{actual[:12]} vs {expected[:12]}"
                    )

        layout = _read(DECKS / deck_id / "layout_index.json")
        if layout is None:
            continue
        if layout.get("deck_id") != deck_id:
            problems.append(f"模板 {deck_id} 的 layout_index.deck_id 与目录名不一致")
        pages = layout.get("pages") or []
        count = layout.get("slide_count")
        if isinstance(count, int) and pages and len(pages) != count:
            problems.append(
                f"模板 {deck_id} 的 layout_index 页数不符：pages={len(pages)} slide_count={count}"
            )
        seen: set[int] = set()
        for page in pages:
            slide = page.get("slide")
            if not isinstance(slide, int) or slide < 1:
                problems.append(f"模板 {deck_id} 存在非法页号：{slide!r}")
                continue
            if slide in seen:
                problems.append(f"模板 {deck_id} 页号重复：{slide}")
            seen.add(slide)
            role = page.get("role")
            if role and role not in ROLE_VOCABULARY:
                problems.append(f"模板 {deck_id} 第 {slide} 页 role 不在枚举内：{role!r}")
            layout_name = page.get("layout")
            if layout_name and layout_name not in LAYOUT_VOCABULARY:
                problems.append(
                    f"模板 {deck_id} 第 {slide} 页 layout 不在枚举内：{layout_name!r}"
                )
    return problems


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="品牌层与版式层自检")
    parser.add_argument("deck", nargs="?", help="只看某套模板的品牌摘要")
    parser.add_argument("--check", action="store_true", help="校验全部品牌与模板")
    args = parser.parse_args(argv)

    if args.check or not args.deck:
        problems = validate_repo()
        if problems:
            print(f"发现 {len(problems)} 个问题：")
            for item in problems:
                print(" -", item)
            return 1
        print("品牌层与版式层一致：0 个问题")
        if not args.deck:
            return 0

    print(json.dumps(describe(args.deck), ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
