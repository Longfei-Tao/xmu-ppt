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
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve()
XMU_PPT = HERE.parents[1]                       # .../skills/xmu-ppt
EXTERNAL = XMU_PPT / "templates" / "external"
CATALOG = EXTERNAL / "external_catalog.json"
LICENSES = EXTERNAL / "licenses.json"
CATEGORIES = EXTERNAL / "categories.json"
ROOT_LOCAL = EXTERNAL / "root.local.json"
STATUS = EXTERNAL / "path_status.json"
SOURCE_MAP = EXTERNAL / "source_map.local.json"

PACK_SCHEMA = "xmu_ppt_template_pack.v1"
PACK_NAME = "xmu-ppt-templates.zip"
DEFAULT_PACK_URL = (
    "https://github.com/Longfei-Tao/xmu-ppt/releases/latest/download/" + PACK_NAME
)
DEFAULT_IMPORT_ROOT = Path.home() / "xmu-ppt-templates"
REPO_ROOT = HERE.parents[3]
GALLERY_BUILDER = REPO_ROOT / "scripts" / "build_local_gallery.py"

PROMO_KEYWORDS = ("定制", "工作室", "购买", "会员", "微信", "二维码", "加群", "淘宝")
ODD_MEDIA = {".wdp", ".emf", ".wmf", ".mp3", ".wav", ".wma", ".m4a", ".tiff"}
SLIDE_RE = re.compile(r"ppt/slides/slide\d+\.xml$")
SEQ_RE = re.compile(r"_(\d{3})$")
CREATOR_RE = re.compile(r"<dc:creator>(.*?)</dc:creator>", re.S)


# 第三方模板站的公开昵称；个人姓名不写入仓库，改用环境变量补充。
AUTHOR_TOKENS = ("偷懒儿ppt", "俞兆达", "李维军", "许苗怡")


def privacy_tokens() -> tuple[str, ...]:
    extra = os.environ.get("XMU_PPT_PRIVACY_TERMS", "")
    return tuple(t.strip() for t in extra.split(",") if t.strip())


def clean_text(value: str) -> str:
    """扫描新模板时把姓名/昵称占位脱敏，避免重新引入个人名称。"""
    for token in (*AUTHOR_TOKENS, *privacy_tokens()):
        value = value.replace(token, "XXX")
    return value


def display_name(raw: str) -> str:
    s = clean_text(raw or "").replace("_XXX", "").replace("XXX", "").strip("_ ·-")
    return s or "未命名模板"


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
    source_ref = path.relative_to(root).as_posix()

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
        "source_ref": source_ref,
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

    # 序号由固定注册表分配：已有身份沿用原序号，新模板只在末尾依次追加。
    # 绝不按本次排序重排、绝不复用或回收（含已被去重隐藏的序号）。
    import template_numbers as tn

    registry = tn.ensure_registry()
    candidates = [
        {
            "template_id": r["id"],
            "name": r["name"],
            "namespace": r["namespace"],
            "source_ref_hash": tn.source_ref_hash(r["source_ref"]),
        }
        for r in records
    ]
    allocated, added = tn.allocate_numbers(registry, candidates)
    number_by_id = {a["template_id"]: a for a in allocated}
    paths = {}
    for record in records:
        assigned = number_by_id[record["id"]]
        record["number"] = assigned["number"]
        record["serial"] = assigned["serial"]
        key = f"EXT-{record['number']:03d}"
        paths[key] = record.pop("source_ref")
        record["source_key"] = key
        record["name"] = display_name(record["name"])
        record["style"] = clean_text(record.get("style", ""))
        record["tags"] = [clean_text(t) for t in record.get("tags", [])]
    records.sort(key=lambda r: r["number"])
    if added:
        print(f"新增 {added} 套模板，已在末尾追加固定序号，未重排既有序号。", file=sys.stderr)
    write_json(SOURCE_MAP, {
        "schema": "external_source_map.v1",
        "note": "本机配置，不入库；含真实文件名，仅用于定位桌面原件，绝不展示。",
        "paths": paths,
    })

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
            "source_key": r["source_key"],
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


