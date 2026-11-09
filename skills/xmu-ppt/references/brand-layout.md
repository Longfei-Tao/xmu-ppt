# 品牌层与版式层

两层，不是四层。目的是让「该用什么颜色、什么字体」变成机器可读的封闭集合，而不是留在 Markdown 里靠 AI 记忆。

## 文件位置

```text
skills/xmu-ppt/templates/
├── brands/厦门大学/
│   ├── brand.json          # 品牌身份：色板、字体、校徽规则、语气
│   ├── design_spec.md      # 人读的完整品牌规范
│   └── xmu_logo.png        # 校徽原件（唯一真源）
└── decks/<模板名>/
    ├── brand.json          # 本套模板绑定哪个品牌、用哪个主色
    ├── layout_index.json   # 版式层：每页 role / layout / 槽位 / 表格图表
    └── design_spec.md      # 人读的本套设计说明
```

- **品牌层**回答「厦门大学长什么样」：主色、辅助色、标题字体、正文字体、校徽摆放规则、语气。
- **模板层**回答「这一套具体怎么用」：绑定品牌、声明本套主色、声明校徽文件。
- **版式层**回答「这一页是什么」：`role`、`layout`、槽位数、表格与图表数量。这一层早就存在，只是现在有了枚举校验。

## 为什么只拆两层

上游 PPT Master 拆成 Brand / Style / Layout / Deck 四层，因为它是自由设计路线，需要 Style 管「怎么讲」。我们的默认路线是**在既有模板里挑页填字**，Style 已经固化在模板版式里，再拆一层只会增加维护成本。

所以：

| 层 | 我们是否需要 | 理由 |
|---|---|---|
| Brand | 需要 | 15 套共用同一套校徽、配色、字体，不该复制 15 份规则 |
| Layout | 已有 | `layout_index.json` 就是版式层，只补校验 |
| Style | 不需要 | 模板本身就是成品风格，不再抽象 |
| Deck | 已有 | 每套 `decks/<id>/` 就是一个成品组合 |

## 色板约束怎么生效

`pages` 输出会带一个 `brand` 块：

```json
{
  "brand_id": "厦门大学",
  "primary_color": "#02367B",
  "palette": ["#02367B", "#204080", "#005FA5", "#1A1A1A", "#FFFFFF", "..."],
  "typography": {"title": ["华文中宋", "..."], "body": ["微软雅黑", "..."]},
  "logo": {"file": "xmu_logo.png", "placement": {"cover": "top-left"}},
  "voice": {"formality": "formal", "emoji": false}
}
```

填字时如果显式写 `"color": "#FF00FF"`，`build` 会在三项检查的「模板一致性」里记一条警告：

```text
模板一致性：文字颜色不在品牌色板内：#FF00FF（可用：#005FA5、#02367B、...）
```

规则细节：

- 不写 `color` = 沿用模板原槽位颜色，永远允许；
- 写了 `color` 必须在 `palette` 里；
- 警告不阻断出稿 —— 深色照片底反白等合理场景需要灵活性，人工复核比硬拦更合适。

用户模板（`U001`）不属于我们的品牌，`pages` 不会给它套厦大色板，也不会输出 `brand` 块。

## 自检

```bash
python scripts/check_brand_layout.py          # 仓库级：品牌层与模板层是否一致
python skills/xmu-ppt/scripts/brand.py --check
python skills/xmu-ppt/scripts/brand.py 厦门大学_主题_经典蓝白   # 看某套的品牌摘要
```

检查项：

1. 每个品牌有 `brand.json`、`design_spec.md`，schema 正确；
2. `primary_color` 是 `#RRGGBB`，且与 `brands_index.json` 一致；
3. 每套模板有 `brand.json`，`brand_id` 已知，`serial` 与 `catalog.json` 一致；
4. 模板 `primary_color` 与 `decks_index.json` 一致；
5. 声明的校徽文件存在，哈希与品牌层相同；
6. `layout_index.json` 的 `deck_id`、页数、页号唯一性正确；
7. `role` 与 `layout` 都在枚举内。

任何一条不满足，脚本退出码为 1。

## 新增一套模板时

1. 建目录 `decks/<新模板>/`，放 `source.pptx`、SVG 原型、`design_spec.md`；
2. 跑 `layout_index` 生成，得到版式层；
3. 新建 `brand.json`：

```json
{
  "schema": "xmu_ppt_deck_brand.v1",
  "deck_id": "<新模板>",
  "serial": "016",
  "brand_id": "厦门大学",
  "brand_ref": "../../brands/厦门大学/brand.json",
  "primary_color": "#005FA5",
  "color_source": "decks_index.json",
  "logo": {"file": "xmu_logo.png", "sha256": "<与品牌层同一文件>"}
}
```

4. 在 `catalog.json` 与 `decks_index.json` 登记；
5. 跑 `check_brand_layout.py`，必须 `OK`。

## 新增一个品牌时

只有真正要用第二个机构身份（别的学校、别的单位）才需要。做法：

1. 建 `brands/<brand_id>/`，放 `brand.json` 与 `design_spec.md`；
2. 在 `brands_index.json` 登记；
3. 对应的模板 `brand.json` 里把 `brand_id` 改过去；
4. 跑自检。

不要为了「以后可能需要」提前建品牌预设 —— 现在只有一个品牌是事实，不是缺陷。
