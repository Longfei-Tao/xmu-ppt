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
2. 出稿前对 plan 做容量校验：超容量的文案优先按视觉宽度分行；
3. 无法分行时直接报错，绝不静默截断（标题、正文、标签一视同仁）；
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
# 容量估算的安全余量：在理论宽度上再留 2%，抵消字体差异与字距
SAFETY = 0.98
LINE_HEIGHT = 1.2


class TextOverflowError(ValueError):
    """文案在文本框内既放不下、也无法通过分行解决。"""

    def __init__(self, problems: list[dict]):
        self.problems = problems
        super().__init__(self._message())

    def _message(self) -> str:
        parts = []
        for item in self.problems:
            parts.append(
                f"第 {item.get('slide')} 页 {item.get('slot_id')}："
                f"{item.get('lines')} 行 / 单行约 {item.get('safe_em')} 字，"
                f"原文「{item.get('text')}」"
            )
        return "文字放不进模板文本框，请改写文案后重试：" + "；".join(parts)


def _char_em(ch: str) -> float:
    """按视觉宽度估算字符占几个中文字宽（em）。"""
    code = ord(ch)
    if (
        0x2E80 <= code <= 0x9FFF
        or 0xAC00 <= code <= 0xD7AF
        or 0xF900 <= code <= 0xFAFF
        or 0xFF00 <= code <= 0xFF60
        or 0xFFE0 <= code <= 0xFFE6
    ):
        return 1.0
    if ch == " ":
        return 0.3
    if ch.isdigit():
        return 0.55
    if ch.isupper():
        return 0.64
    return 0.52


def _line_em(text: str) -> float:
    return sum(_char_em(ch) for ch in text)


