# 用户模板入库与内容先行：xmu-ppt 下一阶段方案

- 日期：2026-11-09
- 状态：方案，未实现
- 基线：`main@7d558ac`（公开版只保留 15 套内置模板）
- 适用范围：`skills/xmu-ppt/`、`docs/`、`tests/`
- 参考对象：PPT Master v6.9.0（只学习架构与方法，不复制文件）

---

## 0. 一页结论

### 学什么

1. **用户自备模板入库**：把用户合法持有的 `.pptx` 变成本机可选的模板，而不是继续分发第三方模板包。
2. **内容先行**：先确认汇报内容和证据，再推荐模板、挑页面、填文字。
3. **页面语义目录**：给每一页标注“适合什么内容”，让 AI 按内容挑页，而不是凭感觉翻页。
4. **轻量 Brand/Layout 分层**：先把品牌身份和页面结构拆开，不照搬 PPT Master 的四层体系。
5. **工程质量门禁**：技术检查继续保留，再增加内容证据检查和权利确认。

### 我们的核心优势

- 模板保真：克隆已有页，只改文字，不重新设计版式。
- 结果可预测：文字容量、内容和模板一致性三项检查，失败不交付。
- 厦大/学术垂直场景：15 套精修模板，适合答辩、组会、课程和医护汇报。
- 用户交互简单：用户只需要报一个模板序号，不需要理解四类模板和复杂参数。
- 本地优先、版权边界清楚：公开仓库只发 15 套；用户模板只留本机。
- 已有工程基础：`analyze`、`fill_plan`、`text_fit`、`sanitize_pptx`、`strict_native`、本地画廊都可以复用。

### 最重要的两个动作

1. **P0：做“我的模板”入库向导**，让用户把自己的 PPTX 接进来。
2. **P0：把“内容策划案”正式放进默认流程**，放在选模板之前。

### 不做什么

- 不把自由设计变成默认路线。
- 不照搬 PPT Master 的 Brand/Style/Layout/Deck 四层体系。
- 不追求 33 个图表、1.2 万个图标这种规模。
- 不公开分发任何用户模板或第三方模板。
- 不为了“功能多”牺牲“模板保真、结果稳定”。

---

## 1. 背景与目标

### 1.1 当前状态

当前 `xmu-ppt` 已经具备：

- 15 套厦大模板，14 套支持原生填充；
- `idea_to_ppt.py` 的 `recommend → confirm → pages → build` 主流程；
- 外部模板的本机扫描、序号登记、离线画廊和严格保真路线；
- 文字容量检查、模板一致性检查、音频/自动翻页净化；
- 公开画廊只展示 15 套内置模板；
- 116 项测试和素材、隐私、文档检查。

当前的主要缺口：

1. 用户想用自己的模板，仍要理解 `root.local.json`、`scan`、目录结构等概念，门槛偏高。
2. 默认流程是“先选模板”，但学术汇报真正重要的是先把内容讲清楚。
3. `layout_index.json` 只有角色、槽位和摘要，没有“这页适合对比、时间线还是 KPI”的语义。
4. 15 套模板是封闭成品，新增风格或场景需要再做一套完整模板。
5. 文档里还保留了一些旧路线说明，容易出现口径不一致。

### 1.2 为什么现在做

公开版已经下架 200 套外部模板包。模板覆盖不能再靠“发一个大模板包”解决，正确方向是：

> **让用户把自己合法持有的模板安全地接入本机。**

这既解决版权问题，也解决模板数量问题。用户不需要我们替他承担第三方模板的再分发风险。

### 1.3 目标

- 用户能在不理解底层目录的情况下，把一个 `.pptx` 加入“我的模板”。
- 用户能在选模板前，先确认一页纸的内容策划案。
- AI 能根据内容形态推荐模板和页面，而不是盲目翻页。
- 现有 15 套模板、现有出稿引擎和三项检查不受破坏。
- 公开仓库仍然只包含 15 套内置模板，不出现任何用户/第三方模板资产。

### 1.4 非目标

- 不做在线模板市场。
- 不做云端模板同步。
- 不做公开的模板包分发。
- 不做完整的四类模板工作区。
- 不做免费自由设计作为默认路线。
- 不在第一阶段做音频旁白、复杂动画和多人协作。

---

## 2. 对照 PPT Master：学什么，不学什么

### 2.1 PPT Master 真正的优点