def _pack_entries(catalog: dict, root: Path) -> list[dict]:
    """按索引 + 本机路径映射收集可打包的原件，指纹不一致直接拒绝。"""
    mapping = (load_json(SOURCE_MAP, {}) or {}).get("paths", {})
    entries = []
    missing = []
    for record in catalog.get("templates", []):
        key = record.get("source_key")
        rel = mapping.get(key)
        if not rel:
            missing.append(key or record.get("id"))
            continue
        source = root / rel
        if not source.is_file():
            missing.append(rel)
            continue
        actual = sha256_file(source)
        if actual != record["sha256"]:
            raise SystemExit(
                f"原件指纹与索引不一致：{rel}；请先重新运行 scan"
            )
        entries.append({
            "id": record["id"],
            "serial": record.get("serial"),
            "name": record.get("name"),
            "category": record.get("primary_category"),
            "file": f"templates/{rel}",
            "sha256": actual,
            "size_bytes": source.stat().st_size,
        })
    if missing:
        preview = "、".join(missing[:5])
        raise SystemExit(
            f"有 {len(missing)} 份原件不在 {root}（如 {preview}）；"
            "请先运行 scan 或修正 root.local.json"
        )
    return entries


def build_template_pack(root: Path, output: Path, catalog: dict | None = None) -> dict:
    """把本机模板目录打成可分发的模板包（manifest + 原件）。"""
    catalog = catalog or load_json(CATALOG)
    if not catalog:
        raise SystemExit("尚未生成模板索引，请先运行: external_templates.py scan")
    entries = _pack_entries(catalog, root)
    if not entries:
        raise SystemExit("模板索引为空，未生成模板包")
    manifest = {
        "schema": PACK_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "count": len(entries),
        "total_bytes": sum(e["size_bytes"] for e in entries),
        "note": (
            "模板包只分发给已合法拥有这些模板的用户；"
            "请先确认你有权再分发其中的第三方模板。"
        ),
        "templates": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as zf:
        for entry in entries:
            zf.write(root / entry["file"][len("templates/"):], entry["file"])
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr("RIGHTS.txt", (
            "本模板包用于分发你已合法拥有的 PPT 模板。\n"
            "其中的第三方模板授权状态未知，请勿在未获授权时公开传播。\n"
            "导入后仅在导入者本机使用；仓库只保留文字索引与指纹。\n"
        ))
    return {"output": str(output), "count": len(entries),
            "bytes": output.stat().st_size}


def _seed_numbers(entries: list[dict]) -> int:
    """把模板包自带的固定序号写进本地注册表，保证不同机器编号一致。

    只在本地还没有任何外部模板序号时执行；已有编号一律不改，
    遵守「一经分配永不变更、不重排」的规则。
    """
    import template_numbers as tn

    registry = tn.ensure_registry()
    if any(e.get("namespace") == "external" for e in registry["entries"]):
        return 0
    used = {e["number"]: e["template_id"] for e in registry["entries"]}
    added = 0
    for entry in entries:
        template_id = entry.get("id")
        raw = str(entry.get("serial") or "")
        member = entry.get("file", "")
        if not template_id or not raw.isdigit() or not member.startswith("templates/"):
            continue
        number = int(raw)
        if number in used:
            if used[number] != template_id:
                print(f"警告：序号 {tn.serial(number)} 已被 {used[number]} 占用，"
                      f"跳过 {template_id}", file=sys.stderr)
            continue
        relative = member[len("templates/"):]
        registry["entries"].append({
            "number": number,
            "serial": tn.serial(number),
            "template_id": template_id,
            "name": entry.get("name", ""),
            "namespace": "external",
            "source_key": None,
            "source_ref_hash": tn.source_ref_hash(relative),
            "status": "active",
        })
        used[number] = template_id
        added += 1
    if added:
        registry["entries"].sort(key=lambda e: e["number"])
        registry["next_number"] = max(e["number"] for e in registry["entries"]) + 1
        registry["external_range"] = [16, max(e["number"] for e in registry["entries"])]
        write_json(tn.REGISTRY_FILE, registry)
    return added


def _read_pack_manifest(pack: Path) -> dict:
    with zipfile.ZipFile(pack) as zf:
        try:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        except KeyError as exc:
            raise SystemExit(f"模板包缺少 manifest.json：{pack}") from exc
        if manifest.get("schema") != PACK_SCHEMA:
            raise SystemExit(f"模板包格式不支持：{manifest.get('schema')}")
        entries = manifest.get("templates") or []
        if len(entries) != manifest.get("count"):
            raise SystemExit("manifest 数量与模板条目数不一致")
        names = set(zf.namelist())
        for entry in entries:
            member = PurePosixPath(entry.get("file", ""))
            if (not member.parts or member.parts[0] != "templates"
                    or member.is_absolute() or ".." in member.parts
                    or member.suffix.lower() != ".pptx"):
                raise SystemExit(f"模板包包含非法路径：{entry.get('file')}")
            if str(member) not in names:
                raise SystemExit(f"模板包缺少文件：{member}")
    return manifest


def import_template_pack(pack: Path, dest: Path, *, force: bool = False,
                         scan: bool = True) -> dict:
    """解压模板包到本机目录，校验指纹后自动登记。"""
    manifest = _read_pack_manifest(pack)
    entries = manifest["templates"]
    dest = Path(dest).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    # 先检查冲突，再写文件，避免导入一半才失败
    for entry in entries:
        member = PurePosixPath(entry["file"])
        target = dest.joinpath(*member.parts[1:])
        if target.is_file():
            if force or sha256_file(target) == entry["sha256"]:
                continue
            raise SystemExit(
                f"目标已存在且内容不同：{target}；确认覆盖请加 --force"
            )

    staging = Path(tempfile.mkdtemp(prefix=".xmu-pack-", dir=str(dest.parent)))
    try:
        with zipfile.ZipFile(pack) as zf:
            for entry in entries:
                member = PurePosixPath(entry["file"])
                staged = staging.joinpath(*member.parts[1:])
                staged.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(str(member)) as src, staged.open("wb") as out:
                    shutil.copyfileobj(src, out, 1024 * 1024)
                if sha256_file(staged) != entry["sha256"]:
                    raise SystemExit(f"模板包内容校验失败：{member}")
        for entry in entries:
            member = PurePosixPath(entry["file"])
            target = dest.joinpath(*member.parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging.joinpath(*member.parts[1:])), str(target))
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    write_json(ROOT_LOCAL, {
        "schema": "external_root.v1",
        "root": dest.as_posix(),
        "updated_at": date.today().isoformat(),
        "note": "由模板包一键导入写入；换目录时重跑 import 或 doctor --set-root。",
    })
    if scan:
        seeded = _seed_numbers(entries)
        if seeded:
            print(f"已沿用模板包的固定序号 {seeded} 条，跨机器编号一致。",
                  file=sys.stderr)
        run_scan(argparse.Namespace(root=str(dest), skip_promo=False))
    return {"root": str(dest), "count": len(entries)}


