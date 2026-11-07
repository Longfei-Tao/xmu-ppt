"""模板固定序号注册表：项目编号的唯一权威来源。

规则（对应使用者要求）
----------------------
1. 序号是三位数字字符串（001、002、…），每个模板有且只有一个固定序号；
2. 序号一经分配永不变更，不重排、不复用；
3. 新增模板只在末尾依次追加，取 next_number 后递增；
4. 被去重隐藏的模板仍占着原序号，标记为 hidden，序号永不回收；
5. 纯数字输入（如 004）一律按序号解析，绝不当作模板 ID（避免 004 ↔ MED-004 混淆）。

注册表只存脱敏后的展示名与相对路径哈希，不含真实文件名或个人名称。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path

EXTERNAL = Path(__file__).resolve().parents[1] / "templates" / "external"
DECKS = Path(__file__).resolve().parents[1] / "templates" / "decks"
REGISTRY_FILE = EXTERNAL / "number_registry.json"
SOURCE_MAP_FILE = EXTERNAL / "source_map.local.json"
BUILTIN_CATALOG = DECKS / "catalog.json"
EXTERNAL_CATALOG = EXTERNAL / "external_catalog.json"
DUP_FILE = EXTERNAL / "duplicates.json"

SCHEMA = "template_number_registry.v1"
RULE = (
    "序号为三位数字字符串，是模板的唯一权威标识；一经分配永不变更。"
    "新增模板只在末尾依次追加，不重排、不复用、不回收（含 hidden 占用的序号）。"
)


def _load(path: Path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise RuntimeError(f"缺少文件：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def serial(number: int) -> str:
    return f"{int(number):03d}"


def source_ref_hash(relative_path: str) -> str:
    return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:12]


def ensure_registry() -> dict:
    """注册表不存在时，按现有 catalog 原样固化（不改变任何现有序号）。"""
    if REGISTRY_FILE.exists():
        return _load(REGISTRY_FILE)

    hidden = {
        g["remove"] for g in _load(DUP_FILE, {"groups": []}).get("groups", [])
    }
    by_key = {}
    mapping = (_load(SOURCE_MAP_FILE, {}) or {}).get("paths", {})
    for key, rel in mapping.items():
        by_key[source_ref_hash(rel)] = key

    entries = []
    for deck in _load(BUILTIN_CATALOG):
        entries.append({
            "number": int(deck["number"]),
            "serial": serial(deck["number"]),
            "template_id": deck["id"],
            "name": deck["name"],
            "namespace": "builtin",
            "source_key": None,
            "source_ref_hash": None,
            "status": "active",
        })
    for item in _load(EXTERNAL_CATALOG)["templates"]:
        entries.append({
            "number": int(item["number"]),
            "serial": serial(item["number"]),
            "template_id": item["id"],
            "name": item["name"],
            "namespace": "external",
            "source_key": item["source_key"],
            "source_ref_hash": None,
            "status": "hidden" if item["id"] in hidden else "active",
        })
    entries.sort(key=lambda e: e["number"])

    # 补上相对路径哈希作为稳定身份键（不入库真实路径）
    for entry in entries:
        rel = mapping.get(entry["source_key"])
        if rel:
            entry["source_ref_hash"] = source_ref_hash(rel)

    max_number = max(e["number"] for e in entries)
    registry = {
        "schema": SCHEMA,
        "generated_on": date.today().isoformat(),
        "rule": RULE,
        "serial_format": "三位数字，001 起；纯数字输入一律按序号解析",
        "builtin_range": [1, 15],
        "external_range": [16, max_number],
        "next_number": max_number + 1,
        "hidden_numbers": sorted(e["number"] for e in entries if e["status"] == "hidden"),
        "entries": entries,
    }
    _write(REGISTRY_FILE, registry)
    return registry


def validate(registry: dict) -> list[str]:
    """检查唯一性、连续占用、next_number 正确。"""
    errors: list[str] = []
    numbers = [e["number"] for e in registry["entries"]]
    if len(numbers) != len(set(numbers)):
        dup = [n for n in numbers if numbers.count(n) > 1]
        errors.append(f"序号重复：{sorted(set(dup))}")
    ids = [e["template_id"] for e in registry["entries"]]
    if len(ids) != len(set(ids)):
        errors.append("模板 ID 重复，无法保证一序号一模板")
    for entry in registry["entries"]:
        if entry["serial"] != serial(entry["number"]):
            errors.append(f"序号 {entry['number']} 的三位写法不一致：{entry['serial']}")
    expected_next = max(numbers) + 1
    if registry["next_number"] != expected_next:
        errors.append(f"next_number 应为 {expected_next}，实际 {registry['next_number']}")
    return errors


def by_serial(registry: dict, value: str) -> dict | None:
    """按序号解析：支持 004 / 4 / 0016 / 216。"""
    text = str(value).strip()
    if not re.fullmatch(r"\d{1,4}", text):
        return None
    number = int(text)
    return next((e for e in registry["entries"] if e["number"] == number), None)


def by_id(registry: dict, template_id: str) -> dict | None:
    return next((e for e in registry["entries"] if e["template_id"] == template_id), None)


def lookup(registry: dict, value: str) -> dict:
    """权威解析入口：纯数字按序号，其余按模板 ID。"""
    if re.fullmatch(r"\d{1,4}", str(value).strip()):
        hit = by_serial(registry, value)
        if hit is None:
            raise RuntimeError(
                f"序号 {serial(int(value))} 不存在。可用范围 001–{serial(max(e['number'] for e in registry['entries']))}；"
                "新增模板会在末尾追加，不会复用或重排已有序号。"
            )
        return hit
    hit = by_id(registry, value)
    if hit is None:
        raise RuntimeError(f"模板 ID 不存在：{value}（若你想按序号选择，请直接输入三位数字，如 004）")
    return hit


def allocate_numbers(registry: dict, candidates: list[dict]) -> tuple[list[dict], int]:
    """为扫描到的模板分配固定序号：已有身份沿用原序号，新面孔只在末尾追加。

    candidates: [{template_id, name, namespace, source_ref_hash, source_key}]
    返回 (补齐 number/serial 后的列表, 新增数量)。不重排、不复用。
    """
    by_hash = {e["source_ref_hash"]: e for e in registry["entries"] if e.get("source_ref_hash")}
    by_template_id = {e["template_id"]: e for e in registry["entries"]}
    next_number = registry["next_number"]
    added = 0
    result = []
    for item in candidates:
        hit = by_hash.get(item.get("source_ref_hash")) or by_template_id.get(item["template_id"])
        if hit:
            result.append({**item, "number": hit["number"], "serial": hit["serial"]})
            continue
        number = next_number
        next_number += 1
        added += 1
        entry = {
            "number": number,
            "serial": serial(number),
            "template_id": item["template_id"],
            "name": item.get("name", ""),
            "namespace": item.get("namespace", "external"),
            "source_key": None,
            "source_ref_hash": item.get("source_ref_hash"),
            "status": "active",
        }
        registry["entries"].append(entry)
        result.append({**item, "number": number, "serial": serial(number)})
        by_hash[entry["source_ref_hash"]] = entry
        by_template_id[entry["template_id"]] = entry
    if added:
        registry["entries"].sort(key=lambda e: e["number"])
        registry["next_number"] = next_number
        registry["external_range"][1] = max(e["number"] for e in registry["entries"])
        _write(REGISTRY_FILE, registry)
    result.sort(key=lambda x: x["number"])
    return result, added


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="按现有 catalog 固化注册表")
    sub.add_parser("check", help="校验唯一性与追加规则")
    sub.add_parser("list", help="列出全部序号与模板对应关系")
    q = sub.add_parser("resolve", help="按序号或模板 ID 解析")
    q.add_argument("value")
    args = parser.parse_args()
    registry = ensure_registry()
    if args.command == "init":
        print(f"注册表已固化：{REGISTRY_FILE} | 共 {len(registry['entries'])} 条 | next={registry['next_number']:03d}")
    elif args.command == "check":
        errors = validate(registry)
        print(json.dumps({
            "ok": not errors, "errors": errors,
            "total": len(registry["entries"]),
            "next_number": registry["next_number"],
            "hidden_numbers": registry["hidden_numbers"],
        }, ensure_ascii=False, indent=2))
        return 0 if not errors else 1
    elif args.command == "list":
        for e in registry["entries"]:
            print(f"{e['serial']}  {e['template_id']:<22} {e['name'][:16]:<18} {e['status']}")
    elif args.command == "resolve":
        hit = lookup(registry, args.value)
        print(json.dumps(hit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
