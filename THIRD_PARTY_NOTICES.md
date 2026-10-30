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
| 校园实景照片 | `厦门大学_官方_厦园晴日/campus_bg.jpg`、`chapter_bg.jpg`、`ending_bg.jpg` | 官方模板内嵌照片 |
| 校训竖版图 | `厦门大学_官方_厦园晴日/side_tab.jpg` | 校徽 + 自强不息 止于至善 |
| 凤凰花、天鹅装饰 | `厦门大学_官方_厦园晴日/flower.png`、`swan.png` | 官方模板装饰素材 |
| 宣纸底纹、绿瓦屋顶、陈嘉庚雕像 | `厦门大学_官方_凤栖青橙/paper_bg.jpg`、`roof.png`、`statue.png` | 官方模板素材 |
| 扁平化建筑插画 | `厦门大学_官方_南强蔚蓝/building.png` | 官方模板素材 |
| 原始 PPTX 模板 | 未随仓库分发 | 保留在作者本地 |

如果要将本仓库公开到 GitHub，建议：

1. 保留 MIT 代码与模板结构；
2. 在 README 中明确“校徽与官方素材仅限校内非商业使用”；
3. 如需完全开源，可移除上述图片素材，仅保留 SVG 结构与占位，由使用者自行放入校徽与照片。

## 3. 字体

本仓库不包含任何字体文件。设计稿中引用的 `华文中宋`、`微软雅黑`、`方正兰亭黑` 均为商业字体，需由使用者自行确保授权；缺失时会回退到系统默认的宋体/黑体。

## 4. 生成工具依赖

`python-pptx`、`PyYAML`、`XlsxWriter`、`skia-pathops`、`uharfbuzz`、`edge-tts` 等依赖遵循各自的开源许可证，详见 `skills/ppt-master/requirements.txt`。
