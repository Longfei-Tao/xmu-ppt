# 进阶使用与维护

[返回首页](../README.md) · [快速开始](quickstart.md)

以下命令从仓库根目录执行，使用已安装核心依赖的 Python。示例中的反斜杠续行适用于 Bash；PowerShell 请合并为一行。占位路径需替换成实际路径。

## 手动使用

### A. SVG 出稿

```bash
# 1. 生成项目骨架
python skills/ppt-master/scripts/project_manager.py init demo --format ppt169

# 2. 校验模板页（只检查素材库，不是成稿验收）
python skills/ppt-master/scripts/svg_quality_checker.py \
  skills/ppt-master/templates/decks/厦门大学_官方_厦园晴日 --template-mode --canonical-authoring

# 3. Agent 在实际项目目录写好页面与 spec_lock 后，先检查成稿再导出
# init 打印的目录一般为 projects/demo_ppt169_YYYYMMDD，请用日志中的实际值
python skills/ppt-master/scripts/svg_quality_checker.py "<实际项目目录>/svg_output" --canonical-authoring
python skills/ppt-master/scripts/svg_to_pptx.py "<实际项目目录>" -s svg_output -t fade -a none
```

### B. 原生填充

```bash
# 1. 看版式清单，决定用哪几页
cat skills/ppt-master/templates/decks/厦门大学_主题_凤凰花开/layout_index.json

# 2. 生成填充计划骨架（--slides 是源页号，可重复、可重排）
python skills/ppt-master/scripts/template_fill_pptx.py scaffold \
  skills/ppt-master/templates/decks/厦门大学_主题_凤凰花开/source.slide_library.json \
  -o fill_plan.json --slides "1,2,3,5,8"

# 3. 手改 fill_plan.json 里的 text

# 4. 校验容量，再导出
python skills/ppt-master/scripts/template_fill_pptx.py check-plan \
  skills/ppt-master/templates/decks/厦门大学_主题_凤凰花开/source.slide_library.json fill_plan.json
python skills/ppt-master/scripts/template_fill_pptx.py apply \
  skills/ppt-master/templates/decks/厦门大学_主题_凤凰花开/source.pptx fill_plan.json -o out.pptx
# 输出自动附加时间戳，后续检查请使用日志中的实际文件路径。
```

### C. 新增一套模板

```bash
python skills/ppt-master/scripts/build_layout_index.py \
  "D:/我的模板/某套模板.pptx" --deck-id 厦门大学_主题_某套
```

它会剥离内嵌字体、压缩图片、生成 `layout_index.json` 与 `source.slide_library.json`，放进 `templates/decks/厦门大学_主题_某套/`。

### D. 生成后自检（两条路线都适用）

```bash
python skills/ppt-master/scripts/review_pptx.py "<实际导出路径>.pptx" --min-level warn
```

直接读 PPTX 的 OOXML 做版面体检，不需要打开 PowerPoint，也不需要截图：

| 能查出 | 判据 |
| --- | --- |
| 文本溢出 | 排版后所需高度 ÷ 框内可用高度 ≥ 1.15 |
| 字体被挤压 | 被 PowerPoint 自动缩到 90% 以下 |
| 元素重叠 | 两块文字区域相交 ≥ 25% |
| 越界 | 文字估算区域超出左右或上下边界 |
| 间距过密 | 上下两段文字间距 < 4pt |
| 占位符残留 | 还留着 `{{...}}` 或 `XXX` |
| 字号过小 | 实际字号 < 9pt |
| 格式错乱 | 同一文本框内混了多种字体/字号 |

每条问题给出页码、形状位置、实测数值和修改建议；`--json` 出机器可读报告；有 ERROR 时退出码为 1，可以直接挡在交付前。

新增源模板会写入指定模板目录；运行前备份同名模板并确认素材许可，不直接覆盖待核验来源的文件。

## 依赖

- **Python 3.10+**（脚本使用 `X | None` 形式的类型注解，3.9 会在导入时抛 `TypeError`）
- 核心：`requirements-core.txt`（`python-pptx`、`PyYAML`、`Pillow`、`requests`），默认出稿不需要图片生成 API 或 TTS
- 按需：PDF / Word / Excel 转换、图片搜索、TTS 等，完整清单见 `skills/ppt-master/requirements.txt`
- 可选：`cairosvg` 或 `svglib`（导出时生成 PNG 后备图）、`playwright`（逐页视觉复核）
- 可选：Microsoft PowerPoint（用于导出 PNG 预览）

## 开发验证

```bash
python -m unittest discover -s tests -v
python skills/ppt-master/scripts/audit_xmu.py --check-svg --json .cache/xmu-audit.json
python scripts/check_docs.py
```

GitHub Actions 会在 Windows / Linux、Python 3.10 / 3.13 上运行回归与资产检查。结构检查不能替代演示软件渲染；交付前应检查全部页面，并放大检查封面、最密正文页、结束页和 Logo。`review_pptx.py` 对顶层文本做估算排版检查，对组合形状和表格只扫描占位符，不能保证所有复杂版面都无溢出。

审查范围、已修复项和能力边界见 [审查记录](plugin-audit.md)。