| 优点 | 具体表现 | 对我们的启发 |
|---|---|---|
| 模板分层 | Brand / Style / Layout / Deck 四类工作区 | 不照搬四层，但可以把品牌和版式拆开 |
| 用户模板创作 | `Create Template` 能从 PPTX、品牌手册、图片中提炼模板 | 做“我的模板”入库向导 |
| 内容先行 | 先确认沟通契约、页面角色和证据，再生成页面 | 增加一页纸内容策划案 |
| 页面/图表词汇 | 页面角色、图表类型、表格类型有明确选择规则 | 给页面加语义标签，按内容形态挑页 |
| 多路线 | 自由设计、编辑原生 PPTX、图片转 PPT、模板创作 | 保留我们的原生填充和严格保真，不盲目加路线 |
| 质量门禁 | 计划、执行、检查、修复分层 | 保留三项技术检查，增加内容和权利检查 |
| 干净的发布包 | 22.8 MB 技能包，不附带第三方整稿模板 | 继续坚持公开版只发 15 套 |

### 2.2 不照搬的部分

| 不学 | 原因 |
|---|---|
| 四类模板完整体系 | 对 15 套模板和普通用户来说太重，维护成本高 |
| 自由设计默认 | 会削弱我们“模板保真、结果稳定”的差异化 |
| 33 个图表、6 个表格、1.2 万图标 | 学术场景高频类型有限，规模不是壁垒 |
| Eight Confirmations 长流程 | 确认成本太高，用户容易疲劳 |
| 音频旁白、复杂动画 | 不是学术汇报的核心痛点，先不做 |
| 用模板数量做卖点 | PPT Master 只有 2 套完整 Deck，说明能力来自组合而不是数量 |

---

## 3. 我们的优势与短板

### 3.1 优势

| 优势 | 说明 |
|---|---|
| 模板保真 | 克隆已有页，只改文字；不重画、不改版式 |
| 结果稳定 | 文字容量和模板一致性检查，放不下就失败，不静默截断 |
| 学术垂直 | 15 套厦大模板覆盖答辩、组会、课程、医护等高频场景 |
| 交互简单 | 用户报三位序号即可，不需要理解模板分类 |
| 本地优先 | 用户模板和成品留本机，公开仓库只发 15 套 |
| 工程基础完整 | 已有 analyze、fill_plan、text_fit、sanitize、strict_native |
| 多宿主 | Codex、Claude Code、Copilot、Gemini CLI 都可调用 |
| 可审计 | 测试、素材、隐私、文档检查已经成体系 |

### 3.2 短板

| 短板 | 影响 |
|---|---|
| 用户模板入口太技术化 | 普通用户不会配置 `root.local.json` |
| 内容策划不正式 | 先选模板容易选错，后面返工 |
| 页面没有语义 | AI 只能读摘要，挑页不稳定 |
| 模板是封闭成品 | 新增场景要复制整套模板 |
| 文档路线多 | 容易出现“不同 Agent 说法不一致” |
| 原生能力有限 | 图表、表格、讲者备注支持不足 |

### 3.3 产品定位

> **厦大/学术场景的模板保真出稿工具：支持用户自备模板，内容先行，但不过度设计。**

不是通用设计引擎，也不是模板市场。我们的核心承诺是：

1. 你的模板不用改版式；
2. 你的内容能讲清楚；
3. 你的文件只留在本机；
4. 出稿失败会明确告诉你为什么。

---

## 4. 目标产品模型

### 4.1 三层轻量模型

不照搬四类模板，只做三层：

```text
Brand（品牌身份）
  颜色、字体、Logo、语气、图标风格
        ↓
Deck（成品模板）
  一套完整模板 + 页面目录 + 槽位
        ↓
Page Catalog（页面语义）
  每页适合什么内容、容量多少、有没有表格/图表
```

`Style` 暂时不单独建层。我们的模板本身已经带有风格；等后续需要“同一套版式换表达方法”时再考虑。

### 4.2 两条主线

```text
主线 A：我的模板入库
用户 PPTX → 权利确认 → 本机模板库 → 页面目录 → 可选模板

主线 B：内容先行出稿
想法/材料 → 内容策划案 → 推荐模板 → 用户选序号 → 页面匹配 → 填字 → 检查 → 交付
```

两条主线共用同一个模板选择、页面目录和出稿引擎。

### 4.3 边界

