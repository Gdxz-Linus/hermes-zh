---
name: imessage
description: "用于在 macOS 上通过 imsg 命令行收发 iMessage 与短信时。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [iMessage, SMS, messaging, macOS, Apple]
prerequisites:
  commands: [imsg]
---

# iMessage

用 `imsg` 经 macOS 的信息应用读取与发送 iMessage 和短信。

## 前置条件

- **macOS**，且信息应用已登录
- 安装：`brew install steipete/tap/imsg`
- 给终端授予完全磁盘访问权限（系统设置 → 隐私与安全性 → 完全磁盘访问权限）
- 首次使用时按提示给信息应用授予自动化权限

## 适用场景

- 用户要求发送 iMessage 或短信
- 读取 iMessage 对话历史
- 查看信息应用最近的会话
- 向手机号或 Apple ID 发送消息

## 不适用场景

- Telegram、Discord、Slack、WhatsApp 消息 → 用对应的网关通道
- 群聊成员管理（拉人、移人）→ 不支持
- 批量群发 → 必须先与用户确认

## 常用命令

### 列出会话

```bash
imsg chats --limit 10 --json
```

### 查看历史

```bash
# 按会话编号
imsg history --chat-id 1 --limit 20 --json

# 附带附件信息
imsg history --chat-id 1 --limit 20 --attachments --json
```

### 发送消息

```bash
# 纯文本
imsg send --to "+141****1212" --text "你好！"

# 带附件
imsg send --to "+141****1212" --text "看看这个" --file /path/to/image.jpg

# 强制走 iMessage 或短信
imsg send --to "+141****1212" --text "你好" --service imessage
imsg send --to "+141****1212" --text "你好" --service sms
```

### 监听新消息

```bash
imsg watch --chat-id 1 --attachments
```

## 服务选项

- `--service imessage`：强制走 iMessage，要求对方也开通 iMessage
- `--service sms`：强制走短信（绿色气泡）
- `--service auto`：由信息应用自行判断（默认）

## 规则

1. 发送前**必须确认收件人与消息内容**
2. **不向陌生号码发送**，除非用户明确同意
3. 添加附件前**先核实文件路径存在**
4. **不要连发**，自己限制发送频率

## 示例流程

用户说：「发消息给我妈，说我会晚点到」

```bash
# 1. 找到妈妈的会话
imsg chats --limit 20 --json | jq '.[] | select(.displayName | contains("Mom"))'

# 2. 向用户确认：「找到妈妈 +155****3456，用 iMessage 发『我会晚点到』？」

# 3. 确认后发送
imsg send --to "+155****3456" --text "我会晚点到"
```
