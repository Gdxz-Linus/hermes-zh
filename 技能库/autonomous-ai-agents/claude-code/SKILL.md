---
name: claude-code
description: "Claude Code CLI 智能体调度：通过非交互打印模式与多轮交互会话，安全委托编码与代码审查任务。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [claude-code, 编码智能体, 任务委托, 自动化开发, anthropic, 智能体协同]
    category: autonomous-ai-agents
    related_skills: [codex, requesting-code-review]
---

# Claude Code CLI 智能体调度技能

## 概述

规范在 Hermes 内部调度 Anthropic 官方推出的自主编程智能体命令行工具（Claude Code CLI，命令行可执行文件为 `claude`）。将独立的模块编码、代码审查与批处理修复任务委托给 Claude Code 自主实施，形成高效的人机工程协作流程。

**核心协同准则**：
- **主助手（Hermes）**：担任架构规划与主审职责，明确派发任务的物理文件边界、输入输出规范与验收标准；
- **委托智能体（Claude Code）**：在受控的命令参数下，自主读取代码、编写实现并运行模块测试。

---

## 一、 两大核心调度模式

根据任务复杂度与交互需求，选择适配的运行模式：

### 模式一：单次非交互打印模式（`-p`，自动化任务首选）
该模式以单次指令启动，执行完毕后自动将最终结果与代码变更输出到标准流并退出，**不启动全屏伪终端（PTY），完全规避交互式确认弹窗**。

```bash
claude -p "请为 src/auth.py 中的所有网络请求增加异常捕获与重试机制" \
  --allowedTools "Read,Edit" \
  --max-turns 10
```

#### 适用场景：
- 单一明确的代码编写任务（修复指定缺陷、实现特定函数）；
- 提取结构化数据或生成特定代码片段；
- 任何不需要多轮人工反复澄清的确定性自动化流水线。

---

### 模式二：多轮交互伪终端模式（基于 tmux / 交互会话）
当需要进行多轮深层交互、利用斜杠命令或在复杂重构中逐步确认时，采用终端会话托管运行：

```bash
# 1. 启动会话并在后台拉起
tmux new-session -d -s claude-session -x 140 -y 40

# 2. 进入项目目录并启动程序
tmux send-keys -t claude-session "cd /path/to/project && claude" Enter

# 3. 发送具体编码指令
tmux send-keys -t claude-session "请分析当前接口的性能瓶颈并提出优化方案" Enter

# 4. 抓取终端输出查看进度与结果
tmux capture-pane -t claude-session -p -S -50

# 5. 任务收尾与安全退出
tmux send-keys -t claude-session "/exit" Enter
```

---

## 二、 交互式授权弹窗自动化处理规约

在交互模式下首次进入新工程目录时，Claude Code 会弹出目录信任与权限确认请求，必须准确按键响应：

1. **工作区目录信任弹窗（首次进入目录）**：
   - 终端显示：`❯ 1. Yes, I trust this folder`
   - 处理方式：发送回车确认（`Enter`），采纳默认信任选项。
2. **工具调用权限提示（涉及文件写盘与系统命令）**：
   - 处理方式：先抓取屏幕确认操作内容无越权，发送回车（`Enter`）确认单次执行；若发现风险操作则发送 `Esc` 拒绝。

---

## 三、 工程纪律与防错措施

1. **任务边界明确**：
   - 派发指令时必须使用明确的物理文件路径（如 `src/network.rs`），严禁使用“上一轮讨论的文件”等模糊词汇；
2. **白名单差异审查**：
   - Claude Code 执行完毕后，主助手必须以批准的文件清单为基准，核验 `git diff --name-only`；
   - 严禁将未经批准的无关修改合并汇报，发现越权修改立即执行还原，恢复原状；
3. **测试范围受控**：
   - 派发时明确限定：“*仅运行当前单元的定向测试，严禁执行全库编译或全量格式化*”，防止外部编译耗时过长导致命令超时。

---

## 四、 自检核对清单

- [ ] 单次任务是否优先使用了 `-p` 非交互打印模式，避免了交互过程中停止响应？
- [ ] 派发指令中是否明确限定了允许操作的工具（`--allowedTools`）与最大交互轮次（`--max-turns`）？
- [ ] 接收改动后是否亲自核验了代码变动范围，确认无越权文件修改？