- 内置 15 套：随公开仓库分发。
- 我的模板：只在本机，不进入公开仓库、不进入 Release、不上传。
- 公开画廊：永远只展示 15 套内置模板。
- 用户模板的序号：使用 `U001` 前缀，避免和内置 `001–015`、外部 `016+` 冲突。
- 用户模板的权利：由用户确认；项目不提供任何第三方授权。

---

## 5. 流程设计

### 5.1 我的模板入库

```text
选择 .pptx
  → 检查格式/大小/宏
  → 用户确认“我合法持有这个模板”
  → 复制到本机模板库（默认）
  → 分析页数、版式、槽位、表格、图表、图片
  → 生成页面目录
  → 生成封面/逐页预览
  → 分配本地序号 U001
  → 写入本地注册表
  → 在本地画廊中可见
```

用户看到的不是“扫描目录”，而是：

```text
已加入“我的模板”：
- 名称：我的组会模板
- 序号：U001
- 页数：18 页
- 检测到：封面、目录、章节页、对比页、表格页、结束页
- 原件：只保存在本机
- 预览：local-gallery/index.html
```

### 5.2 内容先行出稿

```text
用户给出主题/材料
  → 生成内容策划案（一页纸）
  → 用户确认内容、证据和页数
  → 根据页面形态推荐模板
  → 用户报模板序号（001/U001）
  → 查看模板页面，匹配内容策划案
  → 生成 fill_plan
  → build + 技术/内容/权利检查
  → 交付 PPTX
```

### 5.3 兼容旧流程

- 用户已经指定模板时，可以跳过推荐，但仍建议生成内容策划案。
- 用户明确说“赶时间/直接做”时，允许 `--fast` 跳过策划案，但要在交付说明中标注“未做内容确认”。
- 现有 `recommend --idea --positioning` 继续可用；内部自动生成一个最小策划案，避免破坏旧调用。

### 5.4 用户旅程示例

```text
用户：把这个 D:\我的模板\组会模板.pptx 加入我的模板。

Agent：检测到 18 页，包含封面、目录、章节、对比、表格和结束页。
       请确认：你有权在本机使用这个模板吗？
       模板只保存在本机，不会上传，也不会进入公开仓库。

用户：确认。

Agent：已加入，序号 U001。打开 local-gallery/index.html 可以逐页查看。
       以后说“用 U001 做组会汇报”即可。

用户：用 U001 做这次组会汇报，重点是实验设置、结果和下一步。

Agent：先生成一页纸内容策划案：
       P1 封面 / P2 背景 / P3 方法 / P4 实验设置 /
       P5 结果 / P6 失败案例 / P7 判断 / P8 下一步
       每页列出核心结论、证据来源和缺失项。请确认。

用户：确认，开始做。

Agent：根据内容形态匹配 U001 的页面，生成 fill_plan，出稿并检查。
```

---

## 6. 模块一：内容策划案（Content Brief）

### 6.1 目标

把“先选模板”改为“先确认内容”。模板是表达工具，不是内容本身。

### 6.2 CLI

在 `idea_to_ppt.py` 增加 `brief` 子命令：

```bash
PY=.venv/Scripts/python.exe
S=skills/xmu-ppt/scripts/idea_to_ppt.py

$PY $S brief \
  --idea "本次组会汇报" \
  --positioning "课题组组会" \
  --audience "导师和同组同学" \
  --duration 15 \
  -o output/brief.json
```

用户确认后：

```bash
$PY $S recommend --brief output/brief.json
```

保留旧入口：

```bash
$PY $S recommend --idea "..." --positioning "..."
```

旧入口内部生成最小策划案，标记 `fast: true`。

### 6.3 Schema

```json
{
  "schema": "xmu_content_brief.v1",
  "brief_id": "brief-20261109-001",
  "title": "本次组会汇报",
  "audience": "导师和同组同学",
  "occasion": "课题组组会",
  "duration_min": 15,
  "target_pages": 8,
  "status": "draft",
  "sections": [
    {
      "id": "S1",
      "title": "研究背景",
      "purpose": "说明问题和目标"
    }
  ],
  "pages": [
    {
      "page_no": 4,
      "section_id": "S2",
      "purpose": "说明实验设置",
      "key_message": "本次实验采用三组对照，统一数据划分和随机种子",
      "content_shape": ["comparison", "table"],
      "evidence": [
        {
          "type": "file",
          "ref": "实验记录/2026-11-08.md",
          "status": "provided"
        }
      ],
      "data_status": "provided",
      "notes": "需要说明训练阶段和选模规则"
    }
  ],
  "gaps": [
    "测试集结果尚未整理"
  ],
  "confirmed_at": null
}
```

