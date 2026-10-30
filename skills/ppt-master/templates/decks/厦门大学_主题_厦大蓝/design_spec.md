---
deck_id: 厦门大学_主题_厦大蓝
kind: deck
summary: 厦门大学PPT模板 · 清爽蓝白 + 建筑照片 + 斜向蓝条
canvas_format: ppt169
page_count: 5
primary_color: "#6096E6"
---

# 厦门大学_主题_厦大蓝 - Design Specification

> 厦门大学PPT模板 · 清爽蓝白 + 建筑照片 + 斜向蓝条

## II. 画布

- 1280 × 720（viewBox `0 0 1280 720`）

## III. 配色（来自原 PPT 主题）

- `dk1` = `#000000`
- `lt1` = `#FFFFFF`
- `dk2` = `#0F1423`
- `lt2` = `#FFFFFF`
- `accent1` = `#6096E6`
- `accent2` = `#58B6E5`
- `accent3` = `#56CA95`
- `accent4` = `#FFBA55`
- `accent5` = `#F18870`
- `accent6` = `#EC5F74`
- `hlink` = `#0563C1`
- `folHlink` = `#954D72`

## IV. 字体

- majorLatin: `Arial`
- minorLatin: `Arial`
- minorEastAsia: `微软雅黑`

## V. 页面原型

| 文件 | 角色 | 原文件中的页码 |
| --- | --- | --- |
| 01_cover.svg | 封面 | 1 |
| 02_toc.svg | 目录 | 2 |
| 02_chapter.svg | 章节 | 5 |
| 03_content.svg | 内容 | 3 |
| 04_ending.svg | 结束 | 15 |

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
