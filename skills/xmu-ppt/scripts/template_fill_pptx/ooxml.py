"""Shared OOXML primitives for the template-fill pipeline.

Read-side helpers only: namespaces and content-type constants, part /
relationship resolution, EMU unit conversion, slide-shape discovery, and small
JSON readers / writers. Write-side package plumbing lives in ``package.py``.
"""

from __future__ import annotations

import json
import posixpath
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
P14_NS = "http://schemas.microsoft.com/office/powerpoint/2010/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
C14_NS = "http://schemas.microsoft.com/office/drawing/2007/8/2/chart"
C16_NS = "http://schemas.microsoft.com/office/drawing/2014/chart"
C16R2_NS = "http://schemas.microsoft.com/office/drawing/2015/06/chart"

SLIDE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
NOTES_SLIDE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
CHART_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart"
PACKAGE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/package"
SLIDE_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
NOTES_SLIDE_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"
CHART_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EMU_PER_INCH = 914400
PX_PER_INCH = 96


for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)
ET.register_namespace("", REL_NS)
ET.register_namespace("mc", MC_NS)
ET.register_namespace("c14", C14_NS)
ET.register_namespace("c16", C16_NS)
ET.register_namespace("c16r2", C16R2_NS)
ET.register_namespace("p14", P14_NS)


@dataclass(frozen=True)
class SlideRef:
    """Presentation slide reference resolved from presentation.xml.rels."""

    index: int
    rel_id: str
    target: str
    part_name: str
    rels_name: str


def _qn(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}"


def _read_xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        return ET.fromstring(zf.read(name))
    except KeyError as exc:
        raise RuntimeError(f"Missing required PPTX part: {name}") from exc


def _xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _normalize_part(target: str, base: str = "ppt/presentation.xml") -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    normalized = posixpath.normpath(posixpath.join(posixpath.dirname(base), target))
    return normalized.lstrip("/")


def _rels_name_for_part(part_name: str) -> str:
    parent = posixpath.dirname(part_name)
    basename = posixpath.basename(part_name)
    return posixpath.join(parent, "_rels", f"{basename}.rels")