### 6.4 字段规则

| 字段 | 规则 |
|---|---|
| `status` | `draft` 时不能进入推荐；用户确认后写 `confirmed` |
| `target_pages` | 建议值，不硬限制；最终页数由内容和模板决定 |
| `content_shape` | 见 6.5 的枚举 |
| `evidence` | 每个数值/结论至少有一个来源；没有来源写 `missing` |
| `data_status` | `provided` / `missing` / `not_applicable` |
| `gaps` | 明确写出不能编造的内容，交付时保留说明 |

### 6.5 内容形态枚举

```text
cover          封面
toc            目录
chapter        章节页
context        背景/问题
comparison     对比/对照
timeline       时间线/进展
process        流程/方法
kpi            指标/数字
table          表格
chart          图表
image_grid     图片/案例对照
quote          引用/观点
summary        总结
next_steps     下一步
ending         结束页
```

### 6.6 确认门禁

- `recommend --brief` 要求 `status == confirmed`，否则拒绝并提示用户确认。
- `confirm` 把 `brief_sha256` 写入选择门禁。
- `build` 校验 plan 里的 `brief_sha256` 与当前策划案一致；策划案修改后必须重新确认模板。
- `--fast` 允许跳过，但生成一个 `fast: true` 的最小策划案，并在检查报告中标注。

### 6.7 验收标准

- 用户能在对话里看到一页纸策划案，明确每页目的、结论和证据。
- 没有证据的数字不会被硬写成事实。
- 策划案确认后，模板推荐能引用页面形态。
- 修改策划案会使旧模板选择失效，避免“内容变了、模板没变”。

---

## 7. 模块二：我的模板入库（User Template Onboarding）

### 7.1 目标

把“配置目录 + 跑 scan”变成一条用户能理解的命令：

```bash
$PY $S onboard "D:\我的模板\组会模板.pptx" --name "我的组会模板"
```

### 7.2 推荐的产品形态

新增脚本：

```text
skills/xmu-ppt/scripts/user_templates.py
```

提供：

```text
onboard    把一个 PPTX 加入我的模板
list       列出我的模板
doctor     检查原件路径和指纹
remove     从本机模板库移除登记（不删除原件）
```

第一版只需要 `onboard`、`list`、`doctor`。

### 7.3 存储策略

默认：**托管复制**。

```text
~/.xmu-ppt/user-templates/
├── registry.local.json
├── U001/
│   ├── source.pptx
│   ├── user_template.json
│   ├── page_catalog.json
│   └── previews/
│       ├── cover.webp
│       └── pages/
└── U002/
    └── ...
```

理由：

- 用户移动原文件后，模板不会失效；
- 不依赖外部目录结构；
- 所有用户模板和预览都在本机，不进入仓库；
- 需要更新源文件时，重新导入并生成新版本。

高级选项：

```bash
--link
```

只登记原路径，不复制文件。适合文件很大、需要持续更新的模板。`doctor` 会检查路径是否仍然存在。

### 7.4 文件与安全检查

| 检查 | 规则 |
|---|---|
| 扩展名 | 只接受 `.pptx`；拒绝 `.pptm`、`.ppt` |
| 文件大小 | 超过 200 MB 给出警告，超过 500 MB 拒绝 |
| 加密/损坏 | 无法用 `python-pptx` 打开则拒绝 |
| 宏 | `.pptx` 不应含宏；发现异常关系时警告 |
| 外部链接 | 记录外部关系数量，交付时警告 |
| 媒体 | 记录音频/视频/嵌入对象数量；出稿时继续净化 |
| 权利确认 | 必须显式 `--rights-confirmed` 或在交互中确认 |

`--rights-confirmed` 不是法律证明，只是让用户明确知道：

> 模板只在本机使用，公开仓库不提供、不再分发。

### 7.5 分析流水线

复用现有代码：

```text
template_fill_pptx.py analyze
  → source.slide_library.json
  → 页数、槽位、文本、表格、图表、图片
  → page_catalog.py 生成语义目录
  → build_local_gallery.py 生成封面/逐页预览
```

新增 `page_catalog.py`，把 `layout_index.json` 和 `slide_library` 转成：

