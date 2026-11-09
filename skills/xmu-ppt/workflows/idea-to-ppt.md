# 默认出稿流程：想法 + 主题定位 → PPT

> 这是 `xmu-ppt` 的**默认且最高优先级**流程。用户只要给出想法与主题定位，一律按本文件执行；
> 默认采用原生文字填充，用户明确要求灵活排版时采用 SVG 路线，已登记外部模板的严格保真要求按独立工作流处理。

## 一、用户需要给什么

只要两样：**想法**（想讲什么、给谁看、要达成什么）和**主题定位**（如「医护健康科普」「课题组组会汇报」「毕业答辩」）。
用户不需要知道模板 ID、页数、路线名，也不需要自己准备素材；内置/外部模板报三位序号（如 `004`），用户自备模板报 `U001`。

如果用户想用自己的 PPTX，先按 [`user-template-onboarding.md`](user-template-onboarding.md) 入库；入库后再进入本流程。

## 序号规则（权威定义）

- **三位序号是模板的唯一权威标识**，由 `templates/external/number_registry.json` 固化；每个模板有且只有一个固定序号。
- 序号一经分配永不变更：不重排、不复用、不回收；被去重隐藏的模板仍占着原序号（标记 `hidden`）。
- 新增模板只在末尾依次追加（`next_number` 当前为 `216`），绝不插入中间或填补跳号。
- **纯数字输入一律按序号解析**。`004` = 光影厦大（内置）；`MED-004` 是模板 ID，其序号是 `019`。二者不可混淆。
- 常用命令：`template_numbers.py check` 校验唯一性、`list` 列出全部对应、`resolve 004` 按序号查模板。
- **用户自备模板使用独立的 `U` 前缀**（如 `U001`），由 `user_templates.py onboard` 分配；不写入公开序号注册表，也不与 `001–015`、`016+` 冲突。

## 二、五步流程

### 第 1 步：内容策划案（推荐默认）

```bash
$PY $S brief --idea "用户原话里的想法" --positioning "主题定位" \
  --audience "听众" --duration 15 -o output/brief.json
```

- 先生成一页纸草稿，列出每页目的、核心结论、内容形态、证据来源和数据缺口；
- AI 根据用户材料补全 `sections` 与 `pages`，用户确认后执行：

```bash
$PY $S brief --file output/brief.json --confirm
```

- 用户明确说“赶时间/直接做”时，可以跳过本步，改用旧的
  `recommend --idea ... --positioning ...`；交付说明中必须标注“内容未确认”。
- 确认后，后续推荐与出稿会绑定这份策划案的 `brief_sha256`；内容改了要重新确认模板。

### 第 2 步 ⛔ BLOCKING：只给候选链接清单，等待选定

```bash
$PY $S recommend --brief output/brief.json
```

- 按主题定位推荐 8 套候选，输出 **可点击的本地画廊链接清单**（每套可直接打开逐页看版式，另有分类浏览链接）。
- 脚本把门禁状态写成 `waiting`。
- **必须停在这里等用户明确报出选定的序号**（内置/外部三位数字，或本机模板 `U001`）。在此之前：
  - 禁止制作任何页面、禁止写 fill plan、禁止调用出稿脚本；
  - 禁止以「我先帮你做一版看看」为由提前开工；
  - 用户没给主题定位时，可以追问一句定位，但不代选模板。

### 第 3 步：确认选择并查看该模板的每一页版式

```bash
$PY $S confirm <用户选定的序号，如 004 或 U001>
$PY $S pages <同一序号> --brief output/brief.json -o output/pages.json
```

- `confirm` 允许用户在画廊里自行挑选推荐清单之外的模板（关键是**明确选定**，不是必须选中推荐项）。
- `pages` 列出模板每一页的角色、内容形态、密度和容量；带 `--brief` 时还会给每条内容策划案页面返回 `suggested_pages` 和匹配原因。没有精确匹配时会给容量较大的备选，并明确提示“可能需要调整版式或另选模板”。
- 内置模板的输出还带 `brand` 块：`palette`（本套合法文字色）、`typography`（标题/正文字体栈）、`logo`（校徽文件与摆放规则）。显式写 `color` 时只能取 `palette` 里的值。

### 第 4 步：按内容挑页并写 fill plan