def _shape_meta(root: ET.Element) -> dict[str, dict]:
    """按 cNvPr id 收集 wrap / 内边距 / 字号 / 自动调整方式。"""
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
        autofit = "none"
        if body is not None and body.find(A + "spAutoFit") is not None:
            autofit = "spAutoFit"
        elif body is not None and body.find(A + "normAutofit") is not None:
            autofit = "normAutofit"
        meta = {
            "wrap": (body.get("wrap") if body is not None else None) or "square",
            "l_ins": int(body.get("lIns", 91440)) if body is not None else 91440,
            "r_ins": int(body.get("rIns", 91440)) if body is not None else 91440,
            "font_pt": max(sizes) / 100 if sizes else None,
            "autofit": autofit,
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
            # 以「em」为单位估算单行容量：中文 1em，英文/数字约 0.55em
            per_line_em = usable / max(font_px, 1)
            # 预留 2% 字宽误差的安全余量：宁可高估文案宽度，也不让它溢出
            safe_em = max(round(per_line_em * SAFETY, 2), 2.0)
            wrap_none = meta.get("wrap") == "none"
            paragraphs = max(int((slot.get("text_metrics") or {}).get("paragraph_count") or 1), 1)
            # 多段落文本框本来就按 N 行设计，行数下限取其段落数
            max_lines = 1 if wrap_none else max(int(height / max(font_px * LINE_HEIGHT, 1)), paragraphs)
            # spAutoFit 的框会随文字增高，不能把它当成固定行数；放宽到 12 行只防明显失控
            if not wrap_none and meta.get("autofit") == "spAutoFit":
                max_lines = max(max_lines, 12)
            result[slot_id] = {
                "slide": index,
                "shape_id": shape_id,
                "wrap": "none" if wrap_none else "square",
                "width": round(width, 1),
                "height": round(height, 1),
                "font_px": round(font_px, 2),
                "per_line": max(int(safe_em), 2),
                "max_lines": max_lines,
                "paragraphs": paragraphs,
                "autofit": meta.get("autofit", "none"),
                # 单个 run 的安全上限（em）；不再用于截断，只用于校验/提示
                "safe_chars": max(int(safe_em), 2),
                "safe_em": safe_em,
            }
    return result


PUNCT = "、，；：。！？,;:!?）)》」』"
TOKEN_RE = re.compile(rf"[^{PUNCT}]+[{PUNCT}]?")


def _split_lines(text: str, limit_em: float, max_lines: int | None = None) -> list[str]:
    """按视觉宽度把文字切成完整短行，不丢字。

    ``limit_em`` 是单行可容纳的中文字宽数；``max_lines`` 仅作兼容参数，
    不在函数内截断——行数过多应由调用方判定为溢出并报错。
    """
    text = " ".join(text.replace("\n", " ").split())
    if not text:
        return [""]
    if _line_em(text) <= limit_em:
        return [text]
    lines: list[str] = []
    current = ""
    for token in TOKEN_RE.findall(text):
        if _line_em(current + token) <= limit_em:
            current += token
            continue
        if current:
            lines.append(current)
            current = ""
        if _line_em(token) <= limit_em:
            current = token
            continue
        # 单个语义块本身超宽时逐字切，仍不丢字
        piece = ""
        for ch in token:
            if piece and _line_em(piece + ch) > limit_em:
                lines.append(piece)
                piece = ""
            piece += ch
        if piece:
            current = piece
    if current:
        lines.append(current)
    return [line for line in lines if line]


def _limit_em(info: dict) -> float:
    """兼容旧容量表：优先视觉宽度，其次回退到字符数。"""
    value = info.get("safe_em")
    if not isinstance(value, (int, float)) or value <= 0:
        value = info.get("safe_chars", 2)
    return max(float(value), 2.0)


def _max_lines(info: dict) -> int:
    if info.get("wrap") != "square":
        return 1
    return max(int(info.get("max_lines") or 1), 1)


def _overflow_entry(item: dict, rep: dict, info: dict, lines: list[str]) -> dict:
    return {
        "slide": item.get("source_slide"),
        "slot_id": rep.get("slot_id"),
        "lines": len(lines),
        "max_lines": _max_lines(info),
        "line_em": [round(_line_em(line), 2) for line in lines],
        "safe_em": _limit_em(info),
        "wrap": info["wrap"],
        "text": str(rep.get("text", ""))[:60],
    }


def validate_plan(plan: dict, capacity: dict) -> list[dict]:
    """返回所有超出文本框容量的文案（按视觉宽度，不按字符数）。"""
    problems = []
    for item in plan.get("slides", []):
        for rep in item.get("replacements", []) or []:
            slot_id = rep.get("slot_id")
            text = str(rep.get("text", ""))
            info = capacity.get(slot_id)
            if not info or not text:
                continue
            lines = text.split("\n")
            limit = _limit_em(info)
            too_wide = any(_line_em(line) > limit for line in lines)
            too_many = len(lines) > _max_lines(info)
            if too_wide or too_many:
                problems.append(_overflow_entry(item, rep, info, lines))
    return problems


def enforce_plan(plan: dict, capacity: dict) -> tuple[dict, list[dict]]:
    """出稿前适配：可换行的框按视觉宽度完整分行；分不下则报错，绝不截断。

    返回 (新 plan, 修改记录)。绝不改动模板版式，只调整填入的文字。
    """
    import copy

    out = copy.deepcopy(plan)
    changes = []
    problems = []
    for item in out.get("slides", []):
        for rep in item.get("replacements", []) or []:
            info = capacity.get(rep.get("slot_id"))
            text = str(rep.get("text", ""))
            if not info or not text:
                continue
            limit = _limit_em(info)
            lines = text.split("\n")
            if (all(_line_em(line) <= limit for line in lines)
                    and len(lines) <= _max_lines(info)):
                continue
            # wrap="none" 的单行框没有换行能力，只能由使用者改写文案
            if info["wrap"] != "square":
                problems.append(_overflow_entry(item, rep, info, lines))
                continue
            new_lines: list[str] = []
            for line in lines:
                new_lines.extend(_split_lines(line, limit))
            if len(new_lines) > _max_lines(info):
                problems.append(_overflow_entry(item, rep, info, new_lines))
                continue
            new_text = "\n".join(new_lines)
            changes.append({
                "slide": item.get("source_slide"),
                "slot_id": rep.get("slot_id"),
                "before": text[:60],
                "after": new_text[:60].replace("\n", " / "),
                "safe_em": limit,
                "wrap": info["wrap"],
            })
            rep["text"] = new_text
    if problems:
        raise TextOverflowError(problems)
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
