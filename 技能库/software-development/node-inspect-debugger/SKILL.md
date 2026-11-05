---
name: node-inspect-debugger
description: "用于通过 Node.js 内置 inspect 交互终端与 Chrome DevTools 协议（CDP）调试 JavaScript 与 TypeScript 程序。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [nodejs, 调试工具, 断点调试, node-inspect, cdp, 调用路径分析, 变量作用域]
    category: software-development
    related_skills: [systematic-debugging, python-debugpy, inspecting-hermes-desktop-dom]
---

# Node.js Inspect 交互调试与 CDP 协议排障指南

## 概述

指导在终端命令行中，直接利用 Node.js 自带的 V8 调试引擎（`node inspect`）以及 Chrome 开发者工具协议（CDP），对 Node.js 与 TypeScript 应用程序进行深入排障。支持在关键代码行打断点、逐行运行查看代码分支、追踪函数调用链路（Backtrace）、检查内部变量，以及在程序暂停时测试和计算表达式。

## 适用场景

- 运行单元测试报错，需要逐行跟踪并查看函数内部深层嵌套变量的真实取值
- 终端界面组件渲染前数据异常，单纯通过控制台打印日志无法捕获瞬时状态
- 正在运行的后台服务（如网关子进程、任务处理进程）出现阻塞或异常，需要直接接入排查
- 分析内存堆快照（Heap Snapshot）或生成 CPU 性能采样火焰图

---

## 一、 快速交互：`node inspect` 命令行调试工具

无需安装额外第三方依赖，Node.js 原生自带 `inspect` 命令行客户端：

### 1. 启动程序并暂停在第一行
```bash
# 调试标准 JavaScript 脚本
node inspect path/to/script.js

# 调试 TypeScript 脚本（通过 tsx 加载器）
node --inspect-brk --import tsx path/to/script.ts
```

### 2. 交互调试常用命令对照表

在调试提示符 `debug>` 下，常用控制指令如下：

| 快捷命令 | 完整命令 | 真实动作与通俗解释 |
| :--- | :--- | :--- |
| `c` | `cont` | **继续运行**：让程序继续执行，直到遇到下一个断点或执行结束 |
| `n` | `next` | **执行下一行代码**：运行当前行，如果这一行调用了其他函数，直接执行完该函数并停在下一行，不跳进函数内部 |
| `s` | `step` | **进入内部逐行查看**：如果当前行调用了其他函数，直接跳进该函数内部，从第一行代码开始逐行执行 |
| `o` | `out` | **执行完并跳出当前函数**：运行完当前函数剩余的全部代码，返回到上一层调用它的位置 |
| `pause` | `pause` | **立即暂停**：暂停正在持续运行的程序 |
| `sb(42)` | `setBreakpoint` | **设置断点**：在当前文件的第 42 行设置一个暂停断点 |
| `sb('fn')`| `setBreakpoint` | **在函数入口设置断点**：在指定的函数被调用时自动暂停 |
| `cb(42)` | `clearBreakpoint` | **清除断点**：取消当前文件第 42 行的断点 |
| `bt` | `backtrace` | **查看函数调用链路**：自内向外逐层列出当前函数是由谁调用的、完整执行路径是什么（Backtrace） |
| `list(5)`| `list` | **查看代码上下文**：显示当前执行位置前后各 5 行的源代码 |
| `repl` | `repl` | **打开即时求值命令行**：进入当前代码作用域，可直接输入变量名查看内容或测试表达式（按 Ctrl+C 退出） |
| `.exit` | `.exit` | **退出调试**：断开调试器并结束当前程序 |

---

## 二、 接入正在后台运行的常驻服务（Attach）

对于已经启动的后台服务或长期运行的开发服务器，无需重启即可直接接入调试：

1. **服务启动时开放调试端口**：
   ```bash
   # 监听本地 127.0.0.1:9229 端口，程序正常在后台运行
   node --inspect app.js

   # 监听指定端口（避免多进程端口冲突）
   node --inspect=127.0.0.1:9230 app.js
   ```
2. **调试客户端直接连接**：
   ```bash
   # 按端口号接入
   node inspect 127.0.0.1:9230

   # 或通过 WebSocket 调试地址直接接入
   node inspect ws://127.0.0.1:9230/<唯一识别码>
   ```
3. **针对正在运行的进程动态开启调试（仅限 POSIX / Linux 系统）**：
   - 向目标进程发送 `kill -SIGUSR1 <PID>` 信号，Node.js 会在控制台打印调试监听端口，随后即可使用客户端直接接入。

---

## 三、 通过 CDP 协议编写自动化检查脚本

当需要在自动化测试或智能体巡检流程中捕获复杂的数据状态时，可编写 Node.js 脚本通过 WebSocket 发送 CDP 调试协议报文：

```javascript
// 基于 Chrome Remote Interface 的标准自动化调试脚本范式
import CDP from 'chrome-remote-interface';

async function auditRuntime() {
  const client = await CDP({ port: 9229 });
  const { Debugger, Runtime } = client;

  await Debugger.enable();
  await Runtime.enable();

  // 监听断点暂停事件
  Debugger.paused(async ({ callFrames }) => {
    const topFrame = callFrames[0];
    console.log(`执行已暂停于函数: ${topFrame.functionName}, 行: ${topFrame.location.lineNumber}`);
    
    // 在当前执行栈帧中计算表达式
    const { result } = await Debugger.evaluateOnCallFrame({
      callFrameId: topFrame.callFrameId,
      expression: 'JSON.stringify(process.memoryUsage())'
    });
    console.log('当前内存指标:', result.value);

    // 恢复继续执行
    await Debugger.resume();
  });
}
```

---

## 四、 排查原则与资源释放纪律

1. **优先使用简单手段**：
   - 如果只是简单查看某个变量的取值，直接用 `console.log` 打印日志就能查明，不必启动复杂的断点调试；
   - 只有在函数调用层级过深、变量在外部无法直接打印，或者多个异步任务同时运行导致逻辑难以理清时，才需要使用断点调试。
2. **调试结束后必须主动退出**：
   - 调试完成后必须在命令行输入 `.exit` 彻底断开连接。如果非正常关闭窗口，目标服务进程可能会一直停留在暂停状态不再响应请求。
3. **确认端口未被占用**：
   - Node.js 默认使用的 `9229` 端口容易被其他正在运行的实例占用，启动前先核实该端口处于空闲状态。

---

## 五、 检查核对清单

- [ ] 启动调试时是否指定了正确的端口号，未与本机正在运行的其他服务冲突？
- [ ] TypeScript 调试是否正确配置了源码映射文件（Source Map）或 tsx 加载器？
- [ ] 调试完成后是否输入了 `.exit` 退出调试，确认被调试程序已恢复正常运行？
