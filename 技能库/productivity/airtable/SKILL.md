---
name: airtable
description: "用于通过 Airtable REST API 管理多维数据表格、检索过滤记录与批量更新字段。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [AIRTABLE_API_KEY]
  commands: [curl]
metadata:
  hermes:
    tags: [airtable, 多维表格, 数据库, api, 记录管理, 数据同步, 批量更新]
    category: productivity
    related_skills: [notion, xlsx]
    homepage: https://airtable.com/developers/web/api/introduction
---

# Airtable 多维数据表格自动化管理指南

## 概述

指导在终端环境中使用 `curl` 与标准 HTTP 请求，直接调度 Airtable 官方 REST API 对其多维数据表格与数据记录进行管理。涵盖数据行的新增、批量修改、基于公式条件的记录筛选、分页获取以及字段格式映射。无需安装专用 SDK，通过轻量命令行即可完成数据流转。

## 适用场景

- “查询某张 Airtable 数据表中所有状态为‘待审核’的记录清单”
- “向指定的项目管理表中批量插入 5 条新的功能测试记录”
- “根据唯一的任务编号，更新表中特定记录的完成时间与状态”
- “导出某个多维表格的字段结构并分析数据列类型”

---

## 一、 访问凭据配置与权限范围

调用 Airtable API 必须使用个人访问令牌（Personal Access Token，PAT）：

1. **创建与授权访问令牌**：
   - 访问 Airtable 开发者令牌页面（`airtable.com/create/tokens`），创建以 `pat...` 开头的新令牌；
   - **配置最小所需权限范围**：
     - `data.records:read`：读取表格中的数据行；
     - `data.records:write`：创建、更新与删除数据行；
     - `schema.bases:read`：读取多维表格的结构与字段定义。
   - **绑定目标数据表格（关键）**：在创建令牌页面的“Access”列表中，必须显式勾选允许该令牌访问的具体多维表格；若未添加，即使令牌有效，操作目标表时也会返回 403 权限拒绝。
2. **凭据保存**：
   - 将令牌写入环境配置文件 `$HERMES_HOME/.env`：
     ```bash
     AIRTABLE_API_KEY="pat_xxxxxxxxxxxxxxxxxxxxxx"
     ```

---

## 二、 核心对象标识符与频率限制

- **基础接口端点**：`https://api.airtable.com/v0`
- **公共请求头**：
  - `Authorization: Bearer $AIRTABLE_API_KEY`
  - `Content-Type: application/json`
- **核心对象标识符前缀**：
  - 多维表格库 ID（Base ID）：以 `app` 开头（如 `app1234567890abcdef`）；
  - 数据表（Table ID 或表名）：以 `tbl` 开头（亦可直接使用表名，但在自动化流程中推荐使用不变的 Table ID）；
  - 记录 ID（Record ID）：以 `rec` 开头；
  - 字段 ID（Field ID）：以 `fld` 开头。
- **请求频率上限**：每个 Base 每秒最多允许 5 次请求；若短时间内请求过多会收到 429 状态码，需等待后重新发起。

---

## 三、 标准 API 标准操作范式（curl）

### 1. 查询数据表中的记录
获取指定表的前 10 条记录：
```bash
curl -s "https://api.airtable.com/v0/<BASE_ID>/<表名或Table_ID>?maxRecords=10"   -H "Authorization: Bearer $AIRTABLE_API_KEY" | python -m json.tool
```

### 2. 使用公式进行条件筛选
通过 `filterByFormula` 参数筛选特定条件的记录（参数需进行 URL 编码）：
```bash
# 示例：筛选状态等于“已完成”的记录
curl -s -G "https://api.airtable.com/v0/<BASE_ID>/<表名>"   -H "Authorization: Bearer $AIRTABLE_API_KEY"   --data-urlencode "filterByFormula={状态} = '已完成'"   --data-urlencode "maxRecords=20" | python -m json.tool
```

### 3. 创建单条或批量新记录
向数据表中插入记录（单次请求最多支持批量插入 10 条记录）：
```bash
curl -s -X POST "https://api.airtable.com/v0/<BASE_ID>/<表名>"   -H "Authorization: Bearer $AIRTABLE_API_KEY"   -H "Content-Type: application/json"   -d '{
    "records": [
      {
        "fields": {
          "任务名称": "编写系统验证脚本",
          "负责人": "张工",
          "状态": "进行中",
          "预估工时": 4
        }
      }
    ]
  }' | python -m json.tool
```

### 4. 局部更新记录字段（PATCH 操作）
仅更新指定记录的某个字段，其余字段保持不变：
```bash
curl -s -X PATCH "https://api.airtable.com/v0/<BASE_ID>/<表名>/<RECORD_ID>"   -H "Authorization: Bearer $AIRTABLE_API_KEY"   -H "Content-Type: application/json"   -d '{
    "fields": {
      "状态": "已完成"
    }
  }' | python -m json.tool
```

### 5. 按照唯一键执行匹配更新（Upsert 机制）
如果存在某唯一键（如“任务编号”）则更新该行，不存在则新建该行：
```bash
curl -s -X PATCH "https://api.airtable.com/v0/<BASE_ID>/<表名>"   -H "Authorization: Bearer $AIRTABLE_API_KEY"   -H "Content-Type: application/json"   -d '{
    "performUpsert": {
      "fieldsToMergeOn": ["任务编号"]
    },
    "records": [
      {
        "fields": {
          "任务编号": "TASK-1024",
          "任务名称": "核心架构改造",
          "状态": "已验收"
        }
      }
    ]
  }' | python -m json.tool
```

### 6. 删除记录
根据 Record ID 删除指定记录（单次最多批量删除 10 条）：
```bash
curl -s -X DELETE "https://api.airtable.com/v0/<BASE_ID>/<表名>/<RECORD_ID>"   -H "Authorization: Bearer $AIRTABLE_API_KEY"
```

---

## 四、 常见错误与排查注意点

1. **403 Forbidden 权限报错**：检查该令牌是否在 Airtable 控制台中显式添加了对该 Base 的授权；
2. **422 Unprocessable Entity 格式错误**：
   - 检查提交的 JSON 中字段名称是否与数据表表头完全一致（注意空格与特殊符号）；
   - 检查字段类型是否匹配（例如单选字段传入了未预设的选项名称，数字列传入了字符串文本）；
3. **分页处理机制**：单次最多返回 100 条记录；若返回结果包含 `offset` 字段，需在下一次请求追加 `?offset=<值>` 获取下一页数据。

---

## 五、 检查核对清单

- [ ] 个人访问令牌是否已分配了正确的读写权限，并在 Access 列表中勾选了目标表格？
- [ ] 筛选公式是否进行了正确的 URL 编码处理？
- [ ] 单次批量创建或删除记录时，是否控制在 10 条以内的数量限制？
