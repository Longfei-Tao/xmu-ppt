"""idea-to-ppt：把「想法 + 主题定位」变成 PPT 的唯一出稿入口。

流程（与 workflows/idea-to-ppt.md 一致）
----------------------------------------
1. recommend  —— 第一步：只输出「可点模板链接清单」，写入 waiting 状态，**不制作**
2. confirm    —— 用户明确选定模板（三位序号、U001 或模板 ID）后，状态改为 confirmed
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
import template_numbers as numbers  # noqa: E402
import text_fit  # noqa: E402
import user_templates  # noqa: E402

EXTERNAL = SKILL_ROOT / "templates" / "external"
CATALOG_FILE = EXTERNAL / "external_catalog.json"
DUP_FILE = EXTERNAL / "duplicates.json"
DECKS = SKILL_ROOT / "templates" / "decks"
BUILTIN_CATALOG = DECKS / "catalog.json"
GALLERY = REPO / "local-gallery" / "index.html"
PUBLIC_GALLERY = "https://longfei-tao.github.io/xmu-ppt/templates/"
GATE_FILE = REPO / "output" / ".selection.json"
SANITIZED_DIR = REPO / "output" / "_sanitized"
REPORT_DIR = REPO / "output" / "_checks"

CATEGORY_HINTS = {
    "institution": ["厦大", "厦门大学", "高校", "学校", "答辩", "毕业", "校园", "机构", "官方", "学院"],
    "report": ["汇报", "总结", "报告", "工作", "通用", "数据", "年度", "项目", "商务"],
    "clinical": ["医护", "临床", "医学", "医疗", "医院", "医生", "护士", "疾病", "肿瘤", "癌", "护理", "手术", "健康"],
    "maternal-child": ["妇幼", "母婴", "儿童", "儿科", "卡通", "宣教", "手绘", "温馨", "患者"],
    "tcm-style": ["中医", "国风", "中国风", "中药", "传统", "养生"],
    "user": ["我的模板", "自备模板", "本机模板", "自己的模板"],
}

# 主题域判定：医学词用于「同域加分」，也用于「跨域降权」。
MEDICAL_HINTS = (
    "胃癌", "胃", "术后", "护理", "康复", "随访", "外科", "肿瘤", "癌",
    "手术", "营养", "并发症", "宣教", "患教", "临床", "医护", "医生",
    "护士", "健康", "医疗", "医院", "查房", "病例", "救治", "救护",
)
STUDENT_HINTS = (
    "职业规划", "求职", "竞聘", "简历", "面试", "实习", "大学生", "校园",
    "学生", "保研", "考研", "课程", "社团", "读书", "人文", "毕业", "答辩",
    "开题", "组会", "奖学金", "成长", "规划",
)
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


def _gallery_url(template_id: str | None = None, category: str | None = None,
                 number: str | int | None = None) -> str:
    """本机有画廊就用 file:// 深链；用户模板指向独立的本机画廊。"""
    if template_id and user_templates.lookup(template_id):
        uri = user_templates.gallery_uri()
        return uri or "（本机模板画廊尚未生成）"
    if GALLERY.is_file():
        base = GALLERY.resolve().as_uri()
        if template_id:
            return base + "#deck=" + quote(template_id, safe="")
        if category:
            return base + "#cat=" + quote(category, safe="")
        return base
    if number is not None:
        text = str(number)
        if text.isdigit():
            return f"{PUBLIC_GALLERY}?deck={int(text):03d}"
    if category:
        return PUBLIC_GALLERY + "?cat=" + quote(category, safe="")
    return PUBLIC_GALLERY


def _registry() -> dict:
    return numbers.ensure_registry()


def resolve_selection(value: str) -> tuple[str, dict]:
    """权威解析：内置/外部按序号，U 前缀按本机模板，其余按模板 ID。"""
    user_entry = user_templates.lookup(value)
    if user_entry:
        return user_entry["template_id"], user_entry
    entry = numbers.lookup(_registry(), value)
    return entry["template_id"], entry


