---
description: PPT 审阅 —— 生成后对 .pptx 做版面体检，输出问题位置与修改建议
---

# PPT 审阅（Review）

> 位置：**生成之后、交付之前**。检查对象是 `.pptx` 本体，不是 SVG、也不是填充计划。
> 两条路线（`xmu-quick` 的 SVG 出稿、`xmu-native` 的原生填充）产出都是 pptx，所以共用这一道关。

---

## 1. 触发时机

| 时机 | 是否强制 |
| --- | --- |
| `svg_to_pptx.py` 或 `template_fill_pptx.py apply` 跑完之后、把文件交给用户之前 | **强制**，有 ERROR 不许交付 |
| 用户说「看看排版 / 检查一下 / 有没有压字 / 挑挑毛病」 | 立即执行，并把报告原文给用户看 |
| 改完 `fill_plan.json` 或改过某几页 SVG 后重跑 | 强制，只看改动页也要重跑一次 |
| 用户只是问「这文件怎么样」 | 执行，报告只给结论与问题清单 |

不触发的情况：还在写 SVG、还没 apply、只改了 fill_plan 还没生成。

## 2. 检测范围

**对象**：每一页的文本形状、图片、表格、组合形状。不含母版与版式（那是模板作者的职责）。

| 类型 | 代码 | 判据 | 级别 |
| --- | --- | --- | --- |
| 文本溢出 | `TEXT_OVERFLOW` | 排版后所需高度 / 框内可用高度 ≥ 1.15（≥1.40 为错误） | warn/error |
| 字体被挤压 | `FONT_SQUEEZE` | `normAutofit fontScale` < 90%（< 75% 为错误） | warn/error |
| 元素重叠 | `OVERLAP` | 两块**文字**面积相交 ≥ 25%（≥55% 为错误） | warn/error |
| 越界 | `OUT_OF_BOUNDS` | 文字实际右端超出画布 > 2px | warn |
| 间距异常 | `TIGHT_GAP` | 上下相邻文字块间距 < 4pt | info |
| 格式错乱 | `FORMAT_DRIFT` | 同一文本框内 > 2 种字体 或 > 3 种字号 | info |
| 占位符残留 | `UNREPLACED` | 文本含 `{{...}}` 或 `XXX` | error |
| 字号过小 | `TINY_TYPE` | 实际字号 < 9pt | warn |

**关键实现细节**：所有判定都基于「文字实际占位」而不是「文本框」——按字号、换行宽度、对齐方式、垂直锚点先把文字排一遍，算出它真正占的矩形。PPT 的文本框普遍远大于文字，用框判断会产生大量误报。

**明确不检测**：
- 母版 / 版式层的问题
- 字体是否安装（缺字体是渲染时的事）
- 图片内容（人脸被压、照片拉伸）
- 动画与切换
- 像素级视觉差异（这需要真渲染，见下方"深入一层"）

## 3. 呈现方式

### 终端报告（默认）

按页分组，每条三行：位置 → 实测 → 建议。

```
房颤NLRP3答辩_厦园晴日.pptx  ·  14 页  ·  检出 2 错误 / 0 警告 / 0 提示
类型分布：UNREPLACED×2
──────────────────────────────────────────────────────────────────
P01
  ✗ UNREPLACED     s01#5 "指导老师：XXX"
     实测：残留占位符 XXX
     建议：模板原文没被替换，交付前必须填掉
```

### JSON 报告（`--json`）

给自动化用：`summary`（页数、各级计数、按类型分布、每页问题数）+ `issues`（逐条含 `slide` / `kind` / `level` / `where` / `detail` / `advice` / `shape_id`）。

### 退出码

| 情况 | 退出码 |
| --- | --- |
| 无 ERROR | 0 |
| 有 ERROR | 1 |
| 加 `--strict` 且有 WARN | 1 |

可以直接串进流水线：`review_pptx.py out.pptx || echo "有硬伤，先改"`

## 4. 命令

```bash
# 全部级别
python3 ${SKILL_DIR}/scripts/review_pptx.py <deck>.pptx

# 只看要改的（隐藏 info）
python3 ${SKILL_DIR}/scripts/review_pptx.py <deck>.pptx --min-level warn

# 出 JSON 报告
python3 ${SKILL_DIR}/scripts/review_pptx.py <deck>.pptx --json review.json

# 警告也算失败，用于严格交付
python3 ${SKILL_DIR}/scripts/review_pptx.py <deck>.pptx --strict
```

## 5. 拿到报告后怎么改

| 问题 | 处理方式 |
| --- | --- |
| `TEXT_OVERFLOW` | 先删文案（报告里给了要删几行），别先缩字号——缩字号会让这一页比别的页小 |
| `FONT_SQUEEZE` | 说明文案已经超了设计容量，回到 `fill_plan` 砍字，然后把自动缩放改掉 |
| `OVERLAP` | 原生填充路线：换一个更宽的版式，或把内容拆到下一页；SVG 路线：改坐标 |
| `OUT_OF_BOUNDS` | 缩短这一行或左移框；`spAutoFit` 的框也可能因为文字变长而撑出画布 |
| `UNREPLACED` | 必有遗漏的槽位，回 `fill_plan` 补 |
| `TIGHT_GAP` / `FORMAT_DRIFT` / `TINY_TYPE` | 观感问题，时间够就修，不够可放行但要在交付说明里提一句 |

## 6. 深入一层（可选）

估算做不到的部分——照片上的白字对比度、渐变上的深色文字、图标被裁——需要真渲染：

```bash
python3 ${SKILL_DIR}/scripts/visual_review.py <project>   # 需要 playwright + chromium
```

它把每页渲染成 PNG 再逐页看图打分。**只在用户明确要求"看效果"或怀疑有视觉问题时才跑**，不进默认流程。

---

## 已知局限

- **估算模型**：中文按 1em、英文按 0.5–0.6em 估算字宽，与非常规字体（书法体、等宽体）会有 10–15% 偏差，所以阈值留了 15% 余量。
- **`spAutoFit` 的框不判溢出**：这类框会随文字增高，溢出风险转移成"往下压到别的元素"，由 `OVERLAP` 兜底。
- **组合形状不展开**：`group` 内部的文本框按整体外框参与重叠计算，可能漏报组内互压。
- **装饰性大字不判溢出**：≤3 字符且无中文的文本（`01`、`PART`）按设计允许撑出框。
