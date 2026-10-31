---
deck_id: 厦门大学_主题_光影厦大
kind: deck
summary: 厦门大学PPT模板 · 深蓝几何光影 + 光影校园照
canvas_format: ppt169
page_count: 5
primary_color: "#2E75B6"
placeholders:
  01_cover: []
  02_toc: []
  02_chapter: []
  03_content: []
  04_ending: []
---

# 厦门大学_主题_光影厦大 - Design Specification

> 厦门大学PPT模板 · 深蓝几何光影 + 光影校园照

## II. 画布

- 1280 × 720（viewBox `0 0 1280 720`）

## III. 配色（实测自主 SVG 用色）

> 由本套 5 页 SVG 的 `fill` / `stroke` / `stop-color` 频次统计得出，已剔除纯黑、纯白与低饱和灰。
> 原 PPTX 主题色板只是 Office 默认值，不代表本套视觉主色，仅作追溯，见本节末。

| Token | HEX | 角色 | 出现次数 |
| --- | --- | --- | --- |
| `accent1` | `#2E75B6` | **主色**（中蓝） | 55 |
| `accent2` | `#BDD7EE` | 次级色（浅蓝） | 14 |
| `accent3` | `#203864` | 点缀色（深蓝） | 1 |
| `accent4` | `#8FAADC` | 辅助色（浅蓝） | 1 |
| `accent5` | `#649DD2` | 辅助色（中蓝） | — |
| `accent6` | `#235079` | 辅助色（深蓝） | — |
| `dk1` | `#000000` | 正文深色文字（中性） | 4 |
| `dk2` | `#2F5597` | 深底／强调（中蓝） | 2 |
| `lt1` | `#FFFFFF` | 主背景（中性） | 13 |
| `lt2` | `#EBF0F5` | 浅色底块（浅蓝） | — |
| `hlink` | `#2E75B6` | 链接色（中蓝） | 55 |
| `folHlink` | `#BDD7EE` | 已访问链接（浅蓝） | 14 |

**取色规则**：正文与装饰一律取 `accent1`；需要深浅层次时用 `accent1` 的同色系变体，不要引入本表之外的颜色。`dk1` 只用于正文文字，`lt1` 只用于背景。

### 附：原 PPTX 主题色板（仅供追溯，勿用作设计取色）

- `dk1` = `#000000`
- `lt1` = `#FFFFFF`
- `dk2` = `#44546A`
- `lt2` = `#E7E6E6`
- `accent1` = `#5B9BD5`
- `accent2` = `#ED7D31`
- `accent3` = `#A5A5A5`
- `accent4` = `#FFC000`
- `accent5` = `#4472C4`
- `accent6` = `#70AD47`
- `hlink` = `#0563C1`
- `folHlink` = `#954F72`

---


## IV. 字体

- majorLatin: `Calibri Light`
- minorLatin: `Calibri`

## V. Page Roster（页面原型）
| 文件 | 角色 | 原文件中的页码 |
| --- | --- | --- |
| `01_cover.svg` | 封面 | 1 |
| `02_toc.svg` | 目录 | 2 |
| `02_chapter.svg` | 章节 | 3 |
| `03_content.svg` | 内容 | 4 |
| `04_ending.svg` | 结束 | 9 |

## VI. 使用说明

- 本套模板由原 PPTX 一比一转换（create-template / mirror），页面保留原示例文字。
- 生成新 PPT 时，只改文本内容，不要改图形、图片、版式与装饰。
- 换页数时优先复制 `03_content.svg` 做内容页，复制 `02_chapter.svg` 做章节页。
- 颜色与字体以原文件为准；不要引入与风格冲突的新颜色。

## VII. 技术约束

1. viewBox 固定 `0 0 1280 720`
2. 只使用基础图形、文本、图片与 `linearGradient`
3. 禁止 `mask`、`<style>`、`class`、`foreignObject`、`textPath`、`animate*`、`script`
4. 图片相对路径引用 `assets/`

## 成稿正文可读性

SVG 原型中的示例小字不作为新写正文的字号标准。1280×720 画布下，新写正文优先使用 24–28px，注释 16–18px；写入项目 `spec_lock.md`，空间不足时拆页或精简。固定页脚、品牌字和原模板装饰文字可保留原尺寸。原生填充保留源样式，交付前需以实际投影用途检查可读性。
