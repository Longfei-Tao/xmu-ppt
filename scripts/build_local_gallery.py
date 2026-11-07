#!/usr/bin/env python3
"""Build a local-only, offline template gallery.

大白话：生成一个只放在你电脑上的「模板目录网页」，双击就能按分类看封面。
不改在线画廊、不改 README、不上传任何图片；数据用 <script> 直接加载，
所以 file:// 双击打开也能用（不会被浏览器的跨域限制拦住）。
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys_scripts = ROOT / "skills" / "xmu-ppt" / "scripts"
if str(sys_scripts) not in sys.path:
    sys.path.insert(0, str(sys_scripts))
import template_numbers as numbers  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_CATALOG = ROOT / "skills/xmu-ppt/templates/external/external_catalog.json"
BUILTIN_CATALOG = ROOT / "docs/templates/catalog.json"
ROOT_LOCAL = ROOT / "skills/xmu-ppt/templates/external/root.local.json"
CATEGORIES_FILE = ROOT / "skills/xmu-ppt/templates/external/categories.json"
DUP_FILE = ROOT / "skills/xmu-ppt/templates/external/duplicates.json"
SOURCE_MAP_FILE = ROOT / "skills/xmu-ppt/templates/external/source_map.local.json"
DECKS_DIR = ROOT / "skills/xmu-ppt/templates/decks"
TEMPLATE_FILE = ROOT / "scripts/local_gallery_template.html"
BUILTIN_PREVIEWS = ROOT / "docs/templates/previews"

OUT = ROOT / "local-gallery"
COVERS = OUT / "covers"
PAGES = OUT / "pages"
CATEGORY_DIR = OUT / "categories"
PLACEHOLDER = "placeholder.webp"

COVER_W, COVER_H = 960, 540
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def make_placeholder(label: str = "暂无预览") -> None:
    """生成一张明确标注「暂无预览」的占位图，绝不伪装成模板外观。"""
    OUT.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (COVER_W, COVER_H), "#EEF2F6")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(FONT_PATH, 34)
        small = ImageFont.truetype(FONT_PATH, 20)
    except OSError:
        font = small = ImageFont.load_default()
    draw.text((COVER_W // 2, COVER_H // 2 - 30), label,
              fill="#7C8B9C", font=font, anchor="mm")
    draw.text((COVER_W // 2, COVER_H // 2 + 24), "本地模板库 · 仅本机浏览",
              fill="#A6B2BF", font=small, anchor="mm")
    image.save(OUT / PLACEHOLDER, "WEBP", quality=80)


def fit_cover(image: Image.Image) -> Image.Image:
    """等比缩放并居中留白，不拉伸、不裁切模板原图。"""
    image = image.convert("RGB")
    canvas = Image.new("RGB", (COVER_W, COVER_H), "#FFFFFF")
    image.thumbnail((COVER_W, COVER_H), Image.Resampling.LANCZOS)
    canvas.paste(image, ((COVER_W - image.width) // 2, (COVER_H - image.height) // 2))
    return canvas


def extract_embedded_cover(pptx: Path, dest: Path) -> bool:
    """从 pptx 自带的 docProps/thumbnail.jpeg 抽封面；只读，不渲染、不改动原件。"""
    try:
        with zipfile.ZipFile(pptx) as zf:
            if "docProps/thumbnail.jpeg" not in zf.namelist():
                return False
            raw = zf.read("docProps/thumbnail.jpeg")
        with Image.open(io.BytesIO(raw)) as image:
            fit_cover(image).save(dest, "WEBP", quality=82)
        return True
    except (OSError, zipfile.BadZipFile, ValueError):
        return False


def display_name(raw: str) -> str:
    """展示名二次脱敏；索引已清洗，这里兜底去掉任何残留占位。"""
    s = (raw or '').replace('_XXX', '').replace('XXX', '').strip('_ ·-')
    return s or '未命名模板'


def render_cover(template_id: str, dest: Path) -> bool:
    """统一用本机渲染的第 1 页做封面：满幅 16:9、尺寸一致、清晰。"""
    first = PAGES / template_id / '01.webp'
    if not first.exists():
        return False
    with Image.open(first) as image:
        image.convert('RGB').resize((COVER_W, COVER_H), Image.Resampling.LANCZOS).save(
            dest, "WEBP", quality=85
        )
    return True


def count_rendered(template_id: str) -> int:
    folder = PAGES / template_id
    if not folder.exists():
        return 0
    return len([p for p in folder.glob("*.webp") if not p.name.startswith("_")])


def collect_cards() -> tuple[list[dict], dict]:
    external = load_json(EXTERNAL_CATALOG)
    builtin = load_json(BUILTIN_CATALOG)
    categories = load_json(CATEGORIES_FILE)["categories"]
    removed = {g["remove"] for g in load_json(DUP_FILE)["groups"]}
    source_map = (load_json(SOURCE_MAP_FILE, {}) or {}).get("paths", {})
    root = Path(load_json(ROOT_LOCAL)["root"])
    name_by_id = {c["id"]: c["name"] for c in categories}
    registry = numbers.ensure_registry()
    serial_by_id = {e["template_id"]: e["serial"] for e in registry["entries"]}

    cards: list[dict] = []

    # 内置 15 套：封面复用仓库已有预览图，天然满幅清晰
    for deck in builtin:
        cover = COVERS / f"{deck['id']}.webp"
        source_png = BUILTIN_PREVIEWS / f"{int(deck['number']):02d}.png"
        if source_png.exists():
            with Image.open(source_png) as image:
                fit_cover(image).save(cover, "WEBP", quality=82)
            cover_status = "builtin"
        else:
            cover_status = "placeholder"
        deck_dir = DECKS_DIR / deck["id"]
        index_file = deck_dir / "layout_index.json"
        page_count = int(load_json(index_file).get("slide_count") or 0) if index_file.exists() else 0
        has_source = (deck_dir / "source.pptx").exists()
        cards.append({
            "number": int(deck["number"]),
            "serial": serial_by_id.get(deck["id"], f"{int(deck['number']):03d}"),
            "id": deck["id"],
            "name": display_name(deck["name"]),
            "style": deck.get("style", ""),
            "tags": deck.get("tags", []),
            "category": "institution",
            "category_name": name_by_id.get("institution", "厦门大学等高校/机构风格"),
            "pages": page_count or None,
            "cover": f"covers/{cover.name}",
            "cover_status": cover_status,
            "pages_dir": f"pages/{deck['id']}" if has_source else None,
            "pages_ready": count_rendered(deck["id"]) if has_source else 0,
            "namespace": "builtin",
            "rights": "内置模板（素材许可见 docs/assets.md）",
            "flags": [],
            "routes": deck.get("routes", []),
        })

    # 外部模板：跳过重复副本；封面统一改用渲染第 1 页
    for item in external["templates"]:
        if item["id"] in removed:
            continue
        cover = COVERS / f"{item['id']}.webp"
        if render_cover(item["id"], cover):
            status = "rendered"
        else:
            rel = source_map.get(item.get("source_key"))
            pptx = root / rel if rel else None
            if pptx and pptx.exists() and extract_embedded_cover(pptx, cover):
                status = "embedded"
            else:
                status = "placeholder"
        flags = []
        if item.get("promo_text"):
            flags.append("含推广文字")
        if item.get("security_flags"):
            flags.append("含特殊媒体/外部链接")
        cards.append({
            "number": int(item["number"]),
            "serial": serial_by_id.get(item["id"], f"{int(item['number']):03d}"),
            "id": item["id"],
            "name": display_name(item["name"]),
            "style": item.get("style", ""),
            "tags": item.get("tags", []),
            "category": item["primary_category"],
            "category_name": name_by_id.get(item["primary_category"], item["category_name"]),
            "pages": item["page_count"],
            "cover": f"covers/{cover.name}",
            "cover_status": status,
            "pages_dir": f"pages/{item['id']}",
            "pages_ready": count_rendered(item['id']),
            "namespace": item["namespace"],
            "rights": "来源待核验 · 不可再分发",
            "flags": flags,
            "routes": ["strict-native"],
            "style_prefix": item.get("style_prefix", ""),
            "sha8": item["sha256"][:8],
        })

    cards.sort(key=lambda c: c["number"])
    counts = {
        "total": len(cards),
        "builtin": sum(1 for c in cards if c["namespace"] == "builtin"),
        "external": sum(1 for c in cards if c["namespace"] != "builtin"),
        "covers_ready": sum(1 for c in cards if c["cover_status"] != "placeholder"),
        "covers_missing": sum(1 for c in cards if c["cover_status"] == "placeholder"),
        "duplicates_removed": len(removed),
        "by_category": {},
    }
    for card in cards:
        key = card["category"]
        counts["by_category"][key] = counts["by_category"].get(key, 0) + 1
    return cards, {
        "generated_on": date.today().isoformat(),
        "categories": [{"id": c["id"], "name": c["name"]} for c in categories],
        "counts": counts,
        "templates": cards,
    }

def write_catalog_js(data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    (OUT / "catalog.js").write_text(
        "window.LOCAL_CATALOG = " + payload + ";\n", encoding="utf-8"
    )





def write_index_html() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    html = TEMPLATE_FILE.read_text(encoding="utf-8").replace("__PLACEHOLDER__", PLACEHOLDER)
    (OUT / "index.html").write_text(html, encoding="utf-8")


def write_category_mirrors(categories: list[dict]) -> None:
    CATEGORY_DIR.mkdir(parents=True, exist_ok=True)
    for cat in categories:
        target = f"index.html#cat={cat['id']}"
        (CATEGORY_DIR / f"{cat['id']}.html").write_text(
            "<!doctype html><html lang=\"zh-CN\"><meta charset=\"utf-8\">"
            f"<title>{cat['name']} · 本地模板库</title>"
            f"<p>正在打开「{cat['name']}」… <a href=\"../{target}\">若未跳转请点此</a></p>"
            f"<script>location.replace('../{target}');</script></html>\n",
            encoding="utf-8",
        )


def main() -> int:
    root_cfg = load_json(ROOT_LOCAL)
    root = Path(root_cfg["root"])
    if not root.is_dir():
        raise SystemExit(f"外部模板根目录不存在：{root}")
    COVERS.mkdir(parents=True, exist_ok=True)
    PAGES.mkdir(parents=True, exist_ok=True)
    make_placeholder()
    cards, data = collect_cards()
    write_catalog_js(data)
    write_index_html()
    write_category_mirrors(load_json(CATEGORIES_FILE)["categories"])
    counts = data["counts"]
    print(f"本地画廊已生成：{OUT}")
    print(f"共 {counts['total']} 套（内置 {counts['builtin']} + 外部 {counts['external']}）")
    print(f"封面可用 {counts['covers_ready']}，暂无封面 {counts['covers_missing']}（由渲染脚本补齐）")
    print(f"分类分布：{counts['by_category']}")
    print(f"打开方式：双击 {OUT / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
