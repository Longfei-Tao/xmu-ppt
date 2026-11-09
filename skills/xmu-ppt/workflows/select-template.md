# 生成前选择视觉模板

本流程优先于两条厦大出稿工作流中的场景推荐。汇报主题描述内容，视觉模板描述外观，两者分别处理。

## 1. 展示并等待选择

用户尚未指定模板时，先建立项目目录，运行以下命令。

```bash
python ${SKILL_DIR}/scripts/template_selection.py prepare <project_path>
python ${SKILL_DIR}/scripts/confirm_ui/server.py <project_path> --daemon --wait
```

准备命令创建本次请求，重复运行保留已有请求与确认结果。可在 `confirm_ui/recommendations.json` 的 `recommended` 数组写入最多三个模板 ID，按场景推荐。推荐仅调整展示顺序。可选的 `recommendation_reasons` 对象以模板 ID 为键，填写具体理由。

等待用户点击确认。超时、关闭页面或无回复都表示待选择，禁止生成页面。等待命令超时后读取结果校验，仍待选择则回到聊天等用户，禁止自行代选。

## 2. 聊天兼容入口

无法打开本地页面时，运行 `template_selection.py list`，展示真实模板封面路径、名称、编号、风格和路线能力，推荐三套并提供其余模板列表或公开画廊。用户回复编号后映射到统一索引的完整 ID。偏好颜色不等同于选定模板。

用户已经指定模板时，无需重复询问。点击模板代表选定视觉风格，不能仅因“选用模板”就判断为原生填充。明确要求保留原版式时选择 native，其余默认 svg，并简短说明。公开画廊复制的指令含明确路线，直接采用。

```bash
python ${SKILL_DIR}/scripts/template_selection.py confirm <project_path> --template <template_id> --route svg --source chat
```

仅在用户明确表示“你帮我选”等授权时，AI 按场景选择并用 `--source delegated` 记录。不得将赶时间、内容充足或等待超时视为授权。

## 3. 校验与锁定

```bash
python ${SKILL_DIR}/scripts/template_selection.py check <project_path>
python ${SKILL_DIR}/scripts/confirm_ui/server.py <project_path> --shutdown
```

只有校验成功才能进入页面创作。读取返回的 `template_id` 和 `route`，写入 `spec_lock.md`。每页遵守该选择，导出前再次运行校验。结果保存在 `confirm_ui/result.json`，含请求 ID、模板、路线、选择来源及确认时间。

已有选择禁止静默覆盖。用户要求换模板时保留现有项目和内容，在新的项目中记录选择并重新适配。覆盖已有产物前说明影响并获得授权。

南强蔚蓝仅支持 svg。用户要求原生保留时，等待其提供源 PPTX 或同意灵活排版。用户上传自己的模板并要求保留时，走 `template-fill-pptx.md`，以该文件为准，跳过内置库选择。

## 4. 维护公开画廊

在仓库根目录运行 `python scripts/build_template_gallery.py`，更新 `docs/templates/`。公开画廊**只生成 15 套内置模板**；`local-gallery/catalog.js` 中的外部模板仅供本机私有预览，默认不合并、不发布。若确需本机预览外部封面，可显式运行 `--include-external`，产物不得提交到公开仓库。本地页面与公开页面共用索引、脚本和样式。公开页只复制指令，用户将其发给 AI 后才建立项目选择记录。

新增或下架模板时，除更新 `templates/decks/catalog.json` 与 `decks_index.json` 外，还要重跑此命令、同步文档里的模板计数与测试断言，并运行 `audit_xmu.py --check-svg`；公开画廊不会随仓库文件自动刷新。
