# GitHub 展示调研与取舍

[返回首页](../README.md) · [贡献指南](../CONTRIBUTING.md)

2026-10-31 阅读以下 4 个项目的 README 和对应许可文件。这里只借鉴信息组织方式，不搬运截图、文案、模板或 Skill 实现；新增演示内容和图形均在本仓库自主编写。

| 项目 | 首页结构与展示 | 安装与调用 | 案例与可信度 | 许可证核验 |
| --- | --- | --- | --- | --- |
| [PPT Master](https://github.com/hugohe3/ppt-master) | 明确描述输出形式，提供例稿与在线展示入口 | 快速开始与详细工作流分层 | 可下载演示稿，另有能力边界说明 | [MIT](https://github.com/hugohe3/ppt-master/blob/master/LICENSE)；本项目已有引擎归属，新增展示不复制其宣传内容 |
| [PptxGenJS](https://github.com/gitbrent/PptxGenJS) | 从生成 PowerPoint 的用途进入，链接示例和 API 文档 | 安装命令与小型调用代码相邻 | 演示资源与功能文档可对照，不需要依赖营销数据 | [MIT](https://github.com/gitbrent/PptxGenJS/blob/master/LICENSE)；不引入代码或展示图 |
| [Marp CLI](https://github.com/marp-team/marp-cli) | 围绕 Markdown 输入和多种输出格式组织说明 | Quick start、安装、用法各有入口 | 写明浏览器依赖，并区分普通 PPTX 与实验性可编辑导出 | [MIT](https://github.com/marp-team/marp-cli/blob/main/LICENSE)；不引入样式或模板 |
| [Anthropic Skills](https://github.com/anthropics/skills) | 先解释 Skill，再指向示例、规范和使用方式 | 按宿主提供调用路径 | 区分开源示例与文档创建类 Skill 的许可 | [PPTX 专用许可证](https://github.com/anthropics/skills/blob/main/skills/pptx/LICENSE.txt)不是 MIT/Apache；其 README 明示文档类 Skill 仅源码可读，不能套用其他示例的许可 |

## 应用到本项目

- 首页先给一句定位、实际产物截图和输入输出示例，安装入口紧随其后。
- 保留简短的模板风格选择，把完整清单、长命令、依赖和维护验证移到独立文档。
- 同一张展示图能追溯到需求、SVG、PPTX 和渲染器；示意数据就写“虚构示意”，不声称来自真实用户。
- 按工具给出入口，同时列出“官方机制、文档适配、实机验证”，不把一个脚本测试扩写成全平台兼容。
- 保留英文入口，不添加无法核实的星标、用户数、速度或质量承诺。

## 这次没有采用

不复制同类项目的品牌视觉、宣传图或演示文件；不新增模型供应商推荐或账号配置；不为当前仓库虚构插件商店安装命令；不把待核验的学校素材标成已获授权。

此页是维护时的调研记录，不是用户制作 PPT 时需要接收的附件。
