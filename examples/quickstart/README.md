# 四页蓝白工作流演示

[返回首页](../../README.md) · [完整厦大模板原型](../../docs/templates.md)

本例是为仓库展示自主编写的“校园科研协作项目汇报”，不是历史用户案例、科研结论或未经人工检查的一次性生成效果。它展示本仓库 SVG → PPTX 导出链路；未使用校徽、校园照片、校名标准字或第三方图片，因此不代表完整厦大品牌模板的外观。

[需求](brief.md) → [逐页 SVG](svg_output/) → [PPTX 实际产物](demo.pptx) → [PowerPoint 渲染记录](preview/render.json)。全部文本与几何图形为本次原创内容，适用仓库 LICENSE 中的代码与模板结构许可；字体文件不随产物分发。

![四页实际产物拼图](preview/overview.png)

## 页面与内容

| 页 | 内容 | 大图 |
| --- | --- | --- |
| 1 | 蓝白几何封面 | [封面](preview/slide-01.png) |
| 2 | 三部分目录 | [目录](preview/slide-02.png) |
| 3 | 问题与建议做法的两栏正文 | [正文](preview/slide-03.png) |
| 4 | 80% / 60% / 40% 的虚构示意进度 | [图表](preview/slide-04.png) |

进度图由原生文字和矩形组成，**不是带工作簿的 PowerPoint 原生图表**。该示例没有照片，不能作为照片保真测试；也不能据它判断所有厦大模板均已视觉验收。

## 已执行的检查

2026-10-31 在 Windows 上使用仓库导出器生成 `demo.pptx`，通过 Microsoft PowerPoint 16.0 只读打开，逐页导出 1600×900 PNG。拼图仅缩放组合这些实际截图。

检查全部四页截图，并放大检查正文与图表。PowerPoint 报告的字体名称为 Microsoft YaHei，本机存在该字体；未观察到乱码、重叠或截断，文本边界检查无发现。SVG canonical-authoring 与 PPTX 结构检查的结果见维护验证记录。本次未验证 WPS、macOS、移动端及其他字体环境。

## 复现导出

在仓库根目录，使用已安装[核心依赖](../../skills/ppt-master/requirements-core.txt)的 Python：

```bash
python skills/ppt-master/scripts/svg_quality_checker.py examples/quickstart/svg_output --canonical-authoring
python skills/ppt-master/scripts/svg_to_pptx.py examples/quickstart -s svg_output -o .cache/quickstart-demo.pptx -t none -a none
python skills/ppt-master/scripts/review_pptx.py .cache/quickstart-demo.pptx --min-level warn
```

复现命令写到 `.cache/`，不会覆盖已提交的示例。要更新展示产物，请先备份和比较，再显式替换 `examples/quickstart/demo.pptx`。

维护者在安装 PowerPoint 的 Windows 机器上，可用 `python scripts/render_showcase.py` 重新渲染固定的示例产物。此工具额外需要 `pywin32`，不会编辑 PPTX；发现已有 PowerPoint 进程时停止，需要用户自行保存并关闭后再运行。它会更新本例 `preview/` 文件；渲染工具不是普通用户的出稿依赖。
