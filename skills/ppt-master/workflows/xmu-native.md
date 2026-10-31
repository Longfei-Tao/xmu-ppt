---
description: 厦大模板原生填充 —— 在原始 PPTX 里嵌内容，模板的字体/框线/图片/表格一律不动
---

# 厦大模板原生填充（XMU Native Fill）

> 目标：用户说「用这个模板做一份 XX」，产出的是**在原始模板里填好内容的 PPTX**——照片、红条、圆章、表格样式、字体字号全部原样继承，只替换文字与表格数据。
>
> 与 `xmu-quick.md` 的分工：`xmu-quick` 用 SVG 重画（排版自由、模板保真中等）；本流程用原生填充（模板保真最高、排版受槽位约束）。**用户提到「用这个模板 / 别改我的模板 / 保留原样式」时走本流程。**

---

## 0. 硬规则

1. **禁止**跑 `pptx_to_svg.py` / `svg_to_pptx.py` / `finalize_svg.py`。本流程不产生 SVG。
2. 只改 `fill_plan.json` 里的 `replacements` / `table_edits` / `chart_edits`，**不手改 OOXML**。
3. 输出必须来自 `template_fill_pptx.py apply`，不接受手工拼装的 pptx。
4. 源页可重复使用、可跳过、可重排；**源页顺序不是输出顺序**。

---

用户上传了自己的模板并要求保留时，转入 [通用原生填充工作流](template-fill-pptx.md)，使用该上传文件生成索引，不再从下面的内置列表替换源模板。上传 PPTX 只作事实材料时，转入 SVG 路线。

## 1. 选模板

| 用户场景 | 模板 |
| --- | --- |
| 论文答辩 / 开题 / 毕业汇报 | `厦门大学_官方_厦园晴日`、`厦门大学_主题_经典蓝白` |
| 人文社科 / 读书报告 / 课程作业 | `厦门大学_官方_凤栖青橙`、`厦门大学_主题_米金书法` |
| 组会 / 工作汇报 / 项目进展 | `厦门大学_主题_光影厦大`（南强蔚蓝仅支持 SVG） |
| 视觉冲击强、答辩场景 | `厦门大学_主题_凤凰花开`、`厦门大学_主题_蓝天校门` |
| 页数多、版式要丰富（20+ 页） | `厦门大学_主题_米金书法`（22 页）、`厦门大学_主题_经典蓝白`（21 页）、`厦门大学_主题_蓝天校门`（22 页） |

原生填充只适用于同时存在 `source.pptx`、`source.slide_library.json`、`layout_index.json` 的 13 套模板。先检查文件，禁止虚构缺失路径；南强蔚蓝缺少三者，不能推荐为原生填充模板。源文件内已有真实 Logo，必须保留。用户只给主题时遵守 `xmu-quick.md` 的内容真实性规则，不编造结果和身份信息。

## 2. 读版式清单

```bash
cat templates/decks/<deck_id>/layout_index.json
```

每页给出：`role`（cover / toc / chapter-divider / content / ending）、`layout`（版式类型）、`slot_count`、`type_scale_px`、`tables`、`charts`。

| `layout` 值 | 含义 | 适合承载 |
| --- | --- | --- |
| `cover` | 封面 | 题目 + 副标题 + 汇报人 |
| `toc` | 目录 | 3–5 个条目，每项「编号 + 标题 + 一句说明」 |
| `chapter-divider` | 章节过渡（大字 ≥90px） | 只放章节名和一句导语，**不要塞正文** |
| `hero-statement` | 单主张页 | 一个结论 + 一到两段支撑 |
| `two-block` | 两块正文 | 对照、并列两条论据 |
| `list` | 多条目 | 4–8 条并列要点 |
| `numbered-cards` | 编号卡片（01/02…） | 步骤、并列模块，每项短标题 + 一句说明 |
| `multi-block` | 高密度多块 | 12 块以上，适合数据罗列 |
| `ending` | 结束页 | 致谢 |

## 3. 选页与复用

