# Gemini CLI

[工具目录](README.md) · [准备 Python 和源码](../quickstart.md)

工作区技能可通过 CLI 管理，支持从本地目录安装。2026-11-09 使用 Gemini CLI 0.67.0 验证了本地安装与受信任工作区内的技能发现。[Gemini CLI 官方 Skills 文档](https://geminicli.com/docs/cli/using-agent-skills/)。

## 安装到工作区

先确认本地 Gemini CLI 已可用，完成共用 Python 依赖准备。从仓库根目录执行：

```bash
gemini skills list --all
gemini skills install ./skills/xmu-ppt --scope workspace
```

先检查列表是否存在同名技能，冲突时先备份并核对来源，不继续安装覆盖。使用 CC Switch 时由它分发，不重复安装。保留宿主的安装及启用确认，不加入跳过确认的选项。

开始新会话或在会话里运行 `/skills reload`，再用 `/skills list` 确认名称和位置，发送：

工作区技能只在受信任的目录中加载。首次打开项目时完成宿主的信任确认，再重载技能。若安装成功但列表仅显示内置技能，先检查工作区信任状态。本次在未受信任的临时目录复现了这一情况，给予该测试目录单次会话信任后，`xmu-ppt` 显示为 Enabled。[Gemini CLI 信任机制](https://geminicli.com/docs/cli/trusted-folders/)。

```text
请启用 xmu-ppt 技能，制作约 10 页厦大风格的校园科研协作方案汇报。
使用仓库 .venv 的 Python。没有真实数据，不编造实验结果。
将 PPTX 保存到独立项目目录，并给我实际路径。
```

如果版本不支持上述命令，可先按[源码手动流程](../quickstart.md)读取 Skill，再执行本地脚本；这不等于原生安装已经成功。远程 Gemini CLI 的文件和依赖都应准备在远程工作区。
