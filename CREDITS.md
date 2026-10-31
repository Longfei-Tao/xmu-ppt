# 致谢与引用说明 / Credits

本文件记录本项目参考过的第三方开源项目、各自的许可证，以及引用的具体范围。

**原则**：除已注明许可与署名的上游引擎外，视觉参考只记录思路与参数，不引入其字体或素材本体。新增首页演示为自主编写内容。凡涉及素材的，其版权状态不受本项目 MIT 许可影响（见 `LICENSE` 顶部 SCOPE EXCLUSION 段）。

---

## 1. 上游项目

| 项目 | 作者 | 许可证 | 引用范围 |
| --- | --- | --- | --- |
| [PPT Master](https://github.com/hugohe3/ppt-master) | Hugo He | MIT | 完整引擎：SVG→PPTX 转换、模板结构、占位符体系、工作流规范 |

本项目是其分支，保留原始版权声明，详见 `THIRD_PARTY_NOTICES.md` 第 1 节。

---

## 2. 厦门大学相关开源项目

| 项目 | 作者 | 许可证 | 引用范围 | 是否复制代码 |
| --- | --- | --- | --- | --- |
| [F5Soft/xmu-template](https://github.com/F5Soft/xmu-template) | F5Soft | MIT | 三档主题蓝的 RGB 值、字体选型、版式结构（无页眉色条 / 页脚三等分 / 章节页水印）、字号阶梯 | 否 |
| [liu-qilong/college-beamer](https://github.com/liu-qilong/college-beamer) | liu-qilong；XMU 主题由 [Marquis03](https://github.com/Marquis03) 贡献 | CC BY 4.0 | 校徽与封面背景的素材组织方式 | 否 |
| [zeyu10/xmum-beamer-template](https://github.com/zeyu10/xmum-beamer-template) | zeyu10 | MIT | 深色主题的配色思路（马来西亚分校体系，未直接采用） | 否 |

整理结果见 [`references/xmu-design-tokens.md`](references/xmu-design-tokens.md)。

### 2.1 引用范围的具体界定

- **配色数值**（如 `#2864BE`）逐项标注出处，以便追溯；不据此推断相关模板或图片均可再分发。
- **版式结构**（色条高度、页脚比例、水印不透明度）属设计方法，本项目仅借鉴思路，未复制其 `.cls`、`.sty` 或任何 LaTeX 源文件。
- **素材**（校徽、封面背景图）：本项目**未取用**上述任何仓库的图片文件。仓库内现有校徽与照片来自校内流传模板，逐文件权属及公开再分发许可尚待核验，适用 `LICENSE` 中的排除条款；历史来源说明不构成授权证明，见 [素材清单](docs/assets.md)。

### 2.2 未采用的项及原因

| 项目 | 许可证 | 未采用原因 |
| --- | --- | --- |
| [zoam/xmu-thesis-grd](https://github.com/zoam/xmu-thesis-grd) | 无许可证 | 未声明许可证即默认保留所有权利，不可再分发 |
| [CamuseCao/XMU-thesis](https://github.com/CamuseCao/XMU-thesis) | LPPL-1.3c | 未引入；具体分发条件需针对文件和许可版本另行核验，不作笼统的 MIT 兼容性判断 |
| `F5Soft/xmu-template` 内的 `simhei.ttf` / `simkai.ttf` / `simsun.ttc` | 归中易字体权利人 | 字库文件版权不归该仓库作者，MIT 无法覆盖，本项目不引入 |

---

## 3. 字体

本仓库**不包含任何字体文件**。设计稿中引用的 `华文中宋`、`微软雅黑`、`方正兰亭黑`、`黑体`、`宋体` 需由使用者自行确保授权或依赖系统已安装字体。

---

## 4. 贡献者

- 模板整理、SVG 原型、快速通道工作流：本项目作者
- 上游引擎：Hugo He 及 PPT Master 贡献者

如需补充或更正引用信息，请提交 Issue 或 PR。

## 5. 本次 GitHub 展示参考

对比了 PPT Master、PptxGenJS、Marp CLI 与 Anthropic Skills 的信息组织及许可范围，记录见 [展示调研](docs/project-references.md)。本次未复制其首页文案、截图、模板或 Skill 实现。
