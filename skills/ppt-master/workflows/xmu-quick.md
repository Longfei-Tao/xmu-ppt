---
description: 厦门大学模板快速出稿流程（本仓库定制），替代完整 Eight Confirmations 长流程
---

# 厦门大学快速出稿（XMU Quick Deck）

> 目标：用户只说“帮我做一份 XX 汇报，主题是 XX”，就能直接产出一份像人做的厦大风格 PPT。
> 本流程适用于 `templates/decks/厦门大学_*` 全部 14 套模板（3 套精修 + 11 套主题）；非厦大的 deck 或纯自由设计仍走原有 `workflows/` 流程。

---

## 0. 与主流程的关系（优先级）

本节**替代** `SKILL.md` 中的 Eight Confirmations（八项确认）与策略师长报告，但**不放松**以下底线：

1. SVG 必须逐页手写，禁止用脚本批量生成页面；
2. 每页只继承模板的页眉、页脚、装饰，正文必须按内容重新组织；
3. 颜色、字体只能来自对应 `design_spec.md`；
4. 导出前必须跑 `svg_quality_checker.py`；
5. 只做**一次**轻确认，不反复打断用户。

---

## 1. 选模板（唯一一次轻确认）

| 用户场景 | 模板 ID | 目录 |
| --- | --- | --- |
| 论文答辩、开题、预答辩、毕业汇报 | `厦门大学_官方_厦园晴日` | `templates/decks/厦门大学_官方_厦园晴日/` |
| 人文社科、读书报告、课程作业、调研访谈 | `厦门大学_官方_凤栖青橙` | `templates/decks/厦门大学_官方_凤栖青橙/` |
| 组会、工作汇报、项目进展、竞赛路演、招生宣讲 | `厦门大学_官方_南强蔚蓝` | `templates/decks/厦门大学_官方_南强蔚蓝/` |
| 拿不准 | 默认 `厦门大学_官方_厦园晴日` | — |
| 用户明确指定 | 以用户为准 | — |

### 厦大主题库（11 套，按需扩展）

除三套精修模板外，还有 11 套由原 PPTX 一比一转换的厦大主题模板（均为 `厦门大学_主题_*`）。`templates/decks/` 下不含任何非厦大 deck。

- 使用方式与精修模板一致：复制 5 页原型、替换文字、保留图形与图片；
- 原型保留了原示例文字，只改文字即可；
- 原图表对象在原型中以占位符呈现，如需数据图请在内容页重新绘制；
- 用户点名某套风格（如“凤凰花开”“晚霞”“米金书法”）时，直接使用对应原型。

确认话术只发一次，三行以内：

```text
我按「厦园晴日」做，预计 10 页；有数据图就放正文页，没有就用要点+结论。直接开始，如需改模板回我一句即可。
```

用户已给足内容时，**连这句都可以省掉**，直接开工并在交付时说明选择理由。

---

## 2. 收集内容

- 用户给了文件：先转 Markdown（`scripts/source_to_md/`），再提炼。
- 用户只给主题：按「背景 → 问题 → 方法/做法 → 结果 → 结论 → 展望」补全，不允许出现空页或“此处填写”。
- 页数建议 8–14 页：
  - 1 封面
  - 1 目录
  - 3–4 个章节过渡
  - 4–6 个内容页
  - 1 结束页
- 每页只讲一件事，标题写结论而不是写“背景介绍”。

---

## 3. 建立项目与页面骨架

```bash
python3 ${SKILL_DIR}/scripts/project_manager.py init <project_name> --format ppt169
```

把模板的 5 页原型（`01_cover.svg` / `02_toc.svg` / `02_chapter.svg` / `03_content.svg` / `04_ending.svg`）连同素材图片复制进 `<project>/svg_output/`，按下列命名重排。`design_spec.md` 与 `preview.png` 只作参考，**不要**复制进 `svg_output/`：

| 输出文件 | 来源 | 处理 |
| --- | --- | --- |
| `01_cover.svg` | `01_cover.svg` | 填封面占位符 |
| `02_toc.svg` | `02_toc.svg` | 填 4 个目录条目 |
| `03_chapter_01.svg` … | `02_chapter.svg` | 每章复制一份，改序号/标题/说明 |
| `04_content_01.svg` … | `03_content.svg` | 每页复制一份，替换标题/观点，正文在内容区内重新排版 |
| `99_ending.svg` | `04_ending.svg` | 填致谢与联系方式 |

复制时只改文字层，**不要动**弧形色块、三角阵列、校徽、照片、侧边条等固定装饰；正文页的内容框可以按版式需要调整位置，但不能改变页面边距与页眉页脚。

---

## 4. 占位符对照

### 厦门大学_官方_厦园晴日

