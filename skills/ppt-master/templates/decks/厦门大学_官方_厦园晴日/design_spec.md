---
deck_id: 厦门大学_官方_厦园晴日
kind: deck
summary: 厦门大学论文答辩、开题报告、课程汇报与科研组会（蓝白校园实景风）
canvas_format: ppt169
page_count: 5
primary_color: "#005FA5"
---

# 厦门大学「厦园晴日」模板 - Design Specification

> 源自厦门大学 2025 实用风模板系列之「壹 厦园晴日」。以校园实景照片为底，白色半透明信息卡承载文字，蓝色弧形色块与三角阵列作为固定装饰。

---

## I. Template Overview

| Property | Description |
| --- | --- |
| **Template Name** | 厦门大学 · 厦园晴日 |
| **Use Cases** | 论文答辩、开题报告、课程汇报、组会汇报、科研成果展示 |
| **Design Tone** | 明亮、正式、学院感、不过度设计 |
| **Design Features** | 校园实景照片底图；白色半透明信息卡；浅蓝弧形色块；深蓝三角阵列；校徽固定在左上角 |

---

## II. Canvas Specification

| Property | Value |
| --- | --- |
| **Format** | Standard 16:9 |
| **Dimensions** | 1280 × 720 px |
| **viewBox** | `0 0 1280 720` |
| **Page Margins** | 左右 46px，上下 41px |
| **Content Safe Area** | x: 72–1208，y: 96–650 |

---

## III. Color Scheme

| Role | Value | Notes |
| --- | --- | --- |
| **厦园蓝** | `#005FA5` | 标题强调、目录序号、胶囊色块、页码 |
| **校徽深蓝** | `#204080` | 结束页主标题 |
| **晴空浅蓝** | `#BAE2FF` | 弧形色块、三角、横条装饰 |
| **链接蓝** | `#4874CB` | 外边框、分隔线、图标 |
| **正文黑** | `#1A1A1A` | 标题与正文 |
| **卡片白** | `#FFFFFF`（79% 不透明） | 封面／结束页信息卡 |
| **辅助灰蓝** | `#6B7B8C` | 页脚、备注 |

---

## IV. Typography System

| Level | Usage | Size | Weight |
| --- | --- | --- | --- |
| H1 | 封面主标题 | 64px | Bold |
| H2 | 章节标题 | 52px | Bold |
| H3 | 内容页标题 | 34px | Bold |
| H4 | 目录条目 | 38px | Regular |
| P | 正文／说明 | 14–20px | Regular |
| Num | 目录数字 | 64px | Bold |
| Sub | 页脚 | 12–13px | Regular |

**Font Stack**：`"微软雅黑", "Microsoft YaHei", "PingFang SC", "Source Han Sans SC", sans-serif`；数字用 `"Manrope", "Inter", Arial, sans-serif`。

---

## V. Core Visual Elements

1. **校园实景底图**：封面与结束页铺满 `campus_bg.jpg` / `ending_bg.jpg`，章节页左半幅使用 `chapter_bg.jpg`。
2. **白色半透明信息卡**：封面与结束页 `x=96.73 y=226 w=1087.13 h=272.6`，`fill-opacity=0.79`，不加描边和阴影。
3. **弧形色块**：右上、左下两块 `#BAE2FF` 弧形，是整套模板的识别符号，所有页面保持一致。
4. **三角阵列与圆点**：深蓝小三角竖排 5 个，圆点直径约 41px，位于页面四角。
5. **侧边校训条**：内容页右上角 `side_tab.jpg`（校徽＋自强不息 止于至善），宽 68px。
6. **凤凰花图标**：内容页标题左侧 `flower.png`，宽 52px。

---

## VI. Page Types

### 1. 封面（01_cover.svg）
- 铺满校园照片，外描 1px 边框
- 半透明白卡居中：主标题、副标题、分隔线、指导老师／答辩人、学院与日期
- 校徽固定左上角，尺寸 258.73 × 74.27

