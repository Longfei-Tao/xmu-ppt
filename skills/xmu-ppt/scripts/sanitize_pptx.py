"""PPTX 净化：移除音乐/音频元素与自动翻页设置，保留版式与视觉样式。

设计原则（对应「仅保留模板最原始的版式、页面布局、样式和内容结构」）
------------------------------------------------------------------
* 只删「音乐相关」和「自动换页相关」的东西，不做整树重序列化，
  其余 XML 字节保持原样 —— 图片、图形、装饰、占位区、文本、母版、备注一律不动。
* 切换动画（淡入、擦除等）属于视觉样式，保留；只去掉 advTm 自动换片时间。
* 音频喇叭图标本身是页面上的一个图片框：保留这个图片框（版式不变），
  只删掉它的音频引用与媒体播放动作，让它变成不会发声的静态图形。
* 音频部件、指向音频的关系、[Content_Types].xml 里的音频声明同步清理，
  保证 PPTX 包内不再有悬空引用。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

AUDIO_EXT = {"mp3", "wav", "wma", "m4a", "mid", "midi", "aac", "aiff", "au", "wav"}
AUDIO_TYPE_RE = re.compile(
    r'<Relationship\b[^>]*\bType="[^"]*/(?:audio|media)"[^>]*/>', re.I
)
AUDIO_DEFAULT_RE = re.compile(
    r'<Default\b[^>]*\bExtension="(?:' + "|".join(sorted(AUDIO_EXT)) + r')"[^>]*/>', re.I
)
AUDIO_PART_RE = re.compile(r"\.(?:" + "|".join(sorted(AUDIO_EXT)) + r")$", re.I)

# 音乐节点：timing 里的循环播放控制
P_AUDIO_BLOCK_RE = re.compile(r"<p:audio\b[^>]*>.*?</p:audio>", re.S)
P_AUDIO_SELF_RE = re.compile(r"<p:audio\b[^>]*/>")
A_AUDIO_FILE_RE = re.compile(r"<a:audioFile\b[^>]*/>")
P14_MEDIA_EXT_RE = re.compile(
    r"<p:ext\b[^>]*>\s*<p14:media\b[^>]*/>\s*</p:ext>", re.S
)
P14_MEDIA_RE = re.compile(r"<p14:media\b[^>]*/>")
MEDIA_HLINK_RE = re.compile(r"<a:hlinkClick\b[^>]*ppaction://media[^>]*/>", re.I)
MEDIA_CMD_RE = re.compile(r"<p:cmd\b[^>]*cmd=\"(?:play|stop)Media\"[^>]*>.*?</p:cmd>", re.S)
MEDIA_CMD_SELF_RE = re.compile(r"<p:cmd\b[^>]*cmd=\"(?:play|stop)Media\"[^>]*/>", re.S)

ADV_TM_RE = re.compile(r'\s*advTm="\d+"')
ADV_CLICK0_RE = re.compile(r'\s*advClick="0"')
SHOW_TIMINGS_RE = re.compile(r'\s+(?:useTimings|loop)="1"')

XML_PARTS_RE = re.compile(r"ppt/(?:slides|slideLayouts|slideMasters|notesSlides|notesMasters)/[^/]+\.xml$")


def is_audio_part(name: str) -> bool:
    return name.startswith("ppt/media/") and bool(AUDIO_PART_RE.search(name))


def scan(path: Path) -> dict:
    """只读体检：列出音乐与自动翻页的数量。"""
    result = {
        "audio_parts": 0, "audio_relationships": 0, "audio_refs": 0,
        "media_actions": 0, "auto_advance": 0, "forced_auto": 0,
        "show_timings": 0,
    }
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if is_audio_part(name):
                result["audio_parts"] += 1
                continue
            if not (name.endswith(".xml") or name.endswith(".rels")):
                continue
            text = zf.read(name).decode("utf-8", "replace")
            if name.endswith(".rels"):
                result["audio_relationships"] += len(AUDIO_TYPE_RE.findall(text))
            if name == "[Content_Types].xml":
                continue
            result["audio_refs"] += (
                len(P_AUDIO_BLOCK_RE.findall(text)) + len(P_AUDIO_SELF_RE.findall(text))
                + len(A_AUDIO_FILE_RE.findall(text)) + len(P14_MEDIA_RE.findall(text))
            )
            result["media_actions"] += (
                len(MEDIA_HLINK_RE.findall(text)) + len(MEDIA_CMD_RE.findall(text))
                + len(MEDIA_CMD_SELF_RE.findall(text))
            )
            result["auto_advance"] += len(ADV_TM_RE.findall(text))
            result["forced_auto"] += len(ADV_CLICK0_RE.findall(text))
            if name == "ppt/presentation.xml":
                result["show_timings"] += len(SHOW_TIMINGS_RE.findall(text))
    result["clean"] = not any(
        result[k] for k in result if k != "clean"
    )
    return result


def clean_text(name: str, text: str, stats: dict) -> str:
    """对单个 XML/rels 部件做字符串级清理，不重序列化 XML 树。"""
    original = text

    if name.endswith(".rels"):
        text, n = AUDIO_TYPE_RE.subn("", text)
        stats["audio_relationships"] += n
        return text

    if name == "[Content_Types].xml":
        text, n = AUDIO_DEFAULT_RE.subn("", text)
        stats["audio_defaults"] += n
        return text

    # 音乐播放节点与引用
    text, n = P_AUDIO_BLOCK_RE.subn("", text); stats["audio_nodes"] += n
    text, n = P_AUDIO_SELF_RE.subn("", text); stats["audio_nodes"] += n
    text, n = A_AUDIO_FILE_RE.subn("", text); stats["audio_refs"] += n
    text, n = P14_MEDIA_EXT_RE.subn("", text); stats["media_ext"] += n
    text, n = P14_MEDIA_RE.subn("", text); stats["media_refs"] += n
    text, n = MEDIA_HLINK_RE.subn("", text); stats["media_actions"] += n
    text, n = MEDIA_CMD_RE.subn("", text); stats["media_actions"] += n
    text, n = MEDIA_CMD_SELF_RE.subn("", text); stats["media_actions"] += n

    # 自动翻页：去掉按时间换片，保留点击换片与切换动画
    text, n = ADV_TM_RE.subn("", text); stats["auto_advance"] += n
    text, n = ADV_CLICK0_RE.subn(' advClick="1"', text); stats["forced_auto"] += n
    # useTimings / loop 只作用于放映设置，避免误删动画序列里的同名属性
    if name == "ppt/presentation.xml":
        text, n = SHOW_TIMINGS_RE.subn("", text); stats["show_timings"] += n

    if text != original:
        stats["parts_changed"] += 1
    return text


def sanitize(source: Path, output: Path, *, in_place: bool = False) -> dict:
    """生成净化后的 PPTX。in_place=True 时先写临时文件再原子替换源文件。"""
    # 已经干净且是就地处理时，绝不重写 zip —— 避免无谓改动二进制字节
    before = scan(source)
    if before["clean"] and in_place:
        return {
            "source": str(source), "output": str(source),
            "unchanged": True, "ok": True, "after": before,
        }
    stats = {
        "source": str(source), "output": str(output),
        "audio_parts": 0, "audio_relationships": 0, "audio_defaults": 0,
        "audio_nodes": 0, "audio_refs": 0, "media_ext": 0, "media_refs": 0,
        "media_actions": 0, "auto_advance": 0, "forced_auto": 0,
        "show_timings": 0, "parts_changed": 0,
    }
    target = output
    if in_place:
        fd, tmp = tempfile.mkstemp(prefix=".sanitize-", suffix=".pptx", dir=source.parent)
        os.close(fd)
        target = Path(tmp)

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(source) as zin, zipfile.ZipFile(target, "w") as zout:
            for info in zin.infolist():
                name = info.filename
                if info.is_dir():
                    zout.writestr(info, b"")
                    continue
                if is_audio_part(name):
                    stats["audio_parts"] += 1
                    continue
                data = zin.read(name)
                if name.endswith(".xml") or name.endswith(".rels"):
                    data = clean_text(name, data.decode("utf-8"), stats).encode("utf-8")
                zout.writestr(info, data)
        if in_place:
            os.replace(target, source)
            stats["output"] = str(source)
    finally:
        if in_place and target.exists() and target != output:
            target.unlink(missing_ok=True)

    after = scan(Path(stats["output"]))
    stats["after"] = after
    stats["ok"] = after["clean"]
    return stats


def _blank_stats() -> dict:
    return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    chk = sub.add_parser("check", help="只读体检一个 PPTX")
    chk.add_argument("pptx")

    cln = sub.add_parser("clean", help="净化到新文件（不改原件）")
    cln.add_argument("source")
    cln.add_argument("output")

    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            print(json.dumps(scan(Path(args.pptx)), ensure_ascii=False, indent=2))
            return 0
        if args.command == "clean":
            result = sanitize(Path(args.source), Path(args.output))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 1
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"Error: {exc}", file=__import__("sys").stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
