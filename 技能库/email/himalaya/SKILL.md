---
name: himalaya
description: "用于通过 Himalaya 命令行客户端在终端收发与管理 IMAP/SMTP 邮件。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  commands: [himalaya]
metadata:
  hermes:
    tags: [邮件管理, himalaya, imap, smtp, 命令行邮件, 终端工具, 邮箱协同]
    category: email
    related_skills: [email-inbox-triage, google-workspace]
    homepage: https://github.com/pimalaya/himalaya
---

# Himalaya 终端邮件客户端操作指南

## 概述

指导在终端环境中使用开源轻量级命令行邮件客户端 Himalaya，通过标准的 IMAP 与 SMTP 协议连接任意商业或自建邮件服务器。支持邮件列表查看、正文阅读、快速撰写、多账号管理、草稿保存、回复与转发，完全无需图形界面即可高效收发邮件。

**操作安全红线**：
```
发送外部真实邮件或执行永久删除前，必须获得用户明确确认
```
邮件发出后无法撤回，删除操作同样可能导致历史信件丢失。在执行发送（`message send`）或清空垃圾箱操作前，必须向用户出示目标收件人、标题与主要正文，经明确肯定指示后方可执行。

## 适用场景

- “在终端中查看我公司企业邮箱中最近未读的 5 封邮件”
- “读取邮件编号为 1024 的具体正文与附件信息”
- “通过命令行快速拟定一封邮件草稿，发送给合作团队”
- “为指定的发件人自动回复确认收信，并标记为已读”

---

## 一、 前置准备与账号配置

使用本技能需确认本地已安装 `himalaya` 命令行程序：

1. **环境检查**：
   ```bash
   himalaya --version
   ```
2. **配置文件结构（`~/.config/himalaya/config.toml`）**：
   - 配置文件支持配置多个不同的邮箱账户（如个人邮箱、工作邮箱）：
     ```toml
     [accounts.work]
     default = true
     email = "developer@example.com"
     display-name = "技术研发团队"

     # IMAP 收信配置
     backend = "imap"
     imap.host = "imap.example.com"
     imap.port = 993
     imap.login = "developer@example.com"
     imap.auth.type = "password"
     imap.auth.raw = "你的应用专属密码"

     # SMTP 发信配置
     message.send.backend = "smtp"
     smtp.host = "smtp.example.com"
     smtp.port = 465
     smtp.login = "developer@example.com"
     smtp.auth.type = "password"
     smtp.auth.raw = "你的应用专属密码"
     ```
3. **安全交互配置向导**：
   - 新环境亦可运行官方交互向导快速生成初始配置：
     ```bash
     himalaya account configure
     ```

---

## 二、 核心命令使用范式

### 1. 邮件列表浏览与检索
- **查看收件箱前 10 封邮件**：
  ```bash
  himalaya message list --page-size 10
  ```
- **查看其他文件夹中的邮件**（如已发送邮件、垃圾邮件）：
  ```bash
  himalaya message list --folder "Sent"
  ```

### 2. 读取邮件正文
- **查看指定邮件编号的正文内容**：
  ```bash
  himalaya message read <邮件编号>
  ```
- **导出邮件附件至本地目录**：
  ```bash
  himalaya message attachments <邮件编号>
  ```

### 3. 拟定草稿与邮件回复
- **直接发送邮件（经用户确认后）**：
  ```bash
  himalaya message send << 'EOF'
  From: developer@example.com
  To: partner@example.com
  Subject: 技术对接进展更新

  你好，附件方案已完成第一轮评审，请查阅。
  EOF
  ```
- **回复指定邮件**（自动继承主题并引用上文）：
  ```bash
  himalaya message reply <邮件编号>
  ```

### 4. 邮件标记与整理
- **标记指定邮件为已读**：
  ```bash
  himalaya flag add <邮件编号> seen
  ```
- **移动邮件至指定文件夹**：
  ```bash
  himalaya message move <邮件编号> "Archive"
  ```
- **删除邮件（移入废件箱）**：
  ```bash
  himalaya message delete <邮件编号>
  ```

---

## 三、 常见问题与排查指南

1. **认证失败错误**：
   - 绝大多数现代邮箱（如网易企业邮、腾讯企业邮、Gmail）要求必须使用“应用专属授权码/专属密码”，严禁使用邮箱登录主密码；
   - 检查账户配置中端口号（IMAP 通常为 993，SMTP 通常为 465 或 587）以及 SSL/TLS 选项是否与服务商要求一致。
2. **多账号切换**：
   - 如果配置了多个邮箱，使用 `-a` 参数指定特定账号执行操作：
     ```bash
     himalaya -a personal message list
     ```

---

## 四、 检查核对清单

- [ ] 配置文件中是否已正确配置了邮箱收发端点与独立应用专属密码？
- [ ] 实际发信前是否向用户完整出示了收件人与正文草稿，并获得确认？
- [ ] 批量操作或删除前是否确认了操作的目标文件夹与邮件编号无误？
