# 代码与安装审查记录

日期为 2026-11-09，起点提交为 `cb6eec9`。本次审查覆盖 GitHub 源码安装、技能包构建、依赖更新、模板可用性、用户模板入库、文本容量和仓库展示文档。

## 发现与修复

| 优先级 | 问题及影响 | 本次处理 |
| --- | --- | --- |
| P1 | 技能包声称剔除截图和学校素材，实际仍收录文档展示图、示例预览和 11 张模板根目录位图 | 扩展排除规则，审计复用同一规则，保留必要脚本运行图片 |
| P2 | 技能包剔除素材后，选择器仅检查 SVG 本体，仍将无法预览的内置模板标为可用 | 检查 SVG 引用的本机素材，缺失时隐藏该路线，推荐入口复用相同判断 |
| P2 | 首装使用核心依赖，更新器却只监控完整依赖文件，安装失败后重跑也可能跳过同步 | 默认跟踪核心依赖，提供 `--full`，成功后保存与解释器绑定的摘要，失败后重跑会重试 |
| P2 | 独立复制到业务仓库的技能更新器可能操作业务仓库的 Git | 核验 Git 顶层目录，要求从原始源码 checkout 运行 |
| P2 | 逻辑页序与 `slideN.xml` 文件号不一致时，文字容量关联到错误页面 | 复用 OOXML 关系解析，按演示文稿逻辑页序建立容量映射 |
| P2 | 两个项目分别确认模板后，全局门禁可覆盖先前项目的选择 | 原生 build 优先读取计划所在项目的确认记录，保留旧流程入口 |
| P3 | 首次入库缺少预览目录，PPTX 内已有的真实缩略图保存失败 | 保存前创建预览目录 |
| P2 | 使用自定义发布输出路径时，默认别名目录不存在会导致构建中断 | 创建别名父目录并添加回归 |

每项代码修复均补充了针对性回归。文档同步说明源码与技能包的资源差异、完整技能目录层级、Python 环境、主流 Agent 的安装与调用方式、更新方法和验收范围。

## 本地验收

实际执行环境为 Windows、Python 3.13。新建独立虚拟环境，只安装 `requirements-core.txt`，完成以下检查。

- 全部 164 项仓库单元测试通过，包含本次新增回归。
- 从 Git 可分发文件生成的干净源码副本导出四页示例，4 页成功，0 页失败。
- 干净源码副本的模板列表为 15 套，其中 14 套支持原生填充。
- 在隔离目录构建技能包，ZIP CRC、排除规则和本机索引重置通过，仅保留 2 张脚本运行图片。缺少素材的内置模板可用数为 0，自造 PPTX 入库后可用用户模板数为 1，`doctor` 通过。
- 24 份文档的 151 个本地链接检查通过，隐私扫描和打包审计通过。内置 SVG 检查无错误，南强蔚蓝仅支持 SVG 的提示保留。示例 PPTX 结构检查为 0 错误、0 警告。

测试临时目录放在仓库 `.cache/` 内。首次运行遇到沙盒系统临时目录权限错误，换用可写临时目录后重新执行。此环境错误与项目逻辑缺陷分别处理。

维护者可在完整仓库使用虚拟环境解释器复验。

```bash
python -m unittest discover -s tests -q
python scripts/check_docs.py
python scripts/check_assets.py
python scripts/check_privacy.py
python scripts/pack_release.py --check
python skills/xmu-ppt/scripts/audit_xmu.py --check-svg
python skills/xmu-ppt/scripts/svg_to_pptx.py examples/quickstart -s svg_output -o .cache/first-demo.pptx -t none -a none
python skills/xmu-ppt/scripts/review_pptx.py .cache/first-demo.pptx --min-level warn
```

## 后续安装与线上核验

同日继续完成了以下检查，使用仓库 `.cache/` 下的临时项目与隔离客户端目录。

| 入口 | 实测版本 | 结果 |
| --- | --- | --- |
| Codex CLI | 0.167.0-alpha.3.2 | app-server `skills/list` 返回项目技能路径，enabled 为 true |
| Claude Code | 2.1.286 | 初始化事件列出 `xmu-ppt`，独立空目录对照未列出 |
| Copilot CLI | 1.0.107 | `skill list --json` 返回 source 为 project、enabled 为 true |
| Gemini CLI | 0.67.0 | 原生 workspace 安装通过，给予临时目录单次会话信任后可发现技能 |
| Skills CLI | 1.7.6 | 从本地源码向五类 Agent 分发完整目录通过，生成共享与 Claude 副本 |

Gemini 在未受信任的工作区会跳过项目技能，即使安装命令已经成功。安装指南已补充此排查步骤。模型驱动主题创作与技能文件发现分别验收。

GitHub CLI 已恢复访问，确认远端仓库、Pages 配置，并下载当时的最新发布 `v0.2.3`。实际下载的技能包 ZIP CRC 通过，包含 54 张应从纯技能包排除的展示或模板位图，入口位于 `xmu-ppt/skills/xmu-ppt/SKILL.md`。

## 正式发布与线上验收

修复已通过提交 `1c7208bc419ed8f52a0c3221f42c345522e2c797` 推送到 `main`，Ubuntu/Windows 与 Python 3.10/3.13 四组 CI 全部通过，Pages 已部署该提交。[CI 执行记录](https://github.com/Longfei-Tao/xmu-ppt/actions/runs/42576964250)。

已发布 [v0.2.4](https://github.com/Longfei-Tao/xmu-ppt/releases/tag/v0.2.4)，包含两个等内容 ZIP 与 `SHA256SUMS.txt`。包大小为 9,713,939 字节，约 9.3 MiB，仅保留两张脚本运行图片。匿名请求 `releases/latest/download/xmu-ppt-skill.zip` 返回 HTTP 200，重新下载的 SHA256 与本地构建一致，ZIP CRC 检查通过。旧版本作为历史发布保留。

从 GitHub 仓库地址执行 Skills CLI 安装已成功。安装后关键脚本内容与修复提交一致，用该安装副本及隔离 Python 环境导出示例，4 页成功、0 页失败。公开模板画廊返回 HTTP 200，目录中为 15 套内置模板。

## 仍需单独验收的范围

- Cursor 的宿主发现、Copilot IDE 集成与各宿主的模型驱动完整主题创作仍需分别实机验收。
- CI 已定义 Ubuntu/Windows 与 Python 3.10/3.13 组合，本次本机运行只覆盖 Windows Python 3.13。
- 初次匿名 GitHub API 请求返回 HTTP 403，后续通过 GitHub CLI 完成了已发布压缩包的实际下载与内容核验。
- 素材检查仍提示 15 套内置模板的来源或再分发条件待核验。代码 MIT 许可与第三方素材权利分别记录，当前状态见[素材与许可](../assets.md)。
- 自动检查覆盖结构与近似排版，实际演示软件中的字体、换行、图片和复杂图表需要逐页视觉复核。

## 官方机制参考

安装说明核对了 [OpenAI Skills](https://learn.chatgpt.com/docs/build-skills)、[Claude Code Skills](https://code.claude.com/docs/en/skills)、[Cursor Skills](https://cursor.com/docs/skills)、[GitHub Copilot Agent Skills](https://docs.github.com/en/copilot/concepts/customizations/agent-skills) 和 [Gemini CLI Skills](https://geminicli.com/docs/cli/using-agent-skills/)。跨 Agent 安装命令依据 [Vercel Skills CLI](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)，端到端安装仍待验收。
