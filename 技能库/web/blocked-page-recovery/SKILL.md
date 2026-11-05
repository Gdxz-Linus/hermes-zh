---
name: blocked-page-recovery
description: "用于在网页抓取遭遇 403 权限拒绝、429 速率限制、防爬机制或付费墙阻断时，执行多路径恢复提取。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [网络抓取, 403阻断, 防爬绕过, 网页存档, 真实浏览器渲染, 网页恢复]
    category: web
    related_skills: [grounded-citations]
---

# 受阻网页多路径数据恢复指南（Blocked-Page Recovery）

## 概述

规范在抓取网络数据遭遇访问受阻（包括 HTTP 403 权限拒绝、HTTP 429 访问受限、Cloudflare 验证质询、反爬虫拦截或付费墙遮罩）时的系统级应对流水线。严禁在同一个失败的 URL 上机械重复发起无效请求，必须按照“低开销优先、逐级升级”的标准梯队依次尝试多维替代恢复通道。

## 适用场景

- 使用 `web_extract` 抓取某篇文章或报告时返回错误或空白
- 目标页面被 Cloudflare 或人机验证拦截，无法获取正文
- 历史技术网页已被原站点删除，需要调取历史镜像快照

---

## 一、 五级数据恢复阶梯（由轻到重）

当常规抓取失败时，严格按照以下梯次依次降级尝试：

```
第一级：Wayback Machine 历史档案库（公开抓取快照，最权威、带时间戳）
  ↓
第二级：archive.today 镜像多域名轮换（多用于付费墙或删除内容，轮换 .ph/.md/.li/.is）
  ↓
第三级：Jina Reader 云端后台渲染（适用于高度依赖前端 JavaScript 渲染的单页应用 SPA）
  ↓
第四级：同域 API 接口下探（探查是否存在开放的 /api/、/graphql、.json 或 RSS 订阅源）
  ↓
第五级：真实浏览器内核驱动（终极手段，调度本地真实 Chromium 执行 DOM 提取与渲染）
```

---

## 二、 梯队具体操作与实施规约

### 1. 第一级：Wayback Machine（首选，出处最严谨）
- 先查询最接近的有效快照元数据与时间戳：
  ```bash
  curl -sL "https://archive.org/wayback/available?url={目标URL}"
  ```
- 提取响应中 `archived_snapshots.closest.url` 的真实链接，再次获取快照正文；
- 若出现 503 拥塞，直接切换至第二级，杜绝盲目高频重试。

### 2. 第二级：archive.today 镜像轮换（突破付费与删除限制）
- 适用场景：新闻媒体付费阻断或原站已下架内容；
- 实施域名轮换策略，设置最大 20 秒超时时间，避免单点阻塞：
  ```bash
  for d in archive.ph archive.md archive.li archive.is; do
    curl -sL --max-time 20 "https://$d/newest/{目标URL}" -o "$TMPDIR/page.html" && break
  done
  ```
- **警惕假成功（Fake Success）**：若目标返回 HTTP 429，返回体可能仍附带数 KB 的“请求过于频繁”拦截提示页，绝不能仅凭文件大小判断抓取成功，必须检查正文是否包含真实业务关键词。

### 3. 第三级：Jina Reader（针对现代前端 SPA）
- 适用场景：纯客户端 Vue/React 动态渲染、纯静态抓取为空白的单页应用；
- 在请求头中携带必要鉴权后，调用服务端后台渲染通道：
  ```bash
  curl -s -H "Authorization: Bearer <key>" "https://r.jina.ai/{目标URL}"
  ```

### 4. 第四级：同域名 API / 数据源下探
- 很多站点前端页面设有人机校验，但其底层的公开数据接口或移动端接口并未加设阻拦；
- 尝试探测是否存在公开的 RSS 订阅源（`/rss`、`/atom.xml`）、REST 接口（`/api/v1/...`）或嵌入在 HTML 源码中的 `__NEXT_DATA__` JSON 结构，直接抽取干净的结构化数据。

### 5. 第五级：真实浏览器驱动（终极兜底）
- 调用系统提供的 `browser_exec`，驱动真实 Chromium 浏览器内核加载页面；
- 通过 `page_info()` 读取真实 DOM 状态，通过 `js("document.body.innerText")` 直接从渲染完成的运行时树中提取完整文本，彻底瓦解一切前端动态加载阻碍。

---

## 三、 出处纪律与时效标注标准（铁律）

在将恢复提取到的内容用于事实分析或报告撰写时，必须执行严密的事实出处标注：

| 恢复路径 | 出处属性 | 引用规范与时效声明 |
| :--- | :--- | :--- |
| **Wayback / archive.today** | **历史快照（snapshot）** | **必须附带快照抓取日期**（例如：“引自 2026-08-06 历史快照”）。严禁将历史快照包装为当前实时数据。若涉及股价、库存或突发新闻，必须向用户明确说明快照已存在时间差。 |
| **Jina Reader / 真实浏览器** | **实时渲染（live）** | 属于当前时刻的直接渲染结果，按常规来源正常引用。 |

---

## 四、 自检核对清单

- [ ] 遭遇访问阻断时，是否避免了在原失败路径上重复机械重试？
- [ ] 按照“Wayback $\to$ 镜像库 $\to$ 云端渲染 $\to$ API探测 $\to$ 浏览器”梯次逐级尝试？
- [ ] 是否强校验了抓取返回内容的真实性，排除了 429 拦截页等假成功？
- [ ] 引用历史档案数据时，是否显式注明了快照留存的时间戳？