```json
{
  "schema": "xmu_page_catalog.v1",
  "template_id": "USR-a1b2c3d4",
  "pages": [
    {
      "slide": 1,
      "role": "cover",
      "content_shapes": ["cover"],
      "capacity": {
        "max_title_chars": 18,
        "max_body_chars": 0
      },
      "has_table": false,
      "has_chart": false,
      "image_slots": 1,
      "density": "low",
      "summary": "封面，主标题 + 副标题",
      "confidence": 0.95
    }
  ]
}
```

### 7.6 本地注册表

不写入公开的 `number_registry.json`。新增：

```text
~/.xmu-ppt/user-templates/registry.local.json
```

结构：

```json
{
  "schema": "xmu_user_template_registry.v1",
  "next_serial": 2,
  "entries": [
    {
      "serial": "U001",
      "template_id": "USR-a1b2c3d4",
      "name": "我的组会模板",
      "source_path": "U001/source.pptx",
      "source_sha256": "...",
      "slides": 18,
      "status": "active",
      "rights_confirmed_at": "2026-11-09T01:30:00+08:00",
      "created_at": "2026-11-09T01:30:00+08:00"
    }
  ]
}
```

序号规则：

- 内置：`001–015`
- 外部（旧本机库）：`016+`
- 我的模板：`U001+`
- 三类序号互不冲突，`U` 前缀表示本机私有模板。

### 7.7 与现有流程的接入

- `idea_to_ppt._all_templates()` 追加读取 `registry.local.json`。
- `recommend` 输出内置、外部、我的模板；我的模板显示 `U001`。
- `confirm U001` 解析到本地模板 ID。
- `pages U001` 读取 `page_catalog.json`。
- `build` 使用现有 `template_fill_pptx` 读取 `source.pptx`，不新增出稿引擎。
- `strict_native` 也可以复用同一原件；但第一版只承诺原生填充。

### 7.8 预览策略

- Windows：优先用 PowerPoint COM 渲染封面和第 1–6 页；
- macOS/Linux：用 PPTX 内嵌缩略图或占位图，标记“预览不完整”；
- 预览只写入 `~/.xmu-ppt/` 或 `local-gallery/`，不进入公开仓库；
- 没有预览不影响按序号使用，但会影响“按封面挑”的体验。

### 7.9 错误处理

| 情况 | 行为 |
|---|---|
| 文件不存在 | 直接报错，不创建半成品记录 |
| 已有相同 SHA-256 | 返回已有模板，不重复入库 |
| 同名不同文件 | 自动追加 `-2`，不覆盖 |
| 分析失败 | 回滚暂存目录，不写注册表 |
| 预览失败 | 保留模板，标记 `preview_status: partial` |
| 权利未确认 | 拒绝入库，提示用户确认 |
| 复制中断 | 清理 staging，不留下半套文件 |

### 7.10 验收标准

- 一条命令把 `.pptx` 加入“我的模板”，不需要用户手动改 JSON。
- 入库后能在 `local-gallery/index.html` 看到封面和页数。
- `recommend` 能看到 `U001`，`confirm` 能选中，`build` 能出稿。
- 公开 `docs/templates/` 不出现任何用户模板或封面。
- 用户模板原件不进入 Git，不进入 Release。

---

## 8. 模块三：页面语义库与智能挑页

### 8.1 目标

让 AI 知道“这一页适合什么内容”，而不是只看到“槽位数 20”。

### 8.2 页面目录字段

| 字段 | 说明 |
|---|---|
| `role` | 封面、目录、章节、内容、结束 |
| `content_shapes` | 对比、时间线、流程、KPI、表格、图表、图片组、引用等 |
| `capacity` | 标题/正文/标签的最大字符数 |
| `has_table` / `has_chart` | 是否含原生表格/图表 |
| `image_slots` | 可用图片区域数量 |
| `density` | 低/中/高密度 |
| `summary` | 页面内容摘要 |
| `confidence` | 自动分类置信度，低于 0.6 需人工确认 |

### 8.3 自动分类规则

第一版用启发式，不依赖模型：

- 页内有表格 → `table`
- 页内有图表 → `chart`
- 有 2–4 个并列大区块 → `comparison`
- 有 3 个以上小圆/箭头/时间节点 → `timeline` 或 `process`
- 有大数字/百分比 → `kpi`
- 有大图区域 → `image_grid`
- 有长引用文本 → `quote`
- 封面/目录/章节/结束按角色直接映射

