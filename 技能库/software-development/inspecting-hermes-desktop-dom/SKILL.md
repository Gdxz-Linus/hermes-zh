---
name: inspecting-hermes-desktop-dom
description: "用于通过 Chrome DevTools 协议（CDP）实时排查 Hermes 桌面客户端的渲染 DOM 与 CSS 样式。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, 桌面端, electron, cdp, dom检查, css排查, 前端调试]
    category: software-development
    related_skills: [node-inspect-debugger, systematic-debugging]
---

# Hermes 桌面端 DOM 与 CSS 样式实时排查指南（CDP）

## 概述

规范在排查与开发 Hermes 桌面客户端（`apps/desktop`）时，通过 Chrome 开发者工具协议（CDP）直接连接正在运行的 Chromium 渲染进程，实时读取物理渲染树的实际 DOM 结构、几何坐标、最终生效的计算样式以及前端控制台输出。

**核心准则**：
```
以运行时真实 DOM 事实为依据，严禁仅凭组件源码推测样式行为
```
CDP 负责回答关于界面运行时的**确凿客观事实**（如“某节点是否真实挂载”、“计算后的内外边距是多少”、“最终胜出的是哪一条 CSS 选择器规则”）。它不代替用户对视觉美感的最终主观审视，但能彻底消除盲目修改源码试错的低效行为。

## 适用场景

- 修改前端组件后，验证界面在运行态中是否已真实生效
- 样式未按预期展示，需要快速找出具体是哪条全局规则或插件样式覆盖了局部样式
- 提取稳定的组件选择器锚点（`data-slot` 标识）
- 获取用户遇到但在终端无法直接复制的前端渲染层控制台报错日志

---

## 一、 调试端口判定与连接探测

在开发模式启动时，桌面端会自动在本地暴露 Chrome 调试端口（默认 `127.0.0.1:9222`）：

1. **端口开放规则**：
   - 调试端口**仅在开发服务模式下自动开启**；打包后的正式生产发布版或未注入 `HERMES_DESKTOP_DEV_SERVER` 的打包模拟环境中默认关闭。
   - 端口可通过环境变量 `HERMES_DESKTOP_CDP_PORT` 进行重定向（如 `=9333`）或显式禁用（`=off`）。
2. **连接探测命令**：
   ```bash
   curl -s --max-time 3 http://127.0.0.1:${HERMES_DESKTOP_CDP_PORT:-9222}/json/version
   ```
   - 若返回为空，说明调试端口当前未激活；严禁在未确认的情况下随意盲猜其他端口。
3. **红线纪律**：
   - **严禁为了强行获取端口而随意重启用户正在使用的桌面客户端**；这会强行打断用户的交互会话并丢失当前状态。如需排查，应拉起独立的隔离实例。

---

## 二、 读取与求值运行时 DOM

1. **单行快速求值脚本**：
   - 可直接调用工程内置的求值工具：
     ```bash
     cd apps/desktop
     node scripts/eval.mjs "document.querySelectorAll('[data-slot]').length"
     ```
2. **结构化属性提取代码范式**：
   - 使用统一的 CDP 客户端连接并执行包含 Promise 的表达式，将结果在前端运行时内部序列化为紧凑 JSON 返回，**严禁直接导出全量 DOM 树**：
     ```javascript
     import { CDP, SELECTORS } from './scripts/perf/lib/cdp.mjs';

     const cdp = await CDP.connect({ port: 9222, match: '5174' });
     const result = await cdp.eval(`JSON.stringify({
       fontSize: getComputedStyle(document.documentElement).fontSize,
       inputMounted: !!document.querySelector('[data-slot="composer-rich-input"]')
     })`);
     console.log(JSON.parse(result));
     cdp.close();
     ```
   - 优先使用 `scripts/perf/lib/cdp.mjs` 中预定义的 `SELECTORS` 稳定选择器锚点（如输入框、对话消息流、角色面板等），避免易受结构变动破坏的深层级联选择器。

---

## 三、 核心排障场景：哪条样式规则最终胜出？

当样式修改后“看似未生效”时，核心病因通常是 CSS 优先级覆盖或继承机制，排查范式如下：

```javascript
// 提取目标节点自身样式与向上溯源的父级类名
const el = document.querySelector('[data-slot="aui_assistant-message-root"] a');
JSON.stringify({
  ownClasses: el.className,
  fontWeight: getComputedStyle(el).fontWeight,
  ancestorClasses: (() => {
    const list = [];
    let p = el;
    while ((p = p.parentElement) && list.length < 5) list.push(p.className);
    return list;
  })()
});
```

- **诊断决策逻辑**：
  - 若目标节点自身并无显式样式类，则当前值源自父级**继承**；此时在调用处重复修改类名无效，必须修改祖先节点的样式规则；
  - 外部排版插件的默认样式（如 `@tailwindcss/typography` 的 `prose a` 规则）优先级往往高于单一工具类；应在共享层级进行精确重写，而非在各个调用点局部硬改。

---

## 四、 独立无干扰隔离排查环境

若用户窗口未开放调试端口或不便打扰，可构建完全隔离的探测实例：

```bash
cd apps/desktop
HERMES_HOME=$TMPDIR/cdp-probe-home \
HERMES_DESKTOP_DEV_SERVER=http://127.0.0.1:5174 \
HERMES_DESKTOP_CDP_PORT=9333 \
  npx electron . --user-data-dir=$TMPDIR/cdp-probe-userdata
```

- **隔离要点**：
  - 显式指定 `--user-data-dir` 绕开 Electron 的单实例物理互斥锁，杜绝与当前正在运行的图形进程冲突；
  - 显式重定向 `HERMES_HOME` 与 `HERMES_DESKTOP_CDP_PORT`，彻底实现会话数据与网络端口的完全独立、互不干扰；
  - 排查完成后按 PID 平稳收尾，及时释放临时目录。

---

## 五、 自检核对清单

- [ ] 探测前是否核验了 CDP 端口的连通性，未随意杀掉正在运行的用户进程？
- [ ] 查询 DOM 时是否在表达式内部进行了精简投影，避免回传超大体积的无用节点？
- [ ] 样式冲突排查是否检查了层叠上下文与继承链条，准确定位了胜出的规则？
- [ ] 独立测试是否采用了专属的 `user-data-dir`，杜绝触碰正式环境数据？
