# 后端清单（实测）

清单会随上游版本变化，引用前用 `scripts/list_provider_backends.py` 复核一次；这里记的是判据与对照，不是永久事实。

两点容易混淆的能力差别，先分清再答：

- **记忆插件与 MCP 记忆服务器的机制不同**。插件走 `prefetch` / `sync_turn` 接缝，能每轮自动注入、每轮自动写入；MCP 服务器只提供工具，靠模型主动调用，且不能从 MCP 侧关掉内置记忆（`memory_enabled` 是配置项）。用户问「能否自动记得」时按这条分。
- **服务型后端的「服务端」不在插件目录里**。openviking 属此类，Hermes 侧只是客户端，自建步骤见 `selfhosted-backend-ops.md`。

## 一、web 搜索/抓取：11 个后端

| 名称 | 搜索 | 抓取 | 免密钥 | 密钥/地址变量 | 上游 |
|---|---|---|---|---|---|
| brave-free | ✓ | | | `BRAVE_SEARCH_API_KEY` | Brave 自建索引 |
| ddgs | ✓ | | | 无（需装 `ddgs` 包） | DuckDuckGo，多引擎 |
| exa | ✓ | ✓ | ✓ | `EXA_API_KEY` | 自建语义索引 |
| firecrawl | ✓ | ✓ | ✓ | `FIRECRAWL_API_KEY` | 自建抓取+搜索 |
| keenable | ✓ | ✓ | ✓ | `KEENABLE_API_KEY` | 自建索引 |
| openai-native | ✓ | | | 需 openai-codex 登录 | Codex Responses 服务端 |
| parallel | ✓ | ✓ | ✓ | `PARALLEL_API_KEY` | 自建索引 |
| perplexity | ✓ | ✓ | | `PERPLEXITY_API_KEY` | Search API |
| searxng | ✓ | | | `SEARXNG_URL`（自建实例） | 元搜索 |
| tavily | ✓ | ✓ | ✓ | `TAVILY_API_KEY` | 自建索引 |
| xai | ✓ | | | xAI 登录或 `XAI_API_KEY` | Grok agentic 检索 |

配置全空时落在免密钥环（exa → parallel → firecrawl → keenable），实测结果：搜索落 firecrawl、抓取落 exa，日志行分别为 `Web search via firecrawl`、`Exa keyless extract`。

### 传统搜索引擎：只有三条路，且都不在默认池里

| 引擎 | 通路 | 判据 |
|---|---|---|
| Google / Bing / Yandex 等 | `ddgs` 包的内部引擎轮换 | 读包内 `ddgs/engines/` 的 `ENGINES` 注册表；Hermes 调用不传 `backend`，无法指定 |
| Brave 自建索引 | `brave-free` 插件 | `plugin.yaml` 描述与 `https://api.search.brave.com/res/v1/web/search` |
| 聚合（含百度/搜狗/360/夸克） | `searxng` + 自建实例 | 上游 `searx/settings.yml`，对应条目默认 `disabled: true` |

装包后看引擎清单：`uv pip install <pkg>==<ver> --target <dir> --no-deps`，再读 `<dir>/<pkg>/engines/`。

## 二、记忆：7 个插件

| 插件 | 数据落点 | 依赖 | 特点 | 暴露的工具 |
|---|---|---|---|---|
| holographic | 本地 SQLite（`$HERMES_HOME/memory_store.db`） | 无（NumPy 可选） | 事实库 + FTS5 + 可信度打分 + HRR 组合检索 | `fact_store`（add/search/probe/related/reason/contradict/update/remove/list）、`fact_feedback` |
| honcho | Honcho 云或自建 | `honcho-ai` SDK + 账号（OAuth / 设备码 / 密钥） | 跨会话用户建模，多轮辩证推理（1–3 轮）、会话摘要、双向 peer | `honcho_profile`、`honcho_search`、`honcho_context`、`honcho_reasoning`、`honcho_conclude` |
| mem0 | Mem0 云 / 自建 dashboard / 进程内 OSS | `mem0ai` SDK | 服务端 LLM 抽取事实、去重、可选重排；OSS 模式自带 LLM/嵌入/向量库（openai|ollama + qdrant|pgvector） | `mem0_search`、`mem0_add`、`mem0_update`、`mem0_delete` |
| supermemory | Supermemory 云 / 自建（`npx supermemory local`） | `supermemory` SDK | 语义长期记忆，按轮捕获（每会话每 4 小时一个文档），画像召回；`container_tag` 支持 `{identity}` 按 profile 隔离 | `supermemory-save/-search/-forget/-profile`（snake_case 别名仍在） |
| openviking | 自建服务（默认 `127.0.0.1:1933`） | 独立 `openviking-server` | 文件系统式知识层级、分级检索、自动抽取 | `viking_search`、`viking_read`、`viking_browse`、`viking_remember`、`viking_forget`、`viking_add_resource` |
| retaindb | RetainDB 云 | API 密钥（付费） | 混合检索（向量 + BM25 + 重排），7 种记忆类型，含文件类工具 | `retaindb_profile`、`retaindb_search`、`retaindb_context`、`retaindb_remember`、`retaindb_forget` + 文件读写上传删除 |
| byterover | 本地优先，可选云同步 | `brv` CLI | 层级知识树，分级检索（模糊文本 → LLM 驱动搜索） | `brv_query`、`brv_curate`、`brv_status` |

选择口径：只要本地且零依赖 → holographic；要用户建模且接受上云 → honcho（可配置项最多：注入节奏、推理深度、会话归属策略、召回模式、多用户身份映射）；要强抽取去重 → mem0；要按轮捕获与画像 → supermemory；要自建上下文数据库 → openviking；要混合检索多类型 → retaindb；已在用 brv → byterover。

## 三、模型提供者：订阅渠道接入（Antigravity 实测）

模型提供者是第四族（替换推理引擎，工具执行与防线仍归 Hermes）。本机已接入实测：本地 OpenAI 兼容反代（easycli 类，`http://127.0.0.1:8317/v1`）作 provider `easy-gemini`，Antigravity 会员配额消耗，多模态透传可用。三个 Antigravity 插件（oauth/directsdk/agy）横向对比、订阅分渠道权益表（Jio 促销渠道限制：3.1 Pro/Argon 在 Antigravity 不可用，仅 Gemini 应用内）、$10/月 Cloud 抵扣金用法、协议选型（勿为 Responses API 切配置——本版传输注册表无纯 responses 模式）：见 `references/model-provider-subscription.md`。
