---
name: google-workspace
description: "用于通过 gws 命令行或 API 自动化管理 Google 邮件、日历、云端硬盘与文档表格。"
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
required_credential_files:
  - path: google_token.json
    description: Google OAuth2 用户访问令牌（由初始化脚本生成）
  - path: google_client_secret.json
    description: Google OAuth2 客户端凭据（从 Google Cloud 控制台下载）
metadata:
  hermes:
    tags: [google, gmail, 谷歌日历, 谷歌网盘, 电子表格, 文档协作, 办公自动化, oauth]
    category: productivity
    related_skills: [chinese-official-writing, document-to-action-items, weekly-review-planning]
---

# Google Workspace 办公套件自动化管理指南

## 概述

指导在终端环境中使用 `gws` 命令行工具或底层 Python 脚本，自动化调度 Google Workspace 核心办公套件。涵盖 Gmail 邮件收发、Google Calendar 日程管理、Google Drive 云端硬盘文件流转、Google Sheets 数据表读写以及 Google Docs 文档维护。

**核心约束**：
```
发送外部真实邮件或永久删除云端文件前，必须获得用户明确确认
```
邮件投递属于向外部产生直接影响的操作，而永久删除文件（绕过回收站）属于不可逆变更。助手在执行这两类关键操作前，必须向用户陈述操作对象、目标地址或文件名称，经明确指示后方可执行。

## 适用场景

- “帮我查看今天 Gmail 收件箱里有哪些重要未读邮件，并整理成工作简报”
- “查询我下周二的日历日程，并在下午 3 点安排一次架构评审会议”
- “将本地生成的报告上传到 Google Drive 共享文件夹中”
- “向指定的 Google Sheets 表格末尾追加一行今天的测试数据”

---

## 一、 首次初始化与 OAuth2 凭据配置

在正式调用服务前，必须先核查凭据文件是否齐备：

1. **检查既有凭据状态**：
   - 检查 `$HERMES_HOME/` 目录下是否存在 `google_token.json`；如果存在，运行测试指令验证凭据是否有效：
     ```bash
     python scripts/google_api.py gmail list --max 1
     ```
   - 若能正常返回 JSON 数据，说明授权已生效，可直接开始使用。
2. **凭据缺失时的配置引导**：
   - 若不存在该文件，则需引导用户从 Google Cloud 控制台下载客户端凭据并重命名存放在 `$HERMES_HOME/google_client_secret.json`；
   - 运行初始化授权脚本：
     ```bash
     python scripts/setup.py
     ```
   - 脚本会打印授权 URL，用户在浏览器中打开并同意权限后，复制授权码粘贴回终端完成令牌换取。

---

## 二、 核心组件使用范式

### 1. Gmail 邮件处理
- **检索邮件**：使用标准的 Gmail 检索语法（如 `is:unread`、`from:someone`）：
  ```bash
  python scripts/google_api.py gmail list --query "is:unread label:INBOX" --max 10
  ```
- **读取邮件全文**：传入邮件 ID 获取完整正文文本：
  ```bash
  python scripts/google_api.py gmail get --id <邮件ID>
  ```
- **拟定与发送邮件**：
  ```bash
  python scripts/google_api.py gmail send --to "user@example.com" --subject "工作进展汇报" --body "正文内容..."
  ```
- **回复邮件**（自动维持会话引用链）：
  ```bash
  python scripts/google_api.py gmail reply --id <原邮件ID> --body "已收到，正在处理中。"
  ```

### 2. Google Calendar 日程管理
- **查看日程事件**（默认查询未来 7 天内）：
  ```bash
  python scripts/google_api.py calendar list --days 7
  ```
- **创建日程事件**（时间需符合带时区的 ISO 8601 标准）：
  ```bash
  python scripts/google_api.py calendar create     --summary "项目阶段评审会"     --start "2026-10-25T14:00:00+08:00"     --end "2026-10-25T15:30:00+08:00"     --description "评审 smartdns-edge 核心功能验证结果"
  ```
- **删除日程事件**：
  ```bash
  python scripts/google_api.py calendar delete --id <事件ID>
  ```

### 3. Google Drive 云端硬盘管理
- **文件检索**：支持按名称或包含关系查找：
  ```bash
  python scripts/google_api.py drive search --name "架构图"
  ```
- **文件上传与下载**：
  ```bash
  # 上传本地文件（自动推断 MIME 类型）
  python scripts/google_api.py drive upload --path "<工作目录>/架构图.svg" --name "最新架构图.svg"

  # 下载文件至本地
  python scripts/google_api.py drive download --id <文件ID> --path "<工作目录>/下载文件.pdf"
  ```
- **安全删除规约**：
  - 默认执行**移入回收站**操作（可恢复）：
    ```bash
    python scripts/google_api.py drive delete --id <文件ID>
    ```
  - 仅在用户明确要求彻底清除且经确认后，才追加 `--permanent` 参数执行不可逆删除。

### 4. Google Sheets 表格数据维护
- **读取表格内容**：
  ```bash
  python scripts/google_api.py sheets read --id <表格ID> --range "Sheet1!A1:D10"
  ```
- **追加数据行**（格式为 JSON 数组）：
  ```bash
  python scripts/google_api.py sheets append --id <表格ID> --range "Sheet1!A1"     --values '[["2026-10-21", "测试通过", "0 缺陷", "通过"]]'
  ```

---

## 三、 输出规范与错误处理

1. **结构化输出标准**：所有脚本默认输出结构化 JSON，便于通过命令行解析工具直接提取字段；
2. **权限不足报错（403 Forbidden）**：若提示权限范围不足，通常是因为最初授权时仅选择了部分权限，需要重新运行 `setup.py` 并勾选全部所需的读写权限；
3. **令牌过期自动刷新**：脚本内部已封装自动刷新机制，在有效访问令牌过期时会自动使用刷新令牌静默更新，无需用户重复登录。

---

## 四、 检查核对清单

- [ ] 是否已核验本地凭据文件的有效性，且授权未过期？
- [ ] 涉及向外发送正式邮件前，是否向用户出示了收件人与正文并得到确认？
- [ ] 文件删除操作是否默认走可还原的回收站路径，未擅自永久删除？