def download_template_pack(url: str, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"正在下载模板包：{url}", file=sys.stderr)
    with urllib.request.urlopen(url, timeout=60) as response, output.open("wb") as out:
        shutil.copyfileobj(response, out, 1024 * 1024)
    return output


def build_local_gallery() -> bool:
    """导入后生成本机画廊，让使用者能按封面浏览全部模板。

    画廊只读本机原件与索引，不联网；封面优先取 PPTX 内嵌缩略图。
    失败不影响导入结果（模板仍可按序号选定），但会给出明确警告。
    """
    if not GALLERY_BUILDER.is_file():
        print("提示：未找到本地画廊脚本，跳过画廊生成。", file=sys.stderr)
        return False
    print("正在生成离线模板画廊（封面取自 PPTX 内嵌缩略图）...", file=sys.stderr)
    try:
        proc = subprocess.run([sys.executable, str(GALLERY_BUILDER)],
                              cwd=str(REPO_ROOT))
    except OSError as exc:
        print(f"警告：本地画廊生成失败（{exc}）；模板已导入，仍可按序号选定。",
              file=sys.stderr)
        return False
    if proc.returncode != 0:
        print("警告：本地画廊生成失败；模板已导入，仍可按序号选定。", file=sys.stderr)
        return False
    return True


