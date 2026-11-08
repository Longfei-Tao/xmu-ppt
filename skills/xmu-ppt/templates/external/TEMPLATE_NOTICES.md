# External Template Notices / 外部模板声明

对标上游 [PPT Master 的 `THIRD_PARTY_NOTICES.md`](https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/templates/icons/THIRD_PARTY_NOTICES.md)：
**机器台账负责记录客观事实，人工声明负责记录权利主张与边界，两者分开维护。**

本仓库的 MIT 许可（`LICENSE`）只覆盖本项目的代码、脚本、文档与自研的版式结构。
它**不替代**任何第三方模板自身的许可、署名要求、购买协议或商标权利；把一份模板
登记进索引，不等于获得该模板的再分发授权。素材边界总览见 `LICENSE-ASSETS`。

## 1. 随仓库分发的内容

| 内容 | 是否入库 | 说明 |
| --- | --- | --- |
| 15 套内置模板及其逐套授权状态 | 是 | 见 `skills/xmu-ppt/templates/decks/assets_manifest.json` 与 `docs/assets.md` |
| 外部模板的**索引元数据**（名称、分类、页数、指纹、风格标签） | 是 | `external_catalog.json`、`number_registry.json`、`categories.json`、`licenses.json` |
| 外部模板的**原件** `.pptx` / `.ppt` | **否** | 只读扫描本机目录，不复制、不改名、不入库 |
| 外部模板的**预览图与任何衍生截图** | **否** | 只写入本机 `local-gallery/`，已被 `.gitignore` 忽略 |
| 本机模板目录路径、原文件名映射 | **否** | `root.local.json`、`source_map.local.json`、`path_status.json`，均被忽略 |

`scripts/check_assets.py` 会断言仓库中不存在任何外部模板原件；
`tests/test_asset_boundaries.py` 会断言 200 套外部模板均未被标记为可再分发。

## 2. 权利声明

仓库所有者声明：编入外部索引的模板为**其此前购买或自行收集**所得，并声明自己持有
相应的使用权。该声明仅用于说明本机离线使用的来源，**不构成对第三方的授权，也不随
本仓库提供任何权利凭证**。

因此：

- `licenses.json` 中每套的 `status` 保持 `unknown`——含义是「第三方许可文本与凭证
  未随仓库提供」，**不是**对仓库所有者权利的否定；
- 权利凭证（购买记录、授权书、开放许可原文）由所有者自行保管，不上传仓库；
- 任何下载者、二次分发者、商业使用者须**自行核验**所使用模板的权利状态
  （同上游 FAQ 的 `rights are yours to verify`）；
- 如需把某套模板升级为可随仓库公开分发，按 `LICENSE-ASSETS` 第 4 节的流程：
  补齐 `license`、`evidence`、`verified_on` 与 `license_status`，运行
  `python scripts/check_assets.py` 且 0 error 后，才可加入 `public` / `commercial`。

## 3. 署名与商标边界

- 模板原件内的作者署名、水印、品牌标记一律**保持原样**，本项目不剥离、不改写；
- 厦门大学校徽、校名标准字与视觉识别系统素材不因本仓库的 MIT 许可而获得授权，
  公开使用前须遵守学校现行视觉识别规范；
- 索引与展示名称经过脱敏（`external_templates.py` 的 `clean_text`），第三方模板站的
  作者昵称与个人姓名不写入仓库；需要补充的脱敏词通过 `XMU_PPT_PRIVACY_TERMS` 传入；
- 把本仓库或生成的 PPT 对外交付，不代表获得上述任何商标或品牌的使用许可。

## 4. 更新政策

1. 新增模板先运行 `external_templates.py scan` 重建机器台账；**不要手改**
   `licenses.json`（下次 scan 会覆盖，权利声明写在本文件里）；
2. 钉住来源：记录来源类别、扫描日期、文件指纹（`external_catalog.json` 已含 `sha8`）；
3. 每套的权利主张若有变化，在本文件更新声明，并同步
   `LICENSE-ASSETS` 与 `docs/licensing.md`；
4. 每次刷新后重新运行 `python scripts/check_assets.py` 与全量测试；
5. 对外发布前用 `scripts/pack_release.py` 生成**纯技能包**，确认包内不含任何外部
   原件、预览图或本机配置。

## 5. 让别人也能用上这套能力

公开仓库提供的是「会做 PPT 的技能」与 15 套内置模板，不是任何人的私有模板库。
下载者把自己的模板文件夹路径写入 `root.local.json`（示例见 `root.example.json`），
运行扫描与预览渲染，即可在本机选择页里获得与仓库所有者等价的模板浏览与原生填充能力。
原件全程留在使用者自己的电脑上，既不上传，也不随仓库分发。

这一做法与上游一致：上游通过 `/create-template` 把用户自己的 `.pptx` 转成本地
template workspace 并注册，同时提供不含完整仓库历史的轻量技能包（Releases 中的
`ppt-master-skill-*.zip`）。
