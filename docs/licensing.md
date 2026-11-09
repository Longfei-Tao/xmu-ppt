# 授权与边界设计

[返回首页](../README.zh-CN.md) · [素材边界声明](../LICENSE-ASSETS) · [素材核验](assets.md)

本页说明本项目如何把「代码许可」「素材授权」「能力边界」「隔离」拆开管理。
设计参考了上游 PPT Master 的分层做法，但全部实现均为本仓库自有代码，且
**默认不改变任何出稿行为**。

## 1. 三层模型

| 层 | 解决的问题 | 本仓库的落点 |
| --- | --- | --- |
| 法律层 | 哪些能用、能公开到什么程度 | `LICENSE`（代码）+ `LICENSE-ASSETS`（素材边界）+ `assets_manifest.json`（逐套台账） |
| 能力层 | 工具/Agent 能改什么、不能改什么 | `strict_native` 白名单、图片替换三闸门、`feature_flags.json` |
| 隔离层 | 什么东西允许进入公开仓库 | `.gitignore`、`external/licenses.json`、`scripts/check_assets.py` |

三层互相独立：改素材状态不需要动代码；改能力开关不需要动许可；隔离检查
不参与出稿。

## 2. 素材台账

`skills/xmu-ppt/templates/decks/assets_manifest.json` 是机器可读的唯一台账：

```json
{
  "schema": "xmu_ppt_asset_manifest.v1",
  "decks": [
    {
      "deck_id": "厦门大学_主题_四季风景",
      "serial": "007",
      "source_pptx": "skills/xmu-ppt/templates/decks/厦门大学_主题_四季风景/source.pptx",
      "source_sha256": "…",
      "license_status": "unknown",
      "allowed_uses": ["local"],
      "evidence": "docs/assets.md",
      "verified_on": "2026-11-07"
    }
  ]
}
```

字段语义：

| 字段 | 取值 | 说明 |
| --- | --- | --- |
| `license_status` | `project` / `licensed` / `unknown` / `prohibited` | `project` 表示本仓库原创；`licensed` 需有证据；`unknown` 只能本地用 |
| `allowed_uses` | `local` / `public` / `commercial` | 三者可组合；`unknown` 不得声明 `public` 或 `commercial` |
| `source_pptx` | 相对路径或 `null` | `null` 表示该套没有原生源文件（如南强蔚蓝） |
| `source_sha256` | 64 位十六进制 | 锁定当前文件；重新入库或替换素材后需重算 |
| `evidence` | 文档路径或说明 | 指向授权书、购买凭证、开放许可原文或核验记录 |

`docs/templates/previews/`、`docs/assets/screenshots/`、`examples/` 等「展示面」
在 manifest 的 `surfaces` 中按目录登记，规则与 deck 相同。

外部模板库不进入本仓库：`skills/xmu-ppt/templates/external/licenses.json` 中
所有外部模板条目均为 `unknown` / `redistributable: false`，由 `check_assets.py` 守住
「不得出现原件、封面或预览图」的底线。公开仓库只发布 15 套内置模板。

## 3. 能力边界（已有，不改）

这些机制在本改造之前就已存在，本页只把它们记录为契约：

| 机制 | 边界 | 越界行为 |
| --- | --- | --- |
| `strict_native` | 只改被点名页的文字节点；禁删页、禁重排、禁改切换/备注 | 直接拒绝并报错 |
| 图片替换三闸门 | plan 写明 `user_specified` + CLI 授权 + `feature_flags.image_replace` | 任缺其一即拒绝 |
| `check-plan` / `text_fit` | 文字必须落在文本框容量内 | 超容量即失败或自动改写并记录 |
| `sanitize_pptx` | 成品不得含音乐、自动翻页 | 出稿前强制剥离 |

## 4. 隔离策略

| 隔离 | 做法 |
| --- | --- |
| 物理隔离 | 外部模板原件在桌面目录，仓库只存索引；逐页预览图与 `local-gallery/` 被 `.gitignore` 排除，公开画廊只展示 15 套内置模板，不发布任何外部模板封面、预览或下载包 |
| 命名隔离 | `builtin` / `external` 命名空间 + 固定三位序号；序号只追加不重排 |
| 运行时隔离 | 外部模板先净化再出稿；成品只写 `output/` |
| 发布隔离 | `check_assets.py` 检查「公开仓库不得含外部原件」「声明 public 必须有许可」 |

## 5. 新增/替换素材的步骤

1. 放入 `skills/xmu-ppt/templates/decks/<deck_id>/`；
2. 运行 `python scripts/build_asset_manifest.py` 刷新哈希与条目；
3. 在 manifest 中补齐 `license_status`、`allowed_uses`、`evidence`；
4. 运行 `python scripts/check_assets.py`；
5. 只有 0 error 才提交；`public` / `commercial` 需要额外证据。

## 6. 兼容性承诺

本次改造只新增文件与校验脚本，**不修改**：

- `idea_to_ppt.py`、`template_fill_pptx/*`、`text_fit.py`、`sanitize_pptx.py`；
- CLI 参数、plan schema、模板 ID 与序号；
- 默认出稿路径、页数决定方式、三项检查、成品格式。

因此默认出稿结果与改造前逐项一致；`check_assets.py` 不参与构建，只在 CI
或手动执行时运行。

## 7. 适用与不适用

**适用**：代码与素材混排的仓库、模板库、需要区分「本地/公开/商用」的项目、
多人协作需要防误提交的场景。

**不适用**：纯代码库；或者希望「公开仓库直接带未授权品牌素材」——那属于
授权问题，任何边界设计都替代不了许可。

## 8. 隐私检查

```bash
python scripts/check_privacy.py
```

扫描所有已跟踪文本、SVG 与 PPTX 内的姓名标签、邮箱、手机号、证件号，以及
`docProps` 的作者字段。已知占位符（`XXX`、`小夏`、`甲乙丙`）与公开署名
（`作者：Hugo He`）在白名单内；个人姓名可写入被忽略的 `.privacy_terms`
（每行一个），或通过 `XMU_PPT_PRIVACY_TERMS=a,b` 临时补充，不进入仓库。

图片不做 OCR；预览图必须从已通过扫描的源文件重新导出。CI 已接入该检查。
