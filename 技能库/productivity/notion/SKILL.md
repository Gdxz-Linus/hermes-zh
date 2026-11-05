---
name: notion
description: "用于通过 Notion API 与 ntn 命令行管理 Notion 页面、数据库与结构化文档。"
version: 2.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [NOTION_API_KEY]
metadata:
  hermes:
    tags: [notion, 笔记管理, 知识库, 数据库, api, 协同办公, 文档同步]
    category: productivity
    related_skills: [obsidian, chinese-official-writing]
    homepage: https://developers.notion.com
---

# Notion 知识库与数据表格管理指南

## 概述

指导在终端环境中使用 Notion 官方 REST API 以及专用的 `ntn` 命令行工具，高效读写与维护 Notion 页面、多维数据表格与内容块。重点支持将本地 Markdown 文档双向同步至 Notion，以及通过属性条件精确筛选数据库记录。

## 适用场景

- “把本地这篇方案文档直接发布到我的 Notion 知识库对应页面中”
- “从 Notion 需求数据库中筛选出所有状态为‘进行中’的任务条目”
- “读取某个 Notion 页面的完整内容，并在末尾追加今天的讨论结论”
- 在跨平台环境下，通过 HTTP 请求或轻量命令行自动化管理 Notion 团队资产

---

## 一、 前置准备与身份凭据配置

无论使用命令行工具还是直接发送 HTTP 请求，均需要 Notion 的内部集成令牌：

1. **获取访问令牌**：
   - 访问 Notion 开发者控制台（`notion.so/profile/integrations`），创建一个新的内部集成，获取以 `ntn_` 或 `secret_` 开头的 API 令牌；
   - **授予页面访问权限（关键步骤）**：在 Notion 客户端中打开需要操作的目标页面或数据库，点击右上角菜单选择“连接（Connect to）”，将刚刚创建的集成名称添加进来；未显式添加授权的页面，API 访问将返回 404 错误。
2. **凭据保存**：
   - 将令牌写入环境配置文件 `$HERMES_HOME/.env`：
     ```bash
     NOTION_API_KEY="ntn_xxxxxxxxxxxxxxxxxxxxxx"
     ```
3. **运行模式选择**：
   - **方式一：`ntn` 命令行工具**（在支持 npm 的环境中首选，命令简洁）；
   - **方式二：直接 HTTP 请求（curl）**（全平台原生通用，在 Windows 环境下零外部依赖，直接发起请求即可执行）。

---

## 二、 核心操作范式：直接 HTTP 请求（全平台通用）

在 Windows 或无外部扩展的环境中，使用标准 HTTP 请求与 Notion 官方 API 通信：
- **公共请求头**：每次请求均需携带以下头部：
  - `Authorization: Bearer $NOTION_API_KEY`
  - `Notion-Version: 2022-06-28`（或最新版本 `2025-09-03`）
  - `Content-Type: application/json`

### 1. 全局关键词检索
快速检索具备访问权限的页面或数据库：
```bash
curl -s -X POST https://api.notion.com/v1/search   -H "Authorization: Bearer $NOTION_API_KEY"   -H "Notion-Version: 2022-06-28"   -H "Content-Type: application/json"   -d '{"query": "搜索关键词", "page_size": 5}'
```

### 2. 读取页面正文为 Markdown 格式（大模型交互最推荐）
对于支持 Markdown 转换的端点，可直接获取排版整齐的纯文本内容，避免手动解析复杂嵌套的 JSON 块结构：
```bash
curl -s https://api.notion.com/v1/pages/<页面ID>/markdown   -H "Authorization: Bearer $NOTION_API_KEY"   -H "Notion-Version: 2025-09-03"
```

### 3. 读取页面内容块列表
需要逐层分析页面排版结构时，遍历内容块子节点：
```bash
curl -s "https://api.notion.com/v1/blocks/<页面ID>/children?page_size=50"   -H "Authorization: Bearer $NOTION_API_KEY"   -H "Notion-Version: 2022-06-28"
```

### 4. 基于 Markdown 直接创建新页面
在指定的父页面下直接生成一篇包含完整标题、列表与代码块的文档：
```bash
curl -s -X POST https://api.notion.com/v1/pages   -H "Authorization: Bearer $NOTION_API_KEY"   -H "Notion-Version: 2025-09-03"   -H "Content-Type: application/json"   -d '{
    "parent": {"page_id": "<父页面ID>"},
    "markdown": "# 需求设计说明书\n\n## 一、背景概述\n这是由自动化流程生成的结构化正文。"
  }'
```

### 5. 查询与筛选数据库记录
在指定数据库中根据属性条件进行精准过滤：
```bash
curl -s -X POST https://api.notion.com/v1/databases/<数据库ID>/query   -H "Authorization: Bearer $NOTION_API_KEY"   -H "Notion-Version: 2022-06-28"   -H "Content-Type: application/json"   -d '{
    "filter": {
      "property": "状态",
      "status": {"equals": "进行中"}
    },
    "page_size": 20
  }'
```

### 6. 向现有页面末尾追加内容块
在不覆盖原有内容的前提下追加新的段落或结论：
```bash
curl -s -X PATCH https://api.notion.com/v1/blocks/<页面ID>/children   -H "Authorization: Bearer $NOTION_API_KEY"   -H "Notion-Version: 2022-06-28"   -H "Content-Type: application/json"   -d '{
    "children": [
      {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
          "rich_text": [{"type": "text", "text": {"content": "三、评审结论"}}]
        }
      },
      {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
          "rich_text": [{"type": "text", "text": {"content": "技术评审已全部通过，准予进入开发阶段。"}}]
        }
      }
    ]
  }'
```

---

## 三、 高效交互：`ntn` 命令行工具模式

在安装了 `ntn` 命令行工具的环境中，可使用更精炼的命令执行日常管理：
- `ntn search "关键词"`：全局检索页面与表格；
- `ntn page get <页面ID> --format markdown`：将页面内容直接以 Markdown 打印输出；
- `ntn page create --parent <父ID> --title "文档标题" --body-file doc.md`：从本地文件导入创建新页面；
- `ntn db query <数据库ID> --filter '{"property":"优先级","select":{"equals":"高"}}'`：条件筛选数据库行。

---

## 四、 常见问题排查与注意事项

1. **接口返回 404 错误**：90% 的原因并非页面不存在，而是该页面尚未在右侧菜单中向该集成授权（未执行“Connect to”操作）；
2. **页面 ID 格式提取**：Notion 页面链接末尾的 32 位字符即为唯一页面 ID（如 `notion.so/workspace/My-Page-1234567890abcdef1234567890abcdef` 中的 `1234567890abcdef1234567890abcdef`），可以直接传入 API；
3. **内容块单次操作上限**：一次向页面追加内容块的请求最多支持 100 个 Block，超出上限时需拆分为多个请求分批提交。

---

## 五、 检查核对清单

- [ ] 是否已在目标 Notion 页面右上角完成了集成连接授权？
- [ ] 请求头中是否已携带正确的 `Authorization` 令牌与版本号？
- [ ] 批量操作内容块时是否遵守了单次 100 个 Block 的数量上限？
