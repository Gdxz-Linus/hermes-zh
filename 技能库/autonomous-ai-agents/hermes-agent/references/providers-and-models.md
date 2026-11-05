# Providers & Model Aliases

Set via `hermes model` (picker) or `hermes setup`. 35+ provider profiles ship as
plugins under `plugins/model-providers/`; user plugins of the same name override.
Full docs: https://hermes-agent.nousresearch.com/docs/integrations/providers

### Providers

| Provider | Auth | Key env var(s) |
|----------|------|----------------|
| openrouter | API key | `OPENROUTER_API_KEY` |
| anthropic | API key | `ANTHROPIC_API_KEY` (also `CLAUDE_CODE_OAUTH_TOKEN`) |
| nous | OAuth device code | `hermes auth add nous` (or `NOUS_API_KEY`) |
| openai-codex | OAuth | `hermes auth add openai-codex` |
| qwen-oauth | OAuth | `hermes auth add qwen-oauth` |
| minimax-oauth | OAuth | `hermes auth add minimax-oauth` |
| copilot | Token | `COPILOT_GITHUB_TOKEN` / `GH_TOKEN` (Copilot device flow — `gh auth login` tokens do NOT work) |
| copilot-acp | External CLI | Copilot CLI on PATH or `COPILOT_CLI_PATH` |
| gemini | API key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| xai | API key | `XAI_API_KEY` (SuperGrok OAuth also supported) |
| deepseek | API key | `DEEPSEEK_API_KEY` |
| zai (GLM) | API key | `GLM_API_KEY` / `ZAI_API_KEY` |
| minimax / minimax-cn | API key | `MINIMAX_API_KEY` / `MINIMAX_CN_API_KEY` |
| kimi-coding / -cn | API key | `KIMI_API_KEY` / `KIMI_CN_API_KEY` |
| alibaba (+coding-plan) | API key | `DASHSCOPE_API_KEY` / `ALIBABA_CODING_PLAN_API_KEY` |
| xiaomi | API key | `XIAOMI_API_KEY` |
| huggingface | Token | `HF_TOKEN` |
| fireworks / novita / nvidia / deepinfra / gmi / arcee / stepfun / upstage / kilocode / ai-gateway / opencode-zen / opencode-go / ollama-cloud | API key | `<NAME>_API_KEY` |
| bedrock / vertex / azure-foundry | Cloud SDK / key | AWS SDK creds / Vertex ADC / `AZURE_FOUNDRY_API_KEY` |
| custom | Config | `model.base_url` + `model.api_key` in config.yaml |

Multiple credentials per provider pool and rotate automatically (`hermes auth`).
Fallback chain when the primary fails: `hermes fallback add|remove|list`.

### 自建/私有端点想出现在密钥页，必须做成 provider 插件

**先回答「model-provider 插件是干什么的、为何里面带地址」**：这类插件（`plugin.yaml` 里 `kind: model-provider`）
描述的就是「一个模型服务提供方」，地址是它的核心属性。它做三件事：

1. **注册进 provider 注册表**：`register_provider()` 把名字写进 `PROVIDER_REGISTRY`，`hermes auth`、密钥页、模型选择器才能识别它；不注册选模型时报「未知 provider」。
2. **提供默认地址兜底**：插件里的 `base_url` 是当 `config.yaml` 的 `providers.<名>` 没写 `api` 字段时用的默认值。
3. **声明模型能力**：`model_capabilities` 里的上下文长度、工具、推理、视觉声明供选择器徽章与图像路由使用。

因此「插件里写地址」不是重复配置，而是该插件的定义本身。但它也带来一个隐患：
**插件里的地址与 `config.yaml` 里的地址可能不一致，而插件地址只在配置缺失时生效**。
排查时用 `resolve_runtime_provider(requested="<名>")` 看实际返回的 `base_url`，不要假定两边一致；
发现插件地址指向不通的端口时，改插件（用户层，升级不动）比改产品源码便宜。

**先分清是自带插件还是后装的**：`ls <repo>/plugins/model-providers/` 里有就是官方自带（升级会覆盖），
只在 `$HERMES_HOME/plugins/model-providers/` 里有就是后装的（升级不动）。代码侧判据是
`providers.provider_source("<名>")`，返回 `"user"` 即用户层插件。

