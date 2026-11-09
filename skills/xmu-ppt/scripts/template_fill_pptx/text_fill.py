"""apply: replace text inside cloned slide shapes while keeping frames editable.

``_set_container_text`` is the shared text-writing primitive and is also reused
by ``table_fill`` for table-cell edits.
"""

from __future__ import annotations

import copy
from typing import Any
from xml.etree import ElementTree as ET

from .ooxml import NS, _qn, _shape_identity, _text_containers
from .selectors import _replacement_text


def _shape_key_maps(slide_root: ET.Element, source_slide: int) -> dict[str, ET.Element]:
    maps: dict[str, ET.Element] = {}
    for order, container in enumerate(_text_containers(slide_root), start=1):
        shape_id, shape_name = _shape_identity(container, order)
        maps[f"slot_id:s{source_slide:02d}_sh{shape_id}"] = container
        maps[f"shape_id:{shape_id}"] = container
        if shape_name:
            maps[f"shape_name:{shape_name}"] = container
    return maps


def _ensure_text_nodes(container: ET.Element) -> list[ET.Element]:
    text_nodes = container.findall(".//a:t", NS)
    if text_nodes:
        return text_nodes
    tx_body = container.find(".//p:txBody", NS)
    if tx_body is None:
        tx_body = container.find(".//a:txBody", NS)
    if tx_body is None:
        return []
    paragraph = tx_body.find("a:p", NS)
    if paragraph is None:
        paragraph = ET.SubElement(tx_body, _qn(NS["a"], "p"))
    run = paragraph.find("a:r", NS)
    if run is None:
        run = ET.Element(_qn(NS["a"], "r"))
        end_marker = paragraph.find("a:endParaRPr", NS)
        if end_marker is not None:
            paragraph.insert(list(paragraph).index(end_marker), run)
        else:
            paragraph.append(run)
    text_node = run.find("a:t", NS)
    if text_node is None:
        text_node = ET.SubElement(run, _qn(NS["a"], "t"))
    return [text_node]


def _ensure_paragraph_text_node(paragraph: ET.Element) -> list[ET.Element]:
    text_nodes = paragraph.findall(".//a:t", NS)
    if text_nodes:
        return text_nodes
    run = paragraph.find("a:r", NS)
    if run is None:
        run = ET.Element(_qn(NS["a"], "r"))
        end_marker = paragraph.find("a:endParaRPr", NS)
        if end_marker is not None:
            paragraph.insert(list(paragraph).index(end_marker), run)
        else:
            paragraph.append(run)
    text_node = run.find("a:t", NS)
    if text_node is None:
        text_node = ET.SubElement(run, _qn(NS["a"], "t"))
    return [text_node]


def _set_solid_color(run_props: ET.Element, color: str) -> None:
    """给 run 设置纯色文字（只改颜色，保留字号与字重）。"""
    value = color.lstrip("#").upper()
    solid = run_props.find("a:solidFill", NS)
    if solid is None:
        solid = ET.Element(_qn(NS["a"], "solidFill"))
        line = run_props.find("a:ln", NS)
        index = list(run_props).index(line) + 1 if line is not None else 0
        run_props.insert(index, solid)
    for child in list(solid):
        solid.remove(child)
    clr = ET.SubElement(solid, _qn(NS["a"], "srgbClr"))
    clr.set("val", value)


def _set_paragraph_text(
    paragraph: ET.Element,
    text: str,
    fallback_rpr: ET.Element | None = None,
    color: str | None = None,
) -> None:
    lines = text.split("\n")
    if len(lines) > 1:
        _set_paragraph_lines(paragraph, lines, fallback_rpr, color)
        return
    text_nodes = _ensure_paragraph_text_node(paragraph)
    text_nodes[0].text = text
    for node in text_nodes[1:]:
        node.text = ""
    if color:
        run = paragraph.find("a:r", NS)
        if run is not None:
            run_props = run.find("a:rPr", NS)
            if run_props is None:
                run_props = ET.Element(_qn(NS["a"], "rPr"))
                run.insert(0, run_props)
            _set_solid_color(run_props, color)


