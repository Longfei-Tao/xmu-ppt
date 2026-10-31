"""Check public documentation links, heading anchors and local image files.

Offline: external URLs are not requested. Run from any directory.
"""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def heading_ids(text):
    counts = {}
    result = set()
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, re.M):
        heading = re.sub(r"[*`_\[\]]", "", heading).lower()
        slug = re.sub(r"[^\w\-\s]", "", heading).replace(" ", "-")
        index = counts.get(slug, 0)
        result.add(slug + (f"-{index}" if index else ""))
        counts[slug] = index + 1
    return result


def check():
    paths = [ROOT / n for n in ("README.md", "README.en.md", "CONTRIBUTING.md",
                                "CREDITS.md", "THIRD_PARTY_NOTICES.md")]
    paths += sorted((ROOT / "docs").rglob("*.md"))
    paths.append(ROOT / "examples/quickstart/README.md")
    errors = []
    links = 0
    images = set()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"^```.*?^```\s*$", "", text, flags=re.M | re.S)
        for image_mark, dest in re.findall(r"(!?)\[[^\]]*\]\(([^)]+)\)", text):
            dest = dest.strip().strip("<>")
            parts = urlsplit(dest)
            if parts.scheme or parts.netloc:
                continue
            links += 1
            target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
            if not target.is_relative_to(ROOT) or not target.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing or external local target {dest}")
            elif parts.fragment and target.suffix.lower() == ".md":
                if unquote(parts.fragment) not in heading_ids(target.read_text(encoding="utf-8")):
                    errors.append(f"{path.relative_to(ROOT)}: missing heading {dest}")
            elif (image_mark or target.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}) and target.is_file():
                images.add(target)
    for path in images:
        try:
            with Image.open(path) as img:
                img.verify()
        except OSError as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid image: {exc}")
    return {"documents": len(paths), "local_links": links, "images": len(images), "errors": errors}


if __name__ == "__main__":
    import json
    import sys

    report = check()
    print(json.dumps(report, ensure_ascii=True, indent=2))
    sys.exit(int(bool(report["errors"])))
