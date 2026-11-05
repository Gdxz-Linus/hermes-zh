# Hermes web 检索后端（搜索 / 抓取）

## 一、机制

后端全部是随发行版附带的插件，位于 `hermes-agent/plugins/web/<vendor>/`（`plugin.yaml` 以 `kind: backend` + `provides_web_providers` 声明，`provider.py` 实现）。启动时经 `ctx.register_web_search_provider()` 注册进 `agent/web_search_registry.py`。用户自定义插件放 `$HERMES_HOME/plugins/`（本机只有 `model-providers/`，无 web 插件）。

注册之外还有一条不走 provider 的免密钥通道：`plugins/web/keyless_mcp.py` 直连各家的公开 MCP 端点。

能力两类：`web_search`（搜索，对应 `web_search` 工具）、`web_extract`（正文抓取，对应 `web_extract` 工具）。

## 二、清单（本机实测枚举，11 个）

| name | 搜索 | 抓取 | 免密钥层 | 密钥/地址变量 | 说明 |
|---|---|---|---|---|---|
| brave-free | ✓ | | | `BRAVE_SEARCH_API_KEY` | 免费层 2k 次/月 |
| ddgs | ✓ | | | 无 | 需 `pip install ddgs`；唯一以包装与否为可用条件的后端 |
| exa | ✓ | ✓ | ✓ | `EXA_API_KEY` | 免密钥走 `mcp.exa.ai/mcp` |
| firecrawl | ✓ | ✓ | ✓ | `FIRECRAWL_API_KEY` | 免密钥可用；Nous 订阅的托管路由也落在这里 |
| keenable | ✓ | ✓ | ✓ | `KEENABLE_API_KEY` | 免费层在默认轮换内 |
| openai-native | ✓ | | | 需 openai-codex 登录 | 不自己搜索，声明 Responses 的服务端 `web_search` 内置项 |
| parallel | ✓ | ✓ | ✓ | `PARALLEL_API_KEY` | 免密钥走 `search.parallel.ai/mcp` |
| perplexity | ✓ | ✓ | | `PERPLEXITY_API_KEY` | 托管 Nous 路由的搜索侧由它承担 |
| searxng | ✓ | | | `SEARXNG_URL` | 自建实例 |
| tavily | ✓ | ✓ | ✓ | `TAVILY_API_KEY` | |
| xai | ✓ | | | xAI 登录或 `XAI_API_KEY` | 走 Grok 的服务端 `web_search` |

### 枚举命令（只读）

`R.list_providers()` 返回的对象上，`supports_search` / `supports_extract` / `is_keyless_available` / `is_available` 是**方法**（`getattr` 直接打印会显示 bound method），且部分实现不保证有 `KEY_ENV` 属性；必须逐个调用并 `getattr(p, 'KEY_ENV', '')`。解释器用 `installs/*/environments/*/venv/Scripts/python.exe`（见 SKILL.md 第十二节第 6 条）。

```python
import hermes_cli.plugins as P; P.discover_plugins()
import agent.web_search_registry as R
for p in R.list_providers():
    print(p.name, p.supports_search(), p.supports_extract(),
          p.is_keyless_available(), p.is_available(), getattr(p, 'KEY_ENV', ''))
```

## 三、选择阶梯（`agent/web_search_registry.py :: _resolve`）

能力过滤（`supports_search` / `supports_extract`）在每一级都生效，所以只支持搜索的后端被配成 `web.extract_backend` 会继续往下走。

1. `web.search_backend` / `web.extract_backend`，其次共享键 `web.backend`。
2. 唯一一个“已注册且可用”的合格后端。
3. 历史偏好序 `_LEGACY_PREFERENCE`：firecrawl → parallel → tavily → perplexity → exa → searxng → brave-free → ddgs。
4. 免密钥轮换环 `_KEYLESS_PREFERENCE`：exa → parallel → firecrawl → keenable。
5. 都没有则返回 None，工具提示用户去 `hermes tools`。

两条容易读错的语义：

- **显式配置不降级**：`_resolve` 里 `configured` 命中的 provider 不经 `is_available()` 过滤，直接返回 —— 故意选了一个缺密钥的后端，得到的是“缺 `X_API_KEY`”的精确报错，而不是静默换家（`tools/web_tools.py :: _get_backend` 同口径：存过的值一律原样返回，无探测无回退）。
- **免密钥是末位而不是兜底**：第 4 级只在第 3 级全不可用时进入，不会抢占任何已配好的付费后端；关闭用 `web.keyless_fallback: false`。

### 免密钥轮换环的行为

`plugins/web/keyless_mcp.py :: _KEYLESS_RING` 是固定的四家，`_ring_cursor = int(_SESSION_ID, 16) % 4` —— **每个进程一个随机起点**，之后按请求在环上轮转。所以同一会话里连续两次搜索可能落到不同厂商，结果排序不稳定；跨会话比较后端名称时先确认进程是否同一个。

免费层限流在错误信息里以 `rate limit` / `429` / `quota exceeded` 等标记出现（`_RATE_LIMIT_MARKERS`），返回的文案会带“Set <ENV_KEY> (<站点>) for reliable service”。

## 四、本机落点（实测）

`config.yaml` 无 `web:` 段，`.env` 中除 `GOOGLE_API_KEY`、`LLM_GW_*` 外无任何 web 密钥，`ddgs` 未安装 ⇒ 落到第 4 级免密钥环。日志实证：

```
tools.web_tools: Web search via firecrawl: '<query>' (limit: 3)
plugins.web.firecrawl.provider: Firecrawl keyless search: '<query>' (limit=10)
plugins.web.exa.provider: Exa keyless extract: 1 URL(s)
```

