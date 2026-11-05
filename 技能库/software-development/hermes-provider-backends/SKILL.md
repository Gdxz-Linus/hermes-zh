---
name: hermes-provider-backends
description: "用于查阅支持清单、技术选型与配置 Hermes 检索后端、记忆后端与模型推理网关。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, 后端配置, 模型网关, 反向代理, 检索后端, 记忆提供方]
    category: software-development
    related_skills: [hermes-agent, hermes-mcp-server-integration]
---

# Hermes 提供方后端选型与配置指南（Provider Backends）

## 概述

规范 Hermes Agent 各类外部服务后端的支持清单核对、技术选型、本地自建与路由配置。涵盖网络检索后端、长久记忆后端以及模型推理服务商（Model Provider）反向代理的接入规范。

**核心铁律**：
```
未通过生产相同路径发起真实调用验证，严禁向配置文件写入新模型条目
```
向模型提供方配置段（`providers.<名>.models`）新增模型前，严禁仅凭控制台界面显示或口头推断就直接修改配置；反向代理（如 EasyCLIProxyAPI）控制台常包含静态展示模板，界面显示包含某模型绝不代表底层接口真实可用。必须先发起真实 HTTP 请求测试，拿到上游成功返回的有效数据后，才允许向 `config.yaml` 写入该模型条目。

## 适用场景

- “Hermes 当前支持哪些搜索引擎、记忆存储或模型服务商”
- 接入本地自建的 OpenAI 兼容网关或反向代理服务（如 `127.0.0.1:8317`）
- 排查某次网络检索实际路由到了哪个提供方，固定或切换默认检索后端

---

## 一、 四大后端体系分类与存储规约

Hermes 的外部能力由四个相互独立的提供方家族构成，彼此配置边界明确，**严禁混放**：

| 后端家族 | 物理对应目录 | 配置键名（`config.yaml`） | 机密凭据存储位置 |
| :--- | :--- | :--- | :--- |
| **网络检索与抽取** | `plugins/web/<vendor>/` | `web.search_backend` / `web.extract_backend` | `.env`（如 `PERPLEXITY_API_KEY`） |
| **长久记忆存储** | `plugins/memory/<name>/` | `memory.provider`（如 `openviking`） | `.env` 或本地端口监听服务 |
| **MCP 协议扩展** | 外部独立进程 | `mcp_servers:` 段 | 进程启动参数或 `.env` |
| **模型推理服务商** | `plugins/model-providers/` | `providers.<名>:` 与 `model:` 段 | `.env`（如 `EASY_GEMINI_API_KEY`） |

- **存储规约**：非机密性参数（服务地址 `api`、模型名称 `model`、协议模式 `api_mode`）写入 `config.yaml`；API 密钥与访问令牌**唯一存放在 `.env` 中**。

---

## 二、 协议传输模式（`api_mode`）选型与匹配规约

向系统配置模型提供方时，必须根据上游端点真实支持的接口规范准确配置 `api_mode`，严禁随意臆断：

1. **`chat_completions`（经典通用规范，开源推理引擎首选）**：
   - 目标请求路径：`<api>/chat/completions`；
   - 适用于标准 OpenAI API 格式、大部分开源聚合网关及普通商用中转接口；
   - **开源私有化推理框架（如 SGLang、vLLM）首选**：流式生成与工具调用的处理路径最轻量稳定，在超长历史上下文场景下避免了复杂事件流反序列化可能引发的 HTTP 503 队列阻塞。
2. **`codex_responses`（Responses API 规范）**：
   - 目标请求路径：`<api>/responses`；
   - 专为新一代支持状态机与思考过程的接口设计（本地反向代理 easy-gemini 原生支持此协议）；
   - 支持向服务端原样传输深度思考配置与结构化工具定义。
3. **`anthropic_messages`（Claude Messages 规范）**：
   - 目标请求路径：`<api>/v1/messages`；
   - 适配 Anthropic 原生协议或 SGLang 的 Messages 端点。

### 端点级拒绝的诊断顺序（反代只放行部分路径）

本地反代可能只注册部分接口：同一端点上 `/v1/chat/completions` 正常，而 `/v1/responses` 返回 `PROXY_GENERATION_DISABLED: streamGenerateContent is not supported`（aistudio2api 实测）。这不是凭据或模型名问题，而是 `api_mode` 与反代实际放行的路径不匹配——把该 provider 改成 `chat_completions` 即恢复，模型清单无需改动。

