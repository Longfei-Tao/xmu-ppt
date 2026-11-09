# Cursor

[工具目录](README.md) · [准备 Python 和源码](../quickstart.md)

Cursor 支持项目 `.cursor/skills/` 和 `.agents/skills/`，可在 Agent 对话中用 `/` 选择技能。机制于 2026-11-09 按官方文档核对。[Cursor Agent Skills](https://cursor.com/docs/skills)。

## 项目安装

先完成源码下载和核心依赖安装。若当前项目已有 `.agents/skills/xmu-ppt`，先检查 Cursor 是否已发现该技能。需要独立副本时，从仓库根目录执行。

```bash
python -c "from pathlib import Path; import shutil; d=Path('.cursor/skills/xmu-ppt'); d.parent.mkdir(parents=True, exist_ok=True); shutil.copytree('skills/xmu-ppt', d, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))"
```

已有目标目录时复制会失败。使用 CC Switch 管理共享技能时，通过管理器分发。重新打开会话，在 Skills 界面核对 `xmu-ppt` 的实际路径，再发送需求。

```text
/xmu-ppt 制作约 10 页厦大风格的校园科研协作方案汇报。
使用原始源码仓库 .venv 的 Python，先确认内容策划案，再让我选择模板。
没有实测数据，只写方案建议，完成后返回 PPTX 实际路径。
```

## 验证范围

本项目已核对官方发现机制，Cursor 内安装、发现和完整出稿仍待实机验收。云端及远程运行需要在实际执行环境准备技能文件、Python 依赖和模板素材。
