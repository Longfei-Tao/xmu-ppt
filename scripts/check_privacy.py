#!/usr/bin/env python3
"""Scan tracked assets for personal data (names, emails, phones, IDs).

Read-only. Covers text files, SVG/HTML text, tracked PPTX slide/notes XML and
``docProps`` author fields. Images are not OCR-scanned; regenerate previews from
scanned decks instead.

Known placeholders (``XXX`` / ``小夏`` / ``甲乙丙``) and public attribution
(``作者：Hugo He``) are allowed. Add private terms without committing them via
``.privacy_terms`` (one per line) or ``XMU_PPT_PRIVACY_TERMS=a,b``.

Exit code 1 when anything is found.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TERMS_FILE = ROOT / ".privacy_terms"

TEXT_SUFFIXES = {".md", ".markdown", ".json", ".jsonl", ".html", ".htm", ".js", ".css",
                 ".py", ".svg", ".txt", ".yml", ".yaml", ".xml"}
SKIP_PARTS = {".git", ".venv", "output", "local-gallery", "node_modules"}
MAX_BYTES = 8 * 1024 * 1024

LABELS = "答辩人|汇报人|作者|指导教师|导师|联系人|汇报组员|组员"
CN_LABEL_RE = re.compile(rf"({LABELS})\s*[:：]\s*([\u4e00-\u9fa5]{{2,4}})")
EN_LABEL_RE = re.compile(rf"({LABELS})\s*[:：]\s*([A-Za-z][A-Za-z .']{{0,20}})")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![0-9A-Fa-f])1[3-9]\d{9}(?![0-9A-Fa-f])")
ID_RE = re.compile(r"(?<![0-9A-Za-z])\d{17}[0-9Xx](?![0-9A-Za-z])")

ALLOWED_CN_NAMES = {
    "小夏", "甲乙丙", "示例", "示例同学", "姓名", "待定", "待填写", "待补充",
    "甲方", "乙方", "丙方", "某某", "张三", "李四", "王五", "无", "略",
}
ALLOWED_EN_NAMES = {"hugohe", "hugo he", "xmu-ppt", "n/a", "na", "none"}
ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org", "example.net", "localhost", "github.com"}
ALLOWED_AUTHORS = {"", "administrator", "admin", "xmu-ppt", "python-pptx", "powerpoint",
                   "microsoft office user", "user"}
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
DC = "{http://purl.org/dc/elements/1.1/}"


def mask(value: str) -> str:
    value = value.strip()
    if len(value) <= 1:
        return "*"
    return value[0] + "*" * (len(value) - 1)


def explicit_terms() -> tuple[str, ...]:
    terms: list[str] = []
    if TERMS_FILE.exists():
        terms += [line.strip() for line in TERMS_FILE.read_text(encoding="utf-8").splitlines()
                  if line.strip() and not line.startswith("#")]
    env = os.environ.get("XMU_PPT_PRIVACY_TERMS", "")
    terms += [t.strip() for t in env.split(",") if t.strip()]
    return tuple(dict.fromkeys(terms))


def scan_text(text: str, source: str, terms: tuple[str, ...]) -> list[dict]:
    findings: list[dict] = []
    flat = re.sub(r"\s+", "", text)

    for match in CN_LABEL_RE.finditer(flat):
        value = match.group(2)
        if value in ALLOWED_CN_NAMES or value.lower().startswith("xxx"):
            continue
        findings.append({"file": source, "kind": "name", "value": mask(value),
                         "context": match.group(1)})

    for match in EN_LABEL_RE.finditer(text):
        value = match.group(2).strip(" .'")
        if value.lower() in ALLOWED_EN_NAMES or value.lower().startswith("xxx"):
            continue
        findings.append({"file": source, "kind": "name", "value": mask(value),
                         "context": match.group(1)})

    for match in EMAIL_RE.finditer(text):
        address = match.group(0)
        if address.rsplit("@", 1)[-1].lower() in ALLOWED_EMAIL_DOMAINS:
            continue
        findings.append({"file": source, "kind": "email", "value": mask(address), "context": "email"})

    for match in PHONE_RE.finditer(text):
        findings.append({"file": source, "kind": "phone", "value": mask(match.group(0)), "context": "phone"})

    for match in ID_RE.finditer(text):
        findings.append({"file": source, "kind": "id", "value": mask(match.group(0)), "context": "id"})

    for term in terms:
        if term and term in text:
            findings.append({"file": source, "kind": "term", "value": mask(term), "context": "explicit"})

    return findings


def scan_plain(path: Path, terms: tuple[str, ...]) -> list[dict]:
    try:
        if path.stat().st_size > MAX_BYTES:
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    suffix = path.suffix.lower()
    if suffix == ".svg":
        try:
            text = " ".join(ET.fromstring(text).itertext())
        except ET.ParseError:
            pass
    elif suffix in {".html", ".htm"}:
        text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    return scan_text(text, path.relative_to(ROOT).as_posix(), terms)


def scan_pptx(path: Path, terms: tuple[str, ...]) -> list[dict]:
    findings: list[dict] = []
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                is_slide = bool(re.fullmatch(r"ppt/slides/slide\d+\.xml", name))
                is_notes = name.startswith("ppt/notesSlides/notesSlide")
                if not (is_slide or is_notes or name == "docProps/core.xml"):
                    continue
                try:
                    root = ET.fromstring(z.read(name))
                except ET.ParseError:
                    continue
                source = f"{path.relative_to(ROOT).as_posix()}:{name}"
                if name == "docProps/core.xml":
                    for tag in (f"{DC}creator", f"{CP}lastModifiedBy"):
                        node = root.find(f".//{tag}")
                        value = (node.text or "").strip() if node is not None else ""
                        if value.lower() not in ALLOWED_AUTHORS:
                            findings.append({"file": source, "kind": "author", "value": mask(value),
                                             "context": tag.split('}')[-1]})
                    text = " ".join(root.itertext())
                else:
                    paragraphs = ["".join(t.text or "" for t in p.iter(A + "t"))
                                  for p in root.iter(A + "p")]
                    text = "\n".join(paragraphs)
                findings += scan_text(text, source, terms)
    except (OSError, zipfile.BadZipFile):
        return []
    return findings


def tracked_files() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True)
    except OSError:
        return []
    if out.returncode != 0:
        return []
    names = out.stdout.decode("utf-8", "replace").split("\0")
    return [ROOT / n for n in names if n]


def check() -> dict:
    terms = explicit_terms()
    findings: list[dict] = []
    scanned = 0
    for path in tracked_files():
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        suffix = path.suffix.lower()
        if suffix == ".pptx":
            findings += scan_pptx(path, terms)
            scanned += 1
        elif suffix in TEXT_SUFFIXES:
            findings += scan_plain(path, terms)
            scanned += 1
    return {
        "ok": not findings,
        "scanned": scanned,
        "terms": len(terms),
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"scanned={result['scanned']} explicit_terms={result['terms']}")
        for item in result["findings"]:
            print(f"FOUND {item['kind']:<6} {item['file']} -> {item['value']}")
        print("OK" if result["ok"] else "FAILED")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
