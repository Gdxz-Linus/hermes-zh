---
name: box
description: "用于通过 Box CLI 与 API 管理企业云盘文件、权限共享、内容检索与元数据。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  commands: [box]
metadata:
  hermes:
    tags: [box, 企业云盘, 云存储, 文件共享, 内容检索, 元数据, box-cli]
    category: productivity
    related_skills: [google-workspace, document-to-action-items]
    homepage: https://developer.box.com/
---

# Box 企业云存储与文件协作管理指南

## 概述

指导在终端环境中使用 Box 官方命令行工具（Box CLI）以及标准 REST API，对 Box 企业云存储中的文件与目录进行自动化管理。涵盖文件上传下载、多级目录整理、共享权限与链接生成、全文检索、文件元数据提取以及结合 Box AI 开展文档内容提炼。

## 适用场景

- “在企业 Box 云盘中检索包含某技术关键词的全部架构设计文档”
- “将本地生成的报告文件上传到 Box 指定团队文件夹并生成共享只读链接”
- “批量整理 Box 目录结构，提取文件的自定义元数据属性”
- “在无需全量下载超大文件的前提下，对云端文件进行文本抽取与内容分析”

---

## 一、 身份认证与安全准则

1. **OAuth2 用户授权机制**：
   - 通过标准 OAuth 流程授权后，Hermes 在 Box 中的操作权限完全受限于授权账号自身的权限边界；
   - **最小权限原则**：若需限制 Hermes 的访问范围，建议使用仅被邀请至特定项目文件夹的专用账号进行授权，避免使用企业超级管理员账号。
2. **凭据安全红线**：
   - 严禁在对话交流中要求用户提供客户端密钥或私钥明文；
   - 敏感认证信息仅允许在本地命令行安全交互提示符中由用户直接输入，不记入配置文件，不提交至版本库。
3. **环境初始化检查**：
   - 检查本地是否已安装 `box` 命令行工具：
     ```bash
     box --version
     ```
   - 若未安装，可在本地工具目录安装 `@box/cli`，并通过 `box login` 完成浏览器授权登录。

---

## 二、 Box CLI 核心操作范式

### 1. 文件与文件夹检索
- **全局内容与元数据搜索**：
  ```bash
  box search "技术方案" --type file --limit 10
  ```
- **指定文件类型检索**（例如仅检索 PDF 文档）：
  ```bash
  box search "系统架构" --file-extensions pdf
  ```

### 2. 云端目录浏览与列出
- **查看指定文件夹内容**（根目录 ID 为 `0`）：
  ```bash
  box folders:items 0 --fields id,type,name,size
  ```
- **创建新团队文件夹**：
  ```bash
  box folders:create 0 "2026年技术评审资料"
  ```

### 3. 文件上传与下载流转
- **上传本地文件至云端指定目录**：
  ```bash
  box files:upload "D:/Hermes/报告.docx" --parent-folder <目标文件夹ID>
  ```
- **下载云端文件至本地**：
  ```bash
  box files:download <文件ID> --destination "D:/Hermes/下载/"
  ```

### 4. 共享链接与权限协作
- **为文件生成只读共享链接**：
  ```bash
  box files:shared-links:create <文件ID> --access open
  ```
- **邀请团队成员协作文件夹**：
  ```bash
  box collaborations:create <文件夹ID> --role editor --login "user@example.com"
  ```

---

## 三、 高级应用：文档元数据与内容提取

1. **文件元数据读取与挂载**：
   - 查看指定文件挂载的自定义元数据模板与键值：
     ```bash
     box files:metadata:get <文件ID>
     ```
2. **大文件免下载内容抽取**：
   - 对于数十兆的超大文档，优先调用文本抽取接口获取纯文本，避免将整个二进制大文件下载到本地占用带宽和磁盘。

---

## 四、 常见问题与排查

1. **404 Not Found 找不到对象**：Box 严格依据数字 ID（而非文件名）寻址。如果仅提供名称，必须先调用 `box search` 拿到具体的唯一文件 ID；
2. **命名冲突报错（409 Conflict）**：目标文件夹下若已存在同名文件，直接新建会抛出 409 异常。若需更新文件版本，应调用 `box files:upload <路径> --file-id <已有文件ID>` 创建文件新版本，而非新建独立文件；
3. **跨平台交互兼容**：在远程无界面服务器上运行时，使用 `box login --code` 模式，在本地浏览器完成授权后把返回的授权码粘贴回终端。

---

## 五、 检查核对清单

- [ ] 是否确认了目标文件夹的唯一数字 ID，避免仅凭文件名称操作？
- [ ] 上传已有同名文件时，是否选用了版本追加方式，避免触发 409 命名冲突？
- [ ] 涉及重要文件删除或协作权限变更时，是否提前向用户确认？