**不要在产品源码里 grep 插件 provider 的名字**：模型选择器里那一行不是写在 `hermes_cli/models_catalog_static.py`
里的，而是 `sync_plugin_provider_catalog()` 在插件注册后动态追加进 `CANONICAL_PROVIDERS` 的。
在静态目录文件里搜不到该名字不等于它不存在，也不等于它来自配置。用户问「这是内置还是后装」时，
按上面两条目录判据回答，不要凭源码 grep 结果下结论。

**插件里的 `model_capabilities` 可能声明着后端已经不存在的模型名**：后端换模型后，插件里的
`model_capabilities` 与 `name`／`base_url` 都是过期值。这类声明不会报错、也不会生效，但会让人误以为
该通道已配置好。改配置前先核一遍插件里的模型名与后端 `/v1/models` 是否一致。

`providers.<name>` 配置条目能让推理跑通，但它**不进** `PROVIDER_REGISTRY`，所以密钥页、`hermes auth status <name>`、`hermes doctor` 的连通性行都不会有它；而且该段里的 `key_env` 一旦删掉，解析阶梯会落到
`hermes_cli/runtime_provider.py::_raise_for_credentialless_bare_custom()` 的硬拒绝（`provider 'custom' resolved
without credentials`），这就是“删了参数就挂”的位置。

要让它成为一等公民，放进用户插件目录 `$HERMES_HOME/plugins/model-providers/<name>/`（另有内置目录与 pip entry
point；用户插件同名覆盖内置）：

```python
# $HERMES_HOME/plugins/model-providers/llm-gw/__init__.py
from providers import register_provider
from providers.base import ProviderProfile

register_provider(ProviderProfile(
    name="llm-gw", display_name="LLM Gateway",
    api_mode="codex_responses",          # ProviderProfile 自带该字段，默认 chat_completions
    env_vars=("LLM_GW_API_KEY",),        # 独立密钥变量，不再借用 DEEPSEEK_API_KEY
    base_url="http://<服务器地址>:8000/v1", auth_type="api_key",
))
```

同目录再加 `plugin.yaml`（`name:` / `kind: model-provider` / `version:` / `description:`）。