诊断顺序固定为：先按配置里的 `api_mode` 打对应路径 → 拿到 4xx 后换另一条路径复测 → 两条都通才去谈模型清单。跳过换路径直接怀疑模型名，会在正确的模型清单上反复空转。

**探活必须带 `"stream": true`**：Hermes 生产路径走流式，反代可能出现非流式 400（`generateContent is not supported`）而流式 200 的分叉。用非流式探活会得到假阴性，据此删掉本来可用的模型条目。

---

## 三、 配置检查与生效核验

1. **排查实际生效的后端**：
   - 不仅查看 `config.yaml` 的静态字段，必须核对 `.env` 中是否存在对应后端生效所需的有效 API 密钥；
   - 只有当配置段存在且对应环境变量非空时，该后端才会真正被激活。
2. **提供商命名大小写与底层小写匹配铁律（配置致命陷阱）**：
   - Hermes 内部路由引擎（`resolve_provider_full`）在匹配用户配置时，底层强制将传入的提供商名称转换为纯小写（`raw = name.strip().lower()`）并在 `user_providers` 字典中检索；
   - **后果**：若在 `config.yaml` 的 `providers:` 下直接使用大写键名（例如 `providers.JK-deepseek:`），底层执行 `user_providers.get("jk-deepseek")` 时会返回 `None`，导致通道被误判为不存在并报错 `Your request was not processed`；
   - **规范写法**：`config.yaml` 的顶层字典键名**必须使用纯小写**（如 `jk-deepseek`），客户端显示用大写名称时只靠条目内的 `name: "JK-deepseek"` 声明；
   - **严禁同时保留大小写两个键**：`JK-deepseek: &id001` 加 `jk-deepseek: *id001` 的别名写法虽然解决了大小写匹配，但在 `providers:` 字典里仍是两个独立键，模型选择器会渲染出两行同源条目，日志也会把同一后端分别记成具名 provider 与 `custom`——这正是用户感知“模型混用”的常见来源。发现重复键用 `hermes config unset providers.<大写键>` 删掉大写那份，只留小写键加 `name:` 显示字段。
3. **局域网私有化接口代理规约（禁止随意篡改代理）**：
   - 宿主机运行环境已通过系统环境变量自动排除 `10.*` 等局域网地址段；
   - 接入局域网私有节点时，严禁在 `.env` 中额外添加或修改 `NO_PROXY` 设置，直接跟随系统默认环境即可实现无损直连。
4. **跨模型切换会话上下文签名污染陷阱（`Your request was not processed` 根因）**：
   - 当会话中包含 Google Gemini 模型生成的思维链时，由于其返回中带有谷歌私有的加密防篡改签名（`thought_signature` / `encrypted_content`），中途直接切换至 DeepSeek 等开源模型，会导致 Hermes 序列化校验等待超时（51 秒超时退出）；
   - **操作原则**：切换至私有化开源模型（如 `JK-deepseek`）时，**强烈建议点击左上角新建干净会话**，杜绝历史加密签名干扰。
5. **显存配额判据：看 `available_gpu_mem` 余量，不按固定数字教条**：
   - 启动日志每个 rank 会打印 `Capture target decode CUDA graph end ... avail mem=X GB` 与 `available_gpu_mem=X GB`。**这才是唯一可信的判据**：该值稳定在 15 GB 以上即安全，低于 8 GB 则长上下文或高并发下必然 OOM；
   - 8 卡 H200（单卡 141 GB）加载 510 GB 权重后，`--mem-fraction-static 0.90` 实测仍保留约 19.6 GB 计算余量并稳定运行，并非必然崩溃；换用更小显存卡或更大权重时才需要下调；
   - 出现 `CUDA out of memory` 或容器反复重启时，先按第 6 条确认是否真是 OOM，再以 0.05 步长下调该值重试，不要一次性大改。
6. **容器 CrashLoop 的识别（端口忽通忽断）**：
   - 现象：客户端时而能连、时而报 `[WinError 10061] 目标计算机积极拒绝` 或超时；`docker ps -a` 中 `STATUS` 显示 `Up 3 minutes`，但 `CREATED` 是几十分钟前——**创建时间远早于运行时长，就是重启循环的确证**；
   - 排查顺序：`docker logs --tail 80 <容器名>` 看末尾是否 `CUDA out of memory` 或参数解析错误 → 按根因改参数 → `docker rm -f` 后重建（`docker restart` 会沿用旧参数，改了启动命令必须重建）；
   - 权重加载期（510 GB 约 1.5~3 分钟）端口本就不通，此时探测失败属正常，不要误判为故障。
