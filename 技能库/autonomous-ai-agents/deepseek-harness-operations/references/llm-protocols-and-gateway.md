# 协议判定与推理服务探测

用于回答"现在走的是哪条协议"，以及在改协议前后确认推理服务到底支持哪些路由。

## 一、客户端当前用哪条协议

| 客户端 | 读哪里 | 判定字段 |
|---|---|---|
| dsh（`dsh-llm-deepseek`） | `$DSH_HOME/profiles/<name>/cordis.patch.yml` 或旧 `settings.yaml` 的 `llm-deepseek` 分节 | `protocol: chat-completions` / `messages` |
| dsh（`llm-pi-ai`，0.1.7 起常见） | 同文件的 `llm-pi-ai.providers`；`agent-default-model.provider` 指向哪个 provider | 该 provider 的 `api:` 值（`openai-responses` 即 Responses） |
| dsh 运行态复核 | 会话日志每轮的 `request/header` | `provider` / `model` |
| Hermes | `config.yaml` 的 `model.provider` + 该 provider 插件 | provider 插件的 `api_mode` 类字段 |

Hermes 的 provider 插件在 `hermes-agent/plugins/model-providers/<name>/__init__.py`，基类字段定义在 `hermes-agent/providers/base.py`；`api_mode` 默认 `chat_completions`，插件不覆盖就是 chat-completions。Hermes 支持的 `api_mode` 取值：`chat_completions`、`anthropic_messages`、`codex_responses`、`bedrock_converse`、`codex_app_server`（**没有** OpenAI Responses 这一档，不要把它与 `codex_responses` 混为一谈）。

结论要分对象说：同一台机器上 Hermes 与 dsh 往往不在同一条协议上（本机实测：Hermes 走 chat_completions，dsh 0.1.7 走 `llm-pi-ai` 的 `openai-responses`，两者地址不同）。

## 二、探测推理服务

```bash
KEY=$(python -c "import yaml;print(yaml.safe_load(open(r'<DSH_HOME>\\.credentials.yaml',encoding='utf-8'))['refs']['DEEPSEEK_API_KEY'])")
curl -s -H "Authorization: Bearer $KEY" "<baseURL>/models"
```

**请求体一律用文件投递**（`-d @body.json`），不要把含中文的 JSON 内联在 bash 单引号里：编码被破坏后服务端会回 `400 {"detail":"There was an error parsing the body"}`，看起来像协议不支持，实际是载荷坏了。

| 路由 | 协议 |
|---|---|
| `GET <baseURL>/models` | 服务身份：`owned_by` 说明实现（`vllm` 等），`max_model_len` 说明上下文上限 |
| `POST <baseURL>/chat/completions` | OpenAI Chat Completions |
| `POST <baseURL>/responses` | OpenAI Responses（`object: "response"`，`output` 数组，含 `reasoning` 项） |
| `POST <baseURL>/messages` | Anthropic Messages（需 `x-api-key` + `anthropic-version`） |

**未路由的路径通常回 401 而不是 404**，所以 401 只说明"这条路由服务端不认"，不能据此判定密钥失效；判断密钥是否有效，要用另一条确定可用的路由打同一个 key。

## 三、本机网关实测样本（vLLM 实现，非官方端点）

| 探测 | 结果 |
|---|---|
| `GET /v1/models` | 200，`owned_by: vllm`，`max_model_len: 1048576` |
| `POST /v1/chat/completions` | 200，`object: chat.completion`，`finish_reason: stop` |
| `POST /v1/responses` | 200，`object: response` |
| `POST /v1/messages` | 401（不支持 Anthropic 协议，因此协议不能切到 `messages`） |
| 同一 key 打上述任一可用路由 | 均 200，说明问题不在密钥 |

## 四、切换 Hermes 的协议并取证

```bash
hermes config set model.api_mode responses     # 别名，落盘为 codex_responses
hermes config unset model.api_mode            # 回到自动判定
hermes config get model                       # 复核
```

设置进 `config.yaml`，不要写进 `.env`。别名表在 `hermes_cli/config_providers.py::_API_MODE_ALIASES`：`responses`/`openai-responses`/`openai_responses` → `codex_responses`；`openai`/`openai-chat`/`chat-completions` → `chat_completions`；`anthropic`/`messages` → `anthropic_messages`；`bedrock` → `bedrock_converse`。拼写写错会被**静默丢弃**并回落到按主机名猜测，所以落盘后要用 `hermes config get model` 复核拼写。