判定方式固定为读日志，不从配置推断（配置在无 `web:` 段时也能工作）：
`grep -E "Web search via|keyless (search|extract)" "$HERMES_HOME/logs/agent.log" | tail`。

端点可达性实测（GET 裸请求）：`mcp.exa.ai`、`search.parallel.ai` 返回 405（MCP 端点不接受 GET，属正常）；`api.firecrawl.dev`、`api.tavily.com`、`searx.be` 返回 200；`api.keenable.ai`、`api.perplexity.ai` 返回 404（根路径无内容，不代表服务不可用）。

## 五、要固定后端或提升限额

两种方式，等效：配置写入 `web.search_backend` / `web.extract_backend`（或共享的 `web.backend`），或用 `hermes tools` 交互选择；随后在 `.env` 填对应密钥。固定前先读第三节的“显式配置不降级”语义 —— 名字写错或缺密钥会直接失败，不会退回免费层。

## 六、引擎层面的归属（用户问「支持哪些搜索引擎」时的答案层级）

第十一节之前那张表是**厂商/后端**，不是搜索引擎。用户问「搜索引擎」时必须给底层引擎名。实测归属如下：

- **真正对上传统搜索引擎的只有两个后端**：`ddgs`（经 DuckDuckGo，内部再轮换到具体引擎）与 `brave-free`（直连 `api.search.brave.com/res/v1/web/search`，Brave 自建索引）；`searxng` 是元搜索，引擎由实例决定。
- **其余后端都不是传统搜索引擎**，是各自厂商的检索 API／自建索引：exa（神经语义检索）、parallel（按目标调优）、firecrawl、keenable、tavily、perplexity（Search API）、xai（Grok 的 agentic 检索）、openai-native（服务端执行）。回答时不要把这些厂商名当引擎名列出。

### ddgs 的引擎集合（实测，解包 9.16.0 读注册表）

`ddgs/engines/*.py` 里每个引擎类带 `name` / `category` 类属性，`engines/__init__.py` 按此自动构建 `ENGINES`：

- `text`：bing、brave、duckduckgo、google、mojeek、yahoo、yandex、wikipedia（另有 startpage、grokipedia 文件但不在默认注册表）。
- `images` / `news` / `videos`：只有 duckduckgo。
- **无百度、搜狗、360、夸克**。
- **Hermes 的 ddgs 插件无法指定引擎**：`plugins/web/ddgs/provider.py` 只调 `client.text(query, max_results=...)`，不传 `backend`/`region` 参数，故引擎选择完全在包内部。

查证命令（只读，不装进运行环境）：`uv pip install ddgs==<ver> --target <scratch>/ddgspkg --no-deps`，再读 `<scratch>/ddgspkg/ddgs/engines/`。`uv pip` 没有 `download` 子命令，只能 `install --target`。

### 国内引擎：插件层无接入，三条可选路径

- 全仓检索 `baidu|sogou|so\.com|360search|quark|toutiao|cn\.bing\.com|yandex`（范围 `plugins/web/`、`tools/web_tools*.py`、`agent/web_search_registry.py`）命中为零；11 个后端全是境外服务。
- SearXNG 上游 `searx/settings.yml` 确实带这些引擎，但**默认全部 `disabled: true`**：`baidu` / `baidu images` / `baidu kaifa`、`sogou` / `sogou images` / `sogou videos` / `sogou wechat`、`360search` / `360search videos`、`quark` / `quark images`、`bilibili`；`bing` 系列另行注明 `base_url: https://cn.bing.com  # for instances hosted in China`。自建实例后改这几行即可启用。
- **Hermes 的 searxng 插件不指定引擎**：`plugins/web/searxng/provider.py` 只发 `q` / `format` / `pageno` 三个参数，所以走不走百度由实例的 `settings.yml` 决定，Hermes 侧不感知也不可配。
- 网络侧不是障碍：实测 `www.baidu.com`、`www.sogou.com`、`www.so.com`、`cn.bing.com` 均 HTTP 200 可达。结论是「Hermes 侧没有接入」，不是「连不上」。
- 自写 web 搜索插件（`kind: backend` + `provides_web_providers`，见 `hermes-agent/website/docs/developer-guide/web-search-provider-plugin.md`），本机 `$HERMES_HOME/plugins/model-providers/` 已有自建 provider 插件的先例可参照。
- **第四类路径：接入自带国内引擎的检索 MCP 服务器**，不经过 web 插件层，而是以 MCP 工具供模型调用（接线步骤见 `hermes-mcp-server-integration`）。实测 `free-search-mcp` 的 `engines()` 给出 `so360`（360 搜索，直出目标 URL）、`baidu`（百度）、`sogou`（搜狗，返回 `sogou.com/link?url=…` 重定向 URL）、`zhihu`（知乎，常被登录墙拦）、`bilibili`；其中 `baidu` / `brave` / `startpage` / `zhihu` 走浏览器渲染，需 `playwright install chromium`，未装则这几个引擎报错、其余不受影响。该服务器的搜索路由会自动把中文查询带上 `so360`，也可用 `engines=[...]` 显式指定。判断某次搜索落到哪些引擎，读结果头部的 `_engines:` 行，不靠猜。

## 七、与其它通路的分工

搜索/抓取后端负责公开可达的页面。页面被 WAF、支付墙、登录墙拦住（403/429、Cloudflare 拦截页）时改走浏览器工具，顺序见 `blocked-page-recovery`。用户直接给出 URL 时优先 `web_extract`，不经搜索引擎。
