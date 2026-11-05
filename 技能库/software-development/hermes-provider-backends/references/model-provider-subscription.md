# 模型提供者插件：订阅渠道接入（Antigravity 实测）

模型提供者（model-provider）是第四种插件族：替换 Hermes 的推理引擎（脑子），工具执行、审批、防线仍由 Hermes 承担。与 web/记忆/MCP 三族并列，发现机制也不同（`plugins/model-providers/`，首次 `get_provider_profile()` 时懒加载）。

## 一、订阅渠道的核心机制

Google AI Pro/Ultra 会员的模型权益**不延伸到 API**（官方明文：订阅权益仅在 Google 自家界面内），但可以通过官方 `agy` CLI 把订阅配额接入 Hermes——社区有三个插件做这件事，架构统一：

- **agy 只出推理，Hermes 执行所有工具**：agy 以 headless 模式运行，其内置工具被移除或封锁，每次工具调用交回 Hermes（走自己的审批与沙箱）。
- **凭据归 agy**：登录在 agy 内完成一次，插件永不读取/复制凭据文件（部分实现把 token 文件 symlink 进一次性私有 HOME，用完即删）。

## 二、三个插件横向对比（2026-10 实测口径）

| | antigravity-oauth（★69） | antigravity-subscription-directsdk（★17，MIT） | antigravity-agy（★0） |
|---|---|---|---|
| Windows | ✓ | ✓ | ✗（仅 Linux/macOS） |
| agy 内置工具处理 | 转译为对应 Hermes 工具（run_command→terminal 等），未映射的封锁 | 文本 tag 解析；agy 尝试原生工具时杀进程 | 从模型侧移除（自定义 agent），MCP 原生函数调用 |
| 独有功能 | 把 Hermes SOUL.md 写入 agy 工作区 GEMINI.md（语言规范跟着脑子走）＋npx 安装器 | 流式、多轮对话持久化（239k）、工具输出裁剪（长会话 70% 减载）、错误分类（billing/context_overflow/auth） | 失败关闭最严格、预热线程（跳过 agy ~5.5s 启动） |
| 附加依赖 | 无 | 无 | 无 |

选型：Windows 上首选 **antigravity-oauth**（验证最多＋SOUL 传递）；要配额可视化再叠 **antigravity-oauth-plus**（★0，/usage 显示 5 小时/周双窗口余量，只读不烧配额，与 oauth 共存不冲突）。

**oauth 与 plus 的模型目录机制差异（常被误解）**：oauth 的模型列表继承官方 agy CLI（Google 上新模型 agy 先支持，oauth 跟随），并非「固定目录」；plus 是自建解析器＋目录缓存，理论上「实时发现账号可用模型」，代价是多一层自有解析器可能落后于 agy 格式变化（其 README 原话：保守解析器拒绝未来 CLI 格式时是刷新失败而非空目录）。两者都不是硬编码目录——选型差异在验证成熟度与配额可视化，不在模型目录宽度。

**Gemini 应用渠道的最终性价比修正**：Gemini 应用（cookie 反代可达）对 AI Pro 开放 3.1 Pro 与 4 Argon，但额度是共享算力池且与手动使用互抢（5 小时窗口强模型只够几次）；AI Studio Playground 分池独立但日限波动（10-20 次且曾缩水到 5-6 次）；**最稳定的疑难通道是 API＋每月 $10 抵扣金**（数百次 3.1 Pro 问答，不受网页风控波动）。三选一按「额度确定性 > 模型宽度」排序。

## 三、订阅分渠道权益（决定哪些模型实际可用）

会员模型权益**按渠道分**，同一套餐在不同渠道能用的模型不同。以 Google AI Pro（含 Jio 等促销渠道）为例，官方模型表（antigravity.google/docs/models）口径：

| 模型 | Gemini 应用 | Antigravity（Hermes 插件走的渠道） |
|---|---|---|
| Gemini 3.8 Flash 系 | ✓ | ✓（完整权益，促销渠道 18 个月不变） |
| Gemini 3.1 Pro | ✓ | ✗（Enterprise-only） |
| Gemini 4 Argon | ✓ | ✗（Ultra-only） |
| Claude 4.6 系 | — | ✓ 但有退役日期（第三方模型授权收紧，促销渠道不含 5.5） |