生效判定在 `agent/agent_init.py::_resolve_api_mode`（先 Actual 路由，再显式 api_mode，然后按 provider 与主机名猜）。因此**第三方主机上的 Responses 必须显式写** `model.api_mode`，否则不会自动选中。两条易踩的规则：换 provider 会清掉 `model.api_mode` 与 `model.base_url`，换完要重设；已运行的会话进程在启动时已加载配置，**必须重启才生效**。

**协议归属不要只看配置文件，取运行态证据。** 请求日志与数据库都不记录 `api_mode`，但有三处一手证据：

1. `logs/agent.log` 的 `API call #N: … id=resp_…` = Responses 路径，`id=chatcmpl-…` = Chat Completions；同一行还有 `OpenAI client created (codex_stream_request, …)` 可作旁证。按时间段切分即可得到"切换前后各自走哪条"。
2. `state.db` 的 `session_model_usage` 按 `task` 分行（主对话、审批、压缩、后台复核各一行），可看各条通道的用量。
3. 全链路网络抓包：用一次性 `HERMES_HOME` 指向本地记录服务，见下节。

**抓实际请求路径**（`scripts/probe-hermes-wire.py`）：

```bash
python scripts/probe-hermes-wire.py 8123 reset &
TH="$LOCALAPPDATA/Temp/hermes-probe"           # Linux 下 /tmp/hermes-probe
mkdir -p "$TH" && cp <hermes-home>/config.yaml "$TH/"
sed 's|^DEEPSEEK_BASE_URL=.*|DEEPSEEK_BASE_URL=http://127.0.0.1:8123/v1|' <hermes-home>/.env > "$TH/.env"
HERMES_HOME="$TH" hermes chat -Q -q "reply: ok"
```

记录里出现 `POST /v1/responses`、请求体带 `"include":["reasoning.encrypted_content"]` 与 `"instructions"`、SDK 头 `X-Stainless-*`，即为 Responses 在用。

四个坑：

- **一次性 `HERMES_HOME` 必须连 `plugins/` 一起拷。** 只拷 `config.yaml` + `.env` 时，用户目录里的 provider 插件不存在，解析会落到与真实环境不同的阶梯（配置里的 `providers:` 条目也一并删掉时直接报 `Unknown provider '<名>'`；`key_env` 还会报“变量为空”——其实变量就在你刚拷进去的 `.env` 里）。这种"插件缺失态"下测出的地址来源与协议优先级全是错的，结论会反向误导。
- **命令行前置环境变量覆盖不了 `.env`**（dotenv 以 override 方式加载），`DEEPSEEK_BASE_URL=... hermes ...` 会被忽略、请求静默打到真实端点。只能用独立 `HERMES_HOME` 放一份改过的 `.env`；该目录含密钥副本，用完立即删除。
- `/v1/models` 探测发生在对话请求之前，不能作为"对话走哪条协议"的证据。
- 记录服务若对流式请求回非 SSE 体，客户端报 `Codex Responses stream did not emit a terminal response`——这条文案本身就是 Responses 传输在用的证据，不是故障。

## 五、`api_mode` 的作用域：端点级，不是模型级

回答"换模型后协议能不能保持不变"之前先认下这四条实测结论：

1. **它属于"provider + 端点"这条路由，不属于某个模型。** 同一份 `model.api_mode` 被该 provider 下所有模型共用。
2. **换 provider 会清除它。** `hermes config set model.provider`（`hermes_cli/config.py` 调 `route_identity.drop_stale_model_route`）与 `hermes model` 向导（`model_setup_flows_common.py`，`clear_model_endpoint_credentials(clear_api_mode=True)`）都会弹出 `model.api_mode` 与 `model.base_url`；运行时的 `_configured_api_mode` 另有一条约束——provider 不匹配时该键直接失效。
3. **没有 per-model 的协议覆盖。** `config_defaults.py` 里 `api_mode` 只在 `delegation` 与 `delegation.review` 出现；`model_overrides` 不认这个字段。
4. **`providers.<名>.transport` 是死字段，`custom_providers` 条目里的 `api_mode` 才有效。** 实测：`resolve_user_provider` 能把 `transport=codex_responses` 读进 `ProviderDef`，但 `providers.determine_api_mode` 对该 provider 仍返回 `chat_completions`（overlay 只声明了 `base_url_env_var`），运行时不读它（但桌面端「自定义端点」页展示与编辑的正是这个字段，见第七节）。反之 `custom_providers` 条目按端点生效（`runtime_provider_custom._resolve_named_custom_runtime` 读 `custom_provider["api_mode"]`）。

不启动完整会话即可判定（直接调解析函数）：