第二版可以增加 AI 辅助分类，但必须允许人工覆盖。

### 8.4 推荐打分

```text
score = 5 × 内容形态精确匹配数
      + 3 × 页面角色匹配
      + 2 × 容量足够
      + 2 × 表格/图表/图片需求匹配
      + 1 × 模板标签匹配
      - 5 × 必需槽位缺失
```

`recommend` 返回模板候选，`pages` 返回每页的 `suggested_for` 和 `reason`。

### 8.5 验收标准

- 内容策划案中的 `comparison` 页面能优先匹配对比页，而不是封面页。
- `pages` 输出不再只是“第几页、几个槽”，而是“这页适合什么内容、为什么”。
- 分类错误可以手工覆盖，不需要改代码。

---

## 9. 模块四：Brand/Layout 轻量分层（P1/P2）

### 9.1 目标

让品牌身份和页面结构可以复用，减少 15 套模板里的重复校徽、配色和字体。

### 9.2 最小实现

```text
brands/厦门大学/brand.json
  colors / fonts / logo / voice / icon_style

decks/<deck>/deck.json
  brand_id: "厦门大学"
  pages: [...]
  page_catalog: page_catalog.json
```

第一版只做“引用”，不重写现有模板：

- 新模板可以引用品牌；
- 旧模板保持原样；
- 不做四类工作区；
- 不做复杂的继承和覆盖规则。

### 9.3 何时做

等“我的模板”和“内容策划案”稳定后再做。否则会同时改模板结构、导入流程和出稿引擎，风险太高。

---

## 10. 质量门禁

### 10.1 现有技术检查（保留）

- 内容完整性：页数、非空文字、无模板示例残留；
- 文字适配：`check-plan` + `text_fit` 绝对容量；
- 模板一致性：元素数一致、无音乐/自动翻页。

### 10.2 新增内容检查

- 每个内容页必须有 `key_message`；
- 每个数字/结论必须有 `evidence` 或标记 `missing`；
- 策划案中的页面必须全部映射到 plan，或被明确标记“删除/合并”；
- 不允许把 `missing` 写成确定事实。

### 10.3 新增权利检查

- 我的模板必须 `rights_confirmed_at` 非空；
- 用户模板不得出现在 `docs/templates/`；
- 技能发布包不得包含 `~/.xmu-ppt/` 或 `local-gallery/`；
- 公开画廊目录只能是 15 套内置模板。

### 10.4 不静默降级

- 内容策划案未确认：默认不进入推荐；`--fast` 显式跳过；
- 文字超容量：build 失败，不自动截断；
- 用户模板分析失败：不创建半成品；
- 预览失败：标记 `partial`，但交付时说明；
- 任何检查失败：不交付成品。

---

## 11. 技术架构与改动清单

### 11.1 新增文件

```text
skills/xmu-ppt/scripts/content_brief.py
skills/xmu-ppt/scripts/user_templates.py
skills/xmu-ppt/scripts/page_catalog.py
skills/xmu-ppt/workflows/content-brief.md
skills/xmu-ppt/workflows/user-template-onboarding.md
skills/xmu-ppt/references/page-catalog.md
tests/test_content_brief.py
tests/test_user_templates.py
tests/test_page_catalog.py
```

### 11.2 修改文件

| 文件 | 改动 |
|---|---|
| `skills/xmu-ppt/scripts/idea_to_ppt.py` | 增加 `brief` 子命令；`recommend` 支持 `--brief`；`pages` 输出语义建议；`build` 校验 `brief_sha256` |
| `skills/xmu-ppt/scripts/external_templates.py` | 保留旧 scan；新增 `onboard` 复用其分析/登记能力，或由 `user_templates.py` 调用 |
| `skills/xmu-ppt/scripts/build_local_gallery.py` | 合并 `registry.local.json` 的 U 前缀模板 |
| `skills/xmu-ppt/scripts/template_numbers.py` | 不改公开注册表；新增本地 U 序号查询辅助 |
| `skills/xmu-ppt/SKILL.md` | 默认流程改为 brief → recommend → confirm → pages → build；增加“我的模板”入口 |
| `skills/xmu-ppt/workflows/idea-to-ppt.md` | 更新四步为五步 |
| `docs/quickstart.md`、`README.zh-CN.md`、`README.md` | 增加“我的模板”用法；保持公开 15 套口径 |
| `scripts/pack_release.py` | 强制排除 `~/.xmu-ppt`、`user-templates/`、`local-gallery/`、用户预览 |
| `tests/` | 新增 3 个测试文件，更新公开画廊断言 |

