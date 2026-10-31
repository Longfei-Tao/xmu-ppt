# GitHub Copilot

[工具目录](README.md) · [准备 Python 和源码](../quickstart.md)

官方机制：支持 Agent Skills 的 Copilot 环境可读取项目 `.github/skills/`；具体支持范围随宿主版本变化。依据 [GitHub 官方 Agent Skills 文档](https://docs.github.com/en/copilot/concepts/customizations/agent-skills)核验（2026-10-31）。以下步骤尚未在 Copilot 实机验证。

## 本地 Agent 模式

在支持该功能的 IDE 中打开仓库，完成 Python 环境准备。从仓库根目录执行：

```bash
python -c "from pathlib import Path; import shutil; d=Path('.github/skills/ppt-master'); assert not d.exists(), 'Existing skill: back up and resolve first'; d.parent.mkdir(parents=True, exist_ok=True); shutil.copytree('skills/ppt-master', d, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))"
```

已有同名目录时停止，先备份比较。CC Switch 管理的技能由管理器分发。重新打开工作区，使用能执行终端命令的 Agent 模式发送：

```text
请使用项目中的 ppt-master 技能，制作 10 页厦大风格的课程项目汇报。
主题是校园科研协作，只写方案建议，不编造研究结果。
用仓库 .venv 的 Python 执行，最后给我 PPTX 路径。
```

不要把普通补全模式或只读问答当作文件生成环境。不能发现技能时，手动指定 `skills/ppt-master/SKILL.md`，并确认它确实能访问脚本与模板。

## Copilot CLI 和云端 Agent

官方提供多个支持 Skill 的入口，但本项目未逐一验证。云端需要仓库内完整资源与独立依赖安装，本机虚拟环境不可复用；生成的二进制文件应按宿主提供的产物下载流程取回，不要求将演示稿直接提交到业务仓库。