7. **SGLang 忽略模型名的诊断陷阱**：
   - SGLang 只加载一个模型时，请求里的 `model` 字段填任何名字都返回 HTTP 200 并正常推理。**因此"能返回 200"不能证明模型名配置正确**，必须核对会话或配置里的模型名与服务端 `--served-model-name` 一致，否则会长期携带错误标识运行；
   - 同理，`/v1/models` 返回的清单才是服务端真实模型名的唯一依据。
8. **`config.yaml` 只能经 `hermes config` 修改**：
   - `write_file` / `patch` 工具对 Hermes 配置文件有程序级拒绝（报 `Refusing to write to Hermes config file … Agent cannot modify security-sensitive configuration`）。这是设计如此，不要换文件名或换工具绕过；
   - 改配置一律走 `hermes config set <键> <值>` / `hermes config unset <键>`；改前 `cp config.yaml config.yaml.bak-$(date +%Y%m%d-%H%M%S)` 备份，改后用 `hermes config get <键>` 加一次 YAML 解析复核键名与取值；
   - 删除整个 `providers.<名>` 条目用 `hermes config unset providers.<名>`（一次删整段，不必逐字段清）。
9. **模型新增实测标准**：
   - 使用命令行直接构造与生产相同的数据包：
     ```bash
     curl -s -X POST http://127.0.0.1:8317/v1/responses \
       -H "Authorization: Bearer <key>" \
       -H "Content-Type: application/json" \
       -d '{"model": "目标模型名", "input": [{"role": "user", "content": "ping"}]}'
     ```
   - 只有收到包含正常输出的 JSON 响应且 HTTP 状态码为 200 时，方可调用配置命令写入：
     ```bash
     hermes config set providers.<服务商>.models '["已验模型1", "已验模型2"]'
     ```
10. **上下文长度缓存按“模型名@地址”精确匹配（换地址后缓存全失效）**：
   - `$HERMES_HOME/context_length_cache.yaml` 的键是 `模型名@base_url` 全串。后端换 IP、换端口或加/去尾斜杠后，旧键永不命中，Hermes 会每轮现场探测上下文长度；探测超时（日志典型为 `context-length probe for '<模型>' at <地址> exceeded 5.0s — returning unknown`）会直接拖慢桌面端模型信息查询，用户感知为“卡”。
   - **排查动作**：把缓存文件里的键与 `config.yaml` 的 `model.base_url` 及各 `providers.<名>.api` 逐条对拍，地址不一致就重写键。改完用后端 `/v1/models` 的 `max_model_len` 字段核实取值真实。
   - **不要靠 `model.context_length` 硬写绕过**：那是另一层覆盖，写错值会让压缩阈值算错。缓存键与真实地址一致才是正解。
11. **视觉能力开关的三层优先级（`image_input_mode: native` 是绝对覆盖）**：
   - `agent.image_input_mode` 取 `auto` / `native` / `text`。`native` 无视一切能力探测，图片原图直传当前模型；`auto` 下若配了 `auxiliary.vision` 反而会强制走 `text`（有损转述）。
   - 单个模型的视觉声明写在 `providers.<名>.models.<模型名>.supports_vision: true`（**mapping 形式，不是列表**）。写成列表形式（`models: ["x"]`）就无法挂载每模型能力字段。
   - **验证视觉必须发真图**：用纯色或分区块 PNG 让模型报颜色，比问“你能看图吗”可靠。构造最小 PNG 可用 Python `zlib` + `struct` 直接拼（无需 PIL），base64 后以 `image_url` data URI 传入。
12. **探活端点必须与配置的 `api_mode` 一致**：
   - 配 `codex_responses` 就用 `<api>/responses` 探活，配 `chat_completions` 就用 `<api>/chat/completions`。用错端点会得到与生产无关的假阴性（例如反过来测时 `/responses` 报 `PROXY_GENERATION_DISABLED`，而 `/chat/completions` 流式完全正常）。
   - 推理挡位是否真生效，看响应里的 `reasoning_tokens`：拿同一道需要推演的中等难度题分别用 `low` / `medium` / `high` 各发一次，`high` 的推理 token 数应明显最高；若三档数字几乎一致，说明挡位没到达后端。

---


---

## 四、 开源模型私有化部署深度调优参数（DeepSeek SGLang 实战）