def _emu_to_px(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return round(int(value) / EMU_PER_INCH * PX_PER_INCH)
    except ValueError:
        return None


def _parse_relationships(zf: zipfile.ZipFile) -> dict[str, dict[str, str]]:
    rels_root = _read_xml(zf, "ppt/_rels/presentation.xml.rels")
    relationships: dict[str, dict[str, str]] = {}
    for rel in rels_root.findall(_qn(REL_NS, "Relationship")):
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        rel_type = rel.attrib.get("Type")
        if rel_id and target and rel_type:
            relationships[rel_id] = {"target": target, "type": rel_type}
    return relationships


def _parse_slide_refs(zf: zipfile.ZipFile) -> list[SlideRef]:
    pres_root = _read_xml(zf, "ppt/presentation.xml")
    relationships = _parse_relationships(zf)
    sld_id_lst = pres_root.find("p:sldIdLst", NS)
    if sld_id_lst is None:
        return []

    slides: list[SlideRef] = []
    for index, sld_id in enumerate(sld_id_lst.findall("p:sldId", NS), start=1):
        rel_id = sld_id.attrib.get(_qn(NS["r"], "id"))
        if not rel_id or rel_id not in relationships:
            continue
        rel = relationships[rel_id]
        if rel["type"] != SLIDE_REL_TYPE:
            continue
        part_name = _normalize_part(rel["target"])
        slides.append(
            SlideRef(
                index=index,
                rel_id=rel_id,
                target=rel["target"],
                part_name=part_name,
                rels_name=_rels_name_for_part(part_name),
            )
        )
    return slides


def _slide_relationships(zf: zipfile.ZipFile, rels_name: str) -> dict[str, dict[str, str]]:
    try:
        rels_root = _read_xml(zf, rels_name)
    except RuntimeError:
        return {}
    relationships: dict[str, dict[str, str]] = {}
    for rel in rels_root.findall(_qn(REL_NS, "Relationship")):
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        rel_type = rel.attrib.get("Type")
        if rel_id and target and rel_type:
            relationships[rel_id] = {"target": target, "type": rel_type}
    return relationships


def _paragraph_texts(container: ET.Element) -> list[str]:
    paragraphs: list[str] = []
    for paragraph in container.findall(".//a:p", NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//a:t", NS)).strip()
        if text:
            paragraphs.append(text)
    if paragraphs:
        return paragraphs
    text = "".join(node.text or "" for node in container.findall(".//a:t", NS)).strip()
    return [text] if text else []


def _container_geometry(container: ET.Element) -> dict[str, int | None]:
    xfrm = container.find("p:spPr/a:xfrm", NS)
    if xfrm is None:
        xfrm = container.find("p:xfrm", NS)
    if xfrm is None:
        xfrm = container.find(".//a:xfrm", NS)
    if xfrm is None:
        return {"x": None, "y": None, "width": None, "height": None}
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    return {
        "x": _emu_to_px(off.attrib.get("x")) if off is not None else None,
        "y": _emu_to_px(off.attrib.get("y")) if off is not None else None,
        "width": _emu_to_px(ext.attrib.get("cx")) if ext is not None else None,
        "height": _emu_to_px(ext.attrib.get("cy")) if ext is not None else None,
    }


def _text_containers(slide_root: ET.Element) -> list[ET.Element]:
    containers: list[ET.Element] = []
    for tag in ("p:sp", "p:graphicFrame"):
        for element in slide_root.findall(f".//{tag}", NS):
            if element.find(".//p:txBody", NS) is not None or element.findall(".//a:t", NS):
                containers.append(element)
    return containers


def _table_containers(slide_root: ET.Element) -> list[ET.Element]:
    return [
        frame
        for frame in slide_root.findall(".//p:graphicFrame", NS)
        if frame.find(".//a:tbl", NS) is not None
    ]


def _chart_containers(slide_root: ET.Element) -> list[ET.Element]:
    return [
        frame
        for frame in slide_root.findall(".//p:graphicFrame", NS)
        if frame.find(".//c:chart", NS) is not None
    ]


def _shape_identity(container: ET.Element, order: int) -> tuple[str, str]:
    c_nv_pr = container.find(".//p:cNvPr", NS)
    shape_id = c_nv_pr.attrib.get("id") if c_nv_pr is not None else str(order)
    shape_name = c_nv_pr.attrib.get("name") if c_nv_pr is not None else ""
    return shape_id, shape_name


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON: {path}: {exc}") from exc


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Absolute geometry resolution
#
# Two OOXML cases make ``_container_geometry`` report the wrong rectangle or
# nothing at all:
#
# 1. Shapes nested inside ``p:grpSp`` store a *child* coordinate system. The
#    child xfrm must be mapped through every enclosing group
#    (off/chOff/ext/chExt) before it means anything on the slide.
# 2. Placeholders with no xfrm of their own inherit their rectangle from the
#    slide layout, and failing that from the slide master.
#
# Both are resolved here so capacity checks and preview masks use real slide
# coordinates instead of raw child values.
# ---------------------------------------------------------------------------

LAYOUT_REL_TYPE_SUFFIX = "/slideLayout"
MASTER_REL_TYPE_SUFFIX = "/slideMaster"
_SHAPE_TAGS = ("sp", "graphicFrame", "pic", "cxnSp", "grpSp")
_PLACEHOLDER_PATHS = (
    "p:nvSpPr/p:nvPr/p:ph",
    "p:nvGraphicFramePr/p:nvPr/p:ph",
    "p:nvPicPr/p:nvPr/p:ph",
)


def _emu_value(element: ET.Element | None, attrib: str) -> int | None:
    if element is None:
        return None
    raw = element.attrib.get(attrib)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _xfrm_element(container: ET.Element) -> ET.Element | None:
    for path in ("p:spPr/a:xfrm", "p:xfrm", "p:grpSpPr/a:xfrm"):
        xfrm = container.find(path, NS)
        if xfrm is not None:
            return xfrm
    return None


def _xfrm_rect(xfrm: ET.Element) -> dict[str, Any]:
    return {
        "x": _emu_value(xfrm.find("a:off", NS), "x"),
        "y": _emu_value(xfrm.find("a:off", NS), "y"),
        "w": _emu_value(xfrm.find("a:ext", NS), "cx"),
        "h": _emu_value(xfrm.find("a:ext", NS), "cy"),
        "cx": _emu_value(xfrm.find("a:chOff", NS), "x"),
        "cy": _emu_value(xfrm.find("a:chOff", NS), "y"),
        "cw": _emu_value(xfrm.find("a:chExt", NS), "cx"),
        "ch": _emu_value(xfrm.find("a:chExt", NS), "cy"),
        "rot": int(xfrm.attrib.get("rot", 0) or 0),
        "flipH": xfrm.attrib.get("flipH") in ("1", "true"),
        "flipV": xfrm.attrib.get("flipV") in ("1", "true"),
    }


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _resolve_absolute_emu(sp_tree: ET.Element) -> dict[int, dict[str, Any]]:
    """Map every shape inside ``sp_tree`` to absolute slide EMU coordinates.

    Keys are ``id(element)``; callers must keep ``sp_tree`` alive (ElementTree
    returns the same object for repeated lookups, so identity is stable).
    """
    found: dict[int, dict[str, Any]] = {}

    def walk(
        node: ET.Element,
        sx: float,
        tx: float,
        sy: float,
        ty: float,
        depth: int,
        path: list[str],
        mirrored: bool,
    ) -> None:
        for child in node:
            tag = _local_name(child)
            if tag not in _SHAPE_TAGS:
                continue
            xfrm = _xfrm_element(child)
            if tag == "grpSp":
                if xfrm is None:
                    walk(child, sx, tx, sy, ty, depth + 1, path, mirrored)
                    continue
                rect = _xfrm_rect(xfrm)
                gx = sx * (rect["x"] or 0) + tx
                gy = sy * (rect["y"] or 0) + ty
                gw = sx * (rect["w"] or 0)
                gh = sy * (rect["h"] or 0)
                cw, ch = rect["cw"], rect["ch"]
                csx = gw / cw if cw else sx
                csy = gh / ch if ch else sy
                ctx = gx - (rect["cx"] or 0) * csx
                cty = gy - (rect["cy"] or 0) * csy
                group_id, _group_name = _shape_identity(child, len(found) + 1)
                walk(
                    child,
                    csx,
                    ctx,
                    csy,
                    cty,
                    depth + 1,
                    path + [group_id],
                    mirrored or rect["flipH"] or rect["flipV"],
                )
                continue
            if xfrm is None:
                continue
            rect = _xfrm_rect(xfrm)
            found[id(child)] = {
                "x": sx * (rect["x"] or 0) + tx,
                "y": sy * (rect["y"] or 0) + ty,
                "width": sx * (rect["w"] or 0),
                "height": sy * (rect["h"] or 0),
                "rotation": rect["rot"],
                "group_depth": depth,
                "group_path": list(path),
                "mirrored": mirrored,
            }

    walk(sp_tree, 1.0, 0.0, 1.0, 0.0, 0, [], False)
    return found


def _related_part(
    zf: zipfile.ZipFile, rels_name: str, base_part: str, type_suffix: str
) -> str | None:
    for rel in _slide_relationships(zf, rels_name).values():
        if rel["type"].endswith(type_suffix):
            return _normalize_part(rel["target"], base_part)
    return None


def _placeholder_of(container: ET.Element) -> ET.Element | None:
    for path in _PLACEHOLDER_PATHS:
        ph = container.find(path, NS)
        if ph is not None:
            return ph
    return None


def _placeholder_match(root: ET.Element, ph: ET.Element) -> ET.Element | None:
    """Find the placeholder on a layout/master that corresponds to ``ph``."""
    want_type = ph.attrib.get("type", "obj")
    want_idx = ph.attrib.get("idx")
    fallback: ET.Element | None = None
    for candidate in root.findall(".//p:sp", NS):
        cand_ph = _placeholder_of(candidate)
        if cand_ph is None:
            continue
        cand_type = cand_ph.attrib.get("type", "obj")
        cand_idx = cand_ph.attrib.get("idx")
        if want_idx is not None and cand_idx == want_idx and cand_type == want_type:
            return candidate
        if cand_type == want_type and fallback is None:
            fallback = candidate
        elif fallback is None and {cand_type, want_type} <= {"title", "ctrTitle"}:
            fallback = candidate
    return fallback


def _inherited_placeholder_rect(
    zf: zipfile.ZipFile, slide_ref: SlideRef, ph: ET.Element
) -> tuple[dict[str, int | None], str] | None:
    layout_part = _related_part(zf, slide_ref.rels_name, slide_ref.part_name, LAYOUT_REL_TYPE_SUFFIX)
    if layout_part:
        layout_root = _read_xml(zf, layout_part)
        match = _placeholder_match(layout_root, ph)
        if match is not None:
            xfrm = _xfrm_element(match)
            if xfrm is not None:
                return _xfrm_rect(xfrm), "slideLayout"
        master_part = _related_part(
            zf, _rels_name_for_part(layout_part), layout_part, MASTER_REL_TYPE_SUFFIX
        )
        if master_part:
            master_root = _read_xml(zf, master_part)
            match = _placeholder_match(master_root, ph)
            if match is not None:
                xfrm = _xfrm_element(match)
                if xfrm is not None:
                    return _xfrm_rect(xfrm), "slideMaster"
    return None


def _emu_rect_to_px(rect: dict[str, Any]) -> dict[str, Any]:
    def to_px(*keys: str) -> int | None:
        for key in keys:
            value = rect.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return round(value / EMU_PER_INCH * PX_PER_INCH)
        return None

    return {
        "x": to_px("x"),
        "y": to_px("y"),
        "width": to_px("width", "w"),
        "height": to_px("height", "h"),
    }


def resolve_slot_geometries(
    zf: zipfile.ZipFile, slide_ref: SlideRef, slide_root: ET.Element
) -> dict[int, dict[str, Any]]:
    """Absolute pixel geometry for every text container on a slide.

    Returns a dict keyed by ``id(container)``. Each value carries
    ``x/y/width/height`` in px plus provenance hints (``group_depth``,
    ``group_path``, ``inherited_from``) so callers can explain where the
    rectangle came from.
    """
    sp_tree = slide_root.find("p:cSld/p:spTree", NS)
    absolute = _resolve_absolute_emu(sp_tree) if sp_tree is not None else {}

    resolved: dict[int, dict[str, Any]] = {}
    for container in _text_containers(slide_root):
        key = id(container)
        raw = absolute.get(key)
        if raw is not None:
            geometry = _emu_rect_to_px(raw)
            geometry.update(
                {
                    "rotation": raw["rotation"],
                    "group_depth": raw["group_depth"],
                    "group_path": raw["group_path"],
                    "mirrored": raw["mirrored"],
                    "inherited_from": None,
                    "source": "group_absolute" if raw["group_depth"] else "shape_xfrm",
                }
            )
            resolved[key] = geometry
            continue
        ph = _placeholder_of(container)
        inherited = _inherited_placeholder_rect(zf, slide_ref, ph) if ph is not None else None
        if inherited is None:
            # Last resort: whatever raw xfrm the shape itself carries. This is
            # wrong for group children but better than reporting nothing.
            fallback = _container_geometry(container)
            fallback.update(
                {
                    "rotation": 0,
                    "group_depth": 0,
                    "group_path": [],
                    "mirrored": False,
                    "inherited_from": None,
                    "source": "raw_xfrm" if fallback.get("width") is not None else "unresolved",
                }
            )
            resolved[key] = fallback
            continue
        rect, origin = inherited
        geometry = _emu_rect_to_px(rect)
        geometry.update(
            {
                "rotation": rect.get("rot", 0),
                "group_depth": 0,
                "group_path": [],
                "mirrored": bool(rect.get("flipH") or rect.get("flipV")),
                "inherited_from": origin,
                "source": "placeholder_inherited",
            }
        )
        resolved[key] = geometry
    return resolved
