# 选择 AI 工具

[返回首页](../../README.md) · [共用准备步骤](../quickstart.md)

技能入口为 `skills/xmu-ppt/SKILL.md`，安装时保留整个 `skills/xmu-ppt/` 目录。下列机制按官方文档在 **2026-11-09** 核验，实际版本和组织策略可能不同。

| 入口 | 官方机制支持 | 本项目文档 | 本次实机验证 |
| --- | --- | --- | --- |
| [Codex](codex.md) | 项目目录 `.agents/skills/` | 项目安装、源码调用 | app-server 发现临时项目技能，已启用 |
| [Claude Code](claude-code.md) | `.claude/skills/` | 项目安装、显式调用 | 初始化列出技能，空目录对照未列出 |
| [Cursor](cursor.md) | `.cursor/skills/` 或 `.agents/skills/` | 项目安装、显式调用 | 未验证 |
| [GitHub Copilot](copilot.md) | 支持 Agent Skills 的 Agent 模式 | 项目目录 `.github/skills/` | CLI 列出项目技能并启用，IDE 待验收 |
| [Gemini CLI](gemini-cli.md) | 工作区 Skill 管理 | 本地目录安装、发现检查 | 原生安装、受信任工作区发现通过 |

“官方机制支持”只说明宿主提供 Skill 机制，不代表官方认可本项目或保证其脚本兼容。没有把本机 Python 测试当作多个 AI 客户端的端到端验收。

如果使用 CC Switch，优先由它导入和分发，不手工覆盖其客户端副本。独立安装步骤用于未受管理的工作区；有同名条目先核对来源、备份并处理冲突。

## 可直接发送的安装提示词

以下提示词用于安装。出稿时再发送主题、材料和页数。

```text
请从 https://github.com/Longfei-Tao/xmu-ppt 安装 xmu-ppt 技能。
先读取 README 和 skills/xmu-ppt/SKILL.md，按当前 Agent 的官方机制，
默认安装到项目范围，保留完整技能目录并核对是否存在同名技能。
若由 CC Switch 管理共享技能，回到 CC Switch 导入和分发。
遇到同名冲突，比较来源并在替换前让我确认。
保留完整源码仓库，创建 Python 3.10+ 虚拟环境并安装 requirements-core.txt。
运行 examples/quickstart 的四页导出，返回技能路径、解释器与 PPTX 路径，
分别报告文件已安装、宿主已发现技能、示例已导出三个状态。
完成后运行已安装技能的 scripts/install_skill.py --guide，
在对话里显示简短使用说明，让我知道可以直接描述主题或上传一批模板。
```

## 安装后直接显示使用说明

仓库提供项目级安装入口。完成[源码和依赖准备](../quickstart.md)后，从仓库根目录执行。

```bash
python skills/xmu-ppt/scripts/install_skill.py --agent codex
```

把 `codex` 换成 `claude-code`、`cursor`、`github-copilot` 或 `gemini-cli` 即可选择宿主。目标为当前项目的技能目录，`--project` 指向其他已存在的项目，`--lang en` 显示英文。同名条目会使安装停止。

此入口成功后会直接输出“说需求 → 确认内容 → 选模板 → 接收 PPTX”的说明，以及上传一批自备模板的示例。它只安装技能文件，Python 依赖、宿主发现与实际导出分别验收。

Agent 代为安装时，安装提示词要求它在完成后运行已安装技能的 `scripts/install_skill.py --guide` 并回显。通过第三方安装器安装时，其结束界面由该安装器控制。首次启用本技能也有简短引导规则，完整教程随包位于 [GETTING_STARTED.md](../../skills/xmu-ppt/GETTING_STARTED.md)。

## 按 Agent 安装与调用

下表的提示词用于已经下载源码、安装依赖的项目。先让 Agent 建立项目技能副本，再开启新会话核对发现结果。

| Agent | 安装时可以这样说 | 发现后的调用方式 |
| --- | --- | --- |
| Codex | 请将完整 `skills/xmu-ppt` 安装到当前项目的 `.agents/skills/xmu-ppt`，同名冲突先停止并比较 | `$xmu-ppt` 或技能选择界面 |
| Claude Code | 请将完整 `skills/xmu-ppt` 安装到当前项目的 `.claude/skills/xmu-ppt`，同名冲突先停止并比较 | `/xmu-ppt` |
| Cursor | 请将完整 `skills/xmu-ppt` 安装到当前项目的 `.cursor/skills/xmu-ppt`，同名冲突先停止并比较 | `/xmu-ppt` 或技能选择界面 |
| GitHub Copilot | 请将完整 `skills/xmu-ppt` 安装到当前项目的 `.github/skills/xmu-ppt`，同名冲突先停止并比较 | 在 Agent 模式明确要求使用 `xmu-ppt` |
| Gemini CLI | 请检查 `gemini skills list --all`，确认无同名冲突后执行 `gemini skills install ./skills/xmu-ppt --scope workspace` | `/skills reload` 后明确要求启用 `xmu-ppt` |

