# xmu-ppt 简单使用

## 第一次做 PPT

在能读取文件、执行 Python 的 Agent 中发送需求。

```text
请用 xmu-ppt 帮我做约 10 页组会汇报，听众是导师和同组同学。
内容以我上传的材料为依据，先给我确认内容策划案，再让我选择模板。
确认后制作 PPTX，完成检查并给我实际文件路径。
```

Agent 会检查依赖与可用模板，整理内容，等待内容确认与模板选择，再生成和检查。原生填充默认复用模板已有页面。明确要求灵活排版时，可采用 SVG 路线。

## 把自己的模板加进来

把一份或多份 `.pptx` 上传到对话，或提供 Agent 能读取的文件夹路径，附上这句话。

```text
这些 PPTX 都是我有权使用的模板。
请把它们全部加入“我的模板库”，供接下来做 PPT 时选择。
逐份检查并入库，列出编号、名称、页数和失败的文件。
```

每套成功入库的模板会获得 `U001`、`U002` 等实际编号，完全相同的文件复用已有记录。入库后说“用 U003 做这次汇报”即可。推荐清单默认最多显示 8 套，全部成功入库的模板可在“我的模板”画廊查看，清单之外也可直接按编号选择。

只上传文件时，Agent 应先确认它们的用途和使用权。旧 `.ppt` 需另存为 `.pptx`，损坏文件与 `.pptm` 宏模板会被拒绝。单份失败后继续检查其余文件，最后汇总结果。

## 安装后先检查

技能目录需要包含 `SKILL.md`、`scripts/`、`workflows/` 和模板资源。Python 3.10+ 的核心依赖见同目录 `requirements-core.txt`。重新打开或重载 Agent，确认它发现了 `xmu-ppt`。Gemini 的工作区技能需要目录受信任。

从完整仓库安装可使用内置模板。Release 纯技能包剔除了内置原件和模板位图，使用前先入库自备模板。本地 Agent 的私有模板库默认在 `~/.xmu-ppt/user-templates/`，远程或云端 Agent 的库位于相应执行环境。

仓库安装入口成功后会输出简短说明。通过其他安装器安装后，Agent 安装任务应回显说明，首次启用技能时也应主动展示。说明可随时通过 `scripts/install_skill.py --guide` 查看。

## Getting started

Ask your agent to use `xmu-ppt`, provide the topic, audience, source material and slide count, then confirm the content brief and choose a template. The agent prepares and checks an editable PPTX.

To add your own templates, attach the PPTX files and say “I have permission to use these templates. Add all of them to My Templates and list their U identifiers, names, page counts and any failed imports.” Successfully imported templates remain selectable even when absent from the initial shortlist.

Install core Python dependencies from `requirements-core.txt`, then reload your agent and verify skill discovery. The skill-only Release needs user-supplied template files. Run `scripts/install_skill.py --guide --lang en` for the short English guide. Details are in [user-template onboarding](workflows/user-template-onboarding.md).
