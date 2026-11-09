# GitHub Copilot

[工具目录](README.md) · [准备 Python 和源码](../quickstart.md)

支持 Agent Skills 的 Copilot 环境可读取项目 `.github/skills/`、`.claude/skills/` 和 `.agents/skills/`，具体支持范围随宿主版本变化。2026-11-09 使用 Copilot CLI 1.0.107 的 `skill list --json`，验证临时项目中 `xmu-ppt` 的 source 为 project 且已启用。IDE 集成与完整模型驱动创作仍待验收。[GitHub 官方 Agent Skills 文档](https://docs.github.com/en/copilot/concepts/customizations/agent-skills)。

## 本地 Agent 模式

在支持该功能的 IDE 中打开仓库，完成 Python 环境准备。从仓库根目录执行：

```bash
python -c "from pathlib import Path; import shutil; d=Path('.github/skills/xmu-ppt'); assert not d.exists(), 'Existing skill: back up and resolve first'; d.parent.mkdir(parents=True, exist_ok=True); shutil.copytree('skills/xmu-ppt', d, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))"
```

已有同名目录时停止，先备份比较。CC Switch 管理的技能由管理器分发。重新打开工作区，使用能执行终端命令的 Agent 模式发送：

```text
请使用项目中的 xmu-ppt 技能，制作 10 页厦大风格的课程项目汇报。
主题是校园科研协作，只写方案建议，不编造研究结果。
用仓库 .venv 的 Python 执行，最后给我 PPTX 路径。
```

不要把普通补全模式或只读问答当作文件生成环境。不能发现技能时，手动指定 `skills/xmu-ppt/SKILL.md`，并确认它确实能访问脚本与模板。

## Copilot CLI 和云端 Agent

Copilot CLI 可运行 `copilot skill list --json` 检查实际名称、路径、source 和 enabled。云端需要仓库内完整资源与独立依赖安装，本机虚拟环境不可复用，生成的二进制文件按宿主提供的产物下载流程取回。不同 IDE 与云端入口仍需分别验收。[Copilot CLI 命令参考](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)。