在部署 DeepSeek 等拥有深度推演（`<think>` 链）特性的模型时，如果遭遇“满篇废话”、“思考链吐英文”、“代码生成频繁截断错误”等痛点，必须在服务端部署引擎与 Hermes 客户端配置上同时调优：

### 1. 思考链与高级生成参数的正确注入方式（`extra_body` 白名单机制）
Hermes 配置解析器包含严格的键名白名单（`_KNOWN_PROVIDER_KEYS`），**不存在 `assistant_prefill` 或 `default_params` 字段**（写在配置中会被作为未知键忽略）。
必须将需要原样穿透给 SGLang 等底层推理引擎的参数统一放置在 **`providers.<提供商>.extra_body`** 下：
```yaml
providers:
  jk-deepseek:
    name: JK-deepseek
    api: http://10.118.70.129:30000/v1
    key_env: JK_DEEPSEEK_API_KEY
    api_mode: codex_responses
    transport: codex_responses
    discover_models: false
    models:
      deepseek-v4.1-flash:
        supports_vision: true
```
（键名只写小写一份，显示名靠 `name:` 声明；上下文长度见下条，不要写成 provider 下的 `context_length`。）

### 2. 解决“中文能力差、车轱辘废话多”与思考链吐英文问题
- **思考链中文首字前置引导机理**：大模型本质是自回归逐字生成。在 API 请求的 `messages` 队列末尾预置中文 `assistant` 开头（如 `<think>\n【分析与推导】：`），模型的注意力概率分布会瞬间被整体拉入纯中文语境，从根本上杜绝思维链滑向英文推演。
- **网关启用助手消息前置引导的两条实施路径**：
  1. **方案一：SGLang 模板网关原生内置（生产首选）**：
     - 在 SGLang 服务端直接定制分词器的对话模板（完整模板代码详见本技能配套文件 `templates/chinese_thinking_template.jinja`），在模板末尾生成提示符处直接内置中文思考开头：
       ```jinja
       {% if add_generation_prompt %}
           {{ '<｜Assistant｜><think>\n【分析与推导】：' }}
       {% endif %}
       ```
     - 容器编排挂载该模板并在 SGLang 启动参数追加 `--chat-template /template/chinese_thinking_template.jinja`；
     - **技术优势**：零客户端侵入、零多余进程与网络损耗，所有客户端（Hermes、Codex、Claude Code 及第三方脚本）免配置自动生效，100% 物理锁死中文思考链。
  2. **方案二：前置 API 网关中间件动态注入**：
     - 在 SGLang 前端挂载轻量反向代理网关（如 LiteLLM 或轻量 FastAPI 中间件）；
     - 网关拦截客户端请求，若 `messages` 队列最后一条为 `user` 角色，动态在末尾追加：
       ```json
       {
         "role": "assistant",
         "content": "<think>\n【分析与推导】：",
         "prefix": true
       }
       ```
     - 然后原样转交给 SGLang，模型收到未闭合的助手消息后在此基础上继续自回归推导。
- **语言精炼双重物理惩罚**：配置 `frequency_penalty: 0.20` + `presence_penalty: 0.10`，在概率分布层直接扣减重复词句与已讨论主题的权重。
- **超长输出空间纪律**：64K（65536）生成上限是留给**核心业务推导、系统架构设计与完整工程代码**的，严禁用于堆砌无意义的寒暄客套与背景复述；配合系统提示词要求“结论先行、一个句子说一件事”。

### 3. 解决“不主动思考、草草交差”：100 万上下文与 64K 输出显存规划
- **解锁 100 万原生上下文与分块预填充防爆**：SGLang 服务端启动增加 `--context-length 1048576`，Hermes 客户端配置 `context_length: 1048576`。**核心防错措施**：必须显式配置 `--chunked-prefill-size 8192`。当用户输入数万 Token 超长上下文时，若未分块，自注意力矩阵计算开销呈平方级暴涨，会瞬间触发显存溢出崩溃；分块流式加载能彻底消除显存溢出风险，显著降低首字延迟；
- **解锁 64K 单次最大生成（严禁服务端传入 `--max-output-len`）**：SGLang 服务端启动命令中**不存在 `--max-output-len` 参数**，传入会直接报 `unrecognized arguments: --max-output-len` 错误并导致容器死循环重启！服务端整体窗口由 `--context-length 1048576` 统一掌管；64K 单次最大生成由 Hermes 客户端在请求时携带，字段名必须是 **`max_output_tokens`**（Responses API 的字段名），写在 `providers.<名>.extra_body` 下：
  ```yaml
  providers:
    jk-deepseek:
      extra_body:
        max_output_tokens: 65536
  ```
  生效链路：`extra_body` → 运行时解析为 `request_overrides.extra_body` → 传输层 `kwargs.update(request_overrides)` 直接并入请求体。可用 `_custom_provider_request_overrides()` 在写入后核对解析结果，再发一次带 `max_output_tokens=65536` 的真实请求确认后端接受。
