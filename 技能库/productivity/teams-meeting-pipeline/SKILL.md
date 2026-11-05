---
name: teams-meeting-pipeline
description: "用于通过 Microsoft Graph API 提取 Teams 会议转录文本、生成结构化纪要与调度重放。"
version: 1.2.0
author: Hermes Agent + Teknium
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [MSGRAPH_TENANT_ID, MSGRAPH_CLIENT_ID, MSGRAPH_CLIENT_SECRET]
  commands: [hermes]
metadata:
  hermes:
    tags: [teams, 微软会议, 会议纪要, 语音转录, graph-api, 自动化调度, 行动清单]
    category: productivity
    related_skills: [meeting-action-items, chinese-official-writing]
---

# Microsoft Teams 会议转录与纪要自动化管理指南

## 概述

指导在终端环境中使用 `hermes teams-pipeline` 系列命令，连接 Microsoft Graph API，实现对 Microsoft Teams 会议的生命周期管理。涵盖自动获取会议转录文本、提取核心议定事项与待办行动清单、排查会议任务流转状态、重放失败任务以及管理 Graph Webhook 事件订阅。

## 适用场景

- “帮我提取刚才结束的 Teams 会议转录记录，并生成结构化会议纪要”
- “检查 Teams 会议流水线状态，查看最近处理了哪些会议任务”
- “某次会议纪要未能成功生成，需要重新运行（重放）该任务”
- “检查或更新 Microsoft Graph 的会议事件通知订阅，防止推送中断”

---

## 一、 前置准备与身份凭据检查

在使用该功能前，需确认 `$HERMES_HOME/.env` 中已配置 Azure 应用程序凭据：

```bash
MSGRAPH_TENANT_ID=你的微软租户ID
MSGRAPH_CLIENT_ID=你的Azure应用客户端ID
MSGRAPH_CLIENT_SECRET=你的应用机密密钥
```

- **验证连通性**：
  配置完成后，运行以下指令验证与微软 Graph 服务的认证连接是否正常：
  ```bash
  hermes teams-pipeline status
  ```

---

## 二、 核心操作命令矩阵

所有运维与管理操作均统一通过 `hermes teams-pipeline` 命令行执行：

### 1. 流水线运行状态检查
查看会议处理后台是否正常运转、最近接收的会议任务数量以及有无堆积：
```bash
hermes teams-pipeline status
```

### 2. 查看近期会议任务清单
列出最近捕获并处理的 Teams 会议记录与对应的任务编号：
```bash
hermes teams-pipeline list-jobs --limit 10
```

### 3. 查看特定会议详情与转录文本
查看指定任务的原始会议主题、参会人员、录音转录文本以及已生成的纪要：
```bash
hermes teams-pipeline show-job <任务编号>
```

### 4. 重新执行任务（重放）
如果某次会议因大模型响应超时或网络波动导致纪要生成失败，可直接指定任务编号进行重放，无需重新拉取会议音频：
```bash
hermes teams-pipeline replay-job <任务编号>
```

### 5. 管理微软 Graph 管理事件通知订阅（Webhook）
为了让 Teams 在会议结束时主动通知 Hermes，依赖 Graph 订阅机制：
- **查看当前有效的订阅状态与过期时间**：
  ```bash
  hermes teams-pipeline list-subscriptions
  ```
- **为即将到期的订阅执行续期**：
  ```bash
  hermes teams-pipeline renew-subscription <订阅ID>
  ```
- **重新创建全量订阅**：
  ```bash
  hermes teams-pipeline create-subscription
  ```

---

## 三、 会议纪要生成标准与输出规范

在解析转录文本并输出最终纪要时，必须遵循标准四段式结构（结合 `meeting-action-items` 规范）：
1. **会议基本信息**：明确会议主题、召开时间、组织人与参会人员；
2. **核心背景与讨论要点**：陈述讨论议题的技术与业务背景，概括核心争论点；
3. **议定决策事项**：清晰列出会议最终定调的技术选型与业务决定；
4. **行动项清单（责任到人）**：采用表格形式明确“事项说明 + 责任人员 + 明确交付截止日期”。

---

## 四、 常见问题与排查指南

1. **会议结束但未收到纪要推送**：
   - 检查 Graph 订阅是否已过期（微软 Webhook 订阅最长有效期为 3 天，必须配合定时任务定期续期）；
   - 检查组织管理员是否已对该租户启用了“允许录制与会议转录”策略；若会议未开启云端转录，API 将无法获取文本。
2. **凭据认证报错（401 Unauthorized）**：
   - 确认 Azure 控制台中该应用已被授予 `OnlineMeetings.Read.All` 与 `OnlineMeetingTranscript.Read.All` 应用程序权限，并且已由全局管理员点击“授予管理员许可”。

---

## 五、 检查核对清单

- [ ] 是否已核验 Azure AD 凭据与权限，且测试状态命令返回正常？
- [ ] 订阅列表中的过期时间是否处于有效窗口期内？
- [ ] 生成的会议纪要是否完整包含了议定决策与明确责任人的待办行动项？
