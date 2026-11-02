#!/usr/bin/env python3
"""PPTX review — post-generation layout QA on the .pptx itself.

Reads OOXML geometry directly, so it works for both production routes
(SVG hand-authoring and native template fill) and needs no PowerPoint,
LibreOffice or browser renderer.

The key design decision: every check runs against the **text bounding box**
(lines actually laid out, honouring font size, wrap width, alignment and
vertical anchor), not against the raw shape frame. PowerPoint text frames are
routinely much larger than the text they hold — judging overlap or out-of-bounds
by the frame produces mostly false positives.

Checks, per slide:

  TEXT_OVERFLOW    laid-out text needs more vertical room than the frame offers
  FONT_SQUEEZE     normAutofit fontScale < 100% — type was shrunk to fit
  OVERLAP          two text blocks physically collide
  OUT_OF_BOUNDS    the *text* (not the frame) runs past the slide edge
  TIGHT_GAP        two stacked text blocks sit closer than the minimum gutter
  FORMAT_DRIFT     mixed font family / size inside one text frame
  UNREPLACED       leftover {{PLACEHOLDER}} or XXX
  TINY_TYPE        effective type below the readable floor

Exit code 1 when any ERROR is present, so it can gate a pipeline.

Usage:
    python3 scripts/review_pptx.py deck.pptx
    python3 scripts/review_pptx.py deck.pptx --json report.json
    python3 scripts/review_pptx.py deck.pptx --min-level warn --strict
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict

from pptx import Presentation
from pptx.enum.dml import MSO_FILL
from pptx.enum.text import PP_ALIGN

EMU_PER_PT = 12700
EMU_PER_PX96 = 9525

A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

OVERFLOW_WARN = 1.15
OVERFLOW_ERROR = 1.40
OVERLAP_RATIO = 0.25
TIGHT_GAP_PT = 4.0
TINY_PT = 9.0
SQUEEZE_WARN = 0.90

PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}|\bXXX\b")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")

LEVEL_ORDER = {"info": 0, "warn": 1, "error": 2}
LEVEL_MARK = {"error": "✗", "warn": "⚠", "info": "·"}


@dataclass
class Issue:
    slide: int
    kind: str
    level: str
    where: str
    detail: str
    advice: str
    shape_id: int | None = None


@dataclass
class TextLayout:
    widths: list[float] = field(default_factory=list)   # per-line width in pt
    heights: list[float] = field(default_factory=list)  # per-line height in pt

    @property
    def max_w(self) -> float:
        return max(self.widths) if self.widths else 0.0

    @property
    def total_h(self) -> float:
        return sum(self.heights)


@dataclass
class Box:
    slide: int
    shape_id: int
    name: str
    text: str
    left: int
    top: int
    width: int
    height: int
    is_text: bool
    autofit: str = "none"
    font_scale: float | None = None
    max_font_pt: float | None = None
    fonts: set = field(default_factory=set)
    sizes: set = field(default_factory=set)
    layout: TextLayout | None = None
    text_emu: tuple[int, int, int, int] | None = None  # glyph mass: x, y, w, h


# --------------------------------------------------------------------------
# text metrics
# --------------------------------------------------------------------------
def char_em(ch: str) -> float:
    if ch == "\n":
        return 0.0
    if ord(ch) > 0x2E80:
        return 1.0
    if ch in " \t":
        return 0.32
    if ch.isdigit():
        return 0.55
    if ch.isupper():
        return 0.62
    return 0.52


def wrap_lines(text: str, avail_em: float) -> list[float]:
    """Greedy wrap; returns the width of each produced line, in em units."""
    out: list[float] = []
    used = 0.0
    for ch in text:
        if ch == "\n":
            out.append(used)
            used = 0.0
            continue
        w = char_em(ch)
        if w == 0.0:
            continue
        if used + w > avail_em and used > 0:
            out.append(used)
            used = w
        else:
            used += w
    out.append(used)
    return out or [0.0]


def body_props(shape):
    try:
        return shape.text_frame._txBody.find(f"{A_NS}bodyPr")
    except Exception:
        return None


def frame_padding(shape) -> tuple[int, int, int, int]:
    body = body_props(shape)
    if body is None:
        return 91440, 45720, 91440, 45720
    def _v(attr, fb):
        raw = body.get(attr)
        return int(raw) if raw is not None else fb
    return _v("lIns", 91440), _v("tIns", 45720), _v("rIns", 91440), _v("bIns", 45720)


def read_autofit(shape) -> str:
    body = body_props(shape)
    if body is None:
        return "none"
    if body.find(f"{A_NS}spAutoFit") is not None:
        return "spAutoFit"
    if body.find(f"{A_NS}normAutofit") is not None:
        return "normAutofit"
    return "none"


def read_font_scale(shape) -> float | None:
    body = body_props(shape)
    if body is None:
        return None
    fit = body.find(f"{A_NS}normAutofit")
    if fit is None:
        return None
    raw = fit.get("fontScale")
    try:
        return int(raw) / 100000.0 if raw else None
    except ValueError:
        return None


def vertical_anchor(shape) -> str:
    body = body_props(shape)
    if body is None:
        return "t"
    return body.get("anchor") or "t"


def layout_text(shape, box: Box) -> TextLayout | None:
    """Lay the text out inside the frame and return per-line metrics (pt)."""
    if not box.is_text or box.max_font_pt is None:
        return None
    l, t, r, b = frame_padding(shape)
    avail_w_pt = (box.width - l - r) / EMU_PER_PT
    if avail_w_pt <= 4:
        return None

    layout = TextLayout()
    for para in shape.text_frame.paragraphs:
        text = "".join(run.text for run in para.runs) or (para.text or "")
        size = None
        for run in para.runs:
            if run.font.size is not None:
                size = run.font.size.pt
                break
        if size is None:
            size = para.font.size.pt if para.font.size is not None else box.max_font_pt

        spacing = para.line_spacing
        if isinstance(spacing, float) and 0 < spacing < 4:
            line_h = size * spacing
        elif spacing is not None and hasattr(spacing, "pt"):
            line_h = spacing.pt
        else:
            line_h = size * 1.22

        for w_em in wrap_lines(text, avail_w_pt / size):
            layout.widths.append(w_em * size)
            layout.heights.append(line_h)
        if para.space_after is not None and layout.heights:
            layout.heights[-1] += para.space_after.pt
    return layout


def text_bbox(shape, box: Box) -> tuple[int, int, int, int] | None:
    """Where the glyphs actually sit, in EMU, honouring align + anchor."""
    if box.layout is None or box.layout.total_h <= 0:
        return None
    l, t, r, b = frame_padding(shape)
    avail_w = box.width - l - r
    avail_h = box.height - t - b
    text_w = box.layout.max_w * EMU_PER_PT
    text_h = box.layout.total_h * EMU_PER_PT

    align = PP_ALIGN.LEFT
    for para in shape.text_frame.paragraphs:
        if para.alignment is not None:
            align = para.alignment
            break
    if align == PP_ALIGN.CENTER:
        x = box.left + l + (avail_w - text_w) / 2
    elif align == PP_ALIGN.RIGHT:
        x = box.left + box.width - r - text_w
    else:
        x = box.left + l

    anchor = vertical_anchor(shape)
    if anchor == "ctr":
        y = box.top + t + (avail_h - text_h) / 2
    elif anchor == "b":
        y = box.top + box.height - b - text_h
    else:
        y = box.top + t

    return int(x), int(y), int(text_w), int(text_h)


# --------------------------------------------------------------------------
# collection
# --------------------------------------------------------------------------
def collect(slide, index: int) -> list[Box]:
    boxes: list[Box] = []
    for shape in slide.shapes:
        try:
            left, top, width, height = (int(shape.left), int(shape.top),
                                        int(shape.width), int(shape.height))
        except Exception:
            continue
        tf = shape.text_frame if shape.has_text_frame else None
        text = tf.text if tf is not None else ""
        box = Box(slide=index, shape_id=shape.shape_id, name=shape.name or "",
                  text=text or "", left=left, top=top, width=width, height=height,
                  is_text=bool(tf is not None and text.strip()))
        if tf is not None:
            box.autofit = read_autofit(shape)
            box.font_scale = read_font_scale(shape)
            for para in tf.paragraphs:
                for run in para.runs:
                    if run.font.size is not None:
                        box.sizes.add(round(run.font.size.pt, 1))
                    if run.font.name:
                        box.fonts.add(run.font.name)
                if para.font.size is not None:
                    box.sizes.add(round(para.font.size.pt, 1))
            if box.sizes:
                box.max_font_pt = max(box.sizes)
            box.layout = layout_text(shape, box)
            box.text_emu = text_bbox(shape, box)
        boxes.append(box)
    return boxes


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------
def check_overflow(shape, box: Box) -> Issue | None:
    if box.layout is None or box.max_font_pt is None:
        return None
    # spAutoFit grows the frame to the text; the ratio is meaningless there.
    if box.autofit == "spAutoFit":
        return None
    raw = box.text.strip()
    # Decorative numerals and single glyphs are sized to bleed past their frame.
    if len(raw) <= 3 and not CJK_RE.search(raw):
        return None

    l, t, r, b = frame_padding(shape)
    avail_h_pt = (box.height - t - b) / EMU_PER_PT
    if avail_h_pt <= 2:
        return None
    ratio = box.layout.total_h / avail_h_pt
    if ratio < OVERFLOW_WARN:
        return None

    # A transparent text box is just a positioning frame — glyphs spilling past
    # it is normal. A filled shape is a visible card, so overflow there really
    # does break the layout.
    try:
        ft = shape.fill.type
        has_fill = ft is not None and ft != MSO_FILL.BACKGROUND
    except Exception:
        has_fill = False

    if ratio >= 3.0:
        level = "error"                     # 3x over can only be a mistake
    elif ratio >= OVERFLOW_ERROR:
        level = "error" if has_fill else "warn"
    else:
        level = "warn" if has_fill else "info"

    over_pt = box.layout.total_h - avail_h_pt
    lines_over = max(1, round(over_pt / (box.max_font_pt * 1.22)))
    return Issue(
        slide=box.slide, kind="TEXT_OVERFLOW", level=level,
        where=f's{box.slide:02d}#{box.shape_id} "{raw[:18]}"',
        detail=f"文字需 {box.layout.total_h:.0f}pt，框内可用 {avail_h_pt:.0f}pt（{ratio*100:.0f}%）",
        advice=f"删掉约 {lines_over} 行文字，或字号从 {box.max_font_pt:.0f}pt 下调一档",
        shape_id=box.shape_id,
    )


def check_squeeze(box: Box) -> Issue | None:
    if not box.is_text or box.font_scale is None or box.font_scale >= SQUEEZE_WARN:
        return None
    base = box.max_font_pt or 0
    level = "warn" if box.font_scale >= 0.75 else "error"
    return Issue(
        slide=box.slide, kind="FONT_SQUEEZE", level=level,
        where=f's{box.slide:02d}#{box.shape_id} "{box.text[:18]}"',
        detail=f"自动缩放至 {box.font_scale*100:.0f}%（设计 {base:.0f}pt → 实际 {base*box.font_scale:.0f}pt）",
        advice="把文案压到设计容量内，再把自动缩放关掉",
        shape_id=box.shape_id,
    )


def check_bounds(box: Box, page_w: int, page_h: int | None = None) -> Issue | None:
    if box.text_emu is None:
        return None
    x, y, w, h = box.text_emu
    tol = 2 * EMU_PER_PX96
    edges = [("右", x + w - page_w), ("左", -x)]
    if page_h is not None:
        edges.extend([("下", y + h - page_h), ("上", -y)])
    outside = [(edge, over) for edge, over in edges if over > tol]
    if not outside:
        return None
    return Issue(
        slide=box.slide, kind="OUT_OF_BOUNDS", level="warn",
        where=f's{box.slide:02d}#{box.shape_id} "{box.text[:18]}"',
        detail="；".join(f"文字{edge}端超出画布 {over/EMU_PER_PX96:.0f}px"
                         for edge, over in outside),
        advice="缩短文字或把文本框移回画布；投影时超界部分会被裁掉",
        shape_id=box.shape_id,
    )


def check_unreplaced(box: Box) -> Issue | None:
    if not box.is_text:
        return None
    m = PLACEHOLDER_RE.search(box.text)
    if not m:
        return None
    return Issue(
        slide=box.slide, kind="UNREPLACED", level="error",
        where=f's{box.slide:02d}#{box.shape_id} "{box.text[:18]}"',
        detail=f"残留占位符 {m.group(0)}",
        advice="模板原文没被替换，交付前必须填掉",
        shape_id=box.shape_id,
    )


def check_tiny(box: Box) -> Issue | None:
    if not box.is_text or not box.sizes:
        return None
    effective = min(box.sizes) * (box.font_scale or 1.0)
    if effective >= TINY_PT:
        return None
    return Issue(
        slide=box.slide, kind="TINY_TYPE", level="warn",
        where=f's{box.slide:02d}#{box.shape_id} "{box.text[:18]}"',
        detail=f"实际字号 {effective:.1f}pt（下限 {TINY_PT:.0f}pt）",
        advice="投影时 9pt 以下基本看不清，删减要点或放大到 10pt 以上",
        shape_id=box.shape_id,
    )


def check_drift(box: Box) -> Issue | None:
    if not box.is_text:
        return None
    if len(box.fonts) > 2 or len(box.sizes) > 3:
        return Issue(
            slide=box.slide, kind="FORMAT_DRIFT", level="info",
            where=f's{box.slide:02d}#{box.shape_id} "{box.text[:18]}"',
            detail=f"同一文本框内 {len(box.fonts)} 种字体 / {len(box.sizes)} 种字号",
            advice="同层级文字统一字体与字号；混排通常是从别处粘贴带进来的",
            shape_id=box.shape_id,
        )
    return None


def check_overlap(a: Box, b: Box) -> Issue | None:
    if a.text_emu is None or b.text_emu is None:
        return None
    ax, ay, aw, ah = a.text_emu
    bx, by, bw, bh = b.text_emu
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    if ix <= 0 or iy <= 0:
        return None
    inter = ix * iy
    smaller = min(aw * ah, bw * bh)
    if smaller <= 0:
        return None
    ratio = inter / smaller
    if ratio < OVERLAP_RATIO:
        return None

    # Designed word-stacking: a huge CJK title with a tiny Latin caption laid
    # over it ("目录" + "contents"). Extremely common in these templates and
    # always intentional — report it as info so it is not mistaken for a bug.
    a_sz = a.max_font_pt or 0
    b_sz = b.max_font_pt or 0
    stacked = a_sz and b_sz and max(a_sz, b_sz) / min(a_sz, b_sz) > 2.5 and ratio > 0.55
    if stacked:
        return Issue(
            slide=a.slide, kind="OVERLAP", level="info",
            where=f's{a.slide:02d} "{a.text[:12]}" × "{b.text[:12]}"',
            detail=f"文字区域叠合 {ratio*100:.0f}%，字号相差 {max(a_sz,b_sz)/min(a_sz,b_sz):.1f} 倍",
            advice="多为刻意的中英叠字设计，确认视觉上无歧义即可放行",
            shape_id=a.shape_id,
        )

    level = "error" if ratio > 0.55 else "warn"
    return Issue(
        slide=a.slide, kind="OVERLAP", level=level,
        where=f's{a.slide:02d} "{a.text[:12]}" × "{b.text[:12]}"',
        detail=f"文字区域相交 {ratio*100:.0f}%（{ix/EMU_PER_PX96:.0f}×{iy/EMU_PER_PX96:.0f}px）",
        advice="两个文本块压在一起了，缩小其中一个的宽度或错开纵向位置",
        shape_id=a.shape_id,
    )


def check_gap(a: Box, b: Box) -> Issue | None:
    if a.text_emu is None or b.text_emu is None:
        return None
    ax, ay, aw, ah = a.text_emu
    bx, by, bw, bh = b.text_emu
    if not (ax < bx + bw and bx < ax + aw):
        return None
    gap = by - (ay + ah)
    if gap <= 0 or gap >= TIGHT_GAP_PT * EMU_PER_PT:
        return None
    return Issue(
        slide=a.slide, kind="TIGHT_GAP", level="info",
        where=f's{a.slide:02d} "{a.text[:12]}" ↓ "{b.text[:12]}"',
        detail=f"两段文字间距仅 {gap/EMU_PER_PT:.1f}pt",
        advice="至少留 4pt，否则投影时会连成一片",
        shape_id=a.shape_id,
    )


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------
def review(path: str) -> tuple[list[Issue], dict]:
    prs = Presentation(path)
    page_w = int(prs.slide_width)
    page_h = int(prs.slide_height)
    issues: list[Issue] = []
    per_slide = []

    for idx, slide in enumerate(prs.slides, 1):
        boxes = collect(slide, idx)
        shapes = {sh.shape_id: sh for sh in slide.shapes}
        texts = [b for b in boxes if b.is_text and b.text_emu]

        for box in boxes:
            shape = shapes.get(box.shape_id)
            got = check_overflow(shape, box) if shape is not None else None
            for issue in (got, check_squeeze(box), check_bounds(box, page_w, page_h),
                          check_tiny(box), check_drift(box)):
                if issue:
                    issues.append(issue)

        # Scan all DrawingML text, including grouped shapes and table cells.
        # Their coordinates need separate transforms; text-only checks do not.
        for node in slide._element.iter(f"{A_NS}p"):
            text = "".join(t.text or "" for t in node.iter(f"{A_NS}t"))
            match = PLACEHOLDER_RE.search(text)
            if match:
                issues.append(Issue(
                    slide=idx, kind="UNREPLACED", level="error",
                    where=f's{idx:02d} "{text[:18]}"',
                    detail=f"残留占位符 {match.group(0)}",
                    advice="替换为实际内容，未知的个人信息请省略该字段",
                ))

        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                got = check_overlap(texts[i], texts[j])
                if got:
                    issues.append(got)
        texts.sort(key=lambda b: b.text_emu[1])
        for i in range(len(texts) - 1):
            got = check_gap(texts[i], texts[i + 1])
            if got:
                issues.append(got)

        per_slide.append({
            "slide": idx,
            "shapes": len(boxes),
            "text_shapes": len(texts),
            "issues": sum(1 for x in issues if x.slide == idx),
        })

    summary = {
        "file": os.path.basename(path),
        "slides": len(prs.slides),
        "issues": len(issues),
        "error": sum(1 for x in issues if x.level == "error"),
        "warn": sum(1 for x in issues if x.level == "warn"),
        "info": sum(1 for x in issues if x.level == "info"),
        "by_kind": {},
        "per_slide": per_slide,
    }
    for x in issues:
        summary["by_kind"][x.kind] = summary["by_kind"].get(x.kind, 0) + 1
    return issues, summary


def render(issues: list[Issue], summary: dict, min_level: str) -> str:
    out = [f"\n{summary['file']}  ·  {summary['slides']} 页  ·  "
           f"检出 {summary['error']} 错误 / {summary['warn']} 警告 / {summary['info']} 提示"]
    if summary["by_kind"]:
        kinds = "  ".join(f"{k}×{v}" for k, v in
                          sorted(summary["by_kind"].items(), key=lambda x: -x[1]))
        out.append(f"类型分布：{kinds}")
    out.append("─" * 74)

    floor = LEVEL_ORDER[min_level]
    shown = [x for x in issues if LEVEL_ORDER[x.level] >= floor]
    if not shown:
        out.append("未检出问题。")
        return "\n".join(out)

    current = None
    for x in sorted(shown, key=lambda i: (i.slide, -LEVEL_ORDER[i.level], i.kind)):
        if x.slide != current:
            current = x.slide
            out.append(f"\nP{x.slide:02d}")
        out.append(f"  {LEVEL_MARK[x.level]} {x.kind:14s} {x.where}")
        out.append(f"     实测：{x.detail}")
        out.append(f"     建议：{x.advice}")
    out.append("")
    return "\n".join(out)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    ap = argparse.ArgumentParser(description="Post-generation layout QA for a .pptx")
    ap.add_argument("pptx")
    ap.add_argument("--json", help="Write the full report as JSON here")
    ap.add_argument("--min-level", choices=["info", "warn", "error"], default="info")
    ap.add_argument("--strict", action="store_true",
                    help="Exit non-zero on warnings too, not just errors")
    a = ap.parse_args()

    issues, summary = review(a.pptx)
    print(render(issues, summary, a.min_level))

    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"summary": summary, "issues": [asdict(x) for x in issues]},
                      fh, ensure_ascii=False, indent=2, default=str)
            fh.write("\n")
        print(f"JSON 报告：{a.json}")

    if summary["error"]:
        return 1
    if a.strict and summary["warn"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
