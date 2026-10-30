---
deck_id: 厦门大学_官方_南强蔚蓝
kind: deck
summary: 厦门大学课程汇报、开题与答辩的现代简约风模板（蓝紫渐变 · 扁平建筑插画）
canvas_format: ppt169
page_count: 5
primary_color: "#4661CC"
---

# 厦门大学「南强蔚蓝」模板 - Design Specification

> 源自厦门大学 2025 实用风模板系列之「肆 南强蔚蓝」。浅蓝到粉紫的对角渐变、扁平化嘉庚建筑插画、方正兰亭黑大字，是这套模板的全部识别点。

---

## I. Template Overview

| Property | Description |
| --- | --- |
| **Template Name** | 厦门大学 · 南强蔚蓝 |
| **Use Cases** | 课程汇报、开题报告、答辩、社团宣讲、轻量级成果展示 |
| **Design Tone** | 现代、轻盈、年轻、扁平化 |
| **Design Features** | 蓝紫对角渐变；扁平建筑插画；分栏白线；圆角半透明卡片；大字标题 |

---

## II. Canvas Specification

| Property | Value |
| --- | --- |
| **Format** | Standard 16:9 |
| **Dimensions** | 1280 × 720 px |
| **viewBox** | `0 0 1280 720` |
| **Page Margins** | 左右 100px，上下 50px |
| **Content Safe Area** | x: 100–1180，y: 100–660 |

---

## III. Color Scheme

| Role | Value | Notes |
| --- | --- | --- |
| **南强蓝** | `#4661CC` | 主标题、章节名、数字 |
| **浅蓝** | `#6585CC` | 副标题、说明文字 |
| **渐变起点** | `#A2CAFF` | 左上 |
| **渐变中点** | `#CEDCFF` | 中部 |
| **渐变终点** | `#FAEEFF` | 右下 |
| **白线** | `#FFFFFF`（85%） | 分栏线 |
| **卡片** | `#FFFFFF`（35%） | 内容卡片 |

---

## IV. Typography System

| Level | Usage | Size | Weight |
| --- | --- | --- | --- |
| H1 | 封面主标题 | 64px | Bold |
| H2 | 章节标题 | 68px | Bold |
| H3 | 页面标题 | 42px | Bold |
| H4 | 目录条目 | 32px | Bold |
| P | 正文 | 15–18px | Regular |
| Num | 目录数字 | 40px | Bold |

**Font Stack**：`"方正兰亭黑", "FZLanTingHeiS-DB-GB", "微软雅黑", "Microsoft YaHei", "PingFang SC", sans-serif`；数字与英文用 `"Manrope", "Inter", Arial, sans-serif`。

> 方正兰亭黑不是每台电脑都有，会回退到微软雅黑；回退后字形略圆，但整体气质不变。

---

## V. Core Visual Elements

1. **对角渐变底**：`linearGradient` 从 `#A2CAFF` 到 `#FAEEFF`，方向左上→右下，固定不变。
2. **扁平建筑插画**：`building.png`（1159×1865 竖构图），封面与结束页固定在右侧。
3. **分栏白线**：章节页用 2px 白线切分版式，透明度 0.85。
4. **圆角半透明卡片**：内容页 `rx=28`，白色 35%。
5. **校徽**：右上角固定，宽 110px。

---

## VI. Page Types

### 1. 封面（01_cover.svg）
- 左半区：主标题、破折号副标题、汇报人、日期、学院
- 右半区：扁平建筑插画，顶部贴底边
- 校徽右上角

### 2. 目录（02_toc.svg）
- 左侧「目录 / CONTENT」大字
- 右侧 2×2 条目：数字 01–04 + 标题 + 一行说明
- 底部一条白色细线

### 3. 章节过渡（02_chapter.svg）
- 左侧大字章节标题 + PART 序号
- 白线把页面切成左大右小的四个区块
- 右侧三条要点（1.1 / 1.2 / 1.3 位置固定）

### 4. 内容页（03_content.svg）
- 顶部标题 + PART 标记
- 1100×440 的半透明圆角内容卡
- 页脚章节名与页码

### 5. 结束页（04_ending.svg）
- 「感谢垂听 / THANKS」
- 右侧建筑插画，底部学院与日期

---

## VII. SVG Page Roster

| File | Role | Description |
| --- | --- | --- |
| `01_cover.svg` | cover | 封面 |
| `02_toc.svg` | toc | 目录 |
| `02_chapter.svg` | chapter | 章节过渡 |
| `03_content.svg` | content | 正文 |
| `04_ending.svg` | ending | 结束页 |

---

## VIII. Logo Usage Guidelines

| File | Context | Size |
| --- | --- | --- |
| `xmu_logo.png` | 右上角固定 | 宽 110 |

- 渐变底为浅色，蓝色校徽可直接放置
- 不得缩放变形、不得加白底

---

## IX. Spacing Specification

| Element | Value |
| --- | --- |
| 页面左右边距 | 100px |
| 内容卡片圆角 | 28px |
| 内容卡片高度 | 440px |
| 分栏线宽度 | 2px |

---

## X. SVG Technical Constraints

1. viewBox 固定 `0 0 1280 720`
2. 渐变只使用 `<defs><linearGradient>`，色标写 `stop-color`
3. 禁止 `mask`、`<style>`、`class`、`foreignObject`、`textPath`、`animate*`、`script`
4. 透明使用 `fill-opacity` / `stroke-opacity`
5. 图片相对路径引用同目录资源

---

## XI. Placeholder Specification

| Placeholder | Description |
| --- | --- |
| `{{TITLE}}` | 封面主标题 |
| `{{SUBTITLE}}` | 副标题 |
| `{{AUTHOR}}` | 汇报人 |
| `{{INSTITUTION}}` | 学院/单位 |
| `{{DATE}}` | 日期 |
| `{{PAGE_TITLE}}` | 页面标题 |
| `{{CHAPTER_NUM}}` | 章节数字（01、02…） |
| `{{CHAPTER_TITLE}}` | 章节标题 |
| `{{CHAPTER_DESC}}` | 章节导语 |
| `{{CHAPTER_POINT_1}}` / `{{CHAPTER_POINT_1_DESC}}` | 章节要点 1 |
| `{{CHAPTER_POINT_2}}` / `{{CHAPTER_POINT_2_DESC}}` | 章节要点 2 |
| `{{CHAPTER_POINT_3}}` / `{{CHAPTER_POINT_3_DESC}}` | 章节要点 3 |
| `{{KEY_MESSAGE}}` | 核心观点 |
| `{{CONTENT_AREA}}` | 内容区 |
| `{{SECTION_NAME}}` | 页脚章节名 |
| `{{PAGE_NUM}}` | 页码 |
| `{{THANK_YOU}}` | 结束页主文案（默认「感谢垂听」） |
| `{{CONTACT_INFO}}` | 联系方式 |
| `{{TOC_ITEM_1_TITLE}}` … `{{TOC_ITEM_4_TITLE}}` | 目录条目标题 |
| `{{TOC_ITEM_1_DESC}}` … `{{TOC_ITEM_4_DESC}}` | 目录条目说明 |