def _external_source(template_id: str) -> Path | None:
    """本机外部模板原件；缺本机配置时安全返回 None，绝不抛错。"""
    try:
        from external_selection import source_path
        return source_path(template_id)
    except (ImportError, OSError, ValueError):
        return None


def _all_templates() -> list[dict]:
    """合并内置 15 套与外部 200 套，并标记本机是否真的能出稿。"""
    items: list[dict] = []
    registry = _registry()
    entry_by_id = {e["template_id"]: e for e in registry["entries"]}
    removed = {g["remove"] for g in _load(DUP_FILE, {"groups": []}).get("groups", [])}
    for r in _load(CATALOG_FILE)["templates"]:
        if r["id"] in removed:
            continue
        entry = entry_by_id.get(r["id"], {})
        if entry.get("status") not in (None, "active"):
            continue
        items.append({
            "id": r["id"], "serial": entry.get("serial", f"{int(r['number']):03d}"),
            "name": r["name"], "style": r.get("style", ""),
            "category": r["primary_category"], "category_name": r["category_name"],
            "pages": r["page_count"], "namespace": "external",
            "tags": r.get("tags", []), "source_key": r.get("source_key"),
            "route": "native", "usable": _external_source(r["id"]) is not None,
        })
    for r in _load(BUILTIN_CATALOG):
        source = DECKS / r["id"] / "source.pptx"
        folder = DECKS / r["id"]
        has_svg = any((folder / name).is_file()
                      for name in ("01_cover.svg", "03_content.svg"))
        route = "native" if source.is_file() else ("svg" if has_svg else None)
        pages = None
        if source.exists():
            try:
                from pptx import Presentation
                pages = len(Presentation(str(source)).slides)
            except Exception:
                pages = None
        entry = entry_by_id.get(r["id"], {})
        if entry.get("status") not in (None, "active"):
            continue
        items.append({
            "id": r["id"], "serial": entry.get("serial", f"{int(r['number']):03d}"),
            "name": r["name"], "style": r.get("style", ""),
            "category": "institution", "category_name": "厦门大学等高校/机构风格",
            "pages": pages, "namespace": "builtin",
            "tags": r.get("tags", []), "source_key": None,
            "route": route, "usable": route is not None,
        })
    for r in user_templates.list_templates():
        if not r.get("source_ok") or r.get("status") != "active":
            continue
        items.append({
            "id": r["template_id"], "serial": r["serial"],
            "name": r["name"], "style": "我的模板",
            "category": "user", "category_name": "我的模板",
            "pages": r.get("slides"), "namespace": "user",
            "tags": ["我的模板", "本机自备"], "source_key": None,
            "route": "native", "usable": True,
        })
    return items


