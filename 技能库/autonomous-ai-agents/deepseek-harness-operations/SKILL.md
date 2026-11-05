---
name: deepseek-harness-operations
description: "DeepSeek Harness (dsh) 运行环境运维：诊断启动异常、鉴权凭据排查、版本升级与软链接维护。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deepseek, dsh, 智能体运行环境, 故障诊断, junction, 软链接维护]
    category: autonomous-ai-agents
    related_skills: [hermes-agent, codex, runtime-verification]
---

# DeepSeek Harness (dsh) 运行环境运维与故障诊断

## 概述

规范 DeepSeek 官方编程智能体框架 DeepSeek Harness（CLI 命名为 `dsh`，包含 `web`、`tui` 与 `headless` 运行形态）的本地化运行环境运维、启动故障排查、模型鉴权凭据诊断与跨版本平滑升级。

**本机专属架构基准（核心持久化事实）**：
- **物理运行库根目录**：本机 `dsh` 依赖库统一固化在 `%USERPROFILE%\.dsh\runtime` 独立目录中；
- **软链接映射体系（Junction）**：`~/.dsh/profiles/node_modules/@deepseek-ai/*` 下的全部依赖项，通过 Windows 目录联接（Junction）直接指向 `runtime` 实体目录；
- **严禁回装防护纪律**：**绝对严禁将 `dsh` 装回 Hermes 自身管理的内部目录**（否则执行系统更新时会导致该目录被整体删除清空）；升级后若新增了依赖包，只需针对新增包建立软链接即可。

---

## 一、 故障诊断排查核心原则

遇到启动失败、提示密钥失效或异常退出时，严格按以下四项原则进行排查，严禁凭空盲猜：

### 1. 先确定实际生效的物理代码副本
`dsh` 的插件可能存在于全局目录、用户目录或缓存中。
- **判断标准**：依据**报错文本的唯一性特征**进行定位。将报错核心关键词在候选目录中执行全词检索，命中的物理文件即为当前进程实际调用的代码；严禁仅凭文件夹修改时间推测。

### 2. 报“密钥无效”时先核对请求路径与端点
- 当界面提示“Authentication Fails / API key is invalid”时，通常并非密钥本身错误，而是请求被送往了错误的端点（例如将自建网关的密钥送到了官方地址）；
- **取证动作**：先使用 `curl` 携带该密钥向目标 `baseURL` 发起最小化测试请求，确认该密钥对该地址是否有效，再核查配置文件中的路由指向。

### 3. 诊断阶段保持纯只读，确认方案后一并执行
- 查因阶段不修改 `settings.yaml`、不调整配置文件；
- 明确给出结论、实测证据数字与文件行号，展示方案由用户决定；
- 用户下达执行指令后，按步骤执行完毕并完成回归验证后再行交付，不在每个琐碎命令前反复请示。

### 4. 结论先行与书面工程表达
- 明确回答“是否属于配置问题/需不需要修改代码”；
- 从使用者体验角度陈述具体影响，附带完整绝对路径与实测数字。

---

## 二、 标准排查流程与指令

### 1. 基础状态巡检
```bash
# 检查当前启动器物理路径与版本号
which dsh
dsh --version

# 检查全局依赖包版本
npm ls -g --depth=0

# 检查用户配置与凭据目录
ls -la ~/.dsh
```

### 2. 导出完整合并配置（不启动应用排查）
```bash
# 导出当前 profile 经由补丁层合并后的最终生效配置
dsh --profile default --dump-config > "%LOCALAPPDATA%/Temp/dsh_merged_tree.yml"
```
- 打开导出的文件，核验 `agent-default-model.provider` 的指向、`baseURL` 与模型名称是否符合预期。

---

## 三、 凭据解析机制与常见协议陷阱

### 1. 凭据解析层级顺序
`dsh` 解析模型凭据的内部优先级为：  
**启动时环境变量 > 本地存储文件（`.credentials.yaml`） > 工程目录 `.env` > 用户目录 `.env`**

- **重要结论**：`.credentials.yaml` 中的 `refs: {DEEPSEEK_API_KEY: <值>}` 直接保存的是**密钥原文**，而非索引哈希；
- 在外部（如 Hermes 的 `.env`）修改环境变量不会影响 `dsh` 读取自身存储文件中的专用密钥。

### 2. 通信协议模式对应关系

| 协议模式配置 | 目标请求完整路径 | 鉴权请求头格式 | 默认端点规范 |
| :--- | :--- | :--- | :--- |
| **`chat-completions`** | `<baseURL>/chat/completions` | `authorization: Bearer <key>` | `https://api.deepseek.com` |
| **`messages`** | `<baseURL>/v1/messages` | `x-api-key: <key>` | `https://api.deepseek.com/anthropic` |
| **`openai-responses`** | `<baseURL>/v1/responses` | `authorization: Bearer <key>` | 适配本机的 Responses 规范网关 |

- 自建 OpenAI 兼容网关若仅实现了标准 chat 接口，若配置协议模式为 `messages`，会导致所有请求被网关返回 401 报错；必须切换至 `chat-completions` 或配置适配器。

---

## 四、 升级与目录软链接维护手册

当对 `@deepseek-ai/dsh` 执行小版本升级后，按以下步骤重构软链接：

1. **在专属目录安装新版本**：
   ```bash
   npm install --prefix "%USERPROFILE%/.dsh/runtime" @deepseek-ai/dsh@latest
   ```
2. **检查并补建 Windows 目录联接（Junction）**：
   对比 `%USERPROFILE%\.dsh\runtime\node_modules\@deepseek-ai\` 下的所有包名与 `~/.dsh/profiles/node_modules/@deepseek-ai/`；
   对新增的依赖包，在 PowerShell 中执行建立：
   ```powershell
   cmd /c mklink /J "%USERPROFILE%\.dsh\profiles\node_modules\@deepseek-ai\<包名>" "%USERPROFILE%\.dsh\runtime\node_modules\@deepseek-ai\<包名>"
   ```
3. **单行验证**：
   运行一次只读提问验证全链路连通：
   ```bash
   dsh headless "请输出两个字：正常"
   ```

---

## 五、 自检核对清单

- [ ] 诊断时是否先导出了合并配置（`--dump-config`），核验了实际生效的 `baseURL` 与 `provider`？
- [ ] 报告密钥故障时，是否已通过单独命令向端点发送请求获得了确凿的 HTTP 状态码？
- [ ] 升级维护时是否严格遵守了独立 runtime 目录规约，没有将包写入临时受管路径？
- [ ] 软链接是否均指向正确的物理路径，未发生断链？