def run_pack(args) -> int:
    root = get_root(args.root)
    output = Path(args.output).expanduser()
    result = build_template_pack(root, output)
    print(f"已生成模板包：{result['output']}")
    print(f"模板数：{result['count']}，压缩包大小：{result['bytes'] / 1024 / 1024:.1f} MiB")
    print("下一步：把该 ZIP 上传到 GitHub Release，文件名保持 "
          f"{PACK_NAME}；使用者即可一键导入。")
    return 0


def run_import(args) -> int:
    if args.pack:
        pack = Path(args.pack).expanduser()
    else:
        url = args.url or DEFAULT_PACK_URL
        try:
            pack = download_template_pack(url, Path(tempfile.gettempdir()) / PACK_NAME)
        except (urllib.error.URLError, OSError) as exc:
            raise SystemExit(
                f"模板包下载失败（{exc}）。\n"
                "公开仓库不分发模板包；若你合法持有模板包，请用 --pack 指定本地文件，"
                "或用 user_templates.py onboard 把自有 PPTX 入库。"
            ) from exc
    if not pack.is_file():
        raise SystemExit(f"模板包不存在：{pack}")
    dest = Path(args.dest).expanduser() if args.dest else DEFAULT_IMPORT_ROOT
    result = import_template_pack(pack, dest, force=args.force,
                                  scan=not args.skip_scan)
    print(f"已导入 {result['count']} 套模板到 {result['root']}")
    if args.skip_gallery:
        print("已跳过画廊生成（--skip-gallery）；仍可按序号选定模板。")
    elif args.skip_scan:
        print("提示：本次跳过了自动登记，未生成画廊；如需浏览封面请去掉 --skip-scan。")
    elif build_local_gallery():
        print("画廊已生成：local-gallery/index.html（可直接用浏览器打开）。")
    return 0


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
    mapping = (load_json(SOURCE_MAP, {}) or {}).get("paths", {})
    for record in catalog["templates"]:
        rel = mapping.get(record.get("source_key"))
        path = root / rel if rel else None
        if path is None or not path.exists():
            status = "missing"
        elif path.stat().st_size != record["size_bytes"]:
            status = "changed"
        elif args.verify_hash and sha256_file(path) != record["sha256"]:
            status = "changed"
        else:
            status = "ok"
        if status != "ok":
            problems.append({"id": record["id"], "status": status, "path": record.get("source_key")})
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

    p_pack = sub.add_parser("pack", help="把本机模板目录打成可分发的模板包")
    p_pack.add_argument("--root", help="覆盖 root.local.json 中的根目录")
    p_pack.add_argument("-o", "--output", default=str(Path("dist") / PACK_NAME),
                        help="输出 ZIP 路径")
    p_pack.set_defaults(func=run_pack)

    p_import = sub.add_parser("import", help="下载/导入模板包并自动登记")
    p_import.add_argument("--pack", help="本地模板包路径（省略则从 --url 下载）")
    p_import.add_argument("--url", help=f"模板包下载地址（默认 {DEFAULT_PACK_URL}）")
    p_import.add_argument("--dest", help="导入目录（默认 ~/xmu-ppt-templates）")
    p_import.add_argument("--force", action="store_true", help="覆盖已存在且不同的文件")
    p_import.add_argument("--skip-scan", action="store_true", help="只解压，不自动登记")
    p_import.add_argument("--skip-gallery", action="store_true", help="导入后不生成离线画廊")
    p_import.set_defaults(func=run_import)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
