#!/usr/bin/env python3
"""Content brief: confirm what the deck must say before choosing a template.

A brief is deliberately small and human-readable. It records the audience,
occasion, page purposes, key messages, evidence references and data gaps.
The AI fills it with the user; the user confirms it; only then should template
recommendation and page filling proceed.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "xmu_content_brief.v1"
STATUSES = {"draft", "confirmed"}
DATA_STATUSES = {"provided", "missing", "not_applicable"}
CONTENT_SHAPES = {
    "cover", "toc", "chapter", "context", "comparison", "timeline",
    "process", "kpi", "table", "chart", "image_grid", "quote",
    "summary", "next_steps", "ending",
}
REQUIRED_PAGE_FIELDS = ("page_no", "purpose", "key_message", "content_shape", "data_status")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_brief(idea: str, positioning: str = "", audience: str = "",
              duration: int | None = None, target_pages: int | None = None,
              title: str | None = None) -> dict:
    """Create an empty draft. The agent fills sections/pages with the user."""
    return {
        "schema": SCHEMA,
        "brief_id": f"brief-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}",
        "title": title or idea.strip() or "未命名汇报",
        "audience": audience,
        "occasion": positioning,
        "duration_min": duration,
        "target_pages": target_pages,
        "status": "draft",
        "sections": [],
        "pages": [],
        "gaps": [],
        "created_at": _now(),
        "confirmed_at": None,
    }


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path: Path, brief: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _as_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate(brief: dict, *, require_confirmed: bool = False) -> list[str]:
    """Return structural errors. Content correctness stays with the user."""
    errors: list[str] = []
    if not isinstance(brief, dict):
        return ["brief 必须是 JSON 对象"]
    if brief.get("schema") != SCHEMA:
        errors.append(f"schema 必须是 {SCHEMA}")
    if brief.get("status") not in STATUSES:
        errors.append("status 必须是 draft 或 confirmed")
    if require_confirmed and brief.get("status") != "confirmed":
        errors.append("内容策划案尚未确认（status 必须是 confirmed）")
    if not str(brief.get("title") or "").strip():
        errors.append("title 不能为空")
    pages = brief.get("pages")
    if not isinstance(pages, list):
        errors.append("pages 必须是数组")
        pages = []
    if require_confirmed and not pages:
        errors.append("确认前至少需要一页内容")
    seen = set()
    for index, page in enumerate(pages, 1):
        if not isinstance(page, dict):
            errors.append(f"pages[{index}] 必须是对象")
            continue
        page_no = _as_int(page.get("page_no"))
        if page_no is None or page_no <= 0:
            errors.append(f"pages[{index}].page_no 必须是正整数")
        elif page_no in seen:
            errors.append(f"pages[{index}].page_no 重复：{page_no}")
        else:
            seen.add(page_no)
        for field in REQUIRED_PAGE_FIELDS:
            if field not in page:
                errors.append(f"pages[{index}] 缺少 {field}")
        if not str(page.get("purpose") or "").strip():
            errors.append(f"pages[{index}].purpose 不能为空")
        if not str(page.get("key_message") or "").strip():
            errors.append(f"pages[{index}].key_message 不能为空")
        shapes = page.get("content_shape")
        if not isinstance(shapes, list) or not shapes:
            errors.append(f"pages[{index}].content_shape 必须是非空数组")
        else:
            bad = [s for s in shapes if s not in CONTENT_SHAPES]
            if bad:
                errors.append(f"pages[{index}].content_shape 含未知类型：{', '.join(map(str, bad))}")
        status = page.get("data_status")
        if status not in DATA_STATUSES:
            errors.append(f"pages[{index}].data_status 必须是 {sorted(DATA_STATUSES)} 之一")
        evidence = page.get("evidence")
        if evidence is not None and not isinstance(evidence, list):
            errors.append(f"pages[{index}].evidence 必须是数组")
    gaps = brief.get("gaps")
    if gaps is not None and not isinstance(gaps, list):
        errors.append("gaps 必须是数组")
    return errors


def confirm(brief: dict) -> dict:
    candidate = dict(brief)
    candidate["status"] = "confirmed"
    errors = validate(candidate, require_confirmed=True)
    if errors:
        raise ValueError("内容策划案不合法：" + "；".join(errors))
    candidate["confirmed_at"] = _now()
    return candidate


def _hash_payload(brief: dict) -> dict:
    """Content identity excludes status/timestamps, so confirm does not change it."""
    keys = (
        "schema", "title", "audience", "occasion", "duration_min",
        "target_pages", "sections", "pages", "gaps",
    )
    return {key: brief.get(key) for key in keys}


def content_hash(brief: dict) -> str:
    payload = json.dumps(_hash_payload(brief), ensure_ascii=False,
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def render_markdown(brief: dict) -> str:
    lines = [
        f"## 内容策划案：{brief.get('title') or '未命名'}",
        "",
        f"- 受众：{brief.get('audience') or '未填写'}",
        f"- 场景：{brief.get('occasion') or '未填写'}",
        f"- 时长：{brief.get('duration_min') or '未填写'} 分钟",
        f"- 建议页数：{brief.get('target_pages') or '由内容决定'}",
        f"- 状态：{'已确认' if brief.get('status') == 'confirmed' else '待确认'}",
        "",
        "| 页码 | 目的 | 核心结论 | 内容形态 | 数据状态 |",
        "|---|---|---|---|---|",
    ]
    for page in brief.get("pages", []):
        shapes = "、".join(page.get("content_shape") or [])
        lines.append(
            f"| {page.get('page_no')} | {page.get('purpose', '')} | "
            f"{page.get('key_message', '')} | {shapes} | {page.get('data_status', '')} |"
        )
    gaps = brief.get("gaps") or []
    if gaps:
        lines += ["", "### 不能编造/尚缺内容", *[f"- {gap}" for gap in gaps]]
    return "\n".join(lines)