### 2. 目录（02_toc.svg）
- 顶部深蓝胶囊「目录/Contents」，两侧黑天鹅装饰
- 2×2 排列：`01–04` 大号数字 + 目录条目
- 四角弧形块、三角阵列、横条保持与封面一致

### 3. 章节过渡（02_chapter.svg）
- 左半幅校园照片（724.67 × 638.73），右侧留白
- PART 胶囊 + 章节标题 + 一句章节说明

### 4. 内容页（03_content.svg）
- 页眉：凤凰花 + 页面标题，右上角校徽与校训条
- 核心观点条（浅蓝底 + 左侧 3px 蓝条）
- 虚线内容区占位 `1040 × 384`
- 页脚：资料来源 / 章节名 / 页码

### 5. 结束页（04_ending.svg）
- 与封面同构：校园照片 + 白卡
- 主标题默认「恳请各位老师批评指正」

---

## VII. SVG Page Roster

| File | Role | Description |
| --- | --- | --- |
| `01_cover.svg` | cover | 封面：主标题 + 副标题 + 答辩信息 |
| `02_toc.svg` | toc | 目录：4 个条目 |
| `02_chapter.svg` | chapter | 章节过渡页 |
| `03_content.svg` | content | 正文页 |
| `04_ending.svg` | ending | 结束页 |

---

## VIII. Logo Usage Guidelines

| File | Context | Size |
| --- | --- | --- |
| `xmu_logo.png` | 浅色背景（封面左上、内容页右上） | 封面宽 258.73；内容页宽 150 |

- 禁止拉伸、改色、加描边或阴影
- 深色照片区域不要直接放蓝色校徽

---

## IX. Spacing Specification

| Element | Value |
| --- | --- |
| 页面外边距 | 46px |
| 卡片内边距 | 24px |
| 卡片圆角 | 0（保持原模板直角卡片） |
| 胶囊圆角 | 高度的一半 |
| 内容块间距 | 24–28px |

---

## X. SVG Technical Constraints

1. viewBox 固定 `0 0 1280 720`
2. 只使用 `<rect>` `<circle>` `<ellipse>` `<polygon>` `<path>` `<line>` `<text>` `<tspan>` `<image>` `<defs>` `<linearGradient>`
3. 禁止 `mask`、`<style>`、`class`、`foreignObject`、`textPath`、`animate*`、`script`
4. 颜色必须写成 `#RRGGBB`，透明用 `fill-opacity` / `stroke-opacity`
5. 图片使用相对路径引用同目录资源
6. 文字保持可编辑，不转曲

---

## XI. Placeholder Specification

| Placeholder | Description |
| --- | --- |
| `{{TITLE}}` | 封面主标题 |
| `{{SUBTITLE}}` | 副标题（学院/班级/专业） |
| `{{AUTHOR}}` | 答辩人 |
| `{{ADVISOR}}` | 指导老师 |
| `{{INSTITUTION}}` | 学院/单位 |
| `{{DATE}}` | 日期 |
| `{{PAGE_TITLE}}` | 内容页标题 |
| `{{CHAPTER_NUM}}` | 章节序号（01、02…） |
| `{{CHAPTER_TITLE}}` | 章节标题 |
| `{{CHAPTER_DESC}}` | 章节说明 |
| `{{KEY_MESSAGE}}` | 核心观点 |
| `{{CONTENT_AREA}}` | 内容区 |
| `{{SECTION_NAME}}` | 页脚章节名 |
| `{{SOURCE}}` | 资料来源 |
| `{{PAGE_NUM}}` | 页码 |
| `{{THANK_YOU}}` | 结束页致谢语 |
| `{{CONTACT_INFO}}` | 联系方式 |
| `{{TOC_ITEM_1_TITLE}}` … `{{TOC_ITEM_4_TITLE}}` | 目录条目 |