**Jio/促销渠道附加限制**：归为 promotional tier，第三方前沿模型（Claude 5.5 等）不含；第一方 Gemini 模型权益完整。3.1 Pro 级疑难任务的免费消耗点在 **Gemini 应用/AI Studio 网页**（AI Pro 含，约每日 20 次）——不在 Antigravity 渠道。

**API 侧唯一合法免费通道**：AI Pro 内置每月 $10 Cloud 抵扣金（Developer Program premium 已并入 AI Pro），绑定 Billing 账户后 Gemini API 调用优先扣它。Prepay 账户需先存最小预付金，需手机＋两步验证。

## 四、接入流程（以本地 OpenAI 兼容反代为例，实测）

easycli 类反代（本地 `http://127.0.0.1:8317/v1`，OpenAI 兼容）接入步骤：

1. **探活**：`curl /v1/models` 拿模型清单（注意 MSYS curl 发中文会乱码——用 Python urllib 测对话，不是反代的问题）。

   **对话探活用 Python，不用 curl**，两个环境陷阱都会造成假阴性：
   - MSYS 下 `curl -d '{"...中文..."}'` 的请求体在传到后端时已被转成非法 UTF-8，SGLang 回 `str is not valid UTF-8: surrogates not allowed`，看着像模型坏了；
   - `curl --data-binary @<路径>` 在路径含中文时报 `error encountered when reading a file`（工作目录名是中文时必现）。

   正确做法：`urllib.request.build_opener(urllib.request.ProxyHandler({}))` 显式直连（不带 `ProxyHandler({})` 时读注册表代理，“直连测试”测的其实是代理路径），请求体用 `json.dumps(...).encode()` 发 bytes。探活必须带 `"stream": true`，与 Hermes 生产路径一致。
2. **配 provider**：`hermes config set providers.<名>.api <端点>`＋`.key_env <变量名>`＋`.name <名>`；密钥写 `.env`（`<变量名>=<值>`），不进 config.yaml。
3. **重启网关**：`hermes gateway restart`（直连 spawn 即可）。
4. **全链路验证**：`hermes chat -q "..." --provider <名> --model <模型>`，回复入 state.db 后查 messages 表确认内容（chat 输出只有统计行）。
5. **多模态**：反代透传 vision（image_url data URL）实测可用；把 `auxiliary.vision.provider/model` 指向该 provider，图像理解任务即走订阅配额。auxiliary 节只填 provider/model 时 base_url/api_key 留空，靠 provider 引用解析。
6. **模型选择器收敛到单模型**：给 `providers.<名>.models` 设白名单（如 `["gemini-3.8-flash-high"]`）**必须同时设 `discover_models: false`**——默认 true 时选择器实时探测端点 `/v1/models` 并覆盖白名单，白名单形同虚设（两个开关语义见 `model_setup_flows_custom.py`：白名单只在非 discover 模式下作为唯一目录）。生效验证用构建选择器数据源的同一函数：`build_model_options_payload(load_picker_context())` 查目标 provider 行的 `models` 与 `total_models`。

## 五、协议选型：codex_responses 就是标准 Responses API 传输

部分反代同时支持 `/v1/chat/completions` 与 `/v1/responses`（实测 8317 两个都 200）。Hermes 本版传输注册表有 chat_completions / codex_responses / anthropic_messages / bedrock_converse（`registered_api_modes()` 可查）——**`codex_responses` 就是标准 OpenAI Responses API 的传输实现，不是 Codex 官方后端专用**；名字里的 codex 是历史来源，对任何支持 `/v1/responses` 的端点（含本地反代）都可配可用。已在本机反代上实测：文本＋多模态（vision）在 codex_responses 模式下全通过。**用户要求用 Responses 时直接配 `api_mode: codex_responses` 并做全链路验证，不要凭模式名字推断不适用**（曾犯：未测先断言 codex_responses 是 Codex 专用）。推理挡位经 Responses 协议的 `reasoning.effort` 参数传输，反代四挡（none/low/medium/high）实测全 200；挡位实际生效可用 usage 里的 `reasoning_tokens` 差值验证（high 挡实测产生约 1853 推理 token，low 档 0）。

已知映射噪音：本地反代（easycli 类）会把请求的 `gemini-3.8-flash-high` 回显为响应模型 `gemini-3.8-flash-n`，部分控制台会标注「模型不一致」——这是反代侧命名映射的显示噪音，非模型降级；发非 `-high` 后缀的变体名会 HTTP 400（反代只注册了 high 变体）。验证模型身份以反代 `/v1/models` 实际清单为准。