`{{TITLE}}` `{{SUBTITLE}}` `{{AUTHOR}}` `{{ADVISOR}}` `{{INSTITUTION}}` `{{DATE}}`
`{{PAGE_TITLE}}` `{{CHAPTER_NUM}}` `{{CHAPTER_TITLE}}` `{{CHAPTER_DESC}}`
`{{KEY_MESSAGE}}` `{{CONTENT_AREA}}` `{{SECTION_NAME}}` `{{SOURCE}}` `{{PAGE_NUM}}`
`{{THANK_YOU}}` `{{CONTACT_INFO}}` `{{TOC_ITEM_1_TITLE}}` … `{{TOC_ITEM_4_TITLE}}`

### 厦门大学_官方_凤栖青橙

在上一组基础上增加：
`{{THANK_LINE_1}}` `{{THANK_LINE_2}}`（默认「感谢」「垂听」）
`{{TOC_ITEM_1_DESC}}` … `{{TOC_ITEM_4_DESC}}`

### 厦门大学_官方_南强蔚蓝

`{{TITLE}}` `{{SUBTITLE}}` `{{AUTHOR}}` `{{INSTITUTION}}` `{{DATE}}`
`{{PAGE_TITLE}}` `{{CHAPTER_NUM}}` `{{CHAPTER_TITLE}}` `{{CHAPTER_DESC}}`
`{{CHAPTER_POINT_1}}` / `{{CHAPTER_POINT_1_DESC}}` …（3 组）
`{{CONTENT_AREA}}` `{{SECTION_NAME}}` `{{PAGE_NUM}}` `{{THANK_YOU}}` `{{CONTACT_INFO}}`
`{{TOC_ITEM_1_TITLE}}` … `{{TOC_ITEM_4_TITLE}}` 与对应 `_DESC`

---

## 5. 内容页排版（防 AI 味的关键）

内容区尺寸：

| 模板 | 内容区 | 页眉基线 | 页脚 |
| --- | --- | --- | --- |
| 厦园晴日 | x 72–1208，y 236–620 | y≈135 标题 | y≈678 |
| 凤栖青橙 | x 90–1190，y 288–606 | y≈188 标题 | y≈660 |
| 南强蔚蓝 | x 100–1180，y 170–610 | y≈112 标题 | y≈660 |

**四种版式轮换，禁止每页都是卡片网格：**

1. **观点 + 两栏**：左栏 3–4 条要点，右栏一段解释或小图；
2. **数据卡**：3–4 张同尺寸卡片，只放一个数字 + 一句解释，卡片背景用极浅色；
3. **左图右文**：图片占 40%，右侧 3 条结论；
4. **全宽要点**：一条主线 + 底部一条结论横条（用主色 8% 透明度）。

每页必须满足：

- 有一个**结论句**（16–20px），不要只写“背景介绍”；
- 标题 ≤ 16 个汉字；正文单行 ≤ 42 个汉字；
- 正文字号 14–18px，注释 12px，标题按 `design_spec.md`；
- 留白 ≥ 24px，模块之间 ≥ 24px；
- 同页颜色 ≤ 3 种（主色、深色文字、浅色块）；
- 图标只用线性图标，不用 emoji。

**禁止**：彩虹配色、渐变卡片堆叠、每页四个圆角框、把整段原文贴进页面、标题带“首先/其次/最后”。

---

## 6. 导出与自检

```bash
python3 ${SKILL_DIR}/scripts/svg_quality_checker.py <project>/svg_output --template-mode --canonical-authoring
python3 ${SKILL_DIR}/scripts/svg_to_pptx.py <project> -s svg_output -t fade -a none

# 导出后必跑：版面体检（有 ERROR 不许交付）
python3 ${SKILL_DIR}/scripts/review_pptx.py <project>/exports/<name>.pptx --min-level warn
```

`review_pptx.py` 会按页列出溢出、字体被挤压、元素重叠、越界、间距过密、占位符残留等问题，
每条给出实测值与修改建议。**退出码为 1 表示有硬伤**，必须先改再交付。

交付前逐项确认：

- [ ] `review_pptx.py` 无 ERROR（WARN 要么修，要么在交付说明里写明）
- [ ] 所有 `{{...}}` 已替换，没有残留；
- [ ] 文本没有压到装饰、边框、照片人脸；
- [ ] 每页页码连续；
- [ ] 目录条目与正文章节一一对应；
- [ ] 导出的 `.pptx` 能在 PowerPoint 里正常打开，文字可编辑；
- [ ] 至少抽查 3 页的渲染截图。

---

## 7. 交付话术

```text
已生成：<路径>
模板：厦门大学_官方_厦园晴日 ｜ 页数：10
用了你的内容：<列出 3 个关键信息来源>
需要你补的：第 6 页的数据图，可发我 Excel 或截图，我再替换。
```