- 一个源版式**可以反复用**：`slides` 数组里把同一个 `source_slide` 写多次，每次给不同 `replacements`。
- 一个源版式**可以不用**：11 页的模板产出 6 页是正常的。
- 选页看**结构能不能承载内容**，不是看原文写了什么：三点并列 → 找 `numbered-cards`；一正一反 → 找 `two-block`。
- 内容放不进去就换版式或删内容，**不要硬塞**。

## 4. 生成填充计划

```bash
python3 ${SKILL_DIR}/scripts/template_fill_pptx.py scaffold \
  templates/decks/<deck_id>/source.slide_library.json \
  -o <project>/analysis/fill_plan.json --slides "1,2,3,5,8"
```

命令支持重复与重排，如 `--slides "1,3,5,3,5,11"`；每个副本可填写不同内容。骨架保留原示例文字，仅用于起稿，不能直接交付。所有示例正文、作者、时间、图表数据与讲者备注都需逐页检查并替换或清除，保留品牌固定文字。

然后手工编辑 `fill_plan.json`：按上面的选页结果调整 `slides` 顺序、增删条目、填 `text`。

容量约束（关键，写错会溢出）：

| 场景 | 上限估算 |
| --- | --- |
| 中文标题 | `槽宽 ÷ 字号 × 0.95` 个汉字 |
| 中文正文 | `槽宽 ÷ 字号 × 0.90` 个汉字 **每行**，再乘可用行数 |
| 短标签（汇报人、日期） | 不超过原文字的 1.2 倍长度 |

超过就缩短，别指望自动换行救场——原文本框多为「不自动缩放」，超了直接压到装饰上。

## 5. 校验与导出

```bash
python3 ${SKILL_DIR}/scripts/template_fill_pptx.py check-plan \
  templates/decks/<deck_id>/source.slide_library.json <project>/analysis/fill_plan.json

python3 ${SKILL_DIR}/scripts/template_fill_pptx.py apply \
  templates/decks/<deck_id>/source.pptx <project>/analysis/fill_plan.json \
  -o <project>/exports/<name>.pptx
```

`check-plan` 必须 `error=0`。出现 `ratio>1.2` 的警告就回去改文案。

`apply` 会为输出文件追加时间戳。下方 `<实际导出路径>` 必须取自导出日志，不能假定文件名仍是 `-o` 中的名称。

`apply` 之后必须过一遍版面体检——`check-plan` 只验槽位容量，验不了生成后的实际版面：

```bash
python3 ${SKILL_DIR}/scripts/review_pptx.py <实际导出路径>.pptx --min-level warn
```

它会报出文字溢出、字体被自动挤压、文字块互压、越界、占位符残留等，按页给位置与建议。
**退出码 1 = 有硬伤，改完重跑，不许直接交付。**

## 6. 交付前确认

- [ ] `check-plan` 无 error
- [ ] `review_pptx.py` 无 ERROR（WARN 要么修，要么写进交付说明）
- [ ] 页数与预期一致，章节页复用次数正确
- [ ] 每页文字没有压到装饰、照片、边框
- [ ] 图片、表格、图表仍在原位（原生填充不该动它们）
- [ ] 渲染检查全部页面，放大核对封面、最密正文页和结束页。使用 PowerPoint 或可用的演示软件导出预览；本路线不调用 `pptx_to_svg.py`。无渲染环境时明确披露视觉复核未完成。

## 7. 交付话术

```text
已生成：<路径>
模板：厦门大学_主题_凤凰花开（原始模板，未重绘）
页数：9（源模板 11 页，复用了 3 次章节页、2 次内容页）
保留：全部照片、红色标题条、校徽圆章、原字体字号
需要你确认：第 4 页标题已缩短到 6 字，避免压到右边界
```

---

## 已知边界

- **`.ppt` 格式不支持**：`厦门大学_官方_南强蔚蓝` 原始文件是 `.ppt`，需先用 PowerPoint 另存为 `.pptx` 才能入库。
- **组合形状内的文本**：部分模板把内容放在 group 里，`pptx_intake` 读不到组内坐标（geometry 全 0）。这类页不要选。
- **表格与图表**：只有原始模板里存在原生表格/图表时才能改；用形状拼出来的"假表格"只能当文字改。