## 六、模型上限由渠道决定：换渠道突破 3.8 Flash（反代选型）

Antigravity 渠道（agy/easycli 系反代走的路）对 AI Pro 只给 3.8 Flash 系；**3.1 Pro 的免费自动化通道是 AI Studio 网页**——而 AI Studio 分 Playground 与 Build 两个子渠道，2026-09 起 Build 被上游锁定为 Flash-only（无开关无绕过），**Playground 仍含 3.1 Pro**。选反代项目时「走哪个子渠道」是决定性字段：

| 项目 | Stars | 子渠道 | 结果 |
|---|---|---|---|
| **AIStudio2API**（Mag1cFall） | ★262，活跃 | **Playground＋Build 双通道**，额度独立互补，一个触发限额自动切另一个 | **拿到 3.1 Pro**；四协议（OpenAI/Responses/Anthropic/Gemini）；Go 单二进制 Windows 一键 start.bat |
| AIstudioProxyAPI（CJackHwang） | ★2.5k（最高） | 仅 Playground（Chat 界面） | 也能拿 3.1 Pro；但更新频率低、无 headless、Python+Poetry 栈更重 |
| AIStudioToAPI（iBUHub） | ★1.8k | 仅 Build | **拿不到 3.1 Pro**（Build 锁 Flash）——装前先核对该项目走哪个子渠道 |

选型规则：**先查项目的上游子渠道（Playground 还是 Build），再比较其他指标**——子渠道选错，star 数和工程质量都无意义。AIStudio2API 的模型目录实时跟随 AI Studio（`/v1/models` 读当前值），含 `gemini-3.1-pro-preview`（1M 输入/64K 输出）；部署为本地服务后按本文件第四节同一流程接入（端点形如 `http://127.0.0.1:2048`）。

**扩大搜索的另一族：Gemini 应用网页反代（反代目标不同，覆盖面更广）**——反代目标不是 AI Studio 而是 gemini.google.com 网页协议，代表项目 `gemini-web2api-go`（zexadev，★600，MIT，Go 单二进制，10 月仍在活跃发版）。挂付费账号 cookie 后可用模型是所有方案里最全的：gemini-3.1-pro（带思考链）、**gemini-4-argon**（其余方案全部拿不到——Argon 在 AI Studio/Antigravity 渠道对 AI Pro 均不开放，只在 Gemini 应用开放）、3.8-flash（含 -thinking）；协议含 /v1/chat/completions 与 /v1/responses（与 Hermes codex_responses 模式直接匹配）；工程面：Chrome TLS 指纹、cookie 池自动续期、代理池、中文管理面板、SQLite 持久化。

**两族的反向约束是额度结构**：Gemini 应用渠道是共享算力池（2026-05 起，按复杂度动态计，5 小时刷新＋周上限，AI Pro=4x 免费档，强模型每窗口只够几次重提问，与手动使用互抢）；AI Studio 是按模型分池（2026-09 起，每模型独立日限，Pro 档实测 3.1 Pro 约 10-20 次/天、3.8 Flash 约 20-30 次）。**自动化 agent 场景下按模型分池优于共享池**——3.1 Pro 限额烧完不殃及 Flash，反代高频调用也不与手动使用互抢。故：要 Argon 或一次性强推理选 Gemini 应用反代；要稳定可预期的疑难通道选 AI Studio 反代（AIStudio2API）；两者都部署时额度互不干扰。

**部署实录（AIStudio2API Windows，实测）**：下载 `windows-amd64.zip` 解压 → 复制 `.env.example` 为 `.env` → `start.bat` 首启会自动下载 Camoufox（路径可用 `CAMOUFOX_PATH` 指定）→ 管理面板 `http://127.0.0.1:2048` 完成账号登录。管理 API：`/api/status`（服务状态与账户 tier）、`/api/accounts`（账户明细含 `benefit_tier`）、`POST /api/control/start|stop`（生成服务启停——`.env` 改动后必须杀主进程重启才读新值，`control/stop` 只停生成服务）、`GET /v1/models`（模型目录；**空目录 = worker 未启动或同步失败**，先看 `/api/status` 的 state 再看日志）。**Go 程序不走系统代理**：直连 Google 失败（`no such host` / `connectex` 超时）时在 `.env` 写 `PROXY=http://<代理>` 并重启主进程；要自动跟随系统代理（注册表 ProxyEnable/ProxyServer），用 wrapper bat 启动前动态读注册表设置 `PROXY`/`HTTP(S)_PROXY` 环境变量（进程环境优先于 .env），模板见本机 `D:\\\\Nettools\\\\aistudio2api\\\\start-auto-proxy.bat`（纯 ASCII，reg query 动态提取）。代理生效后模型目录同步成功（实测 46 个模型，含 gemini-3.1-pro-preview 与 gemini-4-argon），3.1 Pro 全链路调用验证通过。注意：双击 `start.bat` 启动的进程没有代理环境变量——需代理的部署必须在 `.env` 里固化 PROXY，或用自动跟随 wrapper，或从已设代理环境的终端启动。

