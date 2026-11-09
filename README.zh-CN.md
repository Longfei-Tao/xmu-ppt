# xmu-ppt · 厦门大学 PPT 模板

[![Version](https://img.shields.io/github/v/release/Longfei-Tao/xmu-ppt?label=version&color=blue)](https://github.com/Longfei-Tao/xmu-ppt/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![模板](https://img.shields.io/badge/%E6%A8%A1%E6%9D%BF-15%20%E5%A5%97-4661CC)](docs/templates.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](docs/quickstart.md)
[![CI](https://github.com/Longfei-Tao/xmu-ppt/actions/workflows/validate.yml/badge.svg)](https://github.com/Longfei-Tao/xmu-ppt/actions/workflows/validate.yml)
[![GitHub stars](https://img.shields.io/github/stars/Longfei-Tao/xmu-ppt.svg)](https://github.com/Longfei-Tao/xmu-ppt/stargazers)

**简体中文** · [English](README.md)

把主题、提纲或现有材料，整理成厦大风格的演示文稿。由 AI Agent 逐页排版，导出**文字可编辑**的 `.pptx`。基于 [PPT Master](https://github.com/hugohe3/ppt-master) 的 SVG → PPTX 引擎，增补 15 套厦大模板与三条出稿路线。

**[选择视觉模板](https://longfei-tao.github.io/xmu-ppt/templates/)** · **[在线逐页预览](https://longfei-tao.github.io/xmu-ppt/)** · [快速开始](docs/quickstart.md) · [模板风格](docs/templates.md) · [常见问题](docs/faq.md) · [选择你的 AI 工具](docs/tools/README.md)

<table>
  <tr>
    <td align="center" width="33%">
      <a href="https://longfei-tao.github.io/xmu-ppt/#defense/1"><img src="docs/assets/screenshots/defense-cover.webp" alt="厦园晴日硕士答辩稿封面" /></a><br/>
      <sub><b>厦园晴日</b> — 硕士答辩 14 页：校徽、校园照片与标题层级按模板还原</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://longfei-tao.github.io/xmu-ppt/#group/8"><img src="docs/assets/screenshots/report-content.webp" alt="南强蔚蓝组会汇报内容页" /></a><br/>
      <sub><b>南强蔚蓝</b> — 组会汇报 11 页：正文版式按内容重排，不是每页套卡片</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://longfei-tao.github.io/xmu-ppt/#native/3"><img src="docs/assets/screenshots/native-chapter.webp" alt="凤凰花开原生填充章节页" /></a><br/>
      <sub><b>凤凰花开</b> — 原生填充 9 页：在原 PPTX 里换字，照片与色条不动</sub>
    </td>
  </tr>
</table>

<sub>三张图都是 PowerPoint 打开真实导出产物的截图，不是设计稿。[在线翻完这三套 →](https://longfei-tao.github.io/xmu-ppt/)</sub>

> 非官方个人项目，与厦门大学不存在已确认的授权或合作关系。代码与模板结构适用 [MIT](LICENSE)；校徽、照片、字体等不因此获得授权。部分既有素材的公开再分发条件仍[待核验](docs/assets.md)。

## 这是什么

| | |
| --- | --- |
| 运行方式 | AI Agent 负责内容与排版，Python 脚本负责分析、转换与检查 |
| 内置资源 | 完整仓库含 15 套厦大模板（3 套精修 + 12 套主题），其中 14 套含原始 PPTX |
| 自备模板 | 支持本机入库，分配 `U001` 序号，建立私有模板画廊 |
| 环境要求 | Python 3.10+，以及能读取文件、执行命令的 Agent |
| 编辑与质量 | 文字和简单图形可编辑，照片保持图片形式，复杂版式需要在演示软件中逐页复核 |

默认按 **提出需求 → 内容策划案 → 选择视觉模板 → 生成 PPT** 使用。内容策划案先写清每页目的、核心结论、证据来源和数据缺口；确认后再选模板。用户明确赶时间时可跳过策划案，直接进入模板选择。

每套内置模板有一个**固定的三位序号**（`001`–`015`）。序号只在末尾追加，不重排、不复用；说序号即可选模板，例如 `004` 指「光影厦大」。公开仓库不提供外部模板，使用者自备的模板只在各自本机登记与使用。

[公开模板画廊](https://longfei-tao.github.io/xmu-ppt/templates/)只展示 **15 套内置模板**。第三方模板原件、封面与预览图均不进入公开仓库，也不通过本项目对外分发。

## 三条路线

只给主题时，先确认内容和模板，再默认采用原生填充。用户明确要求重新设计版式时使用 SVG 路线。

| 你的说法 | 路线 | 做法 | 代价 |
| --- | --- | --- | --- |
| 「保留原版式」「别改我的样式」「表格图表要原样」 | 原生填充（默认） | 克隆源页 + 改 `fill_plan`，不生成 SVG | 版式受槽位约束，文字长度有硬上限 |
| 「灵活排版」「重新设计版式」 | SVG 出稿 | 逐页手写 SVG 再导出 | 每页重画，模板保真度中等 |
| 对已登记的本机外部模板要求「一页不少、保留原页序」 | 严格保真 | 整份复制原 PPTX，只覆盖被点名页的文字 XML | 页数必须等于模板原有页数 |

原生填充可用 14 套；`南强蔚蓝` 原始文件是 `.ppt`，仅支持 SVG 路线。

## 输入与输出

你可以直接这样说：

```text
用 xmu-ppt 做一份厦大风格的校园科研协作汇报，约 10 页。
内容包括：材料管理、责任分工、进度安排与提交复核。
先展示视觉模板供我选择，确认后再制作。
没有实测数据，请写成方案建议，不编造结果。输出 PPTX。
```

| 你提供什么 | Agent 如何处理 | 最终得到什么 |
| --- | --- | --- |
| 一个主题或想法 | 补全叙事结构，展示模板候选并等待选定 | `.pptx`；不会据此编造研究结果 |
| 提纲、文档或旧汇报材料 | 提炼内容，展示厦大模板，用户选定后逐页排版 | `.pptx` 和可继续修改的项目源稿 |
| 指定模板和新内容 | 克隆适用源页，填充文字与支持的表格、图表 | 受原版式容量约束的 `.pptx` |

默认只需接收演示文稿与必要说明。文字和简单图形可导出为原生对象，照片等仍是图片；复杂图表与排版需逐页检查，不能保证所有元素均可编辑或格式完全一致。

## 让 Agent 帮你安装

在 Codex、Claude Code、Cursor、Copilot 的 Agent 模式或 Gemini CLI 中复制以下提示词。工具需要能访问网络、文件和终端。

```text
请帮我安装 https://github.com/Longfei-Tao/xmu-ppt 的 xmu-ppt 技能。
先读取仓库 README 和 skills/xmu-ppt/SKILL.md，判断当前 Agent 的技能目录。
默认安装到当前项目，安装完整 skills/xmu-ppt 目录。
如果共享技能由 CC Switch 管理，通过 CC Switch 维护和分发。
发现同名技能时先比较来源，保留备份，并在替换前让我确认。
保留完整源码仓库以使用内置模板，创建 Python 3.10+ 虚拟环境，
使用该环境的解释器安装 requirements-core.txt。
运行仓库四页示例导出，报告技能实际路径、Python 路径和 PPTX 路径，
分别说明文件已放置、宿主已发现技能、示例已导出三个状态。
```

各工具的目录、调用语法及可选的 `npx skills add` 命令见[安装与调用指南](docs/tools/README.md)。

## 快速开始

需要 **Python 3.10+**、Git（或改用下面的 ZIP 方式），以及能读取文件和运行 Python 的 AI Agent。

### 准备源码

**方式 A · Git（推荐，后续可一行命令更新）**

```bash
git clone https://github.com/Longfei-Tao/xmu-ppt.git xmu-ppt
cd xmu-ppt
```

**方式 B · 下载 ZIP（没装 Git 时用）**

下载 [main.zip](https://github.com/Longfei-Tao/xmu-ppt/archive/refs/heads/main.zip) 并解压，进入解压出来的 `xmu-ppt-main` 目录。ZIP 版没有 git 历史，升级时重新下载覆盖，先备份自己改过的模板。

### 选对下载包

| 获取方式 | 包含内容 | 适合用途 |
| --- | --- | --- |
| Git clone / GitHub 源码 ZIP | 完整仓库、15 套内置模板、14 份源 PPTX、示例和测试 | 直接使用厦大内置模板 |
| Release 的 `xmu-ppt-skill.zip` | 脚本、工作流、布局定义、文档，打包时剔除原件与展示图片 | 自备 PPTX 模板后使用 |

技能包解压后入口为 `xmu-ppt/skills/xmu-ppt/SKILL.md`，安装时使用**内层**的 `skills/xmu-ppt/`。
包内缺少内置 PPTX 原件和模板图片，先用 `user_templates.py onboard` 入库自己的模板。
下载是否可用、实际内容以已发布的 Release 为准。下文命令按完整仓库编写。

### 安装依赖

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r skills/xmu-ppt/requirements-core.txt
```

```bash
# macOS / Linux
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/xmu-ppt/requirements-core.txt
```

### 把需求交给 Agent

在 AI 工具中打开这个仓库，把下面一段发给它，即可先从源码使用，无需修改全局配置：

```text
请读取 skills/xmu-ppt/SKILL.md，按其中的厦大工作流制作上一条需求的 PPT。
以该文件所在目录为技能根目录，使用本仓库 .venv 内的 Python。
把生成文件放在独立项目目录中，完成后给我 PPTX 的实际路径。
```

第一次使用时把“上一条需求”替换成自己的主题，或先发送上面的示例需求。完整步骤、环境说明及常见问题见[快速开始](docs/quickstart.md)。

### 验证本地导出

在仓库根目录，用虚拟环境的解释器导出已有四页 SVG 示例。

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe skills/xmu-ppt/scripts/svg_to_pptx.py examples/quickstart -s svg_output -o .cache/first-demo.pptx -t none -a none
```

```bash
# macOS / Linux
.venv/bin/python skills/xmu-ppt/scripts/svg_to_pptx.py examples/quickstart -s svg_output -o .cache/first-demo.pptx -t none -a none
```

成功时报告 4 页转换成功，并生成 `.cache/first-demo.pptx`。此步骤验收已有示例的转换链路。
PDF、Word、网页导入、生图、配音和浏览器复核按需安装额外依赖，见[进阶命令](docs/advanced.md)。

### 更新到最新版

```bash
python skills/xmu-ppt/scripts/update_repo.py
```

请使用同一个虚拟环境的 Python，在原始 Git 源码仓库中运行。脚本遇到已跟踪文件的未提交修改会停止，然后通过 `git pull --ff-only` 更新。首次运行、核心依赖变化或上次安装失败时会同步依赖，成功后记录摘要。`--full` 同时跟踪并安装完整依赖，`--skip-pip` 跳过依赖安装。ZIP 与技能安装副本应通过原下载方式或安装器更新，先保存本地修改。

已有仓库也可以直接用 git：

```bash
git pull
```

`git pull` 会合并上游提交，本地修改冲突时通常会中止。自定义模板和未提交修改应先备份或保存到自己的分支。

## 在你的 AI 工具中使用

| 工具 | 使用入口 | 本仓库验证范围 |
| --- | --- | --- |
| Codex | [项目 Skill 与源码调用](docs/tools/codex.md) | 已通过 app-server 验证临时项目技能发现 |
| Claude Code | [项目 Skill 与 `/xmu-ppt`](docs/tools/claude-code.md) | 已通过初始化事件及空目录对照验证技能注册 |
| Cursor | [项目 Skill 与 `/xmu-ppt`](docs/tools/cursor.md) | 已核对官方机制，宿主验收待完成 |
| GitHub Copilot | [Agent 模式与项目 Skill](docs/tools/copilot.md) | CLI 项目技能发现已验证，IDE 待验收 |
| Gemini CLI | [工作区 Skill](docs/tools/gemini-cli.md) | 原生安装与受信任工作区内技能发现已验证 |
| 网页聊天或其他工具 | [环境要求与手动流程](docs/tools/README.md) | 有文件执行环境才可能运行；不承诺原生安装 |

使用 CC Switch 管理共享 Skills 时，请在 CC Switch 中维护和分发；不要直接覆盖它生成的客户端副本。本仓库尚未提供插件商店安装包或远程 MCP 服务。

**2026-11-09 验证范围。** 已在全新 Windows Python 3.13 虚拟环境安装核心依赖，成功导出四页 SVG 示例，并完成四个 CLI 的临时项目技能发现及 Skills 安装器文件分发验收。各宿主的模型驱动完整创作仍需分别验收。CI 配置包含 Ubuntu/Windows 与 Python 3.10/3.13 组合，详见[本次审查记录](docs/audits/2026-11-09-installation-review.md)。

## 选择风格

| 风格 | 适合的内容 |
| --- | --- |
| 厦园晴日：蓝白、校园照片、明亮留白 | 答辩、开题、毕业汇报 |
| 凤栖青橙：纸感、青绿、橙色点缀 | 人文社科、读书报告、课程展示 |
| 南强蔚蓝：蓝紫、建筑插画、分栏结构 | 组会、项目与工作汇报；目前仅 SVG 路线 |

还有凤凰花开、经典蓝白、米金书法等 12 套主题，序号 `004`–`015`。[查看完整清单与既有原型](docs/templates.md)。

## 示例与文档

| 示例 | 内容 |
| --- | --- |
| [四页工作流演示](examples/quickstart/) | 不含校徽与照片，用于验证导出链路是否可用 |
| [硕士答辩 14 页](examples/房颤NLRP3答辩_厦园晴日.pptx) | 厦园晴日，含校园照片与原生文字 |
| [组会汇报 11 页](examples/组会汇报_南强蔚蓝.pptx) | 南强蔚蓝，逐页按内容重排 |
| [原生填充 9 页](examples/原生填充_凤凰花开.pptx) | 在原始模板里填字，版式未改动 |

| 文档 | 内容 |
| --- | --- |
| [快速开始](docs/quickstart.md) | 环境准备、首次出稿、没有 Git 怎么装 |
| [常见问题](docs/faq.md) | 安装、依赖、换行、容量、更新、素材边界 |
| [模板总览](docs/templates.md) | 15 套模板清单与既有原型 |
| [进阶命令](docs/advanced.md) | 完整依赖、可选工具、批量命令 |
| [选择你的 AI 工具](docs/tools/README.md) | 各宿主的技能目录与调用方式 |
| [素材与许可](docs/assets.md) | 校徽、照片、字体的边界与核验状态 |

## 开源与自备模板

本仓库基于 [PPT Master](https://github.com/hugohe3/ppt-master) 的 SVG → PPTX 引擎，
授权治理也沿用上游做法：**代码按 MIT 开源，第三方模板不随仓库分发**。公开仓库只提供
15 套内置模板；使用者可把自己合法持有的模板放在本机，通过 `root.local.json` 登记，
原件与预览都不会上传。

> 技能包下载入口为 [`xmu-ppt-skill.zip`](https://github.com/Longfei-Tao/xmu-ppt/releases/latest/download/xmu-ppt-skill.zip)，大小与内容随版本变化。[查看全部 Release](https://github.com/Longfei-Tao/xmu-ppt/releases)。

| 你想做的事 | 怎么做 |
| --- | --- |
| 用内置 15 套 | clone 完整仓库（含内置模板原件与封面） |
| 只带技能、模板自备 | 解压上面的纯技能包，填入自己的模板目录即可 |
| 用自己合法持有的模板 | 运行 `user_templates.py onboard "你的模板.pptx" --rights-confirmed`，自动加入“我的模板”，分配 `U001` 序号；原件和预览只留在本机 |
| 生成一份可公开分发的技能包 | `python scripts/pack_release.py`，脚本会拒绝装入任何原件、截图或本机配置 |
| 核验素材边界（仅仓库维护者） | 在**完整仓库**运行 `python scripts/check_assets.py`，发布前要求 0 error；纯技能包不含内置原件与本机配置，**无需运行**此脚本 |

权利声明、逐套台账与更新政策见[外部模板声明](skills/xmu-ppt/templates/external/TEMPLATE_NOTICES.md)、
[素材授权边界](LICENSE-ASSETS)与[素材与许可](docs/assets.md)。公开仓库不提供任何外部模板
原件、封面或下载包；使用者自备模板的权利状态由使用者自行核验。

### 把我的 PPTX 加入模板库

```powershell
# Windows
.\.venv\Scripts\python.exe skills\xmu-ppt\scripts\user_templates.py onboard `
  "D:\我的模板\组会模板.pptx" --name "我的组会模板" --rights-confirmed
```

```bash
# macOS / Linux
.venv/bin/python skills/xmu-ppt/scripts/user_templates.py onboard \
  "/Users/me/我的模板/组会模板.pptx" --name "我的组会模板" --rights-confirmed
```

它会：

1. 检查是否是可解析的 `.pptx`，拒绝 `.pptm` 宏模板；
2. 复制到 `~/.xmu-ppt/user-templates/U001/`（加 `--link` 则只登记原路径）；
3. 生成页面目录和封面；
4. 分配本机序号 `U001`；
5. 生成 `~/.xmu-ppt/user-templates/index.html` 本地画廊。

之后在对话里说“用 U001 做组会汇报”即可。`list` 查看已入库模板，`doctor` 检查原件和目录。
这些模板只在你的电脑上使用，不进入公开仓库、Release 或公开画廊。

## 使用前了解

- **生成需要 Agent。** Python 脚本负责分析、转换与检查，不会独立调用大模型完成主题创作；AI 工具本身的账号或费用另计。
- **真实汇报需要真实材料。** 未提供的实验结果、参考文献、个人信息应省略或补充来源，不能让模型猜测。
- **效果受环境影响。** 缺少字体会改变换行；SVG 转换与原生填充也各有边界。上台前请用目标演示软件检查全部页面。
- **数据不自动“全程本地”。** 转换脚本在执行环境运行，交给 AI 的材料仍受所选工具的数据政策影响；云端也无法直接访问本机路径。
- **学校素材单独核验。** 公开下载入口不等于公开再分发许可；本项目不代表厦门大学官方出品。

**素材不在 MIT 范围内。** 代码与模板结构的许可见 [LICENSE](LICENSE)；素材边界、允许用途与逐套台账见 [LICENSE-ASSETS](LICENSE-ASSETS) 与 [授权与边界设计](docs/licensing.md)。

---

<sub>项目名 `xmu-ppt`；技能名沿用上游的 `xmu-ppt`。旧称 `xmu-xmu-ppt`、XMU PPT Master 均指本仓库。</sub>

[进阶命令与依赖](docs/advanced.md) · [贡献指南](CONTRIBUTING.md) · [素材与许可](docs/assets.md) · [上游致谢](CREDITS.md)