```bash
cd <hermes-home>/hermes-agent && python -c "
import sys; sys.path.insert(0,'.')
from hermes_cli import providers as P, runtime_provider as RP
print(P.determine_api_mode('deepseek','http://<网关>/v1','<模型>'))       # 不看 model.api_mode
print(RP._configured_or_fallback_api_mode('deepseek', {}, 'http://<网关>/v1', '<模型>', opencode_by_model=True))
"
```

第二行传空 `model_cfg` 就是在模拟"`model:` 段已被清空"，得到的即切换后实际会走的协议。**第三方主机上的 Responses 必须显式写 `model.api_mode`**，两者都只输出 `chat_completions` 就说明当前绑定会在切换时丢掉。

## 六、端点 Responses 实现的合规性探测

自建网关的 `/v1/responses` 可能只是"形状像"：`object: response` 与 `output` 数组不足以证明它符合规范。用 `scripts/probe-responses-stream.py <baseURL> <model> [key]` 做流式侦察，看三处：

| 规范 | 本机网关实测 | 后果 |
|---|---|---|
| 推理走 `response.reasoning_summary_text.delta` 等标准事件 | 只发 `response.reasoning_text.delta` | 只认标准事件名的客户端拿不到流式思维链 |
| 推理项文本在 `summary[]` | 在 `content[]`，元素类型 `reasoning_text`，`summary` 为空数组 | 只读 `summary` 的客户端拿不到思维链 |
| `include: ["reasoning.encrypted_content"]` 时附 `encrypted_content` | 恒为 `null` | 跨轮推理连续性只能靠明文回放 |

Hermes 侧对应实现是 `agent/codex_responses_adapter.py::_extract_responses_reasoning_text`，它依次读 `summary`、再读 `text`，**不读 `content[]`**——这类网关上走 Responses 时思维链不进消息表。

**`reasoning_content` 只剩一个空格不是故障。** 它是 Hermes 对 OpenAI 兼容路径的既有设计：`agent/chat_completion_helpers.py::build_assistant_message` 在工具调用轮次补一个空格占位（上游未直接返回该字段时），`agent/message_sanitization.py` 回放时同样以空格补齐（注释写明是 DeepSeek/Kimi 思考模式要求，空串会被服务端拒）。判定异常要对比改动前后的**落库分布**，不看单条消息：实测同一会话在 chat-completions 时期 225 条助手消息的 `reasoning_content` 平均约 967 字符，切到 Responses 后 19 条全为 1 字符，说明思维链只进了用量统计、没进消息表。

## 七、Hermes 自定义 provider 的接线与可见性

命名自建端点写在 `config.yaml` 的 `providers.<名>` 下时，`hermes_cli/config_providers.py` 会把它规范化（`_pick_provider_base_url` 接受 `base_url`/`url`/`api`；`_API_MODE_ALIASES` 把 `responses` 落成 `codex_responses`），但**规范化不等于运行态生效**——实际协议仍按第五节判定（`providers.<名>.transport` 是死字段，靠 `model.api_mode`）。接线与可见性另有四条规则：

1. **`providers:` 条目不会进入 `PROVIDER_REGISTRY`**（`hermes_cli/auth.py`），因此 `hermes auth` 与设置界面的密钥页里**没有它的行**。这是设计而非配置错误：只有 **provider 插件**会经 `hermes_cli/auth_plugin_providers.py::register_plugin_provider()` 镜像进注册表，而该文件的 `_REGISTRY_PLUGIN_SKIP` 明确排除内置 `custom`（openrouter/custom 属聚合与用户自备，运行时另走解析路径）。
2. **要让它出现在 provider 列表/密钥页**：写成 provider 插件，放用户目录 `$HERMES_HOME/plugins/model-providers/<名>/`（`providers/__init__.py` 文档头列出的三个位置之一，同名覆盖内置）。目录里一个 `__init__.py`（import 时调 `register_provider(ProviderProfile(...))`）+ 一个 `plugin.yaml`（`name`、`kind: model-provider`）。`ProviderProfile`（`providers/base.py`）可声明 `name` / `env_vars` / `base_url` / `api_mode`（默认 `chat_completions`，可直接写 `codex_responses`）/ `display_name` / `description` / `auth_type`。**已实测**：插件注册成功后解析走注册表行（报错文案里出现的是 `display_name` 而不是 `custom`），`api_mode` 仍由 `model.api_mode` 钉住（`env_vars` 里声明的 `api_mode` 是 profile 默认值，不是最终判定），记录器实测收到 `POST /v1/responses`。地址优先级另见第 5 条。
3. **密钥来源是 `model.key_env`。** `hermes_cli/auth.py::_model_level_key_env` 在 `model.provider` 等于被解析的 provider 时采用该键指定的环境变量（这套指针是设置界面保存密钥时写下的）。若变量名沿用内置厂商的（如官方 DeepSeek 的 `DEEPSEEK_API_KEY`），自建端点就是在用那份厂商密钥认证——症状正是“自定义 provider 的 base url/api key 仍指向系统自带的 X”。给自建端点单独一个变量名，并在插件的 `env_vars` 里声明同名，值写进 `$HERMES_HOME/.env`。
4. **不要为“看起来干净”删掉端点/密钥字段**：解析阶梯第 3 级是命名自建 provider（`runtime_provider.py::_named_custom_rung` → `_resolve_named_custom_runtime`），地址与凭据都空时落到 `_raise_for_credentialless_bare_custom`，直接报 `provider 'custom' resolved without credentials (no endpoint or API key configured)`。这是设计上的拒绝：要么保留 `model.base_url`/`model.key_env`，要么由插件提供 `base_url`。