- **页数不设固定限制**：由用户的想法与主题定位决定需要几页，再从**已选模板**里挑最合适的页面组合。
- 典型结构：封面 → 目录 → 章节页 → 若干内容页 → 结束页；内容多就多挑几页内容版式，内容少就少挑，不要为凑数硬加页。
- plan 里每页写 `source_slide`（模板原有页号）与 `replacements`（只写要替换的文字）。
- 使用内容策划案时，plan 必须带 `brief_sha256`；内容改了要重新确认策划案并重新选模板。
- **只做内容填充**：文案写进模板已有的文本区；不自行设计页面、不新增图形、不改配色/字体/位置、不重排模板元素、不使用 SVG 逐页重画。
- 不得编造实验结果、统计数字、引用、姓名或单位；医学健康类内容只用公认常识，未知字段直接省略。
- 模板里的占位文字（「单击此处添加标题」「输入医院名称」「YOUR CONPANY NAME」等）必须替换或清空，不能留在成品里。

### 第 5 步：出稿 + 三项检查

```bash
$PY $S build output/plan.json -o output/成品.pptx
```

`build` 依次强制完成：

1. **门禁校验**：状态必须为 `confirmed`，且 plan 的 `template_id` 与选定一致；如果本次使用了内容策划案，plan 的 `brief_sha256` 也必须与确认时一致，否则拒绝出稿。
2. **净化兜底**：无论原件是否已清理，出稿源一律先剥离音乐/音频与自动翻页（见 `sanitize_pptx.py`），切换动画与全部版式元素保留。
3. **挑页填充**：克隆模板已有页面，只覆盖文字，切换效果保持 `keep`。
4. **三项检查**（任一不通过即报错，不交付）：
   - 内容完整性：页数与 plan 一致、每页有文字、无残留模板示例文字；
   - 文字适配布局：`check-plan` 错误/警告为 0，且 `text_fit.py` 的**绝对容量校验**为 0 处溢出。检查每个文本框的 `wrap`、几何宽度与字号；`wrap="none"` 的单行框只允许极短短语，可换行多段框按视觉宽度完整分行。**分行仍放不下时 build 直接失败并列出超限槽位，绝不静默截断或改写你的文案**；调整记录会写进检查报告；
   - 模板一致性：每页元素数与模板源页一致、成品无音乐/自动翻页。
5. 检查报告写到 `output/_checks/<成品名>.check.json`。

单独复核已有成品可用 `$PY $S status` 查看门禁状态，或用 `sanitize_pptx.py check <pptx>` 体检。

## 三、边界规则

| 项 | 规则 |
|---|---|
| 模板状态 | 本次使用的模板（内置或用户自备）必须保持**无音乐、无自动翻页**；原件净化见 `scripts/sanitize_pptx.py`，出稿再兜底一层 |
| 页数 | 不固定，由内容决定；但每一页都必须来自用户选定的那套模板 |
| 视觉 | 只填文字，不改版式、图形、装饰、占位区、母版、配色与字体 |
| strict-native | 「一页不少全保留」与本流程「按内容挑页」冲突，**只有用户明确要求「一页不少」时才启用** |
| 版权 | 外部模板授权状态 `unknown`、不可再分发；成品只留本机，`output/` 被忽略，不得上传公开仓库或对外分发 |
| 医疗数据 | 不得填入真实患者信息；如需真实病例须由用户提供并自行负责脱敏 |

## 四、命令速查

```bash
PY=.venv/Scripts/python.exe
S=skills/xmu-ppt/scripts/idea_to_ppt.py
C=skills/xmu-ppt/scripts/sanitize_pptx.py

$PY $S brief --idea "..." --positioning "..." -o output/brief.json   # 第1步：内容草稿
$PY $S brief --file output/brief.json --confirm                      # 用户确认
$PY $S recommend --brief output/brief.json                            # 第2步，等用户选定
$PY $S confirm U001                                                   # 内置/外部用 004，自备模板用 U001
$PY $S pages U001 --brief output/brief.json -o output/pages.json      # 看版式 + 每页匹配建议
# 编辑 plan.json（挑页 + 只写文案 + brief_sha256）
$PY $S build output/plan.json -o output/成品.pptx                     # 出稿 + 三项检查
$PY $C check output/成品.pptx                                         # 复核无音乐/自动翻页
```
