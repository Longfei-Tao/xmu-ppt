"""idea-to-ppt：把「想法 + 主题定位」变成 PPT 的唯一出稿入口。

流程（与 workflows/idea-to-ppt.md 一致）
----------------------------------------
1. recommend  —— 第一步：只输出「可点模板链接清单」，写入 waiting 状态，**不制作**
2. confirm    —— 用户明确选定模板 ID 后，状态改为 confirmed
3. pages      —— 列出该模板每一页的版式角色，供挑选最合适的页面组合
4. build      —— 门禁校验 → 净化音乐/自动翻页 → 按 plan 克隆模板已有页、只填文字
                 → 内容完整性 / 文字适配 / 模板一致性三项检查 → 交付

硬规则：build 前必须 confirm；页数由 plan 决定，不设固定限制；
只克隆模板已有页面，不自行绘制页面、不改版式与视觉样式。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

SCRIPTS = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPTS.parent
REPO = SKILL_ROOT.parents[1]
sys.path.insert(0, str(SCRIPTS))

from template_fill_pptx.analyzer import analyze_pptx  # noqa: E402
from template_fill_pptx.applier import apply_plan  # noqa: E402
from template_fill_pptx.checker import check_plan  # noqa: E402
import sanitize_pptx  # noqa: E402

EXTERNAL = SKILL_ROOT / "templates" / "external"
CATALOG_FILE = EXTERNAL / "external_catalog.json"
DUP_FILE = EXTERNAL / "duplicates.json"
ROOT_LOCAL_FILE = EXTERNAL / "root.local.json"
SOURCE_MAP_FILE = EXTERNAL / "source_map.local.json"
DECKS = SKILL_ROOT / "templates" / "decks"
BUILTIN_CATALOG = DECKS / "catalog.json"
GALLERY = REPO / "local-gallery" / "index.html"
GATE_FILE = REPO / "output" / ".selection.json"
SANITIZED_DIR = REPO / "output" / "_sanitized"
REPORT_DIR = REPO / "output" / "_checks"

CATEGORY_HINTS = {
    "institution": ["厦大", "厦门大学", "高校", "学校", "答辩", "毕业", "校园", "机构", "官方", "学院"],
    "report": ["汇报", "总结", "报告", "工作", "通用", "数据", "年度", "项目", "商务"],
    "clinical": ["医护", "临床", "医学", "医疗", "医院", "医生", "护士", "疾病", "肿瘤", "癌", "护理", "手术", "健康"],
    "maternal-child": ["妇幼", "母婴", "儿童", "儿科", "卡通", "宣教", "手绘", "温馨", "患者"],
    "tcm-style": ["中医", "国风", "中国风", "中药", "传统", "养生"],
}
PLACEHOLDER_WORDS = [
    "单击此处添加标题", "单击添加标题文字", "YOUR CONPANY NAME", "输入医院名称",
    "请替换文字内容", "从顾客的角度", "此处添加详细文本", "仁心仁术",
    "模板所有页面均有动画", "替换文字内容",
]


def _load(path: Path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise RuntimeError(f"缺少文件：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _gallery_url(template_id: str | None = None, category: str | None = None) -> str:
    base = GALLERY.resolve().as_uri()
    if template_id:
        return base + "#deck=" + quote(template_id, safe="")
    if category:
        return base + "#cat=" + quote(category, safe="")
    return base


def _all_templates() -> list[dict]:
    """合并内置 15 套与外部 200 套，排除画廊已合并的重复副本。"""
    items: list[dict] = []
    removed = {g["remove"] for g in _load(DUP_FILE, {"groups": []}).get("groups", [])}
    for r in _load(CATALOG_FILE)["templates"]:
        if r["id"] in removed:
            continue
        items.append({
            "id": r["id"], "name": r["name"], "style": r.get("style", ""),
            "category": r["primary_category"], "category_name": r["category_name"],
            "pages": r["page_count"], "namespace": "external",
            "tags": r.get("tags", []), "source_key": r.get("source_key"),
        })
    for r in _load(BUILTIN_CATALOG):
        source = DECKS / r["id"] / "source.pptx"
        pages = None
        if source.exists():
            try:
                from pptx import Presentation
                pages = len(Presentation(str(source)).slides)
            except Exception:
                pages = None
        items.append({
            "id": r["id"], "name": r["name"], "style": r.get("style", ""),
            "category": "institution", "category_name": "厦门大学等高校/机构风格",
            "pages": pages, "namespace": "builtin",
            "tags": r.get("tags", []), "source_key": None,
        })
    return items


def resolve_source(template_id: str) -> tuple[dict, Path]:
    for item in _all_templates():
        if item["id"] != template_id:
            continue
        if item["namespace"] == "builtin":
            path = DECKS / template_id / "source.pptx"
        else:
            root = Path(_load(ROOT_LOCAL_FILE)["root"])
            paths = (_load(SOURCE_MAP_FILE, {}) or {}).get("paths", {})
            rel = paths.get(item["source_key"])
            if not rel:
                raise RuntimeError(f"本机映射缺少 {item['source_key']}，请重跑 external_templates.py scan")
            path = root / rel
        if not path.is_file():
            raise RuntimeError(f"模板原件不存在：{path}")
        return item, path
    raise RuntimeError(f"找不到模板：{template_id}")


# ---------------------------------------------------------------------------
# 1. 第一步：候选链接清单（waiting，绝不制作）
# ---------------------------------------------------------------------------

def recommend(idea: str, positioning: str, limit: int = 8) -> dict:
    text = f"{idea} {positioning}"
    scores = {
        cat: sum(1 for word in words if word in text)
        for cat, words in CATEGORY_HINTS.items()
    }
    top_cats = [c for c, s in sorted(scores.items(), key=lambda kv: -kv[1]) if s > 0][:3]
    if not top_cats:
        top_cats = ["report", "clinical", "institution"]
    ranked = {c: 3 - i for i, c in enumerate(top_cats)}
    topic_words = (
        "胃癌", "胃", "术后", "护理", "康复", "随访", "外科", "肿瘤", "癌",
        "手术", "营养", "并发症", "宣教", "患教", "临床", "医护", "医生",
        "护士", "健康", "医疗", "医院", "查房", "病例", "救治", "救护",
    )
    topic_in_query = [w for w in topic_words if w in text]

    def score(item: dict) -> int:
        hay = " ".join([item["name"], item["style"], " ".join(item["tags"])])
        value = ranked.get(item["category"], 0) * 10
        # 用户说到的主题词，出现在模板名称/风格里是最强信号
        value += 6 * sum(1 for word in topic_in_query if word in hay)
        # 模板本身属于医护领域也加分，保证同类里医护模板排在前面
        value += sum(1 for word in topic_words if word in hay)
        if item["pages"] and 10 <= item["pages"] <= 40:
            value += 2
        return value

    pool = sorted(_all_templates(), key=lambda x: (-score(x), x["id"]))
    # 命中分类内按相关度挑满；临床类有 55 套，不需要靠别的分类凑数
    chosen, per_cat = [], {}
    for item in pool:
        cat = item["category"]
        if cat not in top_cats or per_cat.get(cat, 0) >= limit:
            continue
        chosen.append(item)
        per_cat[cat] = per_cat.get(cat, 0) + 1
        if len(chosen) >= limit:
            break
    # 万一命中分类不够，只补名称里确实含主题词的模板，绝不硬塞无关模板
    if len(chosen) < limit:
        seen = {x["id"] for x in chosen}
        for item in pool:
            if item["id"] in seen or not any(w in item["name"] for w in topic_in_query):
                continue
            chosen.append(item)
            seen.add(item["id"])
            if len(chosen) >= limit:
                break

    gate = {
        "status": "waiting", "request_id": secrets.token_urlsafe(16),
        "idea": idea, "positioning": positioning,
        "top_categories": top_cats,
        "candidates": [x["id"] for x in chosen],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": "第一步只提供候选链接清单，等待用户明确选定模板后才能开始制作。",
    }
    _write(GATE_FILE, gate)

    lines = [
        f"## 可选模板清单（主题定位：{positioning or '未指定'}）", "",
        f"请先在下面的链接里浏览、比较每一页的版式，然后**告诉我你选定的模板 ID**。",
        "在你明确选定之前，我不会开始制作任何页面。", "",
        "| # | 模板 | 分类 | 风格 | 页数 | 预览链接 |", "|---|---|---|---|---|---|",
    ]
    for i, item in enumerate(chosen, 1):
        pages = f"{item['pages']} 页" if item["pages"] else "—"
        lines.append(
            f"| {i} | `{item['id']}` · {item['name']} | {item['category_name']} | "
            f"{item['style']} | {pages} | [看每一页]({_gallery_url(template_id=item['id'])}) |"
        )
    cat_names = {
        c["id"]: c["name"]
        for c in _load(EXTERNAL / "categories.json", {"categories": []})["categories"]
    }
    lines += [
        "", "按分类浏览：",
        *[f"- [{cat_names.get(c, c)}]({_gallery_url(category=c)})" for c in top_cats],
        "", f"本地画廊入口：{GALLERY}",
    ]
    gate["markdown"] = "\n".join(lines)
    _write(GATE_FILE, gate)
    return gate


# ---------------------------------------------------------------------------
# 2. 用户选定
# ---------------------------------------------------------------------------

def confirm(template_id: str, request_id: str | None = None) -> dict:
    gate = _load(GATE_FILE)
    if gate.get("status") != "waiting":
        raise RuntimeError("当前没有待选定的请求，请先执行 recommend")
    if request_id and gate.get("request_id") != request_id:
        raise RuntimeError("请求已过期，请重新执行 recommend 生成候选清单")
    outside = template_id not in gate.get("candidates", [])
    item, source = resolve_source(template_id)
    gate.update({
        "status": "confirmed", "template_id": template_id,
        "template_name": item["name"], "page_count": item["pages"],
        "outside_candidates": outside,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    })
    _write(GATE_FILE, gate)
    return gate


def require_confirmed(plan: dict) -> dict:
    gate = _load(GATE_FILE, {})
    if gate.get("status") != "confirmed":
        raise RuntimeError(
            "门禁：尚未选定模板。第一步必须先给出候选链接清单并等待用户明确选定，"
            "在此之前禁止制作 PPT。"
        )
    if plan.get("template_id") and plan["template_id"] != gate["template_id"]:
        raise RuntimeError(
            f"门禁：plan 的模板 {plan['template_id']} 与已选定的 {gate['template_id']} 不一致"
        )
    return gate


# ---------------------------------------------------------------------------
# 3. 模板页版式清单（供挑页）
# ---------------------------------------------------------------------------

def page_layouts(template_id: str) -> dict:
    item, source = resolve_source(template_id)
    library = analyze_pptx(source)
    pages = []
    for slide in library["slides"]:
        pages.append({
            "source_slide": slide["slide_index"],
            "page_type": slide.get("page_type"),
            "text_slots": len(slide.get("slots", [])),
            "summary": str(slide.get("text_summary") or "").replace("\n", " ")[:60],
        })
    return {"template_id": template_id, "slide_count": len(pages), "pages": pages}


# ---------------------------------------------------------------------------
# 4. 三项检查
# ---------------------------------------------------------------------------

def final_check(sanitized_source: Path, output: Path, plan: dict, library: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    # (1) 内容完整性
    with zipfile.ZipFile(output) as zf:
        slide_text = "".join(
            zf.read(n).decode("utf-8", "replace")
            for n in zf.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)
        )
    leftover = [w for w in PLACEHOLDER_WORDS if w in slide_text]
    if leftover:
        errors.append("内容完整性：仍有未替换的模板示例文字：" + "、".join(leftover))
    from pptx import Presentation
    prs_out = Presentation(str(output))
    if len(prs_out.slides) != len(plan["slides"]):
        errors.append(f"内容完整性：成品 {len(prs_out.slides)} 页，plan 要求 {len(plan['slides'])} 页")
    for index, slide in enumerate(prs_out.slides, 1):
        texts = [sh.text_frame.text.strip() for sh in slide.shapes if sh.has_text_frame]
        if not any(texts):
            errors.append(f"内容完整性：第 {index} 页没有任何文字")

    # (2) 文字适配布局
    report = check_plan(library, plan)
    summary = report.get("summary", {})
    if summary.get("error"):
        errors.append(f"文字适配：check-plan 报 {summary['error']} 个错误")
    if summary.get("warn"):
        warnings.append(f"文字适配：check-plan 报 {summary['warn']} 条轻微宽度提示")

    # (3) 模板一致性
    prs_src = Presentation(str(sanitized_source))
    for index, item in enumerate(plan["slides"]):
        n = int(item["source_slide"])
        if not (1 <= n <= len(prs_src.slides)):
            errors.append(f"模板一致性：源页 {n} 超出模板范围")
            continue
        before_shapes = len(prs_src.slides[n - 1].shapes)
        after_shapes = len(prs_out.slides[index].shapes)
        if before_shapes != after_shapes:
            errors.append(
                f"模板一致性：第 {index + 1} 页元素数 {after_shapes} 与模板源页 {before_shapes} 不一致"
            )
    media = sanitize_pptx.scan(output)
    if not media["clean"]:
        errors.append("模板一致性：成品仍含音乐或自动翻页：" + json.dumps(media, ensure_ascii=False))

    return {
        "ok": not errors, "errors": errors, "warnings": warnings,
        "checks": {
            "content_integrity": not any("内容完整性" in e for e in errors),
            "text_fit": not any("文字适配" in e for e in errors),
            "template_consistency": not any("模板一致性" in e for e in errors),
        },
        "slide_count": len(prs_out.slides),
        "media_clean": media["clean"],
    }


# ---------------------------------------------------------------------------
# 5. 出稿编排
# ---------------------------------------------------------------------------

def build(plan_path: Path, output: Path, *, skip_gate: bool = False) -> dict:
    plan = _load(plan_path)
    gate = {} if skip_gate else require_confirmed(plan)
    template_id = plan.get("template_id") or gate.get("template_id")
    if not template_id:
        raise RuntimeError("plan 缺少 template_id，且没有已选定的模板")
    item, source = resolve_source(template_id)

    # 兜底净化：无论桌面原件是否已净化，出稿源一律干净
    SANITIZED_DIR.mkdir(parents=True, exist_ok=True)
    clean_source = SANITIZED_DIR / f"{hashlib.sha256(template_id.encode()).hexdigest()[:12]}.pptx"
    sanitize_pptx.sanitize(source, clean_source)

    library = analyze_pptx(clean_source)
    output.parent.mkdir(parents=True, exist_ok=True)
    apply_plan(clean_source, plan, output, transition="keep")

    result = final_check(clean_source, output, plan, library)
    result.update({
        "template_id": template_id, "template_name": item["name"],
        "output": str(output), "plan": str(plan_path),
        "gate_status": gate.get("status", "bypassed"),
        "source_sanitized": sanitize_pptx.scan(clean_source)["clean"],
    })
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _write(REPORT_DIR / f"{output.stem}.check.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("recommend", help="第一步：只输出候选模板链接清单，等待用户选定")
    rec.add_argument("--idea", required=True)
    rec.add_argument("--positioning", default="")
    rec.add_argument("--limit", type=int, default=8)

    con = sub.add_parser("confirm", help="用户明确选定模板 ID")
    con.add_argument("template_id")
    con.add_argument("--request-id")

    pag = sub.add_parser("pages", help="列出模板每一页的版式角色，供挑页")
    pag.add_argument("template_id")
    pag.add_argument("-o", "--output")

    bld = sub.add_parser("build", help="门禁校验 + 净化 + 挑页填充 + 三项检查")
    bld.add_argument("plan_json")
    bld.add_argument("-o", "--output", required=True)
    bld.add_argument("--skip-gate", action="store_true", help="仅供自动化测试使用")

    st = sub.add_parser("status", help="查看当前门禁状态")

    args = p.parse_args(argv)
    try:
        if args.command == "recommend":
            gate = recommend(args.idea, args.positioning, args.limit)
            print(gate["markdown"])
            print(f"\n[门禁] status=waiting，request_id={gate['request_id']}；等待用户选定。", file=sys.stderr)
            return 0
        if args.command == "confirm":
            gate = confirm(args.template_id, args.request_id)
            print(json.dumps({k: gate[k] for k in ("status", "template_id", "template_name", "page_count")},
                            ensure_ascii=False, indent=2))
            return 0
        if args.command == "pages":
            data = page_layouts(args.template_id)
            if args.output:
                _write(Path(args.output), data)
                print(f"版式清单 -> {args.output}", file=sys.stderr)
            else:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0
        if args.command == "build":
            result = build(Path(args.plan_json), Path(args.output), skip_gate=args.skip_gate)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 1
        if args.command == "status":
            print(json.dumps(_load(GATE_FILE, {"status": "none"}), ensure_ascii=False, indent=2))
            return 0
    except (RuntimeError, ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
