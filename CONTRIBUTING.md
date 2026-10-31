# 贡献指南

欢迎提交使用问题、文档更正和可复现的导出缺陷。请优先用不含个人资料的最小示例说明问题，注明 Python、系统、AI 工具和播放软件版本。

## 本地检查

安装 `skills/ppt-master/requirements-core.txt` 后，从仓库根目录运行：

```bash
python -m unittest discover -s tests -v
python skills/ppt-master/scripts/audit_xmu.py --check-svg
python scripts/check_docs.py
```

涉及演示效果的变更，还应渲染产物并核对所有页面。检查通过不等于所有客户端已验证；在说明中记录环境和未验证范围。长命令与输入格式依赖见[进阶文档](docs/advanced.md)。

## 模板与展示贡献

请提供来源、作者、许可文本或授权记录，以及可再分发的范围。公开可下载、校内可用或非商业使用均不能直接证明允许公开再分发。未知项记录在[素材清单](docs/assets.md)，不要自行把素材统一改成 MIT，也不要擅自删除。

新增截图必须来自实际产物，并附源稿与页码。示意数据明确标记；不要提交私有论文、身份信息、API Key、账号配置、字体文件或无许可图片。校徽和校名标准字不要重画、拉伸或冒充官方授权。

## 文档维护

首页只保留定位、展示、首次使用和限制；工具安装步骤放 `docs/tools/`，官方来源和核验日期随之更新。对比参考见[展示调研](docs/project-references.md)，历史技术检查见[插件审查](docs/plugin-audit.md)。

技能默认交付演示稿和必要说明。维护文档、审查记录与 JSON 验证文件不应自动作为用户附件。

共享 Skills、MCP 和全局提示词若由 CC Switch 管理，应回到 CC Switch 修改源配置；仓库贡献不应改写已安装客户端副本或认证。提交时保持变更范围可审查，并只提交本次修改。
