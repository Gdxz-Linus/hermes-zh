---
name: design-md
description: "用于编写、校验与导出基于 Google DESIGN.md 规范的设计令牌文件。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [设计系统, 设计令牌, design-md, ui规范, 无障碍对比度, tailwind导出, google规范]
    category: creative
    related_skills: [popular-web-designs, claude-design]
---

# Google DESIGN.md 设计令牌规范与校验指南

## 概述

指导编写、校验、版本对比以及导出基于 Google 开源标准的 `DESIGN.md` 设计规范文件。该规范通过单个 Markdown 文件将两部分有机融合：
1. **前置元数据**：供计算机与智能体精准解析的机器可读设计令牌（数值与色值）；
2. **正文描述**：供人类与智能体理解其设计动机、业务背景与使用场景的结构化文字说明。

## 适用场景

- “为我的项目创建一份标准持久化的 DESIGN.md 设计规范文件”
- “校验当前设计系统中的文字与背景配色是否符合 WCAG 无障碍对比度标准”
- “对比新旧两版设计规范，检查是否有非预期的破坏性样式变更”
- “将 DESIGN.md 文件中的设计令牌直接导出为 Tailwind CSS 配置或 W3C DTCG JSON 格式”

---

## 一、 文件物理结构与标准模板

一个标准的 `DESIGN.md` 文件包含以下核心段落：

```markdown
---
version: alpha
name: 工程极简风格
description: 面向开发者的硬核极简高对比度设计系统
colors:
  primary: "#0A0D12"
  secondary: "#60646C"
  accent: "#3B82F6"
  background: "#FFFFFF"
  surface: "#F9FAFB"
  border: "#E5E7EB"
typography:
  fontFamily:
    sans: 'Inter, -apple-system, sans-serif'
    mono: 'JetBrains Mono, monospace'
  h1:
    fontSize: "2.5rem"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
spacing:
  base: "4px"
  md: "16px"
  lg: "24px"
---

# 视觉设计定位与原则

## 核心设计理念
陈述为什么选择这套色彩与字体体系，面向什么业务场景。

## 色彩使用规约
- `primary`：用于主要标题与高权重按钮；
- `accent`：用于可点击的链接、高亮状态与主操作聚焦环。

## 排版阶梯与响应式说明
说明移动端与桌面端在大标题字号上的自适应缩放策略。
```

---

## 二、 命令行工具调用范式（校验、对比与导出）

通过官方 CLI 工具（`npx @google/design.md`）对文件进行自动化审查：

### 1. 结构与色彩对比度校验
自动计算前景色与背景色的对比度比值，强校验是否满足 WCAG AA 级（最低 4.5:1）或 AAA 级（最低 7:0:1）标准：
```bash
npx @google/design.md lint DESIGN.md
```

### 2. 多版本差异比对
对比当前修改与历史版本的差异，检查是否有颜色、圆角被意外破坏：
```bash
npx @google/design.md diff DESIGN.md DESIGN.backup.md
```

### 3. 导出为工程代码配置
- **导出为 Tailwind CSS 配置文件**：
  ```bash
  npx @google/design.md export --format tailwind -o tailwind.config.js
  ```
- **导出为 W3C 标准设计令牌 JSON（DTCG 格式）**：
  ```bash
  npx @google/design.md export --format dtcg -o tokens.json
  ```

---

## 三、 检查核对清单

- [ ] YAML 前置元数据中是否包含了核心颜色、字体栈与间距阶梯？
- [ ] 文本颜色与背景颜色组合是否满足基本的无障碍对比度要求？
- [ ] Markdown 正文中是否清晰交代了各个设计令牌的使用动机与约束场景？