为什么这样就够了（均已实测）：`hermes_cli/auth_plugin_providers.py::register_plugin_provider()` 会把 profile 镜像进
`PROVIDER_REGISTRY`（`_REGISTRY_PLUGIN_SKIP` 只跳过 copilot/kimi/zai/openrouter/**custom**，所以自建名字可以过），镜像后：
`hermes auth status <name>` → `logged in`；`hermes doctor` 出现 `✓ <display_name>` 连通性行；密钥页按 `env_vars` 列出该 provider。
密钥解析实测来源为 `env:LLM_GW_API_KEY`。

**密钥页上“只出现密钥、没有地址输入框”的原因与写法**：密钥页（桌面设置 → 密钥 Tab）的每一行由
`hermes_cli/provider_catalog.py::provider_catalog()` 交付，它只把 `base_url_env_var` 非空的 provider 当可折叠的“高级项”展开地址输入框（
`apps/desktop/src/app/settings/providers-settings.tsx` 取 `profile.url ?? info.url`）。而 `base_url_env_var` 仅来自
`auth_plugin_providers._api_key_env_fields()` 对 `env_vars` 的拆分：**名字以 `_BASE_URL` 或 `_URL` 结尾的那一条**才被认成地址变量；没写就是空串，页面上自然没有 URL 项（只有密钥）。写法：
`env_vars=("<NAME>_API_KEY", "<NAME>_BASE_URL")`，并在 `.env` 里给 `_BASE_URL` 一个初值。

地址优先级（已实测，本地记录器代替端点判定谁被访问）：插件注册成功后，运行时走注册表行，`<NAME>_BASE_URL`
**优先于** `model.base_url` 与 `providers.<name>.api`；后者只剩兵备价值（插件缺失时才生效），因此不必删，也不必为了能在页面改地址而清掉它们。
.responses 的 wire 仍由 `model.api_mode: codex_responses` 钉住（实测记录到 `POST /v1/responses`）。**注意 `provider_catalog()` 在每个进程内缓存**：在页面上看到新 provider 需要重启该进程（桌面端/dashboard）。

配套（均用 `hermes config set`，不要手改 YAML）：`model.key_env` 与 `providers.<name>.key_env` 一起改指新变量；
`model.provider` / `providers.<name>.transport`（= 钉住 wire）保留不动。**`providers:` 条目建议保留**——它才是把某个 wire 钉在某个端点的机制，插件解决的是注册与凭据可见性。只改 `model.key_env` 会剩下一处仍指向旧变量名。

验证 wire 未被改动：用 `scripts/fake_llm_probe.py` + 一次性 `HERMES_HOME`（把 config.yaml 里该 provider 的地址替换成
`http://127.0.0.1:<port>/v1`，`.env` 一并拷贝），实测记录到 `POST /v1/responses`（流式被 answer 成非 SSE 时报
`Codex Responses stream did not emit a terminal response`，这句本身就证明 Responses transport 在用）。用完删掉一次性 home
（内含密钥副本）与 `requests.jsonl`。

### 自定义 Provider 的 URL 格式强校验（Malformed custom endpoint URL 陷阱）

- **规约**：在 `config.yaml` 或 Provider 插件中声明 `api` / `base_url` 时，系统底层（`agent_init.py::_init_openai_client`）会调用严格的 URL 解析器校验端口必须为数字（1~65535）。
- **陷阱**：严禁使用伪端口或非数字主机字符串（例如 `http://127.0.0.1:local`），否则客户端初始化阶段会直接抛出 `RuntimeError: Failed to initialize OpenAI client: Malformed custom endpoint URL: '...'` 并阻断当前会话；必须配置合法的数字端口（如 `http://127.0.0.1:8012/v1`）。

### 桌面端模型切换与网关乐观锁冲突（“必须按 Ctrl+R 才能切模型”的真正根因与根治）

- **现象**：在桌面端左下角下拉菜单中点击模型后，当前活动会话没有实时生效，必须按 `Ctrl+R` 刷新或新开会话才能生效；刷新也时好时坏；界面显示已切到新模型，实际对话仍在跑旧模型（日志里同一会话出现两个不同的 provider／模型交替）。
- **真正根因（版本冲突 `revision_conflict`）**：
  桌面端前端向网关发送 `session.mutate` 请求时，会附带前端内存中记录的会话版本号（`expected_revision`）。当用户连续发送多轮消息或后台自动更新后，前端记录的版本号与底层数据库（`state.db`）中的最新版本号发生数值差异；
  网关底层（`hermes_state_mutation_chat_pick.py::_fenced_row`）强校验发现版本号不一致，抛出 `JsonRpcGatewayError: revision_conflict`；
  **前端桌面端在收到该错误后未执行自动重试，而是直接静默放弃本次切换**；用户按 `Ctrl+R` 强行重载前端页面重新同步了权威版本号，才碰巧切了过去。
- **修复是三处配套，缺一不可**：
  1. 网关 `hermes_state_mutation_chat_pick.py`：`operation` 为 `model` 或 `reasoning` 时自动采用数据库最新版本号（`row['runtime_revision']`），消除版本漂移阻断；
  2. 网关 `gateway/session_busy_controls.py`：旧版 `config.set key=model` 请求不再硬拒 `use_session_mutation_model`，而是补齐 `request_id`／`expected_revision`／`expected_generation` 后转交 `session.mutate`；
  3. 前端 `apps/desktop/src/app/session/hooks/use-model-controls.ts`：捕获 `revision_conflict`／`use_session_mutation_model`／`stale_generation` 时不回滚用户已选的模型，避免界面显示与后端实际不一致。
  只补其中一两处，症状会从“切不过去”变成“看着切过去了但实际没切”，比原故障更难判断。
- **这三处都是 `local:` 补丁，升级后会整体失效**：按发布版本升级会把检出切到游离 HEAD，补丁留在本地分支上而运行代码不含它们。症状表现为“修好的问题又回来了”。判定与重放方法见 `references/local-patch-carry-over.md`；排查模型切换类故障时必须先做这一步，否则会在上游原版代码里反复分析已经修过的问题。
- **诊断入口**：`logs/desktop.log` 搜 `revision_conflict`；`logs/errors.log` 搜 `Dropping reasoning item minted by other`（会话中途换模型的直接痕迹）；`grep -o 'provider=[^ ]* base_url=[^ ]* model=[^ ]*' logs/errors.log | sort | uniq -c` 看同一会话是否出现多个组合。
- **网关后台守护进程与桌面窗口生命周期脱节陷阱**：
  关闭并重新打开 Hermes 桌面端（Electron 窗口）仅仅重启了图形前端，后台的 `hermes-gateway` 进程依然常驻运行。任何涉及 Python 源码的改动或插件升级，必须通过 `hermes gateway restart --yes` 显式重启后台网关进程，否则网关内存中始终运行旧代码，会导致“重启桌面端依然无效”的假象。
- **同一后端在配置里出现多个名字会放大“混用”观感**：`providers:` 下大小写不同的两个键（如 `JK-deepseek` 与 `jk-deepseek`）指向同一地址时，日志会把同一个后端分别记成具名 provider 与 `custom`，看起来像在混用不同通道。排查模型混用前先核对 `providers:` 的键名是否有仅大小写不同的重复项。
- **键名一律全小写，显示名靠 `name:` 字段（用户已定）**：`providers` 与 `model_overrides` 两处的键名都写小写，界面想显示大写就写条目内的 `name: JK-deepseek`。模型选择列表的分组标题套了 `text-transform: uppercase`，显示名还可能来自 `_PROVIDER_LABELS` 内置标签表（键名 `llm-gw` 显示为 `LLM Gateway`），所以「界面上都是大写」不能当作「配置里都是大写键」的证据——判断真实键名要调 `build_model_options_payload` 看 `slug`。
- **同一后端被登记两次的另一原因**：`providers.<名>` 里同时写了 `api` 字段时，它会既作为内置 provider 行出现一次，又作为 `custom:<名>` 自定义端点行出现一次。列表里看到两行属于这个原因，与重复键无关。
- **内置行是空骨架，不要当成故障去修**：内置行（`source: canonical`、`models: []`、`authenticated: false`、`warning: paste <KEY> to activate`）是 `_append_unconfigured_rows()` 补的骨架行，只要它没有模型，界面就不会渲染该分组。判定方法：调 `build_model_options_payload` 后看该行的 `models` 与 `source`。想彻底区分两行，把自定义那行的 `name` 改成与内置标签不同的名字（如 `jk-llm-gw`），改名后内置空行不渲染、只剩一行；改名后要重跑 `_supports_vision_override` 确认逐模型能力声明仍生效。
- **内置行的默认地址与配置地址不一致时不会报错**：内置注册（`hermes_cli/models_catalog_static.py` 与 `plugins/model-providers/<名>/`）自带一个 `base_url`，`config.yaml` 里又写了一个。两者不同时，实际请求走配置那一个（或 `.env` 的 `<NAME>_BASE_URL` 覆盖），内置行则因找不到匹配的凭证而一直显示未认证。排查端口类问题时用 `resolve_runtime_provider` 看实际地址，不要只看任一处的文本。

### 通道身份核验（配置写的模型名 vs 后端实际服务的模型）

自建推理服务（SGLang 系）的 `model` 请求参数可能被整个忽略，只跑它加载的那一个模型。
用户报「某通道下显示的是别的模型」时，按下面三步取证，不要读配置就下结论。

**第一步：问后端自己。** 三个只读端点直接给出答案（均需带 `Authorization: Bearer <key>`）：

| 端点 | 关键字段 | 说明 |
| :--- | :--- | :--- |
| `/get_server_info` | `served_model_name`、`context_length`、`tp_size`、`dp_size` | 进程启动参数 |
| `/get_model_info` | `served_model_name`、`model_type`、`architectures`、`has_image_understanding` | 权重类型与多模态能力 |
| `/metrics` | `model_name="..."` 标签 | **进程自己打的标签，不受请求参数影响，证据最硬** |
| `/v1/models` | `data[].id` | 对外声称的模型清单 |

**第二步：多模型名对照实验。** 用几个不同的模型名（务必包含一个虚构的名字）向同一端点问同一个问题（`temperature: 0`）：

- 回答字节完全相同 → 后端只跑一个模型，`model` 参数无效；
- 回答不同 → 后端确实按 `model` 路由，继续查该名字是否在 `/v1/models` 里。

**第三步：交叉核对其他客户端配置。** 同一地址可能被别的工具共用（例如 dsh 的 `cordis.patch.yml` 里
`baseURL` 与 `models[].id` 成对出现）。这类交叉引用常是用户记忆里「这个地址是 A 模型」的来源，
也可能已经过期。找到就一并报出，不要只报 Hermes 这一侧。

**跨客户端联动的具体位置（本机 dsh）**：

| 内容 | 路径 | 字段 |
| :--- | :--- | :--- |
| 通道与模型 | `~/.dsh/profiles/<档>/cordis.patch.yml` | `llm-pi-ai` 插件下 `providers.<名>.baseURL` 与 `models[].id`／`name` |
| 密钥 | `~/.dsh/.credentials.yaml` | `refs.<KEY_ENV>` |

改 Hermes 侧通道名或模型名时，按上表逐项核对。**先比密钥指纹再决定要不要动密钥**：
两边密钥相同（`sha256` 前 12 位一致）时，dsh 侧只需改模型名，密钥不用动；不同则说明是两条独立凭据，
不要顺手改写。

**`cordis.patch.yml` 用标准 `yaml.safe_load` 读不了**：文件里有 `!js` 自定义标签，
`yaml.safe_load` 报 `could not determine a constructor for the tag 'tag:yaml.org,2002:js'`。
这是文件原有写法，不是改坏的——拿备份文件试同样报错即可确认。要验证结构就注册一个多构造器：

```python
import yaml
class L(yaml.SafeLoader): pass
L.add_multi_constructor('tag:yaml.org,2002:js', lambda loader, suffix, node: None)
d = yaml.load(open(path, encoding='utf-8'), Loader=L)
```

多构造器的回调签名是 `(loader, tag_suffix, node)` 三个参数，写成两个会报 `takes 2 positional arguments but 3 were given`。
dsh 自己用专门的加载器读该文件，不受影响，不要因为标准解析器报错就判定文件损坏。

**该文件是 LF 行尾**，与 Hermes 的 `config.yaml`（CRLF）相反。改它时不要照搬 Hermes 侧的二进制读写模板，
但同样要先 `cp` 备份、改后核对行尾计数与原文一致。

**汇报口径**：先给实测结论（后端实际服务哪个模型），再给配置写的名字，最后说明两者是否一致。
配置与后端冲突时，模型被换掉属于部署问题，改 Hermes 配置解决不了，必须请用户确认服务器端本该跑什么。

### 输出上限（单次最大生成）的唯一受支持入口是 `extra_body`

`model.max_tokens` 与 `HERMES_MAX_TOKENS` 已被官方按设计移除（见仓库 `evals/output_caps_scope.md`），
具名／自定义 provider 的顶层 `max_output_tokens` 字段同样移除。`hermes config set model.max_tokens 65536`
会**正常返回成功并写入文件**，但运行时没有任何代码读取该键——只凭命令回显判定已生效是误报。

正确写法（`extra_body` 作为通用协议原样转交机制被保留）：

```yaml
providers:
  jk-deepseek:
    extra_body:
      max_output_tokens: 65536     # Responses API 的字段名
```

生效链路：`extra_body` → `_custom_provider_request_overrides()` 包成 `request_overrides.extra_body`
→ 传输层 `kwargs.update(request_overrides)` 并入请求体。写入后可用该函数核对解析结果，
再发一次带 `max_output_tokens=65536` 的真实请求确认后端接受。

### 上下文长度缓存按“模型名@地址”精确匹配

`$HERMES_HOME/context_length_cache.yaml` 的键是 `模型名@base_url` 全串。后端换 IP、换端口后旧键永不命中，
Hermes 每轮现场探测，超时（日志 `context-length probe for '<模型>' at <地址> exceeded 5.0s — returning unknown`）
直接拖慢桌面端模型信息查询。排查时把缓存键与 `model.base_url`、各 `providers.<名>.api` 逐条对拍。

### 自建 provider 的模型能力声明（让界面出现推理挡位）

``ProviderProfile.model_capabilities``（键空间与 ``model_overrides`` 一致：``context_window`` /
``supports_tools`` / ``supports_vision`` / ``supports_reasoning`` / ``model_family``）由
``agent/models_dev.py::_provider_model_capabilities()`` 读取，是 picker 徽章、图像路由、上下文长度与
``/api/model/info`` 共享的唯一插件接缝。自建 provider 不在 models.dev 的 provider 映射里，
``get_model_capabilities()`` 返回 None；而 WebUI 聊天侧栏的推理挡位控件（``web/src/components/ReasoningPicker.tsx``，
挂在 ``ChatSidebar``）仅由 ``/api/model/info`` 的 ``capabilities.supports_reasoning`` 门控，因此不声明就看不到控件。
声明后实测：``/api/model/info`` → ``capabilities.supports_reasoning: true``、``effective_context_length: 1048576``。

### User-defined model aliases

Work with `/model <name>` in CLI and every gateway platform. Resolved by
`hermes_cli/model_switch.py::resolve_alias()`; user aliases are checked BEFORE
the built-in table, so a user `sonnet`/`grok` shadows the built-in.

### GitHub / Copilot 别名与嗅探隔离（关键踩坑防线与服务状态）

1. **服务存活性事实**：历史上的公共 GitHub Models 预览端点（`models.inference.ai.azure.com` 与 `models.github.ai`）已于 2026 年 7 月 30 日全网正式退役（DNS 返回 NXDOMAIN 或纯文本桩）。切勿将该已失效的端点作为可用免费通道进行配置或推荐。
2. **别名覆盖陷阱**：`hermes_cli/auth.py` 中硬编码了 `\"github\": \"copilot\", \"github-models\": \"copilot\"`。
   - **表现**：如果提供商名称命名为 `github-models` 或以 `github` 开头，系统会自动将其重写为商业付费的 `copilot` 服务商，桌面端模型下拉菜单会自动展示 Copilot 的商业模型矩阵（GPT-5.4, GPT-5.3-codex 等），并在无 Copilot 商业订阅时调用失败。
   - **规则**：自建或外部提供商名称必须避开 `github` 与 `copilot` 前缀，使用如 `azure-ai-models`。
3. **环境变量嗅探陷阱**：`hermes_cli/copilot_auth.py` 会自动扫描 `GITHUB_TOKEN` 和 `GH_TOKEN` 作为 Copilot 商业凭据。
   - **表现**：只要在 `.env` 或系统环境变量中注入了 `GITHUB_TOKEN`，系统会判定检测到了 Copilot 登录并自动在界面渲染 `GITHUB COPILOT` 菜单。
   - **规则**：任何第三方或自建服务的密钥环境变量名必须完全独立分开（如 `AZURE_AI_KEY`），严禁使用 `GITHUB_TOKEN` 或 `GH_TOKEN`。
4. **误配后的残留清理**：若此前曾误将服务商设为 `github-models` 或写入了 `GITHUB_TOKEN`，系统已在 `%LOCALAPPDATA%/hermes/provider_models_cache.json` 中生成了 `copilot` 缓存。仅修改 `config.yaml` 无法清除前端下拉框的残留，必须删除该 JSON 中的 `\"copilot\"` 节点或清空该缓存文件，并在桌面端按 `Ctrl + R` 刷新生效。
5. **严禁未测试断定可用与模型入库门禁**：
   - 无论自建反代还是外部端点，向 `providers.<name>.models` 添加新模型前，必须先走真实生产网络请求完成全链路推理实测（获得 HTTP 200 且返回有效输出文本），未通过实测严禁写入 `config.yaml`。
   - 切勿信任反代管理后台前端的静态展示：部分管理界面（如 EasyCLIProxyAPI）前端会在配额显示中硬编码拼接静态模型名（如 Gemini 分组固定拼接 `Gemini Argon`），这并非后端真实授权。真实可用性必须以接口实际返回和上游凭据有效性为准。
   - 未经验证的模型一旦写入配置并在客户端被选定，会在首包阶段触发服务端拒绝，导致用户对话轮次中断报错。

```yaml
# Full form
model_aliases:
  fav:
    model: claude-sonnet-4.6
    provider: anthropic
  local-qwen:
    model: qwen3.5:397b
    provider: custom
    base_url: \"https://ollama.com/v1\"
  theta:
    model: theta-1
    provider: custom
    base_url: \"https://theta.example.com/v1\"
    key_env: THETA_API_KEY        # or: api_key: \"${THETA_API_KEY}\"

# Short form (\"provider/model\"), also via CLI:
#   hermes config set model.aliases.fav openrouter/anthropic/claude-sonnet-4.6
model:
  aliases:
    fav: openrouter/anthropic/claude-sonnet-4.6
```

`/model fav` — session-scoped; add `--global` to persist as default.
