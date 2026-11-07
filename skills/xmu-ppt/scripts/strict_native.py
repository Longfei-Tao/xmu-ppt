"""strict-native: 1:1 保真填充外部 PPTX 模板（独立路线，不改动既有生成链）。

设计要点
--------
1. 整份复制原 .pptx（zip 内每个部件逐个写回），只覆盖**被点名页**的 slide XML。
2. slide XML 不做整树重序列化：用正则定位 ``<a:t>`` 文本节点，只替换节点内容，
   因此图片、图形、装饰、占位区、版式、母版、备注、切换效果、未引用素材全部字节级保留。
3. 页序由 ``ppt/presentation.xml`` 原样保留，天然 1:1；plan 中出现删页 / 重排 / 复用页
   等字段一律拒绝。
4. 未被点名的文本框保留原示例文字（可能含模板站推广文字，见交付警示）。
5. 图片替换默认禁止；需三道闸门同时打开（plan 的 user_specified、CLI 开关、feature flag）。

术语说明：PPTX 本质是一个 zip 压缩包，里面一个 XML 文件对应一页；"部件(part)"即包内文件。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape, unescape

SKILL_ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = SKILL_ROOT / "templates" / "external"
CATALOG_FILE = EXTERNAL / "external_catalog.json"
FLAGS_FILE = EXTERNAL / "feature_flags.json"
ROOT_LOCAL_FILE = EXTERNAL / "root.local.json"
SOURCE_MAP_FILE = EXTERNAL / "source_map.local.json"

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
SLIDE_REL_TYPE = NS["r"] + "/slide"

PLAN_SCHEMA = "strict_native_plan.v1"
A_T = "{" + NS["a"] + "}t"
A_T_RE = re.compile(r"(<a:t(?:\s[^>]*)?>)(.*?)(</a:t>)", re.S)
PIC_RE = re.compile(r"<p:pic\b.*?</p:pic>", re.S)
OFF_RE = re.compile(r"(<a:off\s+)[^>]*?(/>)", re.S)
EXT_RE = re.compile(r"(<a:ext\s+)[^>]*?(/>)", re.S)
XF_ATTR_RE = re.compile(r'(<a:(?:off|ext)\s+)([^>]*?)(/>)', re.S)
SLIDE_PART_RE = re.compile(r"ppt/slides/slide\d+\.xml$")

# 严格保真路线禁止出现的字段：任何删页、重排、复用页、改切换效果、改备注的意图
FORBIDDEN_TOP = {
    "remove_slides", "drop_slides", "delete_slides", "slide_order", "reorder",
    "duplicate_slides", "keep_slides", "source_slide", "transition",
    "transitions", "notes", "speaker_notes", "rebuild", "prune",
}
ALLOWED_SLIDE_KEYS = {"slide", "purpose", "replacements", "image_replacements", "slots"}
ALLOWED_REPLACEMENT_KEYS = {
    "slot_id", "shape_id", "shape_name", "text", "old_text", "optional",
}
ALLOWED_IMAGE_KEYS = {
    "shape_id", "shape_name", "asset", "user_specified", "layout_adjustment",
    "note",
}
KEY_PAGES = (2, 3, 4)     # 版式页，重点保护并在报告中单列
IMAGE_EXT_OK = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".emf", ".wmf", ".wdp"}


def qn(prefix: str, tag: str) -> str:
    return "{" + NS[prefix] + "}" + tag


def _load_json(path: Path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise RuntimeError(f"缺少文件：{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON 解析失败：{path}: {exc}") from exc


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _flags(explicit: dict | None = None) -> dict:
    return explicit if explicit is not None else _load_json(FLAGS_FILE, {})


def _require_flag(flags: dict, name: str) -> None:
    if not flags.get(name):
        raise RuntimeError(
            f"总开关 {name} 未开启（{FLAGS_FILE}）。"
            "设为 true 才会启用该能力；全部置 false 可完整回退到原有行为。"
        )


# ---------------------------------------------------------------------------
# 定位模板原件
# ---------------------------------------------------------------------------

def resolve_template(template_id: str, *, verify_hash: bool = True) -> tuple[dict, Path]:
    """按模板 ID 从外部索引 + 不入库的本机映射定位原件。"""
    flags = _flags()
    _require_flag(flags, "strict_native")
    catalog = _load_json(CATALOG_FILE)
    record = next((r for r in catalog.get("templates", []) if r["id"] == template_id), None)
    if record is None:
        raise RuntimeError(f"外部索引中找不到模板：{template_id}")
    if record.get("status") != "ok":
        raise RuntimeError(f"模板状态异常：{template_id} -> {record.get('status')}")

    root = Path(_load_json(ROOT_LOCAL_FILE)["root"])
    mapping = (_load_json(SOURCE_MAP_FILE, {}) or {}).get("paths", {})
    rel = mapping.get(record.get("source_key"))
    if not rel:
        raise RuntimeError(
            f"本机映射缺少 {record.get('source_key')}，请重跑 external_templates.py scan"
        )
    source = root / rel
    if not source.is_file():
        raise RuntimeError(f"模板原件不存在：{source}。请重跑 doctor 并修正 root.local.json")
    if verify_hash:
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != record.get("sha256"):
            raise RuntimeError(
                f"模板原件指纹与索引不一致：{template_id}。文件可能已被替换或移动，请重跑 scan"
            )
    return record, source


# ---------------------------------------------------------------------------
# PPTX 包读取
# ---------------------------------------------------------------------------

def _normalize_part(target: str, base: str = "ppt/presentation.xml") -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), target)).lstrip("/")


def _rels_name(part: str) -> str:
    return posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")


def _slide_parts(zf: zipfile.ZipFile) -> list[str]:
    """按 presentation.xml 的真实页序返回每页的部件名。"""
    pres = ET.fromstring(zf.read("ppt/presentation.xml"))
    rels = ET.fromstring(zf.read("ppt/_rels/presentation.xml.rels"))
    by_id = {
        r.get("Id"): (r.get("Target"), r.get("Type"))
        for r in rels.findall("{" + REL_NS + "}Relationship")
    }
    parts: list[str] = []
    lst = pres.find(qn("p", "sldIdLst"))
    if lst is None:
        raise RuntimeError("presentation.xml 缺少 sldIdLst，无法确认页序")
    for sld in lst.findall(qn("p", "sldId")):
        rid = sld.get(qn("r", "id"))
        target, typ = by_id.get(rid, (None, None))
        if not target or typ != SLIDE_REL_TYPE:
            raise RuntimeError(f"页序中的关系 {rid} 不是有效幻灯片")
        parts.append(_normalize_part(target))
    return parts


def _read_entries(zf: zipfile.ZipFile) -> dict[str, bytes]:
    return {i.filename: zf.read(i.filename) for i in zf.infolist() if not i.is_dir()}


# ---------------------------------------------------------------------------
# 文本节点索引（只读定位，不改结构）
# ---------------------------------------------------------------------------

@dataclass
class Slot:
    index: int                 # 该页 <a:t> 的全局序号（按文档顺序）
    shape_id: str
    shape_name: str
    original: str              # 原文（已反转义，供展示）


@dataclass
class TextIndex:
    text: str
    matches: list
    slots: list[Slot]
    by_key: dict[str, list[int]]


def _text_index(xml_bytes: bytes, slide_no: int) -> TextIndex:
    text = xml_bytes.decode("utf-8")
    matches = list(A_T_RE.finditer(text))
    root = ET.fromstring(xml_bytes)
    parent = {child: p for p in root.iter() for child in p}
    shape_tags = {qn("p", "sp"), qn("p", "graphicFrame"), qn("p", "pic"), qn("p", "grpSp")}

    slots: list[Slot] = []
    for position, node in enumerate(root.iter(A_T)):
        cursor = node
        shape = None
        while cursor in parent:
            cursor = parent[cursor]
            if cursor.tag in shape_tags:
                shape = cursor
                break
        shape_id, shape_name = "", ""
        if shape is not None:
            nv = shape.find(".//" + qn("p", "cNvPr"))
            if nv is not None:
                shape_id = nv.get("id") or ""
                shape_name = nv.get("name") or ""
        slots.append(Slot(position, shape_id, shape_name, unescape(node.text or "")))

    if len(slots) != len(matches):
        raise RuntimeError(
            f"第 {slide_no} 页文本节点数量不一致（XML 解析 {len(slots)} / 正则 {len(matches)}），"
            "为避免破坏版式，已拒绝生成。请反馈该模板 ID。"
        )

    by_key: dict[str, list[int]] = {}
    for slot in slots:
        keys = [f"shape_id:{slot.shape_id}"] if slot.shape_id else []
        if slot.shape_name:
            keys.append(f"shape_name:{slot.shape_name}")
        if slot.shape_id:
            keys.append(f"slot_id:s{slide_no:02d}_sh{slot.shape_id}")
        for key in keys:
            by_key.setdefault(key, []).append(slot.index)
    return TextIndex(text, matches, slots, by_key)


def _selector_keys(rep: dict) -> list[str]:
    keys = []
    if rep.get("slot_id"):
        keys.append(f"slot_id:{rep['slot_id']}")
    if rep.get("shape_id"):
        keys.append(f"shape_id:{rep['shape_id']}")
    if rep.get("shape_name"):
        keys.append(f"shape_name:{rep['shape_name']}")
    return keys


def _write_text(index: TextIndex, replacements: list[dict], slide_no: int) -> tuple[str, list[str]]:
    """只改写目标 <a:t> 的内容；不新增/删除任何 XML 元素。"""
    edits: dict[int, str] = {}
    warnings: list[str] = []
    for rep in replacements:
        keys = _selector_keys(rep)
        indices = next((index.by_key[k] for k in keys if k in index.by_key), None)
        if indices is None:
            if rep.get("optional"):
                continue
            raise RuntimeError(
                f"第 {slide_no} 页找不到文本区域：{', '.join(keys) or '<未指定选择器>'}"
            )
        value = str(rep.get("text", ""))
        lines = value.split("\n")
        if len(lines) > len(indices):
            # 严格保真下不新增段落/run，多余行折进最后一个已有文本节点
            head = lines[: len(indices) - 1]
            tail = "\n".join(lines[len(indices) - 1 :])
            lines = head + [tail]
            warnings.append(
                f"第 {slide_no} 页 {keys[0]} 文案行数({len(value.splitlines())})超出原文本节点数"
                f"({len(indices)})，多余内容已合并到最后一个节点；未新增任何元素。"
            )
        for offset, global_index in enumerate(indices):
            edits[global_index] = escape(lines[offset] if offset < len(lines) else "")

    if not edits:
        return index.text, warnings
    chunks: list[str] = []
    cursor = 0
    for position, match in enumerate(index.matches):
        chunks.append(index.text[cursor : match.start(2)])
        chunks.append(edits.get(position, match.group(2)))
        cursor = match.end(2)
    chunks.append(index.text[cursor:])
    return "".join(chunks), warnings


# ---------------------------------------------------------------------------
# 图片替换（受控）
# ---------------------------------------------------------------------------

def _find_image_part(slide_xml: bytes, rels_xml: bytes, part: str, spec: dict) -> tuple[str, ET.Element]:
    root = ET.fromstring(slide_xml)
    wanted_id = str(spec.get("shape_id", "")) if spec.get("shape_id") else ""
    wanted_name = spec.get("shape_name", "")
    pic = None
    for candidate in root.iter(qn("p", "pic")):
        nv = candidate.find(".//" + qn("p", "cNvPr"))
        if nv is None:
            continue
        if (wanted_id and nv.get("id") == wanted_id) or (wanted_name and nv.get("name") == wanted_name):
            pic = candidate
            break
    if pic is None:
        raise RuntimeError(f"第 {part} 页找不到指定图片框：{wanted_id or wanted_name}")
    blip = pic.find(".//" + qn("a", "blip"))
    if blip is None:
        raise RuntimeError("指定图片框没有图片引用")
    rid = blip.get(qn("r", "embed"))
    if not rid:
        raise RuntimeError("指定图片框没有 r:embed 引用")
    rels = ET.fromstring(rels_xml)
    for rel in rels.findall("{" + REL_NS + "}Relationship"):
        if rel.get("Id") == rid:
            return _normalize_part(rel.get("Target") or "", part), pic
    raise RuntimeError(f"关系 {rid} 未指向图片部件")


def _apply_layout_adjustment(xml_text: str, shape_id: str, adjust: dict) -> str:
    """档 2：仅调整被指定图片框的位置/尺寸，其余元素一律不动。"""
    allowed = {"x", "y", "cx", "cy"}
    if not isinstance(adjust, dict) or set(adjust) - allowed:
        raise RuntimeError("layout_adjustment 只接受 x / y / cx / cy（EMU 单位）")
    out = xml_text
    for match in PIC_RE.finditer(xml_text):
        block = match.group(0)
        if not re.search(r'<p:cNvPr\b[^>]*\bid="' + re.escape(shape_id) + r'"', block):
            continue
        new_block = block
        if any(k in adjust for k in ("x", "y")):
            def repl_off(m):
                attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(2)))
                attrs.update({k: str(adjust[k]) for k in ("x", "y") if k in adjust})
                return m.group(1) + " ".join(f'{k}="{v}"' for k, v in attrs.items()) + " " + m.group(3)
            new_block = XF_ATTR_RE.sub(lambda m: repl_off(m) if m.group(0).startswith("<a:off") else m.group(0), new_block)
        if any(k in adjust for k in ("cx", "cy")):
            def repl_ext(m):
                attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(2)))
                attrs.update({k: str(adjust[k]) for k in ("cx", "cy") if k in adjust})
                return m.group(1) + " ".join(f'{k}="{v}"' for k, v in attrs.items()) + " " + m.group(3)
            new_block = XF_ATTR_RE.sub(lambda m: repl_ext(m) if m.group(0).startswith("<a:ext") else m.group(0), new_block)
        return out[: match.start()] + new_block + out[match.end() :]
    raise RuntimeError(f"找不到图片框 {shape_id} 用于布局调整")


# ---------------------------------------------------------------------------
# plan 校验（删页 / 重排 / 改切换一律拒绝）
# ---------------------------------------------------------------------------

def _validate_plan(plan: dict, slide_count: int, *, allow_image_replace: bool, flags: dict) -> None:
    if not isinstance(plan, dict) or plan.get("schema") != PLAN_SCHEMA:
        raise RuntimeError(f"plan 的 schema 必须是 {PLAN_SCHEMA}")
    if plan.get("keep_all_slides") is not True:
        raise RuntimeError("严格保真路线要求 keep_all_slides: true（一页不少、顺序不变）")
    bad = FORBIDDEN_TOP & set(plan)
    if bad:
        raise RuntimeError(f"plan 含有严格保真禁止的字段：{', '.join(sorted(bad))}。禁止删页、重排、复用页或改切换效果")

    slides = plan.get("slides")
    if not isinstance(slides, list):
        raise RuntimeError("plan.slides 必须是数组")
    seen: list[int] = []
    for item in slides:
        if not isinstance(item, dict):
            raise RuntimeError("slides 每一项必须是对象")
        extra = set(item) - ALLOWED_SLIDE_KEYS
        if extra:
            raise RuntimeError(f"第 {item.get('slide')} 页含禁止字段：{', '.join(sorted(extra))}")
        number = item.get("slide")
        if not isinstance(number, int) or not (1 <= number <= slide_count):
            raise RuntimeError(f"页码 {number} 超出范围 1..{slide_count}")
        seen.append(number)
        for rep in item.get("replacements", []) or []:
            if set(rep) - ALLOWED_REPLACEMENT_KEYS:
                raise RuntimeError(f"第 {number} 页 replacements 含禁止字段（不允许改表格/图表/备注）")
            if not _selector_keys(rep):
                raise RuntimeError(f"第 {number} 页有 replacement 未指定 slot_id / shape_id / shape_name")
        images = item.get("image_replacements", []) or []
        if images and not allow_image_replace:
            raise RuntimeError(
                "plan 含图片替换，但未获得授权。需同时满足：条目 user_specified:true、"
                "命令行 --allow-image-replace、feature_flags.image_replace:true"
            )
        for image in images:
            if set(image) - ALLOWED_IMAGE_KEYS:
                raise RuntimeError(f"第 {number} 页 image_replacements 含未知字段")
            if image.get("user_specified") is not True:
                raise RuntimeError("图片替换必须显式标注 user_specified: true")
            asset = Path(str(image.get("asset", ""))).expanduser()
            if not asset.is_file():
                raise RuntimeError(f"图片素材不存在：{asset}")
            if asset.suffix.lower() not in IMAGE_EXT_OK:
                raise RuntimeError(f"不支持的图片格式：{asset.suffix}")
            if image.get("layout_adjustment") and not flags.get("allow_layout_adjustment"):
                raise RuntimeError("布局调整需额外授权（--allow-layout-adjust）")
    if seen != sorted(set(seen)):
        raise RuntimeError("slides 页码必须唯一且升序（禁止重排）")


# ---------------------------------------------------------------------------
# 生成 / 校验
# ---------------------------------------------------------------------------

def inspect_slots(source: Path, slides: list[int] | None = None) -> dict:
    """列出每页可填文本区，供 AI 或使用者写 plan。"""
    with zipfile.ZipFile(source) as zf:
        parts = _slide_parts(zf)
        entries = _read_entries(zf)
    report = {"source": source.name, "slide_count": len(parts), "slides": []}
    for number, part in enumerate(parts, 1):
        if slides and number not in slides:
            continue
        index = _text_index(entries[part], number)
        grouped: dict[str, dict] = {}
        for slot in index.slots:
            key = f"s{number:02d}_sh{slot.shape_id}" if slot.shape_id else f"s{number:02d}_sh?"
            g = grouped.setdefault(key, {"slot_id": key, "shape_name": slot.shape_name,
                                        "text_nodes": 0, "old_text": []})
            g["text_nodes"] += 1
            if slot.original:
                g["old_text"].append(slot.original)
        report["slides"].append({
            "slide": number,
            "key_page": number in KEY_PAGES,
            "slots": list(grouped.values()),
        })
    return report


def scaffold_plan(source: Path, template_id: str) -> dict:
    """生成骨架：列出全部页，但 replacements 全为空 —— 只改你明确点名的文本区。"""
    info = inspect_slots(source)
    return {
        "schema": PLAN_SCHEMA,
        "template_id": template_id,
        "keep_all_slides": True,
        "note": "严格保真：全页同序保留，只在 replacements 中填写要替换的文案；未点名文本框保留原样。",
        "slides": [
            {"slide": s["slide"], "replacements": [],
             "slots": [{"slot_id": x["slot_id"], "old_text": x["old_text"]} for x in s["slots"]]}
            for s in info["slides"]
        ],
    }


def apply_strict(
    source: Path,
    plan: dict,
    output: Path,
    *,
    allow_image_replace: bool = False,
    allow_layout_adjust: bool = False,
    flags: dict | None = None,
) -> dict:
    """整份复制原 pptx，仅覆盖被点名页的文字（和经授权的图片）。返回审计记录。"""
    flags = _flags(flags)
    _require_flag(flags, "strict_native")
    if allow_image_replace:
        _require_flag(flags, "image_replace")
    if allow_layout_adjust:
        flags = dict(flags, allow_layout_adjustment=True)

    with zipfile.ZipFile(source) as zf:
        infos = zf.infolist()
        parts = _slide_parts(zf)
        entries = _read_entries(zf)

    _validate_plan(plan, len(parts), allow_image_replace=allow_image_replace, flags=flags)

    changed: dict[str, bytes] = {}
    warnings: list[str] = []
    audit_slides: list[dict] = []
    changed_media: list[str] = []

    for item in plan["slides"]:
        number = item["slide"]
        part = parts[number - 1]
        original = entries[part]
        index = _text_index(original, number)
        new_text, warns = _write_text(index, item.get("replacements", []) or [], number)
        warnings.extend(warns)
        layout_used = False

        for image in item.get("image_replacements", []) or []:
            rels_part = _rels_name(part)
            if rels_part not in entries:
                raise RuntimeError(f"第 {number} 页缺少关系文件：{rels_part}")
            media_part, _pic = _find_image_part(original, entries[rels_part], part, image)
            if media_part not in entries:
                raise RuntimeError(f"图片部件不存在：{media_part}")
            asset = Path(str(image["asset"])).expanduser()
            if asset.suffix.lower() != Path(media_part).suffix.lower():
                raise RuntimeError(
                    f"图片格式必须与原部件一致（原 {Path(media_part).suffix} / 新 {asset.suffix}），"
                    "否则会破坏包内声明，严格保真路线拒绝替换"
                )
            changed[media_part] = asset.read_bytes()
            changed_media.append(media_part)
            if image.get("layout_adjustment"):
                shape_id = str(image.get("shape_id", ""))
                new_text = _apply_layout_adjustment(new_text, shape_id, image["layout_adjustment"])
                layout_used = True

        if new_text != original.decode("utf-8"):
            changed[part] = new_text.encode("utf-8")
        audit_slides.append({
            "slide": number,
            "key_page": number in KEY_PAGES,
            "replacements": len(item.get("replacements", []) or []),
            "image_replacements": len(item.get("image_replacements", []) or []),
            "layout_adjusted": layout_used,
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(output, "w") as zout:
        for info in infos:
            data = changed.get(info.filename)
            if data is None:
                data = zin.read(info.filename) if not info.is_dir() else b""
            zout.writestr(info, data)

    audit = {
        "schema": "strict_native_audit.v1",
        "source": str(source),
        "output": str(output),
        "template_id": plan.get("template_id"),
        "slide_count": len(parts),
        "keep_all_slides": True,
        "changed_slides": sorted({a["slide"] for a in audit_slides if a["replacements"] or a["image_replacements"]}),
        "changed_media": sorted(set(changed_media)),
        "layout_adjusted_slides": [a["slide"] for a in audit_slides if a["layout_adjusted"]],
        "slides": audit_slides,
        "warnings": warnings,
    }
    return audit


def _canonical(xml_bytes: bytes, *, normalize_xfrm: bool = False) -> bytes:
    """剥离 <a:t> 内容（可选连 xfrm 数值一起规范化）后的字节，用于证明"只有文字变了"。"""
    def blank_text(m):
        return m.group(1) + m.group(3)
    text = A_T_RE.sub(blank_text, xml_bytes.decode("utf-8"))
    if normalize_xfrm:
        text = re.sub(r"(<a:(?:off|ext)\s+)[^>]*?(/>)", r"\1__NORM__\2", text)
    return text.encode("utf-8")


def verify_strict(source: Path, output: Path, audit: dict | None = None) -> dict:
    """白名单比对：除被点名页的文字与经授权的图片外，其余部件必须字节级全等。"""
    with zipfile.ZipFile(source) as a, zipfile.ZipFile(output) as b:
        ea, eb = _read_entries(a), _read_entries(b)
        parts_a, parts_b = _slide_parts(a), _slide_parts(b)

    errors: list[str] = []
    audit = audit or {}
    text_slides = {int(n) for n in audit.get("changed_slides", [])}
    layout_slides = {int(n) for n in audit.get("layout_adjusted_slides", [])}
    media_allowed = set(audit.get("changed_media", []))
    slide_set = set(parts_a) | set(parts_b)

    if parts_a != parts_b:
        errors.append("页序或页部件名发生变化（严格保真要求 1:1 同序）")
    if set(ea) != set(eb):
        missing = sorted(set(ea) - set(eb))
        added = sorted(set(eb) - set(ea))
        if missing:
            errors.append(f"部件丢失 {len(missing)} 个：{missing[:5]}")
        if added:
            errors.append(f"多出部件 {len(added)} 个：{added[:5]}")

    changed_parts: list[str] = []
    for name in sorted(set(ea) & set(eb)):
        if ea[name] == eb[name]:
            continue
        changed_parts.append(name)
        if name in media_allowed:
            continue
        if name in slide_set and name in parts_a:
            number = parts_a.index(name) + 1
            if number in text_slides:
                if _canonical(ea[name], normalize_xfrm=number in layout_slides) != _canonical(
                    eb[name], normalize_xfrm=number in layout_slides
                ):
                    errors.append(f"第 {number} 页除文字（及已授权布局）外还有其他改动：{name}")
                continue
        errors.append(f"未授权改动的部件：{name}")

    for critical in ("ppt/presentation.xml", "ppt/_rels/presentation.xml.rels", "[Content_Types].xml"):
        if critical in ea and critical in eb and ea[critical] != eb[critical]:
            errors.append(f"关键结构文件被改动：{critical}")

    return {
        "ok": not errors,
        "source": str(source),
        "output": str(output),
        "slide_count": len(parts_a),
        "slide_order_identical": parts_a == parts_b,
        "parts_total": len(ea),
        "parts_changed": len(changed_parts),
        "changed_parts": changed_parts,
        "errors": errors,
        "warnings": audit.get("warnings", []),
    }


def doctor() -> dict:
    flags = _flags()
    catalog = _load_json(CATALOG_FILE, {})
    templates = catalog.get("templates", [])
    root = Path(_load_json(ROOT_LOCAL_FILE, {})["root"])
    mapping = (_load_json(SOURCE_MAP_FILE, {}) or {}).get("paths", {})
    missing = [r["source_key"] for r in templates
               if r.get("source_key") not in mapping or not (root / mapping.get(r["source_key"], "__none__")).is_file()]
    return {
        "flags": flags,
        "templates": len(templates),
        "source_root": str(root),
        "source_root_exists": root.is_dir(),
        "mapped": len(mapping),
        "missing_paths": missing[:10],
        "missing_count": len(missing),
        "ready": flags.get("strict_native") is True and root.is_dir() and not missing,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _delivery_warning(record: dict) -> str:
    lines = [
        "【交付提示】该模板授权状态：{}；不可再分发={}。".format(
            (record.get("rights") or {}).get("status", "unknown"),
            not (record.get("rights") or {}).get("redistributable", False),
        ),
        "成品仅供本机使用，请勿上传公开仓库、公开网盘或对外分发。",
    ]
    if record.get("promo_text"):
        lines.append("注意：本模板含模板站推广文字，严格保真会原样保留未点名的文本框。")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="strict-native：整份复制原 PPTX，只把新文案套入被点名的文本区（不改版式、不删页、不重排）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="体检总开关、索引、本机映射与原件路径")

    p_ins = sub.add_parser("inspect", help="列出模板每页可填文本区")
    p_ins.add_argument("template_id")
    p_ins.add_argument("--slides", help="只看指定页，如 1,2,3")
    p_ins.add_argument("-o", "--output", help="结果写入 JSON 文件（默认打印到屏幕）")

    p_sca = sub.add_parser("scaffold", help="生成严格保真 fill plan 骨架")
    p_sca.add_argument("template_id")
    p_sca.add_argument("-o", "--output", required=True)

    p_app = sub.add_parser("apply", help="按 plan 生成 PPTX")
    p_app.add_argument("template_id")
    p_app.add_argument("plan_json")
    p_app.add_argument("-o", "--output", required=True)
    p_app.add_argument("--allow-image-replace", action="store_true", help="授权档 1：同格式原位换图")
    p_app.add_argument("--allow-layout-adjust", action="store_true", help="授权档 2：调整被指定图片框位置/尺寸")
    p_app.add_argument("--audit", help="审计记录写入 JSON")
    p_app.add_argument("--skip-hash", action="store_true", help="跳过原件指纹校验（仅用于可信环境）")

    p_ver = sub.add_parser("verify", help="白名单比对生成结果")
    p_ver.add_argument("template_id")
    p_ver.add_argument("output_pptx")
    p_ver.add_argument("--audit", help="apply 产出的审计 JSON")
    p_ver.add_argument("--skip-hash", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            print(json.dumps(doctor(), ensure_ascii=False, indent=2))
            return 0

        if args.command in {"inspect", "scaffold", "apply", "verify"}:
            record, source = resolve_template(args.template_id, verify_hash=not getattr(args, "skip_hash", False))

            if args.command == "inspect":
                slides = [int(x) for x in args.slides.split(",")] if args.slides else None
                result = inspect_slots(source, slides)
                payload = json.dumps(result, ensure_ascii=False, indent=2)
                if args.output:
                    Path(args.output).write_text(payload + "\n", encoding="utf-8")
                    print(f"槽位清单 -> {args.output}", file=sys.stderr)
                else:
                    print(payload)
                return 0

            if args.command == "scaffold":
                out = Path(args.output)
                _write_json(out, scaffold_plan(source, args.template_id))
                print(f"plan 骨架 -> {out}（共 {record['page_count']} 页）", file=sys.stderr)
                return 0

            if args.command == "apply":
                plan = _load_json(Path(args.plan_json))
                output = Path(args.output)
                audit = apply_strict(
                    source, plan, output,
                    allow_image_replace=args.allow_image_replace,
                    allow_layout_adjust=args.allow_layout_adjust,
                )
                if args.audit:
                    _write_json(Path(args.audit), audit)
                report = verify_strict(source, output, audit)
                if not report["ok"]:
                    print("校验未通过：" + "; ".join(report["errors"]), file=sys.stderr)
                    return 1
                print(f"严格保真 PPTX -> {output}", file=sys.stderr)
                print(f"校验通过：{report['slide_count']} 页同序，{report['parts_total']} 个部件中仅 {report['parts_changed']} 个变化", file=sys.stderr)
                print(_delivery_warning(record), file=sys.stderr)
                for warning in audit["warnings"]:
                    print("提示：" + warning, file=sys.stderr)
                return 0

            if args.command == "verify":
                audit = _load_json(Path(args.audit)) if args.audit else None
                report = verify_strict(source, Path(args.output_pptx), audit)
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 0 if report["ok"] else 1
    except (RuntimeError, ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
