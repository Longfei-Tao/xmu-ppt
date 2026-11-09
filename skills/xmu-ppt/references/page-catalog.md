# 页面语义目录

> 目的：让 AI 知道“这一页适合放什么内容”，而不是只看槽位数或标题摘要。

## 字段

| 字段 | 含义 |
|---|---|
| `slide` / `source_slide` | 源 PPT 页码 |
| `role` | `cover` / `toc` / `chapter` / `content` / `ending` |
| `page_type` | 分析器原始分类，如 `content_candidate` |
| `layout` | 版式族，如 `hero-statement` / `multi-block` / `numbered-cards` |
| `content_shapes` | `context` / `comparison` / `table` / `chart` / `kpi` / `chapter` 等 |
| `density` | `low` / `medium` / `high` |
| `capacity` | 槽位数、字号尺度；用户模板另有 `max_slot_chars` / `total_safe_chars` |
| `has_table` / `has_chart` | 是否含原生表格/图表 |
| `confidence` | 启发式分类置信度；低于 0.6 需要人工确认 |

## 来源

- 内置模板：从 `templates/decks/<id>/layout_index.json` 生成，不额外写入文件；
- 我的模板：从 `~/.xmu-ppt/user-templates/U001/page_catalog.json` 读取；
- 外部本机模板：暂不生成语义目录，避免每次推荐都做昂贵分析。

## 用法

```bash
$PY $S pages 001 --brief output/brief.json -o output/pages.json
```

`brief_suggestions` 会为内容策划案的每一页给出最多 3 个候选源页、分数和原因。
没有精确匹配时会给出容量较大的内容页作为备选，并明确标注“可能需要调整版式或另选模板”。

## 边界

- 这是**内容形态匹配**，不是视觉质量评分；
- 自动分类可以人工覆盖；
- 表格/图表只在模板已有槽位时才有意义，不能靠语义目录凭空创造；
- 最终仍以 `build` 的内容完整性、文字适配和模板一致性三项检查为准。