- **`model.max_tokens` 与 `HERMES_MAX_TOKENS` 已被官方移除（写入静默忽略）**：官方 `evals/output_caps_scope.md` 明确记载这两项连同具名/自定义 provider 的 `max_output_tokens` 顶层字段一并移除，理由是输出上限不再作为用户级模型设置。`hermes config set model.max_tokens 65536` 会**成功返回**并写入文件，但运行时代码根本不读取该键——只看到写入成功就宣称已生效是典型误判。输出上限唯一受支持的入口是 `extra_body`（保留为通用协议原样转交机制）。
- **显存配额稳健分配（防 OOM 崩溃核心）**：8 卡 H200 总显存达 1128GB，静态权重占用 510GB，配置 `--mem-fraction-static 0.80`，保留约 20%（超 220GB）物理缓冲显存专门充当动态激活张量计算池，确保高并发超长推演稳健运行；杜绝盲目拉满至 0.90 引发显存溢出；
- **并行零损耗切分**：专家网络切分必须能被卡数整除。例如 8 卡部署必须使用 `--tp 8 --ep-size 8`，确保 384 个专家被 8 卡均匀整除，杜绝因未整除引发的跨卡通信精度损失与代码生成幻觉；
- **Responses API 官方截断缺陷与平滑防护（--allow-auto-truncate 核心防错）**：SGLang 的 Responses 接口在未显式传递输出上限时，会根据未展开前的输入粗略估算默认上限。在数十万 Token 超长上下文场景下，由于输入展开后的微小误差，极易发生 `输入 + 默认上限 > context_len` 进而报 HTTP 400 错误（Issue #29287）。必须在服务端启动命令中显式追加 **`--allow-auto-truncate`**；开启后，系统在遇到超限时会自动将多余的输出上限平滑裁剪至上下文物理边界，保证请求以 HTTP 200 正常流式输出，彻底杜绝请求中途被掐断；
- **HiCache 宿主机内存扩展与倍率决策（--hicache-ratio 1 优于 2）**：DeepSeek-V4 等双重混合缓存架构在底层要求主存池与显存池必须保持比例一致，**不支持固定数值参数 `--hicache-size`（传入会抛出 ValueError 拒绝启动），必须使用比例参数 `--hicache-ratio`**。在 8 卡 H200 硬件下，**推荐设置为 `--hicache-ratio 1`**：显存 L1 与内存 L2 各占 336GB（总缓存达 4000 万 Token），容量已极端充沛；相比 2 倍（672GB），1 倍能显著减少树状基数页表的维护负担、消除 PCIe 总线异步换页的性能抖动，并为操作系统内核留出充沛的磁盘页缓存存放静态权重；
- **多卡显存均衡强校验误杀防御（SGLANG_ENABLE_TP_MEMORY_INBALANCE_CHECK=0）**：SGLang 在分布式启动阶段默认执行 `_check_tp_memory_balance` 强校验，若某张卡因前置测试残留、驱动释放延迟几毫秒而出现微小的显存差异（哪怕只差 36MB），就会抛出 `RuntimeError: The memory capacity is unbalanced` 阻止启动。必须在容器环境变量中注入 **`-e SGLANG_ENABLE_TP_MEMORY_INBALANCE_CHECK=0`**，将该检查自动降级为普通警告，避免容器陷入启动自锁；
- **长文本分块预填充尺寸与显存黄金平衡（6144 与 0.75 组合）**：SGLang 底层不要求分块尺寸必须是 2 的整数次幂，`6144` 严格满足 16/64/128/1024 页面大小整倍数规则。相比 8192（激活显存高达 5.5GB 易 OOM），6144 激活显存仅约 3.8GB；配合 `--mem-fraction-static 0.75` 为单卡留出的 35GB 空闲显存与 `-e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`，不仅绝对杜绝显存溢出，而且长文本预填充吞吐量（2300~2500 Token/s）比 4096 提升 15% 以上；
- **本地回环网口对称流量机理定性**：服务启动后监控面板显示的约 5~7 Mbps 流量集中在本地回环网口，且上下行完全对称（延迟 0ms）。这是 SGLang 十几个分布式子进程（API Router、Tokenizer、Scheduler、8 个 GPU Worker）在 `--network=host` 下通过本地 ZeroMQ 内存消息队列进行高频心跳同步、状态轮询与监控采样产生的内部通信，绝非从外部公网下载数据。
- **解析器显式精准绑定（带版本号合法取值）**：针对 DeepSeek-V4.1-Flash 模型，必须显式声明官方认可的取值：`--reasoning-parser deepseek-v41`（带短横线）与 `--tool-call-parser deepseekv41`（不带短横线）。严禁使用未经版本限定的裸词 `deepseek`，否则 SGLang 会因参数不合法（`argument invalid choice`）抛出退出码 2 并导致容器死循环重启；
- **Ubuntu 24.04 / Python 3.12 编排运行环境避坑**：Ubuntu 默认源中的 `docker-compose` 属于已弃用的 Python 脚本版本（1.29.2），在 Python 3.12 下会与新版网络库冲突抛出 `Not supported URL scheme http+docker`。若未配置 Docker 官方源安装 `docker-compose-plugin`，优先推荐直接使用参数 100% 等价的原生 `docker run` 命令拉起容器，彻底绕过 Python 依赖地狱；
- **三大 API 接口原生挂载**：SGLang 默认在单端口同时暴露 Chat、Responses 与 Messages 三大路径，无需单独配置开关，客户端按路径分流请求即可；
- **Responses API 多模态图片请求 400 缺陷与防护（问题编号 29287）**：当客户端（如 Codex 命令行）发送包含图片的请求且未携带 `max_output_tokens` 字段时，SGLang 在图片 Token 展开前计算 `prompt_length`，得出极大的 `default_max_tokens`（几乎等于整机上下文上限），随后在展开后执行校验时因 `input + max_tokens > context_len` 报 HTTP 400 错误。官方在 v0.5.22 版本（合并编号 35524）修复了该预计算逻辑；在未合入该修复的镜像中，必须由客户端显式传递 `max_output_tokens`（如 8192 或 65536），或加反向代理中间件补齐字段；
- **长文本分块预填充尺寸与显存溢出根治三要素**：单批 `--chunked-prefill-size` 不能盲目设为 8192。550B 规模的混合专家模型在长输入（如 3 万以上 Token）分块计算时，单批 8192 会瞬间申请 5.5GB 连续激活显存，在显存余量较低时触发显存溢出崩溃。生产推荐设为 `--chunked-prefill-size 4096`（单批激活峰值降低 60%），配合 `--mem-fraction-static 0.75~0.80`（单卡留出超 25GB 安全可用显存）与环境变量 `-e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` 消除显存碎片；
- **DSpark 推测解码加速原理解析与资源权衡**：DeepSeek-V4.1-Flash 权重内置 DSpark 预测头，配置 `--speculative-algorithm DSPARK --speculative-dspark-block-size 5` 开启。原理上属于严格精确采样，大模型本体逐词强校验，智商与逻辑严谨度零影响；单人独占环境下吐字流速可提升 2 至 3 倍，但需配合 `--mem-fraction-static 0.70~0.75` 为单卡预留 25% 至 30% 显存余量作为推测验证缓冲区；
- **启动初期正常警告与真实崩溃判据**：启动阶段出现 `Warning: CUDA driver error ... init_multicast_for_block` 是 SGLang 检测多机多播失败后的正常日志，紧接着会打印 `Gracefully skipping multicast` 降级为单机点对点通信，不是崩溃；PyTorch 抛出的 `UserWarning: barrier()` 与 `FutureWarning: all_gather_into_tensor` 亦属版本兼容提示，无害。真正的崩溃是日志出现 `torch.OutOfMemoryError` 或 `Received sigquit from a child process`；
- **模板与编排结对存放纪律**：编排文件挂载 `./chinese_thinking_template.jinja` 为相对路径，拷贝至目标服务器时，两个文件必须结对存放在服务器同一工作区目录下，避免挂载为不存在的目录。

## 五、 自检核对清单

- [ ] 新增模型前是否执行了生产相同路径的真实网络测试并拿到上游有效数据？
- [ ] 密钥类信息是否严格保存在 `.env` 文件中，未泄漏至 `config.yaml`？
- [ ] 选取的 `api_mode` 是否与上游服务实际暴露的路径与请求头完全匹配？
- [ ] 部署开源思考模型时，是否挂载了配套模板 `templates/chinese_thinking_template.jinja` 并配置了 `--chat-template` 参数？