### 11.3 数据流

```text
brief.json
  ↓
recommend → selection.json（含 brief_sha256）
  ↓
confirm → 模板 ID + 序号
  ↓
pages → page_catalog + suggested_for
  ↓
fill_plan.json（含 source_slide、replacements、brief_sha256）
  ↓
build → sanitize → analyze → text_fit → apply → 三项检查
  ↓
pptx + check report
```

### 11.4 兼容性

- 旧 `recommend --idea --positioning` 继续可用；
- 旧 `confirm`、`pages`、`build` 参数不变；
- 内置 15 套模板不改目录结构；
- 外部本机模板的 `root.local.json` 继续可用；
- 公开画廊仍只 15 套。

---

## 12. 安全、版权与隐私

### 12.1 用户模板

- 默认复制到 `~/.xmu-ppt/user-templates/`；
- 原件不上传、不进入 Git、不进入 Release；
- 预览只在本机；
- 用户必须确认自己有合法使用权；
- 项目不提供任何第三方模板授权；
- 用户可以随时 `remove` 登记，原件保留或删除由用户决定。

### 12.2 公开仓库

- 只保留 15 套内置模板；
- 不发布用户模板、用户预览、用户路径；
- `build_template_gallery.py` 默认只生成 15 套；
- `pack_release.py` 强制排除本机目录；
- 测试断言公开目录必须是 15 套。

### 12.3 文件安全

- 拒绝 `.pptm` 宏模板；
- 拒绝无法解析的损坏文件；
- 记录外部链接和嵌入对象；
- 出稿继续使用 `sanitize_pptx.py` 剥离音频和自动翻页；
- 不修改用户原件，只复制或引用。

---

## 13. 测试计划

### 13.1 单元测试

- `content_brief.py`：schema 校验、draft/confirmed 门禁、缺失证据、页面编号。
- `user_templates.py`：格式拒绝、权利确认、重复 SHA、序号 U001、复制回滚、损坏文件。
- `page_catalog.py`：封面/目录/表格/图表/对比页分类、低置信度。
- `idea_to_ppt.py`：`--brief` 推荐、brief hash 失效、旧入口兼容。

### 13.2 集成测试

- 构造一个 4 页合成 PPTX：封面、对比、表格、结束；
- 入库 → U001 → 本地画廊 → recommend → confirm → pages → build；
- 校验成品页数、无模板示例文字、无音乐/自动翻页；
- 校验公开 `docs/templates/catalog.json` 仍为 15 套。

### 13.3 回归测试

- 现有 116 项测试全绿；
- `check_docs.py`、`check_assets.py`、`check_privacy.py` 全绿；
- `audit_xmu.py --check-svg` 通过；
- 全新 clone 没有 `local-gallery/` 时仍可用 15 套内置模板；
- `pack_release.py` 生成的 ZIP 不含用户模板和预览。

### 13.4 手工验收

- Windows + PowerPoint：入库、预览、出稿、打开成品；
- macOS/Linux：无 PowerPoint 时使用缩略图降级，不阻断出稿；
- 中文路径、空格路径、长文件名；
- 200 MB 大文件、损坏文件、`.pptm` 文件。

---

## 14. 实施阶段

### 阶段 0：方案确认（本文档）

产出：

- 本方案评审通过；
- 确认 U 前缀序号、默认复制、内容策划案默认开启；
- 确认公开版仍只 15 套。

### 阶段 1：我的模板入库 MVP（P0）

任务：

1. 新增 `user_templates.py` 的 `onboard/list/doctor`；
2. 复制到 `~/.xmu-ppt/user-templates/U001/`；
3. 复用 `template_fill_pptx analyze` 和 `build_local_gallery`；
4. 新增本地注册表；
5. `idea_to_ppt` 支持 U 前缀；
6. 更新 SKILL 和文档；
7. 测试：入库、重复、损坏、权利确认、公开目录 15 套。

验收：

- 用户一条命令入库；
- 本地画廊可见；
- `recommend` / `confirm` / `build` 全链路可用；
- 公开仓库无用户资产。

### 阶段 2：内容策划案（P0）

