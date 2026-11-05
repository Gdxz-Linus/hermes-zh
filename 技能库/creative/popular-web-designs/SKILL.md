---
name: popular-web-designs
description: "用于参考主流互联网产品（如 Stripe、Linear、Vercel 等）的视觉设计规范，生成高质量 HTML/CSS 界面。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [网页设计, 前端样式, css, html, 设计系统, 界面模板, stripe风格, linear风格]
    category: creative
    related_skills: [claude-design, design-md, architecture-diagram]
---

# 主流互联网产品设计系统与前端模板库（Popular Web Designs）

## 概述

收录并规范了 54 种全球主流互联网与科技产品（如 Stripe、Linear、Vercel、Notion、Airbnb、GitHub 等）的真实视觉设计系统。每个模板完整提取了对应产品的调色板、字号阶梯、组件圆角与阴影、间距网格系统、响应式断点以及直接可用的 CSS 样式值，供在生成前端页面、管理后台或展示面板时直接参考复用。

## 适用场景

- “帮我设计一个类似于 Linear 风格的高质感暗黑管理后台页面”
- “参考 Stripe 官方网站的渐变色彩与卡片排版，制作一个产品介绍页”
- “生成一个符合 Vercel 极简黑白科技风格的数据监控面板”
- “查阅某知名科技产品的标准配色代码、字体排版与组件阴影参数”

---

## 一、 关联设计技能选型矩阵

在开展前端设计任务时，系统提供了三项分工明确的设计技能：

| 技能标识 | 核心定位与职责分工 | 典型触发场景 |
| :--- | :--- | :--- |
| **`popular-web-designs`（本技能）** | **视觉词汇与参数库**：提供 54 种成熟产品的精确颜色、字体栈、组件样式与 CSS 真实取值。 | 明确要求“做成类似 Stripe / Linear 风格”，或需要成熟视觉体系时。 |
| **`claude-design`** | **设计全流程控制**：指导如何审阅需求、构建页面结构、多方案比对、本地真机预览以及杜绝 AI 常见排版套话。 | 从零构思全新的原型页面、展示文档或独立交互组件。 |
| **`design-md`** | **形式化规范导出**：编写标准的 DESIGN.md 设计令牌规范文件，支持无障碍对比度检查与导出为代码。 | 形成可被工程团队复用的长期设计规范文件。 |

- **协作范式**：由 `claude-design` 掌控构思与验证流程，由 `popular-web-designs` 提供精准的视觉设计参数。

---

## 二、 54 款设计系统调用方法

1. **查阅与加载对应产品的设计模板**：
   - 模板文件存放在本技能目录下的 `templates/<产品名称>.md`；
   - 调用查看指令提取具体参数：
     ```bash
     skill_view(name="popular-web-designs", file_path="templates/linear.md")
     ```
2. **模板核心内容结构**：
   - **字体引用链接**：预置了免费的 Google Fonts 或本地替代字体，可直接复制粘贴；
   - **CSS 自定义属性变量**：包括背景色、文字主色、次要文字色、强调色、边框色；
   - **核心组件规范**：按钮状态、卡片阴影、导航栏高斯模糊与输入框焦点样式。

---

## 三、 标准 HTML 页面生成代码结构

生成单文件独立 HTML 页面时，遵循现代流式排版规范：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>页面标题</title>
  <!-- 引入对应模板指定的字体 -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
  <style>
    :root {
      /* 从模板文件中提取的具体颜色与间距变量 */
      --bg-primary: #08090a;
      --text-primary: #f7f8f8;
      --text-secondary: #8a8f98;
      --accent: #5e6ad2;
      --border: rgba(255, 255, 255, 0.08);
      --radius: 8px;
    }
    body {
      margin: 0;
      background-color: var(--bg-primary);
      color: var(--text-primary);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
  </style>
</head>
<body>
  <!-- 具体的语义化结构：header, main, section, footer -->
</body>
</html>
```

---

## 四、 交付与验证规约

1. **单文件直接写入**：使用 `write_file` 将完整的 HTML 代码写入本地文件（如 `D:/Hermes/页面设计/linear-dashboard.html`）；
2. **应用内即时预览**：在回复中使用应用内预览语法呈现，便于直接浏览与交互：
   ```
   ::preview{file="D:/Hermes/页面设计/linear-dashboard.html"}
   ```

---

## 五、 检查核对清单

- [ ] 是否根据用户诉求选取了契合的产品设计模板并提取了真实的 CSS 变量？
- [ ] 页面是否采用了语义化 HTML5 标签并支持全屏自适应响应式布局？
- [ ] 产物是否为自包含的独立 HTML 文件，并提供了标准的应用内预览标识？
