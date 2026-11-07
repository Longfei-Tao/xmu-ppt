# strict-native 严格保真路线

> 适用场景：用户从「本地模板库」选定了**外部模板**（200 套，ID 形如 `MED-001` / `CAMPUS-...`），并要求「保留原模板每一页的版式，只换文字」。
>
> 本路线是**独立新增**的第三条出稿路线。内置 15 套厦大模板、默认 SVG 出稿、原生填充 `apply` 全部保持原样；把 `templates/external/feature_flags.json` 的 `strict_native` 设为 `false` 即可完整回退。

## 一、先理解几个词

| 词 | 大白话 |
| --- | --- |
| PPTX 部件（part） | `.pptx` 其实是个 zip 压缩包，里面每个文件叫一个「部件」：一页对应一个 XML，图片、备注、母版各是独立部件 |
| 只改文字 | 打开原文件，把要改的那几个文字格子里的内容换掉，**其它一个字节都不碰** |
| 版式页 | 第 2、3、4 页通常是目录页、章节页、图文页，是用户「看上这个模板」的主要原因，本路线特别标注保护 |
| plan | 一张「替换清单」：写清楚第几页、哪个文字区域、换成什么。不写进清单的地方一律不动 |
| verify | 出稿后自动比对原件与成品，证明「除点名文字外没有任何东西被改动」 |

## 二、完整流程

1. **用户给主题与想法** → AI 推荐 1–2 个分类与候选模板，**不代选**。
2. 用户在本机打开 `local-gallery/index.html`，按分类浏览、用页码滑杆看**每一页**的布局，点「复制给 AI 的选用指令」。
3. 指令里含模板 ID（如 `MED-001`）与「1:1 保留全部页面、尤其第 2/3/4 页、不删页不重排不替换素材」。
4. **体检**：`doctor` 确认总开关、索引、本机路径映射、原件指纹都正常。
5. **看槽位**：`inspect <ID>` 列出每页有哪些可填文字区、每个区有几个文本节点、原文是什么。
6. **生成清单**：`scaffold <ID>` 产出含全部页的 plan 骨架（默认 `replacements` 全空）。
7. **填文案**：只在要改的页写 `replacements`；未点名的文本框保留原示例文字。
8. **出稿 + 自动校验**：`apply` 生成 PPTX 并立即跑白名单比对；不通过直接报错，不交付。
9. **交付**：只给本机 PPTX，附版权与推广文字提示。

### 具体命令（在 `D:\Coding\xmu-ppt-master` 下执行）

```bash
PY=.venv/Scripts/python.exe
S=skills/xmu-ppt/scripts/strict_native.py

$PY $S doctor
$PY $S inspect MED-001 -o output/inspect-MED-001.json
$PY $S scaffold MED-001 -o output/plan-MED-001.json
# 编辑 plan-MED-001.json，只填要改的 replacements
$PY $S apply MED-001 output/plan-MED-001.json \
    -o output/strict-native/MED-001.pptx \
    --audit output/strict-native/MED-001.audit.json
$PY $S verify MED-001 output/strict-native/MED-001.pptx \
    --audit output/strict-native/MED-001.audit.json
```

`apply` 已内置 `verify`，正常出稿无需单独执行第 5 条；单独 `verify` 用于事后复核别人给的成品。

## 三、plan 格式（schema `strict_native_plan.v1`）

```json
{
  "schema": "strict_native_plan.v1",
  "template_id": "MED-001",
  "keep_all_slides": true,
  "slides": [
    {"slide": 1, "replacements": [
      {"slot_id": "s01_sh13", "text": "课题组年度汇报"}
    ]},
    {"slide": 3, "replacements": [
      {"shape_name": "章节标题", "text": "研究背景与意义"}
    ]}
  ]
}
```

- `slot_id` 形如 `s03_sh12`（第 3 页、形状 id 12），来自 `inspect`；也可用 `shape_id` 或 `shape_name` 定位。
- `text` 用 `\n` 分行；一个形状内若有多段文字，按行依次填入已有文本节点。
- `slides` 中页码必须唯一且升序；**没列进清单的页照样原样保留**（不是删除）。
- 允许字段白名单：`slide` / `purpose` / `replacements` / `image_replacements` / `slots`。

## 四、硬规则（代码层强制，不是口头约定）

