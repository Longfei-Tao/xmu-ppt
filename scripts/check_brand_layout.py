#!/usr/bin/env python3
"""Validate the brand layer and layout layer of the built-in decks.

Read-only. Exit code 1 means the two layers disagree with the catalogue:
a missing brand binding, a colour that is not #RRGGBB, a primary colour that
drifted from ``decks_index.json``, a logo whose hash differs from the brand
preset, or a page role/layout outside the documented vocabulary.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "xmu-ppt" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import brand  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="品牌层与版式层自检")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--deck", help="只看某套模板的品牌摘要")
    args = parser.parse_args(argv)

    if args.deck:
        print(json.dumps(brand.describe(args.deck), ensure_ascii=False, indent=2))
        return 0

    problems = brand.validate_repo()
    result = {
        "ok": not problems,
        "problems": problems,
        "stats": {
            "brands": len(brand.brand_index()),
            "decks": sum(1 for p in brand.DECKS.iterdir() if p.is_dir()),
        },
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"brands={result['stats']['brands']} decks={result['stats']['decks']}")
        for item in problems:
            print("ERROR", item)
        print("OK" if result["ok"] else "FAILED")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
