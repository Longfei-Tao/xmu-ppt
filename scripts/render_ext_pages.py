#!/usr/bin/env python3
"""Render per-slide previews for external templates, on this machine only.

大白话：用你电脑上装好的 PowerPoint，把模板的前几页「拍照」成本地图片，
供本地画廊查看。原件只读打开、绝不修改；生成的图片只放在 local-gallery/
（已被 .gitignore 忽略），不会上传 GitHub。

安全约束：绝不附加到已经打开的 PowerPoint；发现它正在运行就直接停止。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_CATALOG = ROOT / "skills/xmu-ppt/templates/external/external_catalog.json"
DUPLICATES = ROOT / "skills/xmu-ppt/templates/external/duplicates.json"
DECKS_DIR = ROOT / "skills/xmu-ppt/templates/decks"
BUILTIN_CATALOG = ROOT / "docs/templates/catalog.json"
ROOT_LOCAL = ROOT / "skills/xmu-ppt/templates/external/root.local.json"
GALLERY = ROOT / "local-gallery"
COVERS = GALLERY / "covers"
PAGES = GALLERY / "pages"
MANIFEST = GALLERY / "render_manifest.json"
SOURCE_MAP_FILE = ROOT / "skills/xmu-ppt/templates/external/source_map.local.json"
# 固定复用一个临时 PNG：不做逐文件删除，避免触发批量删除保护，也不会留下上千个中间文件
RENDER_TMP = GALLERY / "_render_tmp" / "slide.png"


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def guard() -> None:
    if os.name != "nt":
        raise RuntimeError("此渲染器仅支持 Windows + Microsoft PowerPoint")
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq POWERPNT.EXE", "/FO", "CSV", "/NH"],
        capture_output=True, check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if b"powerpnt.exe" in result.stdout.lower():
        raise RuntimeError(
            "检测到 PowerPoint 正在运行。为避免干扰你的工作，已停止渲染；"
            "请保存并关闭 PowerPoint 后重试。"
        )


def resolve_source(item: dict) -> Path:
    """按 source_key 从本地映射定位原件；索引中不含原文件名。"""
    root = Path(load_json(ROOT_LOCAL)["root"])
    mapping = (load_json(SOURCE_MAP_FILE, {}) or {}).get("paths", {})
    rel = mapping.get(item.get("source_key"))
    if not rel:
        raise FileNotFoundError(f"本地映射缺少 {item['id']} 的路径，请重跑 scan")
    return root / rel


def to_webp(png: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(png) as image:
        image.convert("RGB").save(dest, "WEBP", quality=80)


def already_done(template_id: str, count: int) -> bool:
    folder = PAGES / template_id
    if count <= 0:
        return False
    return all((folder / f"{i:02d}.webp").exists() for i in range(1, count + 1))


def builtin_items() -> list[dict]:
    """内置 15 套也纳入逐页渲染，让使用者能看每一页版式。"""
    items = []
    for deck in load_json(BUILTIN_CATALOG):
        src = DECKS_DIR / deck["id"] / "source.pptx"
        if not src.exists():
            continue
        count = 0
        index_file = DECKS_DIR / deck["id"] / "layout_index.json"
        if index_file.exists():
            count = int(load_json(index_file).get("slide_count") or 0)
        items.append({"id": deck["id"], "page_count": count, "_abs": src})
    return items


def select_items(args) -> list[dict]:
    items = load_json(EXTERNAL_CATALOG)["templates"]
    removed = {g["remove"] for g in load_json(DUPLICATES)["groups"]}
    items = [x for x in items if x["id"] not in removed]
    if args.include_builtin:
        items = items + builtin_items()
    if args.deck:
        items = [x for x in items if x["id"] == args.deck]
        if not items:
            raise SystemExit(f"索引中找不到模板 ID：{args.deck}")
    elif args.category:
        items = [x for x in items if x["primary_category"] == args.category]
    elif args.only_missing_covers:
        items = [x for x in items if not (COVERS / f"{x['id']}.webp").exists()]
    if not args.force:
        items = [x for x in items if not already_done(x["id"], x.get("page_count", 0))]
    if args.limit:
        items = items[: args.limit]
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="本机 PowerPoint 逐页预览渲染器")
    parser.add_argument("--all", action="store_true",
                        help="渲染全部外部模板（不传任何过滤参数时也是这个行为）")
    parser.add_argument("--deck", help="只渲染指定模板 ID")
    parser.add_argument("--category", help="只渲染指定一级分类")
    parser.add_argument("--include-builtin", action="store_true",
                        help="同时渲染内置 15 套的每一页")
    parser.add_argument("--only-missing-covers", action="store_true",
                        help="只处理没有内嵌封面的模板")
    parser.add_argument("--limit", type=int, help="本轮最多处理几套")
    parser.add_argument("--pages", type=int, default=0,
                        help="每套渲染前几页；0 表示全部页（默认），便于逐页查看版式")
    parser.add_argument("--force", action="store_true", help="忽略断点续传，重新渲染")
    args = parser.parse_args()

    guard()
    root = Path(load_json(ROOT_LOCAL)["root"])
    if not root.is_dir():
        raise SystemExit(f"外部模板根目录不存在：{root}")

    items = select_items(args)
    if not items:
        print("没有需要渲染的模板（可能已全部完成）。")
        return 0
    print(f"本轮待渲染 {len(items)} 套，每套前 {args.pages} 页", flush=True)

    import win32com.client

    COVERS.mkdir(parents=True, exist_ok=True)
    PAGES.mkdir(parents=True, exist_ok=True)
    RENDER_TMP.parent.mkdir(parents=True, exist_ok=True)
    app = win32com.client.DispatchEx("PowerPoint.Application")
    app.DisplayAlerts = 1               # ppAlertsNone：不弹修复/字体提示
    try:
        app.AutomationSecurity = 3       # 禁用宏
    except Exception:
        pass

    ok, failed, pages_rendered = 0, [], 0
    try:
        for index, item in enumerate(items, 1):
            template_id = item["id"]
            source = item.get("_abs") or resolve_source(item)
            folder = PAGES / template_id
            folder.mkdir(parents=True, exist_ok=True)
            deck = None
            try:
                if not source.exists():
                    raise FileNotFoundError(source)
                deck = app.Presentations.Open(
                    str(source), ReadOnly=True, Untitled=False, WithWindow=False
                )
                total = deck.Slides.Count if args.pages <= 0 else min(args.pages, deck.Slides.Count)
                for page in range(1, total + 1):
                    dest = folder / f"{page:02d}.webp"
                    if dest.exists() and not args.force:
                        continue
                    deck.Slides(page).Export(str(RENDER_TMP), "PNG", 1280, 720)
                    to_webp(RENDER_TMP, dest)
                    pages_rendered += 1
                    if page == 1 and not (COVERS / f"{template_id}.webp").exists():
                        to_webp(dest, COVERS / f"{template_id}.webp")
                ok += 1
                print(f"  [{index}/{len(items)}] {template_id} OK ({total} 页)", flush=True)
            except Exception as exc:                     # 单套失败不中断整批
                failed.append({"id": template_id, "error": str(exc)[:220]})
                print(f"  [{index}/{len(items)}] {template_id} FAILED: {exc}", flush=True)
            finally:
                if deck is not None:
                    try:
                        deck.Close()
                    except Exception:
                        pass
    finally:
        try:
            if app.Presentations.Count == 0:
                app.Quit()
        except Exception:
            pass

    report = {
        "last_run": date.today().isoformat(),
        "renderer": "Microsoft PowerPoint (COM)",
        "ok": ok,
        "failed": failed,
        "pages_rendered": pages_rendered,
        "pages_per_deck": args.pages,
    }
    GALLERY.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"完成：成功 {ok} 套、失败 {len(failed)} 套、新增 {pages_rendered} 张页面图")
    print(f"记录：{MANIFEST}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
