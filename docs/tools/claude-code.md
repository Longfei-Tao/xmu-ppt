# Claude Code

[工具目录](README.md) · [准备 Python 和源码](../quickstart.md)

官方机制：项目技能位于 `.claude/skills/<name>/SKILL.md`，可用 `/name` 调用。依据 [Claude Code 官方 Skills 文档](https://code.claude.com/docs/en/skills)核验（2026-10-31）。以下是文档适配步骤，本项目尚未在 Claude Code 实机验收。

## 项目级安装

先完成共用依赖步骤。在未受管理的仓库根目录执行：

```bash
python -c "from pathlib import Path; import shutil; d=Path('.claude/skills/ppt-master'); assert not d.exists(), 'Existing skill: back up and resolve first'; d.parent.mkdir(parents=True, exist_ok=True); shutil.copytree('skills/ppt-master', d, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))"
```

已有目录时命令停止，不覆盖。使用 CC Switch 时改由它分发。打开或重新打开该目录的 Claude Code 会话，检查 `/skills` 列表中的名称与来源，再发送：

```text
/ppt-master 用厦园晴日风格做一份校园科研协作方案汇报，约 10 页。
使用仓库 .venv 的 Python；仅写建议，不编造数据。
完成后给我 PPTX 路径与必要说明。
```

若命令未出现，先显式要求读取源码 Skill，检查目录层级、重名技能和宿主策略；不通过修改认证或全局设置解决。

## Claude 网页、Cowork 与云端

本机项目目录安装不等于在网页或云端启用。官方文档区分本地技能与账户/云端技能；本仓库未制作或验证这些产品的专用上传包。请先确认完整资源、Python 依赖及文件导出机制可用，不直接照搬本地路径。
