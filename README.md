# XMU PPT Master · 厦门大学 PPT 模板分支

基于 MIT 开源的 [PPT Master](https://github.com/hugohe3/ppt-master) 修改而来：保留它的 SVG→原生 PPTX 引擎，只保留 14 套厦门大学模板（3 套官方 + 11 套主题）和一条「说一句话就出稿」的快速通道。

![模板总览](examples/厦大PPT模板总览.png)

## 这套东西能做什么

你只需要说：

> 帮我做一份组会汇报，主题是「术后营养管理与加速康复」，内容我发你。

它会自动完成：选模板 → 拆内容 → 排页面 → 手写 SVG → 导出可编辑 `.pptx`，不需要你先搭框架、选配色、调字号。

### 两种做法，先选一种

| | 原生填充（推荐给别人看） | SVG 出稿（推荐给自己改） |
| --- | --- | --- |
| 一句话 | 在**原始模板**里嵌内容 | 照着模板风格**重画** |
| 模板保真 | 照片、红条、校徽圆章、表格样式、字体字号全部原样 | 图片与装饰能留，复杂版式需手工还原 |
| 页数 | 版式库有多少用多少，同一版式可反复套用 | 靠复制 5 页原型扩展 |
| 排版自由度 | 受槽位约束 | 想怎么排怎么排 |
| 什么时候用 | 答辩、汇报这类「不能改模板」的场合 | 想要新排版、或模板里没有合适的版式 |

说「用这个模板做」，走原生填充；只说「做个厦大风格的 PPT」，走 SVG 出稿。

## 模板库（纯厦大，共 14 套 + 1 个品牌预设）

> 全部模板均为 16:9 / 1280×720。每套模板目录里同时有三种资产：
>
> - `source.pptx` — 原始 PPTX（剥离内嵌字体、压缩过图片，体积降 80% 以上），原生填充的克隆源，页数与版式完整
> - `layout_index.json` — 版式画像：每页是封面 / 目录 / 章节 / 几宫格 / 编号卡片，以及字号与槽位数量
> - `01_cover.svg` … `04_ending.svg` — 5 页 SVG 原型，供 SVG 出稿路线使用

### 官方模板（3 套，人工重制，推荐日常使用）

| 模板 ID | 风格 | 适用场景 |
| --- | --- | --- |
| `厦门大学_官方_厦园晴日` | 蓝白校园实景、半透明白卡、三角装饰 | 论文答辩、开题、预答辩、毕业汇报 |
| `厦门大学_官方_凤栖青橙` | 宣纸底纹、宋体大字、绿瓦屋顶、陈嘉庚雕像 | 人文社科答辩、课程汇报、读书报告 |
| `厦门大学_官方_南强蔚蓝` | 蓝紫渐变、扁平建筑插画、分栏白线 | 组会、工作汇报、项目进展、竞赛路演 |

另有 `厦门大学` 品牌预设（`skills/ppt-master/templates/brands/厦门大学/`），只锁校徽、配色、字体与语气，页面可自由排版。

### 主题风格（11 套，由原 PPTX 一比一转换）

按 PPT Master 官方 create-template 的 mirror 模式转换；页面保留原示例文字，使用时只替换文字、不动版式。

| 模板 ID | 风格 |
| --- | --- |
| `厦门大学_主题_光影厦大` | 深蓝几何光影 + 光影校园照 |
| `厦门大学_主题_凤凰花开` | 深色照片底 + 凤凰花红 |
| `厦门大学_主题_厦大蓝` | 清爽蓝白 + 建筑照片 + 斜向蓝条 |
| `厦门大学_主题_四季风景` | 校园四季实景照片 + 蓝白卡片 |
| `厦门大学_主题_晕染风` | 紫蓝水彩晕染 + 大面积留白 |
| `厦门大学_主题_晚霞` | 暖橙几何 + 晚霞校园照片 |
| `厦门大学_主题_木棉花` | 木棉花照片 + 深蓝半透明标题条 |
| `厦门大学_主题_清凉一厦` | 浅绿清新 + 校园插画 |
| `厦门大学_主题_蓝天校门` | 蓝天校门实景 + 简洁白底 |
| `厦门大学_主题_米金书法` | 米金底色 + 书法校训 + 庄重 |
| `厦门大学_主题_经典蓝白` | 经典蓝白 + 校门照片 |

> 注意：主题模板是“结构原型”——颜色、照片、版式完整保留，但原图表对象会以占位符形式呈现，示例文字需在生成时整体替换。追求像素级还原时，优先选三套官方模板。

## 快速选型

| 你的场景 | 推荐模板 |
| --- | --- |
| 论文答辩 / 开题 / 毕业汇报 | `厦门大学_官方_厦园晴日`，或 `厦门大学_主题_经典蓝白` |
| 人文社科 / 读书报告 / 课程作业 | `厦门大学_官方_凤栖青橙`，或 `厦门大学_主题_米金书法`、`厦门大学_主题_晚霞` |
| 组会 / 工作汇报 / 项目进展 | `厦门大学_官方_南强蔚蓝`，或 `厦门大学_主题_光影厦大` |
| 需要特定视觉风格 | 直接点名 `厦门大学_主题_*` 下的原型 |

## 目录结构

```text
.
├── LICENSE                     # MIT（保留上游与本仓库版权）
├── THIRD_PARTY_NOTICES.md      # 上游署名 + 厦大素材使用边界
├── examples/                   # 官方样张 + SVG 出稿示例 + 原生填充示例 + 总览图
└── skills/
    └── ppt-master/             # 完整引擎（脚本 / 参考 / 工作流 / 模板）
        ├── SKILL.md            # 已加入「厦门大学模板优先」路由（含两条路线判定）
        ├── workflows/
        │   ├── xmu-quick.md    # SVG 出稿快速通道
        │   └── xmu-native.md   # 原生填充快速通道（在原始模板里嵌内容）
        ├── templates/
        │   ├── brands/厦门大学/
        │   └── decks/          # 14 套厦门大学模板
        │       └── <deck_id>/
        │           ├── source.pptx              # 原始模板（克隆源）
        │           ├── source.slide_library.json # 槽位明细
        │           ├── layout_index.json        # 版式画像（选页依据）
        │           └── 01_cover.svg …           # 5 页 SVG 原型
        ├── scripts/
        │   ├── build_layout_index.py  # 新模板入库：瘦身 + 版式索引
        │   ├── template_fill_pptx.py  # 原生填充：scaffold / check-plan / apply
        │   ├── svg_to_pptx.py
        │   └── svg_quality_checker.py
        └── references/
```

## 安装

```bash
git clone <your-repo-url> xmu-ppt-master
cd xmu-ppt-master
pip install -r skills/ppt-master/requirements.txt
```

然后把 `skills/ppt-master` 整个目录复制到你的 Agent 技能目录（Codex 默认是 `~/.codex/skills/`）：

```bash
# Windows PowerShell
Copy-Item -Recurse skills/ppt-master "$env:USERPROFILE\.codex\skills\ppt-master"
```

重启会话后，直接说「用 ppt-master 做一份厦大组会汇报」即可。

## 快速通道行为

`workflows/xmu-quick.md` 定义了四条规则：

1. **按场景选模板**，不让你先选一堆参数；
2. **最多一次轻确认**（模板 + 页数），内容给足时连确认都省略；
3. **内容页四种版式轮换**（观点+两栏 / 数据卡 / 左图右文 / 全宽要点），避免每页都是圆角卡片；
4. **导出前强制质量检查**，文字必须是可编辑的原生形状，不是贴图。

## 手动使用

### A. SVG 出稿

```bash
# 1. 生成项目骨架
python skills/ppt-master/scripts/project_manager.py init demo --format ppt169

# 2. 校验模板页
python skills/ppt-master/scripts/svg_quality_checker.py \
  skills/ppt-master/templates/decks/厦门大学_官方_厦园晴日 --template-mode --canonical-authoring

# 3. 导出
python skills/ppt-master/scripts/svg_to_pptx.py demo -s svg_output -t fade -a none
```

### B. 原生填充

```bash
# 1. 看版式清单，决定用哪几页
cat skills/ppt-master/templates/decks/厦门大学_主题_凤凰花开/layout_index.json

# 2. 生成填充计划骨架（--slides 是源页号，可重复、可重排）
python skills/ppt-master/scripts/template_fill_pptx.py scaffold \
  skills/ppt-master/templates/decks/厦门大学_主题_凤凰花开/source.slide_library.json \
  -o fill_plan.json --slides "1,2,3,5,8"

# 3. 手改 fill_plan.json 里的 text

# 4. 校验容量，再导出
python skills/ppt-master/scripts/template_fill_pptx.py check-plan \
  skills/ppt-master/templates/decks/厦门大学_主题_凤凰花开/source.slide_library.json fill_plan.json
python skills/ppt-master/scripts/template_fill_pptx.py apply \
  skills/ppt-master/templates/decks/厦门大学_主题_凤凰花开/source.pptx fill_plan.json -o out.pptx
```

### C. 新增一套模板

```bash
python skills/ppt-master/scripts/build_layout_index.py \
  "D:/我的模板/某套模板.pptx" --deck-id 厦门大学_主题_某套
```

它会剥离内嵌字体、压缩图片、生成 `layout_index.json` 与 `source.slide_library.json`，放进 `templates/decks/厦门大学_主题_某套/`。

### D. 生成后自检（两条路线都适用）

```bash
python skills/ppt-master/scripts/review_pptx.py out.pptx --min-level warn
```

直接读 PPTX 的 OOXML 做版面体检，不需要打开 PowerPoint，也不需要截图：

| 能查出 | 判据 |
| --- | --- |
| 文本溢出 | 排版后所需高度 ÷ 框内可用高度 ≥ 1.15 |
| 字体被挤压 | 被 PowerPoint 自动缩到 90% 以下 |
| 元素重叠 | 两块文字区域相交 ≥ 25% |
| 越界 | 文字实际右端超出画布 |
| 间距过密 | 上下两段文字间距 < 4pt |
| 占位符残留 | 还留着 `{{...}}` 或 `XXX` |
| 字号过小 | 实际字号 < 9pt |
| 格式错乱 | 同一文本框内混了多种字体/字号 |

每条问题给出页码、形状位置、实测数值和修改建议；`--json` 出机器可读报告；有 ERROR 时退出码为 1，可以直接挡在交付前。

## 依赖

- **Python 3.10+**（脚本使用 `X | None` 形式的类型注解，3.9 会在导入时抛 `TypeError`）
- 核心：`python-pptx`、`PyYAML`、`Pillow`、`requests`
- 按需：PDF / Word / Excel 转换、图片搜索、TTS 等，完整清单见 `skills/ppt-master/requirements.txt`
- 可选：`cairosvg` 或 `svglib`（导出时生成 PNG 后备图）、`playwright`（逐页视觉复核）
- 可选：Microsoft PowerPoint（用于导出 PNG 预览）

## 许可证与素材边界

- 代码：MIT，保留上游版权声明即可商用与再分发。
- **校徽、校园照片、官方模板素材版权归厦门大学所有，仅限校内非商业使用**，不在 MIT 授权范围内。公开发布前请阅读 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
- 仓库不包含任何商业字体；`华文中宋`、`微软雅黑`、`方正兰亭黑` 需使用者自行确保授权。

## 上游与致谢

- PPT Master by Hugo He — <https://github.com/hugohe3/ppt-master>
- 本分支的模板结构、占位符体系与 SVG 技术约束均沿用上游规范。