如实的边界：论坛有 AI Pro 用户反馈 AI Studio 网页的 3.1 Pro 日限额波动（低至每日 5-6 次），Google 会动态收紧——此通道定位为疑难任务备用，日常仍走 Antigravity 渠道 3.8 Flash。浏览器自动化方案固有风险：AI Studio 改版即失效需等项目更新、Google 风控可能要求重新验证。

**额度对比（选渠道的第二决定因素，模型清单之外必查）**：两大网页渠道计量机制不同——Gemini 应用是算力池（2026-05 起：按提示复杂度/模型档位/功能动态计，5 小时刷新＋周上限，AI Pro=4x 免费档，超限降级到小模型），强模型每窗口只够数次重提问，且与手动使用共享池；AI Studio 是按模型分池（2026-09 起：每模型独立日限，Pro 档实测 3.1 Pro 约 10-20 次/天、3.8 Flash 约 20-30 次，换模型可继续）。对自动化 agent 场景：**按模型分池 > 共享算力池**——分池意味着 3.1 Pro 限额烧完不殃及 Flash，且反代高频调用不与手动使用互抢。部署反代后若发现账号被判为 Free tier（账户页 `benefit_tier` 字段），先查订阅渠道性质（促销/合作渠道在某些工具侧的 tier 判定可能不准），再查代理是否生效——模型目录同步失败的报错（`no such host` / `connectex` 超时）十有八九是 Go 程序不走系统代理：在项目 `.env` 写 `PROXY=http://<代理地址>` 并重启进程即愈。

## 七、已知边界

- **Claude 模型大工具集遵从问题**：Claude Sonnet 4.6 在约 40 个工具下会拒绝或改用 agy 原生工具导致回合失败（10 个以内正常）——模型行为，插件侧已尽力。
- **插件自带文本处理的必须验证运行时行为**：曾有语言包插件（hermes-zh）除 locales 外还带运行时文本拦截，低质量转换污染回复；卸载后体验变好。引入任何可能触碰回复内容的插件前，实测确认其 hook 是否作用于回复文本——不能只信目录页描述。防线（SOUL＋guard 插件）每层要求行为完全可知。
- **语言防线对所有 provider 生效**：SOUL 语言规范与 zh-jargon-guard 拦截层不绑定特定 provider，切换推理引擎（glm/Gemini/Claude）后防线照常工作；换更强模型是提升中文质量的第一手段，防线是保底。

## 八、第三方模型提供者真实边界与陷阱（实测证据）

1. **反代控制台“虚假显示”陷阱与模型准入铁律（实测证据）**：
   - 虚假显示根因：部分反代控制台（如 EasyCLIProxyAPI Web 界面）在前端配额展示层存在硬编码映射（前端脚本中写死 `AO=new Map([['group_gemini_models',['Gemini Argon']]])`），当解析谷歌返回的模型分组时，前端会无条件强行向界面追加显示 `Gemini Argon`；但反代后端从谷歌获取的凭据真实状态仍为 `gemini-4-argon-disabled`（谷歌上游禁用），上游直接拒绝，反代底层路由也未注册该模型。
   - 模型准入铁律（未真实调通绝不写盘）：向 `providers.<名>.models` 新增模型时，**严禁仅凭控制台界面显示或口头指示就直接修改配置**。必须先经由生产相同路径（向 `/v1/responses` 或 `/v1/chat/completions` 发起带有测试提示词的真实 HTTP 请求）进行前置调用核验；只有拿到上游成功吐出的真实内容（HTTP 200 且返回有效文字）后，才允许向 `config.yaml` 写入该模型条目。若调用返回 `unknown provider for model` 或 `HTTP 404 NOT_FOUND`，必须出示确凿错误证据并拒绝写入，杜绝盲目修改配置导致界面不可用。
