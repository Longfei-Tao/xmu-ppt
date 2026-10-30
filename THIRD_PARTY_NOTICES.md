# 第三方声明 / Third-Party Notices

## 1. 上游代码

本仓库基于 **PPT Master** 修改而来：

- 项目：https://github.com/hugohe3/ppt-master
- 作者：Hugo He
- 许可证：MIT（Copyright (c) 2025-2026 Hugo He）

MIT 许可证允许修改、再分发与商用，但要求在任何副本中保留原始版权声明与许可声明。本仓库根目录的 `LICENSE` 同时保留了上游与本仓库的版权行。

上游仓库中的 `references/ai-image-comparison/` 图片示例目录未纳入本仓库（约 43 MB），其余 `skills/ppt-master/` 内容保持原样。

## 2. 厦门大学素材（不在 MIT 授权范围内）

以下素材版权归 **厦门大学** 所有，仅用于校内学习、教学与科研演示，**不得公开售卖或作为商业产品分发**：

| 素材 | 位置 | 说明 |
| --- | --- | --- |
| 厦门大学校徽组合标志 | `skills/ppt-master/templates/brands/厦门大学/xmu_logo.png` 及各 deck 目录 | 校徽与校名标准字 |
| 校园实景照片 | `厦门大学_官方_厦园晴日/campus_bg.jpg`、`chapter_bg.jpg`、`ending_bg.jpg` | 原始模板内嵌照片 |
| 校训竖版图 | `厦门大学_官方_厦园晴日/side_tab.jpg` | 校徽 + 自强不息 止于至善 |
| 凤凰花、天鹅装饰 | `厦门大学_官方_厦园晴日/flower.png`、`swan.png` | 原始模板装饰素材 |
| 宣纸底纹、绿瓦屋顶、陈嘉庚雕像 | `厦门大学_官方_凤栖青橙/paper_bg.jpg`、`roof.png`、`statue.png` | 原始模板素材 |
| 扁平化建筑插画 | `厦门大学_官方_南强蔚蓝/building.png` | 原始模板素材 |
| 原始 PPTX 模板 | `skills/ppt-master/templates/decks/<deck_id>/source.pptx` | 已剥离内嵌商业字体、图片降采样；版权仍归原作者与厦门大学 |

### 2.1 关于 `source.pptx`

`templates/decks/<deck_id>/source.pptx` 是从校内流传的答辩模板整理而来，用于「原生填充」路线（在原始模板里嵌内容）。入库时做了两项处理：

- 剥离 `ppt/fonts/` 中内嵌的商业字体（既不可再分发，也占原体积 70% 以上）；
- 将超过 1440px 的图片降采样并重编码。

**未处理**：这些模板中的校园照片、校徽、装饰图形的版权状态与原文件一致，仍归厦门大学或原作者所有，同样仅限校内非商业使用。

### 2.2 已采取的合规措施

本仓库为**个人非官方项目**，与厦门大学无隶属、授权或背书关系。为明确边界，已采用以下措施：

1. **许可证分层**：代码与模板结构按 MIT 发布；校徽、校园照片等学校素材明确排除在 MIT 授权之外（见 `LICENSE` 顶部的 SCOPE EXCLUSION 段）；
2. **醒目声明**：README 首段设有独立「非官方声明」区块，而非仅在文末提及；
3. **命名澄清**：模板 ID 中的「官方」二字为早期目录命名，含义是「按学校视觉规范精修重制」，**不代表学校出品或授权**；因该命名已被大量示例、命令与索引文件引用，为保证现有用法不被破坏而保留；
4. **字体清理**：仓库不包含任何商业字体文件。

### 2.3 使用者责任

- 校徽、校名与校园照片**仅限校内学习、教学、科研演示**等非商业场景；
- 对外正式发布（商业路演、公开出版、对外宣传物料等）前，请自行向学校相关部门确认素材使用范围与视觉规范要求；
- 因使用本仓库素材产生的任何争议，由使用者自行承担，与本项目作者及厦门大学无关。

### 2.4 权利主张与下架

若厦门大学相关部门或素材权利人认为本仓库内容不妥，请通过 Issue 联系，作者将在收到通知后立即调整或移除相关内容，不持异议。

## 3. 字体

本仓库不包含任何字体文件。设计稿中引用的 `华文中宋`、`微软雅黑`、`方正兰亭黑` 均为商业字体，需由使用者自行确保授权；缺失时会回退到系统默认的宋体/黑体。

## 4. 生成工具依赖

实际直接引用的第三方包为：`python-pptx`、`PyYAML`、`Pillow`、`requests`、`beautifulsoup4`、`curl_cffi`、`PyMuPDF`、`openpyxl`、`mammoth`、`markdownify`、`ebooklib`、`nbconvert`、`edge-tts`、`google-genai`、`flask`、`numpy`、`svglib`、`reportlab`。可选：`cairosvg`、`playwright`。

完整清单与用途见 `skills/ppt-master/requirements.txt`，各包遵循其自身的开源许可证。

> 说明：`XlsxWriter` 不是本项目的直接依赖（仅在安装 `python-pptx` 时被间接引入）；`skia-pathops`、`uharfbuzz` 在上游旧版本中使用，本分支代码已不再引用两者。
