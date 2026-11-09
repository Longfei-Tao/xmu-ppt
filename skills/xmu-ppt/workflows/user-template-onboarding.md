# 我的模板：本机 PPTX 入库

> 适用场景：用户有自己合法持有的 `.pptx` 模板，想用 xmu-ppt 的“挑页 + 填字 + 检查”流程。
> 公开仓库不提供第三方模板包；这份工作流只处理用户本机的模板。

## 一、一句话流程

```text
用户 PPTX → 权利确认 → 复制到本机模板库 → 分析页数/槽位 → 生成页面目录和封面
→ 分配 U001 → 在推荐/确认/页面/出稿中使用
```

## 二、命令

```bash
PY=.venv/Scripts/python.exe
U=skills/xmu-ppt/scripts/user_templates.py

# 入库（推荐先复制；--link 只登记原路径）
$PY $U onboard "D:\我的模板\组会模板.pptx" --name "我的组会模板" --rights-confirmed

# 查看、体检、重新生成画廊
$PY $U list
$PY $U doctor
$PY $U gallery
```

macOS/Linux 把 `PY` 换成 `.venv/bin/python`，路径按实际目录替换。

## 三、存储位置

```text
~/.xmu-ppt/user-templates/
├── registry.local.json
├── index.html
├── placeholder.webp
└── U001/
    ├── source.pptx
    ├── source.slide_library.json
    ├── page_catalog.json
    ├── user_template.json
    └── previews/cover.webp
```

- 默认 `copy`：复制源文件，原文件移动后不影响使用；
- `--link`：只登记原路径，适合大文件或持续更新的模板；`doctor` 会检查路径；
- 所有文件只在本机，不进入仓库、Release 或公开画廊。

## 四、序号规则

| 类型 | 序号 | 说明 |
|---|---|---|
| 内置模板 | `001–015` | 随公开仓库分发 |
| 旧本机外部模板 | `016+` | 由旧的外部模板库扫描产生 |
| 我的模板 | `U001+` | 本机私有，不污染公开注册表 |

在对话里说 `U001` 即可选择；`USR-xxxx` 是内部模板 ID，普通用户不需要记。

## 五、安全检查

- 只接受 `.pptx`；拒绝 `.pptm` 宏模板；
- 超过 200 MB 警告，超过 500 MB 拒绝；
- 无法解析的损坏文件拒绝入库；
- 必须显式确认“合法持有或有权使用”；
- 出稿时仍会经过 `sanitize_pptx.py`，剥离音乐和自动翻页；
- 不会修改源文件；默认复制，`--link` 只读。

## 六、入库后怎么用

```bash
S=skills/xmu-ppt/scripts/idea_to_ppt.py

$PY $S recommend --idea "本次组会汇报" --positioning "课题组组会"
# 候选清单会包含 U001
$PY $S confirm U001
$PY $S pages U001 -o output/pages.json
# 编辑 output/plan.json，写 template_id=USR-xxxx 或 U001
$PY $S build output/plan.json -o output/成品.pptx
```

## 七、常见问题

**Q：入库后公开画廊会多一套吗？**  
不会。公开画廊固定 15 套；`U001` 只出现在 `~/.xmu-ppt/user-templates/index.html`。

**Q：原始 PPTX 会被上传吗？**  
不会。脚本只在本机复制/读取；但如果你把材料发给云端 Agent，材料仍受该 AI 工具的数据政策约束。

**Q：模板里的字体、图片、Logo 会有授权吗？**  
没有。项目只提供入库和出稿工具，不替用户取得模板素材的授权；公开分发前请自行核验。

**Q：可以删除吗？**  
可以删除 `~/.xmu-ppt/user-templates/U001/`，但请先确认不需要保留源文件；`copy` 模式下源文件在模板库内，删除前先备份。
