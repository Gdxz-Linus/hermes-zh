---
name: architecture-diagram
description: "系统架构图设计：生成暗黑专业风格的独立 HTML/SVG 矢量系统架构图与技术拓扑。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [架构图, SVG, 系统设计, 技术拓扑, 矢量图表, 可视化]
    category: creative
    related_skills: [docx, powerpoint]
---

# 系统架构图设计与矢量呈现技能（Architecture Diagram）

## 概述

生成高质感、暗黑专业风格（Dark-themed）的系统架构图与基础设施拓扑图。产物为包含内联 SVG 矢量的独立 HTML 文件，无需依赖任何第三方外部渲染库或在线服务，离线环境下使用任何现代浏览器即可直接渲染并无损放大。

**核心视觉标准**：
- **暗黑底色与工程网格**：统一采用深邃深蓝底色（Slate-950 `#020617`）配合浅灰网格参考线（`#1E293B`），呈现严谨现代的工程视觉质感；
- **分层容器架构清晰**：遵循标准分层拓扑（接入层 $\to$ 核心服务层 $\to$ 计算引擎层 $\to$ 存储设施层），避免模块无规则堆砌；
- **协议与数据流向明确**：连线必须标注通信协议（如 HTTP/gRPC/WebSocket）与数据方向，严禁无标注实线乱穿。

## 适用场景

- 软件系统分层架构设计（前端应用、后端集群、数据库分片、缓存网络）；
- 云原生基础设施拓扑（VPC 网段、负载均衡器、网关、容器编排 Pod 集群）；
- 微服务调用链与消息总线异步通信拓扑；
- 技术立项评审、架构设计文档（Design Spec）中的核心技术图表展示。

---

## 一、 系统架构四层标准容器模型

设计复杂系统时，必须自上而下按照以下四个标准层级容器进行模块划分：

1. **第一层：接入与终端层（Client & Gateway Layer）**：
   - 包含 Web 客户端、移动端 App、CLI 命令行工具、外部第三方调用源以及前置反向代理/API 网关；
   - 色彩体系：青色系（边框 `#22D3EE`，半透明底色 `rgba(8, 51, 68, 0.4)`）。
2. **第二层：核心业务与应用服务层（Application Services Layer）**：
   - 包含微服务集群、业务编排中枢、任务调度守护进程、认证鉴权中心；
   - 色彩体系：翡翠绿系（边框 `#34D399`，半透明底色 `rgba(6, 78, 59, 0.4)`）。
3. **第三层：数据传输与协议处理层（Protocol & Middleware Layer）**：
   - 包含异步消息队列（Kafka/RabbitMQ）、事件总线、RPC 通信中间件、分布式锁管理器；
   - 色彩体系：琥珀橙系（边框 `#FB923C`，半透明底色 `rgba(251, 146, 60, 0.3)`）。
4. **第四层：持久化存储与基础设施层（Persistence & Infrastructure Layer）**：
   - 包含关系型数据库集群、时序数据库、分布式缓存（Redis）、对象存储及物理计算宿主机；
   - 色彩体系：紫罗兰系（边框 `#A78BFA`，半透明底色 `rgba(76, 29, 149, 0.4)`）。

---

## 二、 关键图形绘制技巧（SVG 规范）

### 1. 双矩形遮罩技术（防止箭头穿透）
当组件使用带有半透明色彩的圆角矩形时，背景穿过的连接线箭头容易透视出来导致杂乱。
- **解决方法**：每个组件绘制两次：
  1. 先绘制一个完全不透明的深色底矩形（`fill="#0F172A"`）；
  2. 再在其上方叠加半透明带样式的属性矩形（`fill="rgba(...)" stroke="#..."`）。

### 2. 标准连线与箭头绘制顺序
- **Z 轴层级顺序**：连接线与箭头必须在组件矩形之前绘制（紧随网格之后），这样连线的端点自然隐入组件节点后方，保持接口边缘干净整齐；
- **连接线转角**：优先使用横平竖直的正交折线（Orthogonal Lines），避免出现斜插交错的杂乱斜线。

---

## 三、 标准 HTML/SVG 架构图模板示例

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>系统总体技术架构图</title>
  <style>
    body {
      margin: 0;
      background-color: #020617;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      font-family: -apple-system, "Microsoft YaHei", sans-serif;
    }
    svg {
      max-width: 100%;
      height: auto;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }
    .node-title { font-size: 13px; font-weight: bold; fill: #F8FAFC; }
    .node-sub { font-size: 10px; fill: #94A3B8; }
    .edge-label { font-size: 9px; fill: #64748B; background: #020617; }
  </style>
</head>
<body>
  <svg width="1000" height="600" viewBox="0 0 1000 600" xmlns="http://www.w3.org/2000/svg">
    <!-- 1. 背景网格定义 -->
    <defs>
      <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E293B" stroke-width="0.5"/>
      </pattern>
      <!-- 箭头定义 -->
      <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 8 5 L 0 9 z" fill="#64748B" />
      </marker>
    </defs>

    <!-- 背景底层 -->
    <rect width="1000" height="600" fill="#020617" />
    <rect width="1000" height="600" fill="url(#grid)" />

    <!-- 2. 连接线（先于组件绘制） -->
    <path d="M 500 120 L 500 200" fill="none" stroke="#64748B" stroke-width="1.5" marker-end="url(#arrow)" />
    <text x="510" y="165" class="edge-label">HTTP / JSON</text>

    <!-- 3. 组件节点（双矩形遮罩） -->
    <!-- 接入层节点 -->
    <g transform="translate(400, 60)">
      <rect width="200" height="60" rx="8" fill="#0F172A" />
      <rect width="200" height="60" rx="8" fill="rgba(8, 51, 68, 0.4)" stroke="#22D3EE" stroke-width="1.5" />
      <text x="100" y="28" text-anchor="middle" class="node-title">API 统一路由网关</text>
      <text x="100" y="46" text-anchor="middle" class="node-sub">反向代理 / 负载均衡</text>
    </g>

    <!-- 核心业务服务层节点 -->
    <g transform="translate(400, 200)">
      <rect width="200" height="60" rx="8" fill="#0F172A" />
      <rect width="200" height="60" rx="8" fill="rgba(6, 78, 59, 0.4)" stroke="#34D399" stroke-width="1.5" />
      <text x="100" y="28" text-anchor="middle" class="node-title">推理编排核心服务</text>
      <text x="100" y="46" text-anchor="middle" class="node-sub">分布式会话 / 状态机</text>
    </g>
  </svg>
</body>
</html>
```

---

## 四、 交付与自检核对清单

- [ ] 是否采用了深色背景网格与明确的分层色彩标识？
- [ ] 中文标注文字是否清晰无乱码，排版在容器居中呈现？
- [ ] 各组件之间的连线是否使用了标准的正交折线，并标明了数据流向与网络协议？
- [ ] 生成的 `.html` 文件能否在本地离线环境下直接使用浏览器正常展示并平滑缩放？