源码目录 `skills/xmu-ppt` 和宿主发现目录各有用途。只下载仓库后，可以直接要求 Agent 读取源码入口并运行脚本。复制安装后，需要从原始来源同步更新，Python 虚拟环境仍需单独准备。

官方机制分别见 [OpenAI](https://learn.chatgpt.com/docs/build-skills)、[Claude Code](https://code.claude.com/docs/en/skills)、[Cursor](https://cursor.com/docs/skills)、[GitHub Copilot](https://docs.github.com/en/copilot/concepts/customizations/agent-skills) 和 [Gemini CLI](https://geminicli.com/docs/cli/using-agent-skills/)。

### 可选的跨 Agent 安装器

Vercel 的 Skills CLI 支持从 GitHub 仓库发现和安装技能。先安装其要求的 Node.js 版本，当前上游要求 Node.js 22.20+，检查同名条目后，在目标项目目录执行。保留安装器的交互确认。

```bash
# 先查看可发现的技能
npx skills add Longfei-Tao/xmu-ppt --list

# 按你的宿主选择一条
npx skills add Longfei-Tao/xmu-ppt --skill xmu-ppt --agent codex
npx skills add Longfei-Tao/xmu-ppt --skill xmu-ppt --agent claude-code
npx skills add Longfei-Tao/xmu-ppt --skill xmu-ppt --agent cursor
npx skills add Longfei-Tao/xmu-ppt --skill xmu-ppt --agent github-copilot
npx skills add Longfei-Tao/xmu-ppt --skill xmu-ppt --agent gemini-cli
```

此安装器只安装技能文件，仍需用安装后的实际技能路径安装 `requirements-core.txt`。仓库四页验收示例位于 `examples/quickstart`，另行保留完整 checkout 才能运行该示例。项目更新器只适用于原始 Git checkout，安装器副本用其更新机制维护。本次用 Skills CLI 1.7.6 验证了本地源码目录到五类 Agent 的项目级文件分发，实际生成共享 `.agents/skills/` 和 Claude Code 的 `.claude/skills/` 副本。CC Switch 管理的共享技能通过 CC Switch 维护。命令选项及支持的 agent 标识见 [Skills CLI 官方仓库](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)。

## Release 技能包的目录

`xmu-ppt-skill.zip` 解压后包含外层 `xmu-ppt/`，实际技能目录为其中的 `skills/xmu-ppt/`。只把内层目录安装到宿主的技能路径。
打包器剔除源 PPTX、模板位图、展示截图和本机配置，使用自备模板前按[快速开始](../quickstart.md)完成入库。缺少所需素材的内置 SVG 模板会从本机可用列表中隐藏。

## 如何验收

1. **文件已安装**，目标目录中存在 `SKILL.md`、`scripts/`、`workflows/`、`templates/` 和许可文件。
2. **宿主已发现**，在新会话中可看到 `xmu-ppt` 及其实际来源路径。
3. **转换已验证**，用虚拟环境解释器完成四页示例导出，打开 PPTX 检查结果。
4. **实际创作已验证**，在该宿主中发送主题，完成内容确认、模板选择、生成与逐页复核。

本次已验证 Windows Python 3.13 的隔离依赖安装与示例导出，并完成 Codex、Claude Code、Copilot CLI、Gemini CLI 的技能发现。Cursor 的宿主发现与各宿主第 4 项仍待验收。Gemini 工作区需要完成信任确认，未受信任时可能安装成功但列表中只有内置技能。[审查范围与结果](../audits/2026-11-09-installation-review.md)。

## 其他工具与网页聊天

仓库当前没有插件商店清单、MCP 服务器或平台专用打包产物，不能把 GitHub 地址当作任意客户端的安装链接。

能读取仓库并执行 Python 的其他工具，可按[快速开始](../quickstart.md)显式读取 `SKILL.md`，再执行对应脚本；这属于手动工作流，未承诺原生发现或实机兼容。只有对话能力的网页界面可协助写提纲，无法单靠粘贴本文执行本地导出。

具备云端文件执行能力的产品还需要完整上传素材、安装依赖并导出结果。宿主即使支持云端 Skill，也不意味着会自动同步本机配置；本仓库尚未验证这条安装链路。
