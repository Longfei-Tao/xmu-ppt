# 厦门大学 PPT / XMU PPT Master

把主题、提纲或现有材料，整理成厦大风格的演示文稿。

面向论文答辩、科研组会、课程展示与校园项目汇报。基于 [PPT Master](https://github.com/hugohe3/ppt-master) 的 SVG → PPTX 引擎，提供 **14 套厦大 SVG 模板、13 套原生填充模板**，由 AI Agent 组织内容、排版并导出 `.pptx`。

[快速开始](docs/quickstart.md) · [选择你的 AI 工具](docs/tools/README.md) · [模板风格](docs/templates.md) · [English](README.en.md)

![自主编写的蓝白演示稿：封面、目录、正文和示意图表，来自实际 PPTX 的 PowerPoint 截图](examples/quickstart/preview/overview.png)

上图是本仓库引擎导出的四页演示，使用虚构示意内容，不含校徽或校园照片，不代表完整厦大品牌模板。[下载 PPTX](examples/quickstart/demo.pptx) · [查看需求、源稿与单页大图](examples/quickstart/README.md)。已有校徽模板的外观见[模板总览](docs/templates.md)。

> 非官方个人项目，与厦门大学不存在已确认的授权或合作关系。代码与模板结构适用 [MIT](LICENSE)；校徽、照片、字体等不因此获得授权。部分既有素材的公开再分发条件仍[待核验](docs/assets.md)。

## 输入与输出

你可以直接这样说：

```text
用 ppt-master 做一份厦大风格的校园科研协作汇报，约 10 页。
内容包括：材料管理、责任分工、进度安排与提交复核。
没有实测数据，请写成方案建议，不编造结果。输出 PPTX。
```

| 你提供什么 | Agent 如何处理 | 最终得到什么 |
| --- | --- | --- |
| 一个主题或想法 | 补全叙事结构，默认制作方案或知识介绍稿 | `.pptx`；不会据此编造研究结果 |
| 提纲、文档或旧汇报材料 | 提炼内容，选择厦大模板，逐页排版 | `.pptx` 和可继续修改的项目源稿 |
| 指定模板和新内容 | 克隆适用源页，填充文字与支持的表格、图表 | 受原版式容量约束的 `.pptx` |

默认只需接收演示文稿与必要说明。文字和简单图形可导出为原生对象，照片等仍是图片；复杂图表与排版需逐页检查，不能保证所有元素均可编辑或格式完全一致。

## 快速开始

需要 **Python 3.10+**、Git，以及能读取文件和运行 Python 的 AI Agent。先在本机终端准备源码和依赖：

```bash
git clone https://github.com/Longfei-Tao/xmu-ppt.git xmu-ppt-master
cd xmu-ppt-master
python -m venv .venv
```

按系统安装核心依赖：

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe -m pip install -r skills/ppt-master/requirements-core.txt
```

```bash
# macOS / Linux
.venv/bin/python -m pip install -r skills/ppt-master/requirements-core.txt
```

在 AI 工具中打开这个仓库，把下面一段发给它，即可先从源码使用，无需修改全局配置：

```text
请读取 skills/ppt-master/SKILL.md，按其中的厦大工作流制作上一条需求的 PPT。
以该文件所在目录为技能根目录，使用本仓库 .venv 内的 Python。
把生成文件放在独立项目目录中，完成后给我 PPTX 的实际路径。
```

第一次使用时把“上一条需求”替换成自己的主题，或先发送上面的示例需求。完整步骤、环境说明及常见问题见[快速开始](docs/quickstart.md)。

## 在你的 AI 工具中使用

| 工具 | 使用入口 | 本仓库验证范围 |
| --- | --- | --- |
| Codex | [项目 Skill 与源码调用](docs/tools/codex.md) | 当前 Windows 会话已运行本地脚本；未做全新安装验收 |
| Claude Code | [项目 Skill 与 `/ppt-master`](docs/tools/claude-code.md) | 已按官方机制编写文档，未实机验证 |
| GitHub Copilot | [Agent 模式与项目 Skill](docs/tools/copilot.md) | 已按官方机制编写文档，未实机验证 |
| Gemini CLI | [工作区 Skill](docs/tools/gemini-cli.md) | 已按官方机制编写文档，未实机验证 |
| 网页聊天或其他工具 | [环境要求与手动流程](docs/tools/README.md) | 有文件执行环境才可能运行；不承诺原生安装 |

使用 CC Switch 管理共享 Skills 时，请在 CC Switch 中维护和分发；不要直接覆盖它生成的客户端副本。本仓库尚未提供插件商店安装包或远程 MCP 服务。

## 选择风格

| 风格 | 适合的内容 |
| --- | --- |
| 厦园晴日：蓝白、校园照片、明亮留白 | 答辩、开题、毕业汇报 |
| 凤栖青橙：纸感、青绿、橙色点缀 | 人文社科、读书报告、课程展示 |
| 南强蔚蓝：蓝紫、建筑插画、分栏结构 | 组会、项目与工作汇报；目前仅 SVG 路线 |

还有凤凰花开、经典蓝白、米金书法等 11 套主题。[查看完整清单与既有原型](docs/templates.md)。

## 使用前了解

- **生成需要 Agent。** Python 脚本负责分析、转换与检查，不会独立调用大模型完成主题创作；AI 工具本身的账号或费用另计。
- **真实汇报需要真实材料。** 未提供的实验结果、参考文献、个人信息应省略或补充来源，不能让模型猜测。
- **效果受环境影响。** 缺少字体会改变换行；SVG 转换与原生填充也各有边界。上台前请用目标演示软件检查全部页面。
- **数据不自动“全程本地”。** 转换脚本在执行环境运行，交给 AI 的材料仍受所选工具的数据政策影响；云端也无法直接访问本机路径。
- **学校素材单独核验。** 公开下载入口不等于公开再分发许可；本项目不代表厦门大学官方出品。

[进阶命令与依赖](docs/advanced.md) · [贡献指南](CONTRIBUTING.md) · [素材与许可](docs/assets.md) · [上游致谢](CREDITS.md)
