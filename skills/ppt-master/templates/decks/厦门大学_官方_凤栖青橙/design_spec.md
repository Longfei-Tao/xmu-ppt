---
deck_id: 厦门大学_官方_凤栖青橙
kind: deck
summary: 厦门大学人文社科类答辩、课程汇报与研究成果展示（宣纸宋体 · 嘉庚建筑风）
canvas_format: ppt169
page_count: 5
primary_color: "#D37820"
---

# 厦门大学「凤栖青橙」模板 - Design Specification

> 源自厦门大学 2025 实用风模板系列之「叁 凤栖青橙」。宣纸质感底纹、宋体大字、绿瓦屋顶与陈嘉庚雕像构成完整的人文视觉语言。

---

## I. Template Overview

| Property | Description |
| --- | --- |
| **Template Name** | 厦门大学 · 凤栖青橙 |
| **Use Cases** | 人文社科答辩、课程汇报、读书报告、研究成果展示、校园文化活动 |
| **Design Tone** | 人文、克制、编辑感、有纸张温度 |
| **Design Features** | 宣纸底纹；超大字宋体；绿瓦屋顶插画；陈嘉庚雕像；橙色序号；蓝色建筑线稿 |

---

## II. Canvas Specification

| Property | Value |
| --- | --- |
| **Format** | Standard 16:9 |
| **Dimensions** | 1280 × 720 px |
| **viewBox** | `0 0 1280 720` |
| **Page Margins** | 左右 90px，上下 40px |
| **Content Safe Area** | x: 90–1190，y: 100–660 |

---

## III. Color Scheme

| Role | Value | Notes |
| --- | --- | --- |
| **青橙** | `#D37820` | 序号、标签、强调线 |
| **苔绿** | `#647F5E` | 分隔线、色带 |
| **纸色** | `#F2EDE2` | 宣纸底纹近似色（实际使用 `paper_bg.jpg`） |
| **墨黑** | `#111111` | 大标题 |
| **正文黑** | `#1A1A1A` | 正文 |
| **灰褐** | `#7A7466` | 辅助说明、页脚 |
| **校徽蓝** | `#204080` | 底部细线、建筑线稿 |

---

## IV. Typography System

| Level | Usage | Size | Weight |
| --- | --- | --- | --- |
| H1 | 封面主标题 | 88px | Bold |
| H2 | 章节数字 | 110px | Bold |
| H3 | 页面标题 | 46px | Bold |
| H4 | 目录条目 | 26px | Regular |
| P | 正文 | 17–20px | Regular |
| Num | 目录序号 | 44px | Bold |

**Font Stack**：`"华文中宋", "Source Han Serif SC", "思源宋体", "SimSun", serif`；数字用 `"Manrope", Arial, sans-serif`。

> 这一套的识别度来自宋体大字。不要换成黑体，也不要加粗到失真。

---

## V. Core Visual Elements

1. **宣纸底纹**：`paper_bg.jpg` 铺满整页，不叠加渐变。
2. **绿瓦屋顶插画**：`roof.png` 固定在页面下半部，是整套模板的签名元素。
3. **陈嘉庚雕像**：`statue.png` 用于封面与结束页，永远位于左侧。
4. **蓝色建筑线稿**：`building_line.png` 用于目录页底部。
5. **橙色序号**：`01–04`，字号 44，宋体加粗。
6. **大字投影**：用同色文字错位 6px 复本模拟，不使用滤镜。

---

## VI. Page Types

### 1. 封面（01_cover.svg）
- 左下屋顶插画 + 雕像，右侧右对齐标题与汇报信息
- 校徽固定左上角，尺寸 138.07 × 39.4

### 2. 目录（02_toc.svg）
- 左侧超大字「目录」+ 斜体 Contents 水印
- 右侧 2×2 条目：橙色序号 + 宋体标题 + 一行说明
- 底部蓝色建筑线稿 + 一条深蓝底线

### 3. 章节过渡（02_chapter.svg）
- 左下屋顶插画，右侧右对齐 PART + 章节数字 + 章节标题
- 数字使用 110px 宋体，是整套模板最有记忆点的一页

### 4. 内容页（03_content.svg）
- 顶部橙色章节标签，宋体大标题 + 核心观点
- 苔绿细线分隔，下方半透明内容区
- 页脚左右分布章节名与页码

### 5. 结束页（04_ending.svg）
- 五段绿色色带 + 左侧雕像
- 右侧白色宋体「感谢垂听」+ 致谢语
- 底部 END 横线

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
| `xmu_logo.png` | 左上角固定 | 宽 138.07 |

- 宣纸底色与蓝色校徽对比度足够，不要加白底块
- 禁止改色、描边、投影

---

## IX. Spacing Specification

| Element | Value |
| --- | --- |
| 页面左右边距 | 90px |
| 标题与正文间距 | 44px |
| 色带高度 | 300px |
| 内容区高度 | 318px |

---

## X. SVG Technical Constraints

1. viewBox 固定 `0 0 1280 720`
2. 只使用基础图形、文本、图片与 `linearGradient`
3. 禁止 `mask`、`<style>`、`class`、`foreignObject`、`textPath`、`animate*`、`script`
4. 颜色写 `#RRGGBB`，透明用 `fill-opacity`
5. 旋转文字只用 `transform="rotate(...)"`，不使用 3D 变换
6. 图片相对路径引用同目录资源

---

## XI. Placeholder Specification

| Placeholder | Description |
| --- | --- |
| `{{TITLE}}` | 封面主标题 |
| `{{SUBTITLE}}` | 副标题 |
| `{{AUTHOR}}` | 汇报人 |
| `{{ADVISOR}}` | 指导老师 |
| `{{INSTITUTION}}` | 学院/单位 |
| `{{DATE}}` | 日期 |
| `{{PAGE_TITLE}}` | 页面标题 |
| `{{CHAPTER_NUM}}` | 章节数字（01、02…） |
| `{{CHAPTER_TITLE}}` | 章节标题 |
| `{{CHAPTER_DESC}}` | 章节说明 |
| `{{KEY_MESSAGE}}` | 核心观点 |
| `{{CONTENT_AREA}}` | 内容区 |
| `{{SECTION_NAME}}` | 章节名／页脚 |
| `{{SOURCE}}` | 资料来源 |
| `{{PAGE_NUM}}` | 页码 |
| `{{THANK_LINE_1}}` / `{{THANK_LINE_2}}` | 结束页两行大字（默认「感谢」「垂听」） |
| `{{THANK_YOU}}` | 致谢语（默认「恳请各位老师批评指正」） |
| `{{CONTACT_INFO}}` | 联系方式 |
| `{{TOC_ITEM_1_TITLE}}` … `{{TOC_ITEM_4_TITLE}}` | 目录条目标题 |
| `{{TOC_ITEM_1_DESC}}` … `{{TOC_ITEM_4_DESC}}` | 目录条目说明 |