2. **规则固化层级边界（严禁向 SOUL.md 堆砌局部工具规则）**：
   - 边界原则：工具调度与选型优先级（如“本地 free-search-mcp 主用，内置 web_search 备用”）属于局部执行层策略，**严禁将其写入系统提示正本（SOUL.md）或长久记忆中**，避免造成顶层法典无序膨胀；
   - 正确落点：局部工具调度必须通过**程序层（插件的 `pre_tool_call` 拦截代码）**在底层对工具调用实施物理拦截与分流，由底层代码逻辑负责主备降级，保持系统提示词与记忆库的纯净精简。
3. **GitHub Models 退役事实**：GitHub Models（`models.inference.ai.azure.com` / `models.github.ai`）已于 2026-07-30 被微软与 GitHub 官方正式退役下线。旧域名直接返回 DNS NXDOMAIN 或占位文本 `OK`，不可作为生产或实验模型上游。
2. **Hermes 别名劫持与 Copilot 误报陷阱**：
   - Hermes 核心源码（`hermes_cli/auth.py` 第 1461~1463 行）内置硬编码别名映射：`\"github-models\": \"copilot\"`、`\"github\": \"copilot\"`；同时 `copilot_auth.py` 将环境变量 `GITHUB_TOKEN` 作为 Copilot 凭据来源探测。
   - 陷阱后果：任何命名为 `github-models` 或环境变量设为 `GITHUB_TOKEN` 的配置，会被系统自动劫持并映射为商业付费的 `copilot` 服务商，并在桌面端模型下拉菜单强制渲染出 Copilot 商业模型清单（GPT-5.4、GPT-5.2-codex 等）。因普通 PAT（`ghp_`）无法通过 Copilot 鉴权，该列表会彻底失效并污染界面。
   - 解决规则：配置第三方或反代服务商时，`config.yaml` 内的服务商名称严禁包含 `github` 或 `copilot` 关键字，环境变量严禁命名为 `GITHUB_TOKEN` 或 `GH_TOKEN`，必须采用独立自定义前缀（如 `GH_MODELS_TOKEN`、`free-provider`）。
3. **OpenCode Zen 免费模型门禁机制**：
   - OpenCode 目录中的 `*-free` 免费模型（如 `deepseek-v4.1-flash-free`、`glm-5.3-flash-free`）在官方服务端施加了客户端指纹限制。
   - 门禁表现：通过外部程序以 Service Account API Key（`oc_sk_...`）或免密形式发起原生 HTTP 请求，服务端统一返回 `403 FreeTierError: \"OpenCode's free tier can only be used from within OpenCode\"`；而调用付费模型（如 `deepseek-v4.1-flash`）则要求账户必须有资金余额（`402 Insufficient account funds`）。
   - 可用路径：若需免费使用 OpenCode Zen 的免费模型，不可通过裸 API 直连，必须通过官方 OpenCode CLI 客户端登录后由外部以子代理（ACP / 命令行委托）形式调用。
4. **AI Studio 配额冷却（Cooldown）与动态最新别名规避（实测证据）**：
   - 冷却机制：`aistudio2api`（2048 端口）对 Google 官方预览模型实施了严格的 429 自动熔断（`generate_requests_per_model_per_user` 单日限 10 次，`generate_content_tokens_per_model_per_user` 单日限 1100 万 Token）。超限后软件自动挂起该模型至次日 08:59:59 (PST 00:00)，控制台显示为“冷却”，期间向其发送请求会被直接拒绝。
   - 动态最新别名（Latest Aliases）调度：官方在 2048 端口同时提供了 `gemini-pro-latest` 与 `gemini-flash-latest` 动态别名。经真机调用验证（HTTP 200，支持完整推理思维链与 `/v1/responses` 传输），这两个别名具有独立的配额调度，在固定预览版本（如 `gemini-3.1-pro-preview`）触发冷却挂起时，切换至这两个 `latest` 模型依然能够畅通响应。
5. **短期尝鲜模型的工程规避纪律**：
   - 第三方平台限时提供、仅剩数日生命周期的临时试用版本随时会被官方下线收回，为这类“快闪模型”配置反代或工作流程沉没成本过高，且会引发生产环境中断。
   - 纪律：坚决不依赖短期试用模型构建核心流水线，主力工程开发仅绑定具备长期保障（如 18 个月权益周期）的常态稳定模型（`gemini-3.8-flash-high` 结合 `glm-5.3-flash` 托底）。