| 编号 | 规则 |
| --- | --- |
| R1 | 整份复制原 PPTX，只覆盖被点名页的 slide XML；`presentation.xml`、`[Content_Types].xml`、关系文件一律原样 |
| R2 | 页序与页数 1:1；plan 出现 `remove_slides` / `slide_order` / `duplicate_slides` / `transition` / `notes` 等字段立即拒绝 |
| R3 | slide XML **不做整树重排**：只替换 `<a:t>` 节点内容，图片、图形、装饰、占位区、组合形状、SmartArt、图表、母版引用全部字节级保留 |
| R4 | 备注页、页面切换效果、**未被任何页面引用的素材部件**全部保留（不做垃圾回收） |
| R5 | 不新增/删除 `<a:t>`、`<a:r>`、`<a:p>` 等元素；多行文案超容量时折进已有节点并给出警告，不撑开版式 |
| R6 | 未点名文本框保留原示例文字（可能含模板站推广文字，交付时必须披露） |
| R7 | 第 2、3、4 页在 `inspect` 与审计记录中标注为「版式页·重点保护」 |
| R8 | 出稿自动 `verify`：部件集合、关键结构文件、被改页「剥离文字后字节全等」全部通过才交付 |

## 五、图片 / 素材替换（默认禁止）

必须**三道闸门同时打开**，缺一即报错：

1. `plan` 条目显式写 `user_specified: true` 且给出 `asset` 本机路径；
2. 命令行加 `--allow-image-replace`；
3. `templates/external/feature_flags.json` 的 `image_replace: true`（默认 `false`，用完应改回）。

| 档位 | 授权 | 允许的动作 |
| --- | --- | --- |
| 档 1（默认） | 上述三闸门 | 只把**被指定那一页、被指定那个图片框**对应的图片部件换成同格式新图；尺寸、位置、形状 XML 一律不动，版式零变化 |
| 档 2 | 额外加 `--allow-layout-adjust`，且 plan 写 `layout_adjustment: {"x":…,"y":…,"cx":…,"cy":…}`（EMU） | 在上述基础上，仅调整该图片框的位置/尺寸；**其余页与其余元素一律不动** |

约束：新图扩展名必须与原图片部件一致（否则会破坏包内声明，直接拒绝）；每次替换写入 `audit.json`（模板 ID、页号、部件名、是否调整布局）供追溯。用户没有明确指定图片或素材时，AI 不得擅自替换、增删或重排任何图片。

## 六、边界与红线

- **版权**：外部模板授权状态一律 `unknown`、不可再分发。原件留在本机 `D:\桌面\PPT模板`，索引只入库文字元数据；`local-gallery/` 预览图与全部成品均被 `.gitignore` 忽略。**不得上传 GitHub、公开网盘、对外分发或商用**。
- **推广文字**：29 套模板含模板站推广文字。严格保真会原样保留未点名文本框，交付时必须主动说明，不要假装已清理。
- **医疗数据**：模板属医护主题，若填入真实患者信息，另涉敏感个人信息保护，`output/` 目录不得随意外发。
- **原件漂移**：`apply` 会校验原件 sha256 与索引一致；文件被移动/替换时报错，重跑 `external_templates.py scan` 与 `doctor`，不要加 `--skip-hash` 绕过。
- **多行容量**：`inspect` 会给出每个槽位的 `text_nodes` 数；文案行数超出时合并到最后一个节点并告警，建议改文案或换用容量更大的文本框，而不是要求引擎新增段落。

## 七、验收要点

1. `doctor` 返回 `ready: true`，`missing_count: 0`。
2. `apply` 输出「校验通过：N 页同序，M 个部件中仅 K 个变化」，且 K = 被点名改文案的页数 +（授权的）被换图片数。
3. `verify` 返回 `ok: true`、`errors: []`。
4. 用 PowerPoint 实际打开成品，逐页比对第 1/2/3/4 页：背景、图形、装饰、图片、占位区位置与原件一致，只有点名文字不同。
5. 回归测试：`.venv/Scripts/python.exe -B -m unittest discover -s tests -q` 全绿（含 `test_strict_native.py` 的 9 项）。
6. 回退验证：把 `strict_native` 置回 `false`，`apply` 立即拒绝；内置 15 套与 SVG 出稿不受影响。
