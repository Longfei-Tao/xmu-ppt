# Codex

[工具目录](README.md) · [准备 Python 和源码](../quickstart.md)

官方机制：Codex 会扫描项目中的 `.agents/skills/`，支持显式选择技能。路径与调用机制依据 [OpenAI 官方说明](https://learn.chatgpt.com/docs/build-skills)核验（2026-10-31）。本项目当前只验证了 Windows Codex 会话中的仓库脚本执行，未做全新安装验收。

## 在本项目使用

最短路径是不安装：在 Codex 中打开仓库，按[快速开始](../quickstart.md)要求读取 `skills/ppt-master/SKILL.md`。需要技能自动发现时，可在未受 CC Switch 管理的工作区终端，从仓库根目录执行：

```bash
python -c "from pathlib import Path; import shutil; d=Path('.agents/skills/ppt-master'); assert not d.exists(), 'Existing skill: back up and resolve first'; d.parent.mkdir(parents=True, exist_ok=True); shutil.copytree('skills/ppt-master', d, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))"
```

该命令只建立项目副本，已有同名目录时停止；不修改全局配置。重新打开会话，在技能选择界面确认 `ppt-master` 的路径属于当前项目，避免同名上游技能。

在 Codex CLI / IDE 中可用 `/skills` 或 `$` 选择技能；界面入口以所用版本为准。调用示例：

```text
$ppt-master
制作一份 10 页厦大风格的校园科研协作方案汇报。
使用项目 .venv 的 Python。没有研究数据，不编造结果。
把 PPTX 放在独立项目目录并返回实际路径。
```

## 远程和云端

本地目录不会自动出现在云端。远程运行时在远程工作区准备同样的文件和依赖；仅把 `SKILL.md` 发给模型不足以导出。项目副本更新需从源码重新同步，遇到已有条目先备份和比较，不能覆盖 CC Switch 的运行副本。