5. **`env_vars` 里必须有一条以 `_BASE_URL` 或 `_URL` 结尾的名字，界面上才有地址栏。** `auth_plugin_providers.py::_api_key_env_fields()` 把 `env_vars` 拆成（密钥变量, 地址变量）：只有名字以 `_BASE_URL`/`_URL` 结尾的那条被认成地址变量并写进注册表行的 `base_url_env_var`，其余算密钥变量；一条都不结尾就是空串，密钥页只渲染密钥、没有 URL 输入项。写法 `env_vars=("<名>_API_KEY", "<名>_BASE_URL")`，并在 `.env` 给地址变量一个初值。**地址优先级实测**：插件注册生效后，该 `<名>_BASE_URL` **优先于** `model.base_url` 与 `providers.<名>.api`——把 `.env` 里这条指向本地记录器，即使 config 里两个地址都在，记录器照样收到请求；因此不必为了能在界面改地址而清掉它们，后者只剩插件缺失时的兜底价值。（反过来，`_BASE_URL` 尚未声明时就测不到优先级：那时它根本没被接线。）
6. **设置界面各处的分工（别在错误的地方找协议）。** 密钥页只放凭据：桌面端与 web 端同源，后端 `provider_catalog()` / `web_routers/config_env.py::_get_env_vars_sync()` 会把该 provider 的密钥变量与地址变量各输出一条（`category: provider`、`advanced: true`），web 端即 `web/src/pages/EnvPage.tsx` 的密钥卡。**协议的界面入口只在桌面端的「自定义端点」页**（`apps/desktop/src/app/settings/custom-endpoints-settings.tsx`，四项下拉 Auto-detect / Chat Completions / Responses API / Anthropic Messages），后端 `web_routers/config_env.py::_endpoint_api_mode()` 读 `providers.<名>.api_mode`（或旧 `transport`）。**Web 仪表盘没有协议项**：它的配置页是 schema 驱动表单（`GET /api/config/schema`），schema 里有 `auxiliary.review.api_mode` 与 `delegation.api_mode`，**没有 `model.api_mode`**；唯一改法是切到该页的 YAML 模式，走后端 `GET|PUT /api/config/raw`（`web_routers/analytics.py`）。
7. **`provider_catalog()` 与 `_get_env_vars_sync()` 的结果是进程内缓存**：新增插件或新增环境变量后，运行中的桌面端/仪表盘仍显示旧清单，必须重启该进程（用后端函数直接取值可立即验证改动是否落库）。
8. **改 `.env` 用带闸门的脚本**：先备份到 `backups/`，命中计数必须恰为 1 行，否则中止不落盘（多行同名或零命中都说明威胁模型变了），改完复核残留计数为 0。

只读取证命令：`grep -n "_KNOWN_PROVIDER_KEYS\|_pick_provider_base_url\|_API_MODE_ALIASES" hermes_cli/config_providers.py`、`grep -n "_REGISTRY_PLUGIN_SKIP" hermes_cli/auth_plugin_providers.py`、`sed -n '1,30p' providers/__init__.py`（插件位置与覆盖规则）。

**`tool_calls` 里的 `response_item_id` 不能当协议证据。** 它是 Hermes 保存工具调用的固定结构（`agent/chat_completion_helpers.py::_assistant_tool_call_dict` 恒写入），在本机全库自最早会话起就存在，与走哪条传输无关。用 `reasoning_content` / `codex_reasoning_items` 是否落库判断同样不可靠。