def resolve_source(template_id: str) -> tuple[dict, Path]:
    for item in _all_templates():
        if item["id"] != template_id:
            continue
        if item["namespace"] == "builtin":
            path = DECKS / template_id / "source.pptx"
        elif item["namespace"] == "user":
            path = user_templates.source_path(template_id)
            if path is None:
                raise RuntimeError(
                    f"我的模板原件不在本机：{template_id}。请重新运行 user_templates.py onboard。"
                )
        else:
            path = _external_source(template_id)
            if path is None:
                raise RuntimeError(
                    f"模板原件不在本机：{template_id}。请先运行 external_templates.py scan "
                    "指向你的模板目录，或改选内置厦大模板。"
                )
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
    query_is_medical = any(w in text for w in MEDICAL_HINTS)
    query_is_student = any(w in text for w in STUDENT_HINTS)
    if query_is_student and not query_is_medical and "institution" not in top_cats:
        top_cats = ["institution"] + top_cats[:2]
    if not top_cats:
        top_cats = ["institution", "report"]
    # 本机“我的模板”始终进入候选池，避免用户导入后还要靠关键词碰运气。
    if any(x["namespace"] == "user" for x in _all_templates()):
        top_cats = ["user"] + [c for c in top_cats if c != "user"]
    ranked = {c: 3 - i for i, c in enumerate(top_cats)}
    medical_in_query = [w for w in MEDICAL_HINTS if w in text]

    def score(item: dict) -> int:
        hay = " ".join([item["name"], item["style"], " ".join(item["tags"])])
        value = ranked.get(item["category"], 0) * 10
        if item["category"] == "user":
            # 用户刚导入的模板应优先出现，不能被人群更大的内置分类挤出候选。
            value += 12
        if query_is_medical:
            # 医学主题：主题词命中模板名称/风格是最强信号
            value += 6 * sum(1 for word in medical_in_query if word in hay)
            value += sum(1 for word in MEDICAL_HINTS if word in hay)
        else:
            # 非医学主题：模板自带的医疗属性是减分项，不能反过来加分
            if any(word in hay for word in MEDICAL_HINTS):
                value -= 24
            value += 8 * sum(1 for word in STUDENT_HINTS if word in text and word in hay)
            if query_is_student and item["category"] == "institution":
                value += 10
        if item["pages"] and 10 <= item["pages"] <= 40:
            value += 2
        return value

    # 只推荐本机真的能出稿的模板：缺 source.pptx 的内置模板、缺原件的本机外部模板都不进候选
    usable = [x for x in _all_templates() if x.get("usable")]
    pool = sorted(usable, key=lambda x: (-score(x), x["serial"]))
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
    name_terms = [w for w in (*MEDICAL_HINTS, *STUDENT_HINTS) if w in text]
    if len(chosen) < limit:
        seen = {x["id"] for x in chosen}
        for item in pool:
            if item["id"] in seen or not any(w in item["name"] for w in name_terms):
                continue
            chosen.append(item)
            seen.add(item["id"])
            if len(chosen) >= limit:
                break
    # 纯技能包/全新克隆只有内置厦大模板：主题词完全对不上时不能返回空清单
    fallback = not chosen
    if fallback:
        chosen = pool[:limit]

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
        "请先点链接浏览、比较每一页的版式，然后**报序号**：内置/外部三位数字（如 `004`），",
        "我的模板用 `U` 前缀（如 `U001`）。在你明确选定之前，我不会开始制作任何页面。", "",
    ]
    if fallback:
        lines += ["> 本机没有与该主题完全匹配的专用模板，以下为全部可用模板。", ""]
    lines += [
        "| 序号 | 模板 | 分类 | 风格 | 页数 | 出稿路线 | 预览链接 |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in chosen:
        pages = f"{item['pages']} 页" if item["pages"] else "—"
        route = "原生填充" if item.get("route") == "native" else "SVG 灵活排版"
        lines.append(
            f"| `{item['serial']}` | {item['name']}（`{item['id']}`） | {item['category_name']} | "
            f"{item['style']} | {pages} | {route} | "
            f"[看每一页]({_gallery_url(template_id=item['id'], number=item['serial'])}) |"
        )
    cat_names = {
        c["id"]: c["name"]
        for c in _load(EXTERNAL / "categories.json", {"categories": []})["categories"]
    }
    lines += [
        "", f"本机可用模板共 {len(pool)} 套。不喜欢上面的候选，可以打开完整画廊按封面挑，"
        "把序号发给我即可。",
        "",
        "按分类浏览：",
        *[f"- [{cat_names.get(c, c)}]({_gallery_url(category=c)})"
          for c in top_cats if c != "user"],
        "", f"- [打开完整模板画廊（{len(pool)} 套）]({_gallery_url()})",
    ]
    if user_templates.gallery_uri():
        lines.append(f"- [打开我的模板画廊]({user_templates.gallery_uri()})")
    gate["markdown"] = "\n".join(lines)
    _write(GATE_FILE, gate)
    return gate


# ---------------------------------------------------------------------------
# 2. 用户选定
# ---------------------------------------------------------------------------

def confirm(selection: str, request_id: str | None = None) -> dict:
    gate = _load(GATE_FILE)
    if gate.get("status") != "waiting":
        raise RuntimeError("当前没有待选定的请求，请先执行 recommend")
    if request_id and gate.get("request_id") != request_id:
        raise RuntimeError("请求已过期，请重新执行 recommend 生成候选清单")
    # 纯数字按固定序号解析；模板 ID 仍可用，但绝不与序号混淆
    template_id, entry = resolve_selection(selection)
    outside = template_id not in gate.get("candidates", [])
    item = next((x for x in _all_templates() if x["id"] == template_id), None)
    if item is None:
        raise RuntimeError(f"找不到模板：{template_id}")
    if item.get("route") == "svg":
        source = None
    else:
        item, source = resolve_source(template_id)
    gate.update({
        "status": "confirmed", "template_id": template_id,
        "serial": entry["serial"], "selection": str(selection),
        "template_name": item["name"], "page_count": item["pages"],
        "route": item.get("route", "native"),
        "source": str(source) if source else None,
        "outside_candidates": outside,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    })
    if gate["route"] == "svg":
        gate["warning"] = (
            "该模板缺少原生源 PPTX，只能走 SVG 灵活排版（会重新设计版式）；"
            "原生 build 会拒绝出稿，请按 workflows/xmu-quick.md 执行。"
        )
    _write(GATE_FILE, gate)
    return gate


def require_confirmed(plan: dict) -> dict:
    gate = _load(GATE_FILE, {})
    if gate.get("status") != "confirmed":
        raise RuntimeError(
            "门禁：尚未选定模板。第一步必须先给出候选链接清单并等待用户明确选定，"
            "在此之前禁止制作 PPT。"
        )
    if gate.get("route") == "svg":
        raise RuntimeError(
            "门禁：已选定的模板走「SVG 灵活排版」路线（缺少原生 PPTX 页库），"
            "不能调用原生 build。请按 SVG 排版流程制作，或改选支持原生填充的模板。"
        )
    requested = plan.get("template_id")
    if requested:
        # plan 里写序号（如 "004"）或模板 ID 都允许，统一按注册表归一
        try:
            requested, _ = resolve_selection(requested)
        except RuntimeError:
            pass
        if requested != gate["template_id"]:
            raise RuntimeError(
                f"门禁：plan 的模板 {plan['template_id']} 与已选定的 "
                f"{gate.get('serial', '?')} / {gate['template_id']} 不一致"
            )
    return gate


# ---------------------------------------------------------------------------
# 3. 模板页版式清单（供挑页）
# ---------------------------------------------------------------------------

def page_layouts(template_id: str) -> dict:
    template_id, _ = resolve_selection(template_id)
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

def _shape_texts(shapes) -> list[str]:
    """递归收集组合、表格里的文字，避免把「有内容」误判成空白页。"""
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    texts: list[str] = []
    for shape in shapes:
        if getattr(shape, "has_text_frame", False):
            texts.append(shape.text_frame.text.strip())
        if getattr(shape, "has_table", False):
            for row in shape.table.rows:
                for cell in row.cells:
                    texts.append(cell.text.strip())
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            texts.extend(_shape_texts(shape.shapes))
    return texts


def final_check(sanitized_source: Path, output: Path, plan: dict, library: dict,
                *, capacity: dict | None = None) -> dict:
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
        texts = _shape_texts(slide.shapes)
        if not any(texts):
            errors.append(f"内容完整性：第 {index} 页没有任何文字")

    # (2) 文字适配布局
    report = check_plan(library, plan)
    summary = report.get("summary", {})
    if summary.get("error"):
        errors.append(f"文字适配：check-plan 报 {summary['error']} 个错误")
    if summary.get("warn"):
        warnings.append(f"文字适配：check-plan 报 {summary['warn']} 条轻微宽度提示")
    # 绝对容量：只看长度比例会漏掉「长示例 → 仍很长的文案」造成的横向溢出
    if capacity is None:
        capacity = text_fit.build_capacity_map(sanitized_source, library)
    overflow = text_fit.validate_plan(plan, capacity)
    if overflow:
        sample = "、".join(
            f"{p['slot_id']}（{max(p['line_em'], default=0):.1f}>{p['safe_em']:.1f} em）"
            for p in overflow[:4]
        )
        errors.append(f"文字适配：{len(overflow)} 处文案超出文本框容量：{sample}")

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

def build(plan_path: Path, output: Path) -> dict:
    plan = _load(plan_path)
    gate = require_confirmed(plan)
    template_id = plan.get("template_id") or gate.get("template_id")
    if not template_id:
        raise RuntimeError("plan 缺少 template_id，且没有已选定的模板")
    template_id, entry = resolve_selection(template_id)
    item, source = resolve_source(template_id)

    # 兜底净化：无论桌面原件是否已净化，出稿源一律干净
    SANITIZED_DIR.mkdir(parents=True, exist_ok=True)
    clean_source = SANITIZED_DIR / f"{hashlib.sha256(template_id.encode()).hexdigest()[:12]}.pptx"
    sanitize_pptx.sanitize(source, clean_source)

    library = analyze_pptx(clean_source)
    capacity = text_fit.build_capacity_map(clean_source, library)
    meta = {
        "template_id": template_id, "serial": entry["serial"],
        "template_name": item["name"],
        "output": str(output), "plan": str(plan_path),
        "gate_status": gate.get("status", "confirmed"),
        "source_sanitized": sanitize_pptx.scan(clean_source)["clean"],
        "capacity_slots": len(capacity),
        "wrap_none_slots": sum(1 for v in capacity.values() if v["wrap"] == "none"),
    }
    try:
        plan, fit_changes = text_fit.enforce_plan(plan, capacity)
    except text_fit.TextOverflowError as exc:
        # 放不下就明确失败，让使用者改写文案；绝不截断后假装成功
        result = {"ok": False, "errors": [f"文字适配：{exc}"], "warnings": [],
                  "checks": {"content_integrity": False, "text_fit": False,
                             "template_consistency": False},
                  "text_fit_adjustments": [], **meta}
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        _write(REPORT_DIR / f"{output.stem}.check.json", result)
        return result

    output.parent.mkdir(parents=True, exist_ok=True)
    apply_plan(clean_source, plan, output, transition="keep")

    result = final_check(clean_source, output, plan, library, capacity=capacity)
    result.update({"text_fit_adjustments": fit_changes, **meta})
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

    con = sub.add_parser("confirm", help="用户明确选定模板（三位序号、U001 或模板 ID）")
    con.add_argument("selection", help="三位序号如 004、本机模板如 U001，或模板 ID")
    con.add_argument("--request-id")

    pag = sub.add_parser("pages", help="列出模板每一页的版式角色，供挑页")
    pag.add_argument("selection", help="三位序号如 004、本机模板如 U001，或模板 ID")
    pag.add_argument("-o", "--output")

    bld = sub.add_parser("build", help="门禁校验 + 净化 + 挑页填充 + 三项检查")
    bld.add_argument("plan_json")
    bld.add_argument("-o", "--output", required=True)

    st = sub.add_parser("status", help="查看当前门禁状态")

    args = p.parse_args(argv)
    try:
        if args.command == "recommend":
            gate = recommend(args.idea, args.positioning, args.limit)
            print(gate["markdown"])
            print(f"\n[门禁] status=waiting，request_id={gate['request_id']}；等待用户选定。", file=sys.stderr)
            return 0
        if args.command == "confirm":
            gate = confirm(args.selection, args.request_id)
            print(json.dumps({k: gate[k] for k in (
                "status", "serial", "template_id", "template_name", "page_count", "selection")},
                ensure_ascii=False, indent=2))
            return 0
        if args.command == "pages":
            data = page_layouts(args.selection)
            if args.output:
                _write(Path(args.output), data)
                print(f"版式清单 -> {args.output}", file=sys.stderr)
            else:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0
        if args.command == "build":
            result = build(Path(args.plan_json), Path(args.output))
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