任务：

1. 新增 `content_brief.py`；
2. `idea_to_ppt.py brief`；
3. `recommend --brief`；
4. `confirm` 记录 `brief_sha256`；
5. `build` 校验；
6. 更新默认工作流和文档；
7. 测试：draft 拒绝、confirmed 通过、brief 修改失效、fast 兼容。

验收：

- 用户先看到一页纸策划案；
- 推荐模板引用页面形态；
- 策划案变化会触发重新选模板；
- 旧入口不破坏。

### 阶段 3：页面语义库与智能挑页（P1）

任务：

1. 新增 `page_catalog.py`；
2. 为 15 套内置模板生成 `page_catalog.json`；
3. `pages` 输出 `suggested_for`；
4. `recommend` 增加内容形态打分；
5. 允许人工覆盖；
6. 测试：对比、时间线、表格、KPI、低置信度。

验收：

- 内容策划案里的对比页优先匹配对比版式；
- 减少 AI 盲目翻页；
- 分类错误可修正。

### 阶段 4：Brand/Layout 轻量分层（P2）

任务：

1. 抽取 `brand.json`；
2. 新模板引用品牌；
3. 旧模板保持兼容；
4. 不做四类工作区。

验收：

- 新模板可以复用品牌；
- 旧 15 套出稿不变；
- 不增加用户操作复杂度。

### 阶段 5：可选增强（P2/P3）

- 讲者备注；
- 原生图表/表格只在已有占位时填充；
- 4:3 画布；
- 多模板组合。

这些必须等前三个阶段稳定后再做。

---

## 15. 指标

| 指标 | 目标 |
|---|---|
| 用户模板入库成功率 | ≥ 95%（合法 PPTX） |
| 入库后可直接出稿率 | ≥ 90% |
| 推荐模板被用户接受率 | 逐步提升，不设虚假基线 |
| build 一次通过率 | 不低于当前水平 |
| 公开仓库外部模板资产 | 0 |
| 公开画廊模板数 | 15 |
| 全量测试 | 全部通过 |

---

## 16. 风险与应对

| 风险 | 应对 |
|---|---|
| 页面自动分类不准 | 低置信度要求人工确认；允许手工覆盖 |
| 用户模板含宏/恶意对象 | 拒绝 `.pptm`；记录外部关系；出稿净化 |
| 用户模板太大 | 大小警告/拒绝；支持 `--link` |
| 复制占空间 | 默认复制，提供 `--link`；`remove` 不删原件 |
| 序号冲突 | U 前缀与内置/外部分离 |
| 内容策划案增加摩擦 | 学术场景默认开启；`--fast` 可跳过 |
| 公开仓库泄漏用户资产 | `.gitignore` + `pack_release` + 测试断言 |
| 文档再次不一致 | 默认流程只保留一个入口；旧路线标记 legacy |

---

## 17. 待确认决策

| 决策 | 建议 |
|---|---|
| 用户模板序号 | `U001` 前缀，避免和 001–015、016+ 冲突 |
| 默认复制还是引用 | 默认复制；`--link` 作为高级选项 |
| 内容策划案是否强制 | 学术场景默认；`--fast` 显式跳过 |
| 是否做四类模板 | 不做；只做 Brand + Deck + Page Catalog |
| 是否做图表/图标大库 | 不做；先做 8–10 个高频页面形态 |
| 是否做音频旁白 | 暂不做；先做讲者备注（可选） |

---

## 18. 结论

PPT Master 最值得学的不是“模板多”，而是：

> **把模板拆成可组合的层，把内容放在模板之前，把用户自己的材料变成可复用资产。**

我们的项目不需要变成 PPT Master。我们应该保留：

- 模板保真；
- 三项检查；
- 15 套厦大模板；
- 简单序号选择；
- 本地优先和版权边界。

然后补上：

1. **我的模板入库**：解决“用户自己的模板怎么用”。
2. **内容策划案**：解决“先讲什么，再选什么模板”。
3. **页面语义库**：解决“AI 怎么挑对页面”。
4. **轻量 Brand/Layout**：解决“模板怎么复用”。
5. **内容/权利门禁**：解决“不会编、不会泄漏”。

这五件事做完，我们仍然是“厦大模板保真出稿工具”，但会从“15 套模板的工具”升级为“任何用户都能带自己的模板、先想清楚内容、再稳定出稿的工具”。