def _set_paragraph_lines(
    paragraph: ET.Element,
    lines: list[str],
    fallback_rpr: ET.Element | None = None,
    color: str | None = None,
) -> None:
    """把一个段落写成多行：行间插入 <a:br/>，并复用首个 run 的字体设置。

    PowerPoint 不认 ``<a:t>`` 里的 ``\\n``，必须用 ``<a:br/>`` 才是真换行。
    段落本身没有 run 时（模板里的空段落），退回同形状首个 run 的格式，
    否则新增的行会掉成默认黑色，与同页其它行不一致。
    """
    runs = paragraph.findall("a:r", NS)
    run_props = None
    if runs:
        run_props = runs[0].find("a:rPr", NS)
    if run_props is None and fallback_rpr is not None:
        run_props = fallback_rpr
    end_props = paragraph.find("a:endParaRPr", NS)
    for child in list(paragraph):
        if child.tag in (_qn(NS["a"], "r"), _qn(NS["a"], "br"), _qn(NS["a"], "endParaRPr")):
            paragraph.remove(child)
    for index, line in enumerate(lines):
        if index:
            paragraph.append(ET.Element(_qn(NS["a"], "br")))
        run = ET.SubElement(paragraph, _qn(NS["a"], "r"))
        if run_props is not None:
            props = copy.deepcopy(run_props)
            if color:
                _set_solid_color(props, color)
            run.append(props)
        elif color:
            props = ET.Element(_qn(NS["a"], "rPr"))
            _set_solid_color(props, color)
            run.append(props)
        node = ET.SubElement(run, _qn(NS["a"], "t"))
        if line != line.strip():
            node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        node.text = line
    if end_props is not None:
        paragraph.append(end_props)


def _color_all_runs(container: ET.Element, color: str) -> None:
    for run in container.iter(_qn(NS["a"], "r")):
        props = run.find("a:rPr", NS)
        if props is None:
            props = ET.Element(_qn(NS["a"], "rPr"))
            run.insert(0, props)
        _set_solid_color(props, color)


def _set_container_text(container: ET.Element, text: str, color: str | None = None) -> None:
    lines = text.splitlines() or [""]
    paragraphs = container.findall(".//a:p", NS)
    fallback_rpr = container.find(".//a:r/a:rPr", NS)
    if len(lines) > 1 and paragraphs:
        for index, paragraph in enumerate(paragraphs):
            if index < len(lines):
                _set_paragraph_text(paragraph, lines[index], fallback_rpr, color)
            else:
                _set_paragraph_text(paragraph, "")
        if len(lines) > len(paragraphs):
            _set_paragraph_text(
                paragraphs[-1], "\n".join(lines[len(paragraphs) - 1 :]), fallback_rpr, color
            )
        return

    text_nodes = _ensure_text_nodes(container)
    if not text_nodes:
        raise RuntimeError("Matched shape does not contain a text body")
    if len(lines) <= len(text_nodes):
        for index, node in enumerate(text_nodes):
            node.text = lines[index] if index < len(lines) else ""
        if color:
            _color_all_runs(container, color)
        return
    text_nodes[0].text = text
    for node in text_nodes[1:]:
        node.text = ""
    if color:
        _color_all_runs(container, color)


def _apply_replacements_to_slide(
    slide_root: ET.Element,
    *,
    source_slide: int,
    replacements: list[dict[str, Any]],
) -> None:
    maps = _shape_key_maps(slide_root, source_slide)
    errors: list[str] = []
    for replacement in replacements:
        selectors = []
        if replacement.get("slot_id"):
            selectors.append(f"slot_id:{replacement['slot_id']}")
        if replacement.get("shape_id"):
            selectors.append(f"shape_id:{replacement['shape_id']}")
        if replacement.get("shape_name"):
            selectors.append(f"shape_name:{replacement['shape_name']}")
        container = next((maps[key] for key in selectors if key in maps), None)
        if container is None:
            if replacement.get("optional"):
                continue
            errors.append(", ".join(selectors) or "<missing selector>")
            continue
        _set_container_text(
            container,
            _replacement_text(replacement),
            (replacement.get("color") or None),
        )
    if errors:
        raise RuntimeError(f"Missing replacement target(s) on slide {source_slide}: {'; '.join(errors)}")
