#!/usr/bin/env python3
"""External PPTX template index (local-only, read-only source inspection).

大白话：这个脚本只「看」桌面上的模板文件，把每套的页数、大小、指纹、
风格标签、预览图有无、可疑内容等登记成一份文字清单。原件一个字节都不动，
不复制、不改名、不入库；清单里也不写任何个人信息。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve()
XMU_PPT = HERE.parents[1]                       # .../skills/xmu-ppt
EXTERNAL = XMU_PPT / "templates" / "external"
CATALOG = EXTERNAL / "external_catalog.json"
LICENSES = EXTERNAL / "licenses.json"
CATEGORIES = EXTERNAL / "categories.json"
ROOT_LOCAL = EXTERNAL / "root.local.json"
STATUS = EXTERNAL / "path_status.json"

PROMO_KEYWORDS = ("定制", "工作室", "购买", "会员", "微信", "二维码", "加群", "淘宝")
ODD_MEDIA = {".wdp", ".emf", ".wmf", ".mp3", ".wav", ".wma", ".m4a", ".tiff"}
SLIDE_RE = re.compile(r"ppt/slides/slide\d+\.xml$")
SEQ_RE = re.compile(r"_(\d{3})$")
CREATOR_RE = re.compile(r"<dc:creator>(.*?)</dc:creator>", re.S)


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_root(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    cfg = load_json(ROOT_LOCAL, {}) or {}
    root = cfg.get("root")
    if not root or str(root).startswith("<"):
        raise SystemExit(
            "未配置外部模板根目录。请编辑 root.local.json，"
            "或运行: external_templates.py doctor --set-root <绝对路径>"
        )
    return Path(root)


def category_for(folder: str, categories: list[dict]) -> tuple[str, str]:
    for item in categories:
        if item.get("match") == "folder" and item.get("folder") == folder:
            return item["id"], item["name"]
    for item in categories:
        if item.get("match") == "fallback":
            return item["id"], item["name"]
    return "medical-other", "其他医护综合"


def inspect_one(path: Path, root: Path, categories: list[dict], scan_promo: bool = True) -> dict:
    """只读解析单个 pptx；不写回原件，不导出任何图片。"""
    stem = path.stem
    match = SEQ_RE.search(stem)
    seq = int(match.group(1)) if match else None
    body = stem[:match.start()] if match else stem
    bits = body.split("_", 1)
    style_prefix = bits[0] if len(bits) == 2 else ""
    subject = bits[1] if len(bits) == 2 else body

    folder = path.parent.name
    size_bytes = path.stat().st_size
    digest = sha256_file(path)
    rel_path = path.relative_to(root).as_posix()

    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        slides = [n for n in names if SLIDE_RE.search(n)]
        media = [n for n in names if n.startswith("ppt/media/")]
        has_thumbnail = "docProps/thumbnail.jpeg" in names

        # 作者名可能是个人信息，只存不可逆指纹，不存原文（修正复核 M3）
        author_hash = None
        if "docProps/core.xml" in names:
            core = zf.read("docProps/core.xml").decode("utf-8", "ignore")
            creator = CREATOR_RE.search(core)
            if creator and creator.group(1).strip():
                author_hash = hashlib.sha256(
                    creator.group(1).strip().encode("utf-8")
                ).hexdigest()[:8]

        promo_hits: set[str] = set()
        if scan_promo:
            for slide_name in slides:
                text = zf.read(slide_name).decode("utf-8", "ignore")
                for keyword in PROMO_KEYWORDS:
                    if keyword in text:
                        promo_hits.add(keyword)

        # 安全提示：外部链接 / 嵌入对象 / 罕见媒体格式只记录，不自动处理（修正复核 M5）
        external_targets = 0
        for name in names:
            if name.endswith(".rels"):
                rels = zf.read(name).decode("utf-8", "ignore")
                external_targets += rels.count('TargetMode="External"')
        embedded = [
            n for n in names
            if n.startswith("ppt/embeddings/") or "activex" in n.lower()
        ]
        odd_media = sorted({
            Path(n).suffix.lower() for n in media
            if Path(n).suffix.lower() in ODD_MEDIA
        })

    security_flags: list[str] = []
    if external_targets:
        security_flags.append(f"external_relationships:{external_targets}")
    if embedded:
        security_flags.append(f"embedded_objects:{len(embedded)}")
    if odd_media:
        security_flags.append("uncommon_media:" + ",".join(odd_media))

    cat_id, cat_name = category_for(folder, categories)
    template_id = f"MED-{seq:03d}" if seq is not None else f"CAMPUS-{digest[:8]}"

    return {
        "id": template_id,
        "namespace": "medical" if seq is not None else "institution",
        "seq": seq,
        "raw_filename": path.name,
        "source_path": rel_path,
        "size_bytes": size_bytes,
        "sha256": digest,
        "folder": folder,
        "primary_category": cat_id,
        "category_name": cat_name,
        "name": subject or body,
        "style": style_prefix,
        "style_prefix": style_prefix,
        "tags": [cat_name] + ([style_prefix] if style_prefix else []),
        "routes": ["strict-native"],
        "page_count": len(slides),
        "media_count": len(media),
        "has_thumbnail": has_thumbnail,
        "preview_status": "thumbnail" if has_thumbnail else "missing",
        "preview": None,
        "author_hash": author_hash,
        "promo_text": sorted(promo_hits),
        "security_flags": security_flags,
        "rights": {"status": "unknown", "license": None, "redistributable": False},
        "status": "ok",
    }


def build_catalog(root: Path, categories: list[dict], scan_promo: bool = True) -> dict:
    files = sorted(
        p for p in root.rglob("*.pptx") if not p.name.startswith("~$")
    )
    if not files:
        raise SystemExit(f"在 {root} 下未找到任何 .pptx 文件")

    records = []
    for index, path in enumerate(files, 1):
        records.append(inspect_one(path, root, categories, scan_promo))
        if index % 25 == 0:
            print(f"  已扫描 {index}/{len(files)} ...", file=sys.stderr)

    # 序号稳定：带序号者按 1..180，无序号者排在其后；number 只按本次顺序分配
    records.sort(key=lambda r: (r["seq"] is None, r["seq"] or 0, r["id"]))
    for offset, record in enumerate(records):
        record["number"] = 16 + offset

    by_category: dict[str, int] = {}
    for record in records:
        key = record["primary_category"]
        by_category[key] = by_category.get(key, 0) + 1

    return {
        "schema": "external_catalog.v1",
        "generated_on": date.today().isoformat(),
        "source_root_note": "原件路径写在 root.local.json（不入库）；source_path 为相对路径",
        "counts": {
            "builtin": 15,
            "external": len(records),
            "total": 15 + len(records),
            "external_pages": sum(r["page_count"] for r in records),
            "with_thumbnail": sum(1 for r in records if r["has_thumbnail"]),
            "without_thumbnail": sum(1 for r in records if not r["has_thumbnail"]),
            "with_promo_text": sum(1 for r in records if r["promo_text"]),
            "with_security_flags": sum(1 for r in records if r["security_flags"]),
            "by_category": by_category,
        },
        "delivery_warning": (
            "部分模板含第三方推广文字或二维码。严格保真路线默认保留未点名文本，"
            "这些文字会随成品一起交付；交付前必须向使用者披露并提供隔离选项。"
        ),
        "rights_warning": (
            "外部模板未见授权文件与许可文本，rights.status 一律 unknown、"
            "redistributable=false。原件、预览图与逐页截图均不入库、不公开再分发。"
        ),
        "templates": records,
    }


def build_licenses(catalog: dict) -> dict:
    entries = [
        {
            "id": r["id"],
            "source_path": r["source_path"],
            "status": "unknown",
            "license": None,
            "redistributable": False,
            "evidence": "未见许可文件、授权书或购买凭证；docProps 含第三方模板站痕迹",
            "note": "仅限本机离线索引与浏览；逐套登记另见 docs/assets.md",
        }
        for r in catalog["templates"]
    ]
    return {
        "schema": "external_licenses.v1",
        "generated_on": date.today().isoformat(),
        "counts": {"total": len(entries), "unknown": len(entries)},
        "entries": entries,
    }


def run_scan(args) -> int:
    root = get_root(args.root)
    if not root.is_dir():
        raise SystemExit(f"外部模板根目录不存在：{root}")
    categories = (load_json(CATEGORIES, {}) or {}).get("categories", [])
    if not categories:
        raise SystemExit(f"分类规则缺失或为空：{CATEGORIES}")
    catalog = build_catalog(root, categories, scan_promo=not args.skip_promo)
    write_json(CATALOG, catalog)
    write_json(LICENSES, build_licenses(catalog))
    counts = catalog["counts"]
    print(
        f"已登记 {counts['external']} 套 / {counts['external_pages']} 页；"
        f"有缩略图 {counts['with_thumbnail']}、无缩略图 {counts['without_thumbnail']}、"
        f"含推广文字 {counts['with_promo_text']}、带安全提示 {counts['with_security_flags']}"
    )
    print(f"分类分布：{counts['by_category']}")
    print(f"写出：{CATALOG}")
    print(f"写出：{LICENSES}")
    return 0


def run_doctor(args) -> int:
    if args.set_root:
        cfg = load_json(ROOT_LOCAL, {}) or {}
        cfg["root"] = str(args.set_root).replace("\\", "/")
        cfg["updated_at"] = date.today().isoformat()
        write_json(ROOT_LOCAL, cfg)
        print(f"已更新本机根目录：{cfg['root']}")
        return 0

    root = get_root(args.root)
    catalog = load_json(CATALOG)
    if not catalog:
        raise SystemExit("尚未生成索引，请先运行 scan")
    problems = []
    for record in catalog["templates"]:
        path = root / record["source_path"]
        if not path.exists():
            status = "missing"
        elif path.stat().st_size != record["size_bytes"]:
            status = "changed"
        elif args.verify_hash and sha256_file(path) != record["sha256"]:
            status = "changed"
        else:
            status = "ok"
        if status != "ok":
            problems.append({"id": record["id"], "status": status, "path": record["source_path"]})
    report = {
        "checked_on": date.today().isoformat(),
        "root": str(root),
        "total": len(catalog["templates"]),
        "ok": len(catalog["templates"]) - len(problems),
        "problems": problems,
        "verified_hash": bool(args.verify_hash),
    }
    write_json(STATUS, report)
    print(f"体检：{report['ok']}/{report['total']} 正常，问题 {len(problems)} 条")
    for item in problems[:10]:
        print(f"  {item['status']:8s} {item['id']}  {item['path']}")
    return 0 if not problems else 1


def run_list(args) -> int:
    catalog = load_json(CATALOG)
    if not catalog:
        raise SystemExit("尚未生成索引，请先运行 scan")
    records = catalog["templates"]
    if args.category:
        records = [r for r in records if r["primary_category"] == args.category]
    print(f"共 {len(records)} 套")
    for record in records[: args.limit]:
        print(
            f"  {record['number']:3d}  {record['id']:<14s} "
            f"{record['page_count']:3d}页  {record['name'][:28]:<28s} "
            f"{record['primary_category']}"
        )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="外部 PPTX 模板只读索引工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="只读盘点并生成 external_catalog.json / licenses.json")
    p_scan.add_argument("--root", help="覆盖 root.local.json 中的根目录")
    p_scan.add_argument("--skip-promo", action="store_true", help="跳过推广文字扫描（更快）")
    p_scan.set_defaults(func=run_scan)

    p_doctor = sub.add_parser("doctor", help="核对原件路径与指纹")
    p_doctor.add_argument("--root", help="覆盖根目录")
    p_doctor.add_argument("--set-root", help="写入新的本机根目录")
    p_doctor.add_argument("--verify-hash", action="store_true", help="同时重算 sha256（较慢）")
    p_doctor.set_defaults(func=run_doctor)

    p_list = sub.add_parser("list", help="列出索引中的模板")
    p_list.add_argument("--category", help="按一级类 ID 过滤")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.set_defaults(func=run_list)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
