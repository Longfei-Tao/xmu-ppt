#!/usr/bin/env python3
"""Ingest native PPTX decks into the template library.

For each source deck this produces two artifacts inside
`templates/decks/<deck_id>/`:

  source.pptx        slimmed copy (embedded fonts stripped, oversized media
                     downscaled) — the clone source for native fill
  layout_index.json  per-slide layout profile: role, slot count, type scale,
                     and an inferred layout label, so the AI can pick a page by
                     "what shape of content fits here" instead of guessing

Why slim: these decks ship with 15-30 MB of embedded commercial fonts which
cannot be redistributed and are never read by PowerPoint on another machine.
Stripping them plus downscaling oversized media typically cuts 75-90% of the
payload while leaving every shape, table, chart and photo intact.

Usage:
    python3 scripts/build_layout_index.py <source.pptx> --deck-id 厦门大学_主题_凤凰花开
    python3 scripts/build_layout_index.py <dir> --auto-map mapping.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
DECKS_DIR = os.path.join(SKILL_DIR, "templates", "decks")

FONT_REL_RE = re.compile(rb'<Relationship[^>]*Target="fonts/[^"]*"[^>]*/>')
FONT_OVERRIDE_RE = re.compile(rb'<Override[^>]*PartName="/ppt/fonts/[^"]*"[^>]*/>')
EMBEDDED_FONT_RE = re.compile(rb'<p:embeddedFontLst>.*?</p:embeddedFontLst>', re.S)
NUMBERED_RE = re.compile(r"^(0?\d+[\.、/]?|\d+/\s*)$")


# --------------------------------------------------------------------------
# slim
# --------------------------------------------------------------------------
def _compress_image(data: bytes, name: str, max_edge: int, quality: int) -> tuple[bytes, str]:
    """Return (payload, filename). The filename may switch .png -> .jpg.

    Photos stored as PNG are the single biggest waste in these decks: a 1440px
    photo is 1.5-2.5 MB as lossless PNG and ~200 KB as JPEG q80. Because the
    extension is referenced from slide rels and [Content_Types].xml, a format
    switch is returned to the caller so it can rewrite those references.
    """
    ext = name.rsplit(".", 1)[-1].lower()
    if ext in ("svg", "emf", "wmf", "gif", "wdp"):
        return data, name
    try:
        im = Image.open(io.BytesIO(data))
    except Exception:
        return data, name

    w, h = im.size
    if max(w, h) <= max_edge and len(data) < 400 * 1024:
        return data, name

    scale = min(1.0, max_edge / max(w, h))
    if scale < 1.0:
        im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)

    alpha = False
    if im.mode in ("RGBA", "LA"):
        alpha = im.getchannel("A").getextrema()[0] < 255
    elif im.mode == "P" and "transparency" in im.info:
        alpha = True

    if ext in ("jpg", "jpeg"):
        out = io.BytesIO()
        im.convert("RGB").save(out, "JPEG", quality=quality, optimize=True, progressive=True)
        return (out.getvalue(), name) if out.tell() < len(data) else (data, name)

    if alpha:
        # Genuinely translucent artwork: keep PNG, only resize.
        out = io.BytesIO()
        im.save(out, "PNG", optimize=True)
        return (out.getvalue(), name) if out.tell() < len(data) else (data, name)

    # Opaque raster: try JPEG first — for photos this is a 5-10x win. Only keep
    # PNG re-encode when JPEG is somehow not smaller (flat colour art).
    jout = io.BytesIO()
    im.convert("RGB").save(jout, "JPEG", quality=quality, optimize=True, progressive=True)
    if jout.tell() < len(data) * 0.85:
        return jout.getvalue(), name.rsplit(".", 1)[0] + ".jpeg"

    pout = io.BytesIO()
    im.convert("RGB").save(pout, "PNG", optimize=True, compress_level=9)
    return (pout.getvalue(), name) if pout.tell() < len(data) else (data, name)


def slim_pptx(src: str, dst: str, max_edge: int = 1440, quality: int = 80) -> dict:
    stats = {"before": os.path.getsize(src), "fonts": 0, "media": 0, "renamed": 0}
    zin = zipfile.ZipFile(src)

    # Pass 1 — decide media payloads and any extension changes.
    all_names = {os.path.basename(i.filename) for i in zin.infolist()
                 if i.filename.startswith("ppt/media/")}
    media: dict[str, bytes] = {}
    rename: dict[str, str] = {}
    for item in zin.infolist():
        name = item.filename
        if item.is_dir() or not name.startswith("ppt/media/"):
            continue
        data = zin.read(name)
        new_data, new_name = _compress_image(data, name, max_edge, quality)
        if new_name != name and os.path.basename(new_name) in all_names:
            # The deck already ships a part with that name — never alias two
            # different images onto one entry, PowerPoint resolves it by name.
            stem = new_name.rsplit(".", 1)[0]
            new_name = f"{stem}_c.jpeg"
        media[name] = new_data
        if new_name != name:
            rename[name] = new_name
            stats["renamed"] += 1
        if len(new_data) < len(data):
            stats["media"] += 1

    # Pass 2 — write, rewriting every reference to a renamed asset.
    refs = [(os.path.basename(old).encode(), os.path.basename(new).encode())
            for old, new in rename.items()]
    rewritten = 0
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        for item in zin.infolist():
            if item.is_dir():
                continue
            name = item.filename
            if name.startswith("ppt/fonts/"):
                stats["fonts"] += 1
                continue

            if name in media:
                new_name = rename.get(name, name)
                zout.writestr(new_name, media[name])
                continue

            data = zin.read(name)
            if refs and (name.endswith(".xml") or name.endswith(".rels")):
                for old_b, new_b in refs:
                    if old_b in data:
                        data = data.replace(old_b, new_b)
                        rewritten += 1

            if name == "ppt/presentation.xml":
                data = EMBEDDED_FONT_RE.sub(b"", data)
            elif name.endswith(".rels"):
                data = FONT_REL_RE.sub(b"", data)
            elif name == "[Content_Types].xml":
                data = FONT_OVERRIDE_RE.sub(b"", data)
                if b'Extension="jpeg"' not in data and b'Extension="jpg"' not in data:
                    data = data.replace(
                        b"</Types>",
                        b'<Default Extension="jpeg" ContentType="image/jpeg"/></Types>',
                    )
            zout.writestr(item, data)
    zin.close()
    stats["after"] = os.path.getsize(dst)
    stats["refs_rewritten"] = rewritten
    return stats


# --------------------------------------------------------------------------
# layout profiling
# --------------------------------------------------------------------------
def _font(slot: dict) -> float:
    return float((slot.get("text_metrics") or {}).get("font_size_px") or 0)


def _text(slot: dict) -> str:
    return (slot.get("text") or "").strip()


def classify(slide: dict) -> str:
    """Infer a human-meaningful layout label from slot geometry and type scale."""
    slots = slide.get("slots") or []
    role = slide.get("page_type") or ""
    if role.startswith("cover"):
        return "cover"
    if role.startswith("toc"):
        return "toc"
    if role.startswith("ending"):
        return "ending"

    sizes = [s for s in (_font(x) for x in slots) if s]
    max_px = max(sizes) if sizes else 0
    filled = [x for x in slots if _text(x)]

    if max_px >= 90 and len(filled) <= 6:
        return "chapter-divider"

    numbered = sum(1 for x in filled if NUMBERED_RE.match(_text(x)))
    if numbered >= 3:
        return "numbered-cards"
    if len(filled) >= 12:
        return "multi-block"
    if len(filled) >= 8:
        return "list"
    if len(filled) <= 6:
        bodies = [x for x in filled if x.get("role") == "body_candidate"]
        return "two-block" if len(bodies) >= 2 else "hero-statement"
    return "content"


def build_index(library_path: str, deck_id: str) -> dict:
    lib = json.load(open(library_path, encoding="utf-8"))
    pages = []
    for s in lib.get("slides", []):
        slots = s.get("slots") or []
        sizes = [round(_font(x)) for x in slots if _font(x)]
        filled = [x for x in slots if _text(x)]
        pages.append({
            "slide": s.get("slide_index"),
            "role": s.get("page_type"),
            "layout": classify(s),
            "slot_count": len(slots),
            "filled_slot_count": len(filled),
            "type_scale_px": sorted(set(sizes), reverse=True)[:5],
            "tables": len(s.get("tables") or []),
            "charts": len(s.get("charts") or []),
            "summary": (s.get("text_summary") or "").replace("\n", " ")[:60],
        })
    return {
        "deck_id": deck_id,
        "source": "source.pptx",
        "canvas_px": lib.get("canvas_px"),
        "slide_count": lib.get("slide_count"),
        "layout_kinds": sorted({p["layout"] for p in pages}),
        "pages": pages,
    }


def ingest_one(src: str, deck_id: str, out_root: str) -> dict:
    deck_dir = os.path.join(out_root, deck_id)
    os.makedirs(deck_dir, exist_ok=True)

    slim_path = os.path.join(deck_dir, "source.pptx")
    stats = slim_pptx(src, slim_path)

    tmp = os.path.join(deck_dir, "_intake")
    os.makedirs(tmp, exist_ok=True)
    r = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "pptx_intake.py"), slim_path, "-o", tmp],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"intake failed: {r.stderr[-300:]}")

    libs = [f for f in os.listdir(tmp) if f.endswith(".slide_library.json")]
    if not libs:
        raise RuntimeError("no slide_library.json produced")
    index = build_index(os.path.join(tmp, libs[0]), deck_id)
    with open(os.path.join(deck_dir, "layout_index.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # Keep the full slot-level library too: `check-plan` and manual plan
    # authoring need every slot id, not just the summary in layout_index.json.
    shutil.copy2(os.path.join(tmp, libs[0]), os.path.join(deck_dir, "source.slide_library.json"))
    shutil.rmtree(tmp, ignore_errors=True)

    stats.update({
        "deck_id": deck_id,
        "pages": index["slide_count"],
        "layout_kinds": index["layout_kinds"],
    })
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="A .pptx file, or a directory to scan")
    ap.add_argument("--deck-id", help="Target deck id (required for a single file)")
    ap.add_argument("--out", default=DECKS_DIR, help="Deck library root")
    ap.add_argument("--auto-map", help="JSON: {filename_substring: deck_id}")
    a = ap.parse_args()

    jobs = []
    if os.path.isfile(a.source):
        if not a.deck_id:
            raise SystemExit("--deck-id is required when ingesting a single file")
        jobs.append((a.source, a.deck_id))
    else:
        mapping = json.load(open(a.auto_map, encoding="utf-8")) if a.auto_map else {}
        for root, _dirs, files in os.walk(a.source):
            for fn in sorted(files):
                if not fn.lower().endswith(".pptx"):
                    continue
                deck_id = next((v for k, v in mapping.items() if k in fn), None)
                if deck_id:
                    jobs.append((os.path.join(root, fn), deck_id))
                else:
                    print(f"  skip (no mapping): {fn}")

    total_before = total_after = 0
    for src, deck_id in jobs:
        try:
            s = ingest_one(src, deck_id, a.out)
        except Exception as exc:
            print(f"  FAIL {deck_id}: {exc}")
            continue
        total_before += s["before"]
        total_after += s["after"]
        print(f"  {deck_id:26s} {s['before']/1024/1024:6.1f} -> {s['after']/1024/1024:5.1f} MB  "
              f"{s['pages']:>2} 页  {len(s['layout_kinds'])} 种版式  {s['layout_kinds']}")

    if jobs:
        print(f"\n合计 {total_before/1024/1024:.0f} MB -> {total_after/1024/1024:.0f} MB "
              f"({len(jobs)} 套)")


if __name__ == "__main__":
    main()
