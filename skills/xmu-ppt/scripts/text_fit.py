"""文本容量适配：保证填入的文案落在模板原有文本框边界内，不溢出、不互相压盖。

为什么需要
----------
模板里大量短标签使用 ``wrap="none"``（不自动换行），而填充器会把整句写进
第一个文本 run 并清空其余 run。若给这类框填入长句，文字会横向铺开，
压盖相邻元素。既有 check-plan 只比较「新文案/原示例」长度比例，
且把可容纳行数放宽到原段落数，无法检出绝对溢出。

策略（只约束文案，绝不改动模板版式）
------------------------------------
1. 从模板源 XML 读取每个文本框的 wrap、内边距、字号；从 slide_library
   读取几何（px），算出「单行可容纳字数」；
2. 出稿前对 plan 做容量校验：超容量的文案必须缩短或分行；
3. 提供自动兜底：按容量安全截断（优先在标点处断句），并写入检查报告；
4. 三项检查中的「文字适配布局」纳入绝对容量结果。
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
EMU_PER_PX = 914400 / 96
SLIDE_RE = re.compile(r"ppt/slides/slide(\d+)\.xml$")


def _shape_meta(root: ET.Element) -> dict[str, dict]:
    """按 cNvPr id 收集 wrap / 内边距 / 最大字号（百分之一磅）。"""
    out: dict[str, dict] = {}
    for sp in root.iter(P + "sp"):
        nv = sp.find(".//" + P + "cNvPr")
        if nv is None:
            continue
        sid = nv.get("id")
        if not sid:
            continue
        body = sp.find(".//" + A + "bodyPr")
        sizes = [
            int(m) for m in re.findall(r'\bsz="(\d+)"', ET.tostring(sp, encoding="unicode"))
        ]
        meta = {
            "wrap": (body.get("wrap") if body is not None else None) or "square",
            "l_ins": int(body.get("lIns", 91440)) if body is not None else 91440,
            "r_ins": int(body.get("rIns", 91440)) if body is not None else 91440,
            "font_pt": max(sizes) / 100 if sizes else None,
        }
        out[sid] = meta
    return out


def _fallback_font_px(geometry: dict, role: str) -> float:
    height = geometry.get("height")
    if isinstance(height, (int, float)) and height > 0:
        return max(10.0, min(height / 1.35, 24.0))
    return 16.0 if "title" in role else 13.0


def build_capacity_map(source: Path, library: dict) -> dict[str, dict]:
    """返回 slot_id -> 容量信息。slot_id 形如 s11_sh21。"""
    shape_meta_by_slide: dict[int, dict[str, dict]] = {}
    with zipfile.ZipFile(source) as zf:
        for name in zf.namelist():
            match = SLIDE_RE.fullmatch(name)
            if not match:
                continue
            try:
                shape_meta_by_slide[int(match.group(1))] = _shape_meta(ET.fromstring(zf.read(name)))
            except ET.ParseError:
                continue

    result: dict[str, dict] = {}
    for slide in library.get("slides", []):
        index = int(slide["slide_index"])
        metas = shape_meta_by_slide.get(index, {})
        for slot in slide.get("slots", []):
            slot_id = slot["slot_id"]
            shape_id = slot_id.split("_sh")[-1] if "_sh" in slot_id else ""
            meta = metas.get(shape_id, {})
            geometry = slot.get("geometry") or {}
            width = geometry.get("width")
            height = geometry.get("height")
            if not isinstance(width, (int, float)) or width <= 0:
                width = 200
            if not isinstance(height, (int, float)) or height <= 0:
                height = 40
            metrics = slot.get("text_metrics") or {}
            font_px = metrics.get("font_size_px")
            if not isinstance(font_px, (int, float)) or font_px <= 0:
                font_pt = meta.get("font_pt")
                font_px = (font_pt * 96 / 72) if font_pt else _fallback_font_px(geometry, slot.get("role", ""))
            padding = (meta.get("l_ins", 91440) + meta.get("r_ins", 91440)) / EMU_PER_PX
            usable = max(width - padding - 4, 12)
            # 中文按一个字号宽估算，保守留 5% 余量
            per_line = max(int(usable / max(font_px * 1.05, 1)), 2)
            wrap_none = meta.get("wrap") == "none"
            max_lines = 1 if wrap_none else max(int(height / max(font_px * 1.3, 1)), 1)
            result[slot_id] = {
                "slide": index,
                "shape_id": shape_id,
                "wrap": "none" if wrap_none else "square",
                "width": round(width, 1),
                "height": round(height, 1),
                "font_px": round(font_px, 2),
                "per_line": per_line,
                "max_lines": max_lines,
                "paragraphs": max(int((slot.get("text_metrics") or {}).get("paragraph_count") or 1), 1),
                # 单个 run 的安全上限：填充器会把整句塞进第一个 run
                "safe_chars": per_line,
            }
    return result


def _shorten(text: str, limit: int) -> str:
    """按容量安全缩短，优先在标点处断句，避免半截词。"""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    window = text[:limit]
    for mark in ("。", "、", "，", "；", "：", " ", "|", "/", "·"):
        pos = window.rfind(mark)
        if pos >= max(4, limit // 2):
            return window[:pos].rstrip("、，；：·|/ ")
    return window.rstrip("、，；：·|/ ")


def _split_lines(text: str, limit: int, max_lines: int) -> list[str]:
    """按中文标点把长句切成不超过 limit 的短行，保持语义完整。"""
    text = " ".join(text.replace("\n", " ").split())
    if len(text) <= limit:
        return [text]
    chunks = re.split(r"(?<=[、，；：。！？])", text)
    lines: list[str] = []
    current = ""
    for chunk in chunks:
        if not chunk:
            continue
        while len(chunk) > limit:
            if current:
                lines.append(current)
                current = ""
            lines.append(chunk[:limit])
            chunk = chunk[limit:]
        if len(current) + len(chunk) <= limit:
            current += chunk
        else:
            lines.append(current)
            current = chunk
    if current:
        lines.append(current)
    return [line for line in lines if line][:max_lines]


def validate_plan(plan: dict, capacity: dict) -> list[dict]:
    """返回所有超出文本框容量的文案。"""
    problems = []
    for item in plan.get("slides", []):
        for rep in item.get("replacements", []) or []:
            slot_id = rep.get("slot_id")
            text = str(rep.get("text", ""))
            info = capacity.get(slot_id)
            if not info or not text:
                continue
            lines = text.split("\n")
            limit = info["safe_chars"]
            max_lines = max(info["max_lines"], 1) if info["wrap"] == "square" else 1
            too_long = max((len(line) for line in lines), default=0) > limit
            too_many = len(lines) > max_lines
            if too_long or too_many:
                problems.append({
                    "slide": item.get("source_slide"),
                    "slot_id": slot_id,
                    "length": max((len(line) for line in lines), default=0),
                    "lines": len(lines),
                    "safe_chars": limit,
                    "max_lines": max_lines,
                    "wrap": info["wrap"],
                    "text": text[:60],
                })
    return problems


def enforce_plan(plan: dict, capacity: dict) -> tuple[dict, list[dict]]:
    """出稿前兜底：单行框缩短；可换行多段框按容量分行，保持原有分段结构。

    返回 (新 plan, 修改记录)。绝不改动模板版式，只调整填入的文字。
    """
    import copy

    out = copy.deepcopy(plan)
    changes = []
    for item in out.get("slides", []):
        for rep in item.get("replacements", []) or []:
            info = capacity.get(rep.get("slot_id"))
            text = str(rep.get("text", ""))
            if not info or not text:
                continue
            limit = info["safe_chars"]
            lines = text.split("\n")
            fits = (all(len(line) <= limit for line in lines)
                    and (len(lines) <= max(info["max_lines"], 1) or info["wrap"] == "square"))
            if fits:
                continue
            if info["wrap"] == "none" or info["max_lines"] <= 1 or info["paragraphs"] <= 1:
                new_text = _shorten(text, limit)
            else:
                # 多行框：按原段落数分行，填充器会把每行写进对应段落
                allowed = min(info["max_lines"], max(info["paragraphs"], 1))
                new_text = "\n".join(_split_lines(text, limit, max(allowed, 1)))
            changes.append({
                "slide": item.get("source_slide"),
                "slot_id": rep.get("slot_id"),
                "before": text[:60],
                "after": new_text[:60].replace("\n", " / "),
                "safe_chars": limit,
                "wrap": info["wrap"],
            })
            rep["text"] = new_text
    return out, changes


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    chk = sub.add_parser("check", help="检查 plan 是否有超容量文案")
    chk.add_argument("library_json")
    chk.add_argument("plan_json")
    chk.add_argument("--source", required=True, help="模板源 PPTX")
    args = parser.parse_args(argv)
    library = json.loads(Path(args.library_json).read_text(encoding="utf-8"))
    plan = json.loads(Path(args.plan_json).read_text(encoding="utf-8"))
    capacity = build_capacity_map(Path(args.source), library)
    problems = validate_plan(plan, capacity)
    print(json.dumps({
        "slots": len(capacity),
        "wrap_none_slots": sum(1 for v in capacity.values() if v["wrap"] == "none"),
        "overflow_count": len(problems),
        "overflow": problems[:20],
        "ok": not problems,
    }, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
