---
name: opencode
description: "用于向开源 OpenCode CLI 派发独立的代码编写、重构与模块审查任务。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [opencode, 编码智能体, 任务委托, 代码审查, 智能体协同]
    category: autonomous-ai-agents
    related_skills: [claude-code, codex, requesting-code-review]
---

# OpenCode CLI 智能体调度技能

## 概述

规范在 Hermes 内部调度开源编码智能体 OpenCode CLI（命令行可执行文件为 `opencode`）。将特定的代码编写、架构重构、单测生成与模块审查任务委托给 OpenCode 独立实施，形成主副协同的自动化开发流水线。

**核心协同分工**：
- **主助手（Hermes）**：担任架构规划与主审职责，负责需求梳理、规格拟定、方案制定、物理文件范围划定、真实验证与终审；
- **委托实施助手（OpenCode）**：担任代码实施角色，负责在指定的目录与参数约束下执行代码修改与定向单元测试。

---

## 一、 核心调度模式

### 1. 单次非交互运行模式（`opencode run`，确定性任务首选）
用于目标明确、无需多轮交互确认的单次修改任务：

```bash
# 执行单次代码重构任务
opencode run "为 src/auth.rs 中的接口调用增加超时控制与异常强校验"

# 附带上下文参考文件
opencode run "严格对照规格说明书实现新模块" -f spec.json -f config.yaml

# 指定特定的模型提供方与模型名称
opencode run "修复单元测试失败问题" --model openrouter/anthropic/claude-sonnet-4
```

### 2. 交互式后台会话模式（复杂多步任务）
当需要进行多轮连续交互或分步迭代确认时，利用后台进程管理工具拉起会话：

```python
# 1. 在后台以交互伪终端形式拉起进程
session = terminal(command="opencode", workdir="D:/project", background=True, pty=True)
session_id = session["session_id"]

# 2. 向进程提交首轮开发任务指令
process(action="submit", session_id=session_id, data="重构网络请求模块并补充单测")

# 3. 轮询并查验任务执行日志
process(action="poll", session_id=session_id)
process(action="log", session_id=session_id)

# 4. 任务结束安全退出（发送中断信号或强制结束）
process(action="kill", session_id=session_id)
```
*注意：在 OpenCode 中严禁发送 `/exit`（此命令会被识别为模型选择器，导致界面停止响应），退出必须发送中断信号或调用进程结束指令。*

---

## 二、 工程纪律与防错措施

1. **物理文件边界明确**：
   - 派发指令时必须显式声明允许修改的绝对或相对文件路径，严禁使用“该文件”、“上述代码”等模糊词汇；
2. **白名单差异核验**：
   - 任务返回后，主助手必须以任务前批准的清单核对 `git diff --name-only`；
   - 凡发现未经批准修改的文件，立即调用 `git restore <文件路径>` 执行还原，恢复原状；
3. **测试范围受控**：
   - 明确限定：“*仅运行当前单元的定向测试，严禁执行全库编译或全量格式化*”，防止命令超时中断。

---

## 三、 自检核对清单

- [ ] 派发单次任务时是否优先使用了 `opencode run` 非交互模式？
- [ ] 派发指令中是否指定了明确的目标文件清单与业务验收要求？
- [ ] 实施完成后是否由主助手亲自审查了 Git 变更差异并确认未发生越权修改？
