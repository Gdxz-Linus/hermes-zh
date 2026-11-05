# 汉化成果在官方升级时的存活策略

本文件处理一类结构性矛盾：汉化改的是官方源码，而官方升级会覆盖这些源码。目标是在「汉化生效」与「升级不受影响」之间找到代价最小的落点。

## 一、 先分清哪些资产本来就不受升级影响

动手设计任何覆盖方案之前，先确认现有机制已经保护了哪些资产。重复造一层覆盖是常见的浪费。

| 资产 | 存放位置 | 升级时 |
| :--- | :--- | :--- |
| `SOUL.md` | 用户层 `$HERMES_HOME/SOUL.md` | 不动 |
| `config.yaml` | 用户层 `$HERMES_HOME/config.yaml` | 不动 |
| `.env` | 用户层 `$HERMES_HOME/.env` | 不动 |
| 语言包 | 仓库 `locales/` + 用户层 `$HERMES_HOME/locales/` | 仓库版被覆盖，用户层保留 |
| 提示词源码 | 仓库 `agent/*.py` | 被覆盖 |
| 技能 | 用户层 `$HERMES_HOME/skills/` | 改过的保留（哈希比对） |
| 插件 | 用户层 `$HERMES_HOME/plugins/` | 不动（第三方插件自带 Git 仓库） |

判定方法：`git ls-files | grep -E '^SOUL\.md$|^config\.yaml$'`。仓库里没有这两个文件，说明它们只在用户层，升级动不到。仓库里出现的 `SOUL.md` 是模板，与用户层那份内容不同，不要混淆。

### 技能的升级保护是哈希比对，不是「升级不碰」

技能虽在用户层，但仓库 `skills/` 会定期同步过来，不能简单归为「升级不动」。`tools/skills_sync.py` 的规则：

- 新技能：直接复制并记入 `.bundled_manifest`；
- 已有技能：仅当「仓库版变了」且「用户副本仍与清单里的原始哈希一致」才更新；
- 用户改过的（哈希对不上）：跳过，不覆盖；
- 用户删过的：不重新加回来。

所以汉化过的 `SKILL.md` 升级后不会被冲掉，但仓库新增的技能会被补装。判定某技能是否属于「用户已改」：比对它在 `.bundled_manifest` 里记录的哈希与当前文件哈希，不同即已改。

### 技能的加载优先级不是用户层最高

`get_skill_search_roots()` 的顺序：项目技能目录 → 用户层 `$HERMES_HOME/skills/` → 创建目录 → 外部目录。项目内的 `.hermes/skills/` 会盖过用户层同名技能。排查「技能改了不生效」时先确认没有项目级同名技能。

## 二、 语言包已有用户层覆盖，但优先级方向容易搞反

`agent/i18n.py` 的目录加载顺序，优先级从高到低：

1. 插件语言包（`PluginContext.register_locale`，后注册者胜）
2. **用户层 `$HERMES_HOME/locales/<lang>.yaml`**
3. 仓库内 `locales/<lang>.yaml`
4. 同一链条的 `en` 层
5. 裸键

每一层都可以是部分键集合，缺失的键向下回落。

**关键后果：用户层优先级高于仓库层。** 若用户层放的是完整语言包副本，它会把仓库里的新版整体盖住，改仓库版等于白改。

验证方法（比读代码更直接）：

```python
from agent.i18n import t
print(t('gateway.hooks.command_blocked', command='test'))
```

取一个刚在仓库版里改过的键，看返回的是新译法还是旧译法。返回旧译法即证明用户层在覆盖。

**同一进程内改完语言包后必须清缓存再取值**，否则读到的是首次加载时缓存下来的旧字典：

```python
from agent import i18n
i18n.reset_language_cache()
from agent.i18n import t
print(t('gateway.hooks.command_blocked', command='test'))
```

`t()` 按 `(home, lang)` 缓存合并后的字典。不清缓存的话，删掉用户层文件后仍会返回旧值，容易误判成「删除没生效」。

### 正确用法：用户层只放差异

用户层文件应当只保留需要覆盖的少数键，其余全部走仓库版。这样官方更新仓库语言包时新文案能正常生效，自定义改动也不会丢。

**不要把完整语言包复制到用户层当作备份**——那不是备份，是覆盖。

若本地清洗过的译法写在仓库版里，升级后同样会被官方新版盖掉。正确做法是把这些清洗过的键抽出来放进用户层差异文件，仓库版保持官方原样。这样升级拿到官方新文案，本地清洗仍然生效。

### 四个变体必须同步

`zh.yaml`、`zh-hant.yaml`、`zh.tui.yaml`、`zh-hant.tui.yaml` 是四份独立文件，同一句文案各存一份。只改简体版会让繁体版与两个终端版继续输出旧译法。改完对四个文件同时做反向检索。

### 语言包的覆盖边界：只能管界面文案

语言包是一张扁平键值表（约 3486 个键），**只有代码里写了 `t("键")` 的字符串受它控制**。超出这个范围的文本，改语言包一律无效，而且不报错。

| 层面 | 是否受语言包控制 | 实际存放位置 |
| :--- | :--- | :--- |
| 核心界面文案 | 是 | `locales/zh*.yaml`，共 96 个源文件调用 `t()` |
| 核心提示词正文 | 否 | `agent/*.py` 硬编码字符串常量 |
| 技能描述 | 否 | `SKILL.md` 的 YAML 头，由 `parse_frontmatter` 直读 |
| 工具 schema 描述 | 否 | `tools/*.py` 硬编码 |
| 插件描述与工具描述 | 否 | `plugin.yaml` 与插件内 `schemas.py` 直读原文 |

键的分区分布（`zh.yaml`）：`cli` 1543、`gateway` 818、`platform` 418、`tips` 388、`display` 132、`slash` 119、`approval` 38、`explainer` 30。全部集中在命令行、网关与平台适配器。

**判定方法（比读代码快）**：在目标模块里检索 `from agent.i18n import`。命中数为 0 即该模块的文本不受语言包控制。六个提示词模块中只有 `background_review.py` 命中，且仅用于界面显示行（`display.review.*`），提示词正文仍是硬编码。

**推论：调整模型措辞不要改语言包。** 模型输出的语气、行话、翻译腔取决于提示词正文，那在 `agent/*.py` 里。改语言包只能调整按钮、提示条、审批文案这类给人看的文字。

### 五层汉化状态的核查判据

回答「现在某层汉化还在不在」时，逐层用各自判据实测，不要凭印象概括。五层结论可能各不相同，笼统答「都是中文」或「都是英文原版」都会错。

| 层面 | 判据 | 要点 |
| :--- | :--- | :--- |
| 核心提示词 | 中文字符数 + 常量取值 | 统计 `agent/<文件>.py` 的中文字符数；再 `import` 模块取 `DEFAULT_AGENT_IDENTITY` 等常量看是否中文 |
| 工具 | 含中文的文件数 | 遍历 `tools/*.py`，统计中文字符超阈值的文件 |
| 语言包 | `t()` 返回值 | 取一个刚改过的键看返回新译法还是旧译法 |
| 技能 | `SKILL.md` 头的 description 语言 | 遍历用户层 `skills/**/SKILL.md`，检查 frontmatter |
| 插件 | `plugin.yaml` 的 description 语言 | 注意多行 `>` 写法：按行首 `description:` 判断会把中文多行块误判成英文，必须读正文 |

汇报这类状态时必须给出每层的实测数字，不要用「已全部汉化」这类笼统结论代替。

## 三、 提示词源码的三条存活路线

`agent/` 下生成系统提示词的六个文件（`prompt_builder.py`、`system_prompt.py`、`coding_context.py`、`context_compressor.py`、`background_review.py`、`curator.py`）合计约 7.9 万字符。官方升级会整体覆盖，三条可选路线各有硬约束。

### 路线一：插件注册提示词段落（官方接口，容量与位置都不够）

`ctx.register_system_prompt_section(id, content, position=..., max_chars=...)` 是官方给插件的接口。三个硬限制：

| 限制 | 实际值 |
| :--- | :--- |
| 可插入位置 | 只有 `after_memory` 一个（`SYSTEM_PROMPT_SECTION_POSITIONS`） |
| 单段长度上限 | 4000 字符（`MAX_SYSTEM_PROMPT_SECTION_CHARS`） |
| 能否替换已有内容 | 不能，只能追加 |

7.9 万字符远超 4000 上限，且位置固定在记忆之后，无法替换原有英文段落。**这条路无法承载提示词汉化。**

### 路线二：`llm_request` 中间件改写请求（可行但成本转移）

插件可注册 `llm_request` 中间件，在请求发出前拿到完整 `api_kwargs`。调用点在 `agent/turn_api_request.py` 的 `apply_llm_request_middleware`，中间件返回 `{"request": {...}}` 即替换 provider kwargs。

**实测确认可改写的两个字段**（Responses 与 chat 两种协议下均已验证）：

| 字段 | 内容 | 改写后生效 |
| :--- | :--- | :--- |
| `request["instructions"]` | 系统提示词正文 | 是 |
| `request["tools"][n]["description"]` | 工具描述 | 是 |

验证方式：构造一个假中间件追加到 `_middleware[LLM_REQUEST_MIDDLEWARE]`，调用 `apply_llm_request_middleware(req, ...)` 后检查 `res.payload` 与 `res.changed`。

四条代价，缺一不可评估：

1. 需要在插件里维护完整的英文到中文映射，或维护一份完整中文提示词；
2. 官方每次调整提示词，映射表必须跟着改，否则出现「新增段落未翻译」或「翻译的段落已被删除」；
3. 中间件在每个请求上运行，全文字符串替换有性能开销；
4. `api_kwargs` 结构官方不保证稳定，升级可能直接失效。

本质是把「改源码」换成「改请求」，维护成本没有消失，只是转移到运行时。

**适用范围按改动频率分层**：工具 schema 描述措辞稳定、官方极少调整，适合走中间件；提示词正文官方每次升级都可能改动，映射表需要跟着维护，但**仍优于 Git 提交**——映射表失效只影响未匹配的段落回落英文，Git 提交失效则会让整层汉化消失，且需人工解冲突。

### 映射表的两类索引方式

中间件改写需要一份映射表。索引方式直接决定维护量：

| 索引方式 | 内容 | 维护量 |
| :--- | :--- | :--- |
| 全文替换对 | 完整英文描述 → 完整中文描述 | 每条描述都要维护，官方改一个字就失配 |
| **按路径索引** | `工具名.参数名` → 中文描述 | 只维护改过的条目，未命中的自动保持英文 |

工具 schema 是结构化数据，每个描述有唯一路径（如 `terminal.parameters.timeout.description`）。中间件按路径查表，命中则替换、未命中保持英文。官方新增工具或参数自动走英文不会出错，官方改动某条描述只需更新那一条。

提示词正文是一整段文本，用「首句特征匹配」而非全文精确匹配：映射表存「匹配串 → 中文段落」，官方改了段落中间的文字但首句不变时仍能命中；官方新增段落匹配不到就保持英文，不报错。

### 中间件插件落地的三个门槛

写中间件插件时，以下三处任一没做对，插件都会**静默不生效**，不报错、不影响启动：

**门槛一：插件必须登记在 `config.yaml` 的 `plugins.enabled` 列表里。**

仅把插件目录放进 `$HERMES_HOME/plugins/` 不够。未登记的插件在发现阶段就被跳过，日志里只有一行 `Skipping '<名称>' (not in plugins.enabled)`，很容易漏看。

```yaml
plugins:
  enabled:
    - zh-jargon-guard
    - zh-localization-overlay   # 新增的中间件插件必须加在这里
```

验证插件是否真的加载：

```python
from hermes_cli.plugins import _ensure_plugins_discovered
mgr = _ensure_plugins_discovered()
print(mgr.has_middleware('llm_request'))  # 必须为 True
```

**门槛二：`plugin.yaml` 不认 `provides_middleware` 字段。**

清单里写 `provides_middleware: [llm_request]` 会被当成未知字段忽略（日志 `unknown manifest field(s) ignored: provides_middleware`）。中间件靠 `__init__.py` 里的 `register(ctx)` 调 `ctx.register_middleware("llm_request", 回调)` 注册，清单只声明 `name`、`version`、`description`、`kind`、`requires_hermes` 即可。

**门槛三：映射表的英文基线必须自动识别，不能写死提交号。**

**先分清两个阶段，两者对 Git 的依赖完全不同：**

| 阶段 | 是否看 Git | 做法 |
| :--- | :--- | :--- |
| 首次生成映射表 | 是（仅此一次） | 沿历史回溯找中英切换点，与当前汉化版配对 |
| 升级后日常维护 | **否** | 对比「当前仓库源码」与「映射表」，只处理变化项 |

**映射表一旦生成，它自己就是基线。** 升级到哪个版本，那个版本就是新基线。日常维护脚本绝不能设计成「每次重新从 Git 找英文基线重新配对」——那等于把映射表重新绑回仓库，升级后必然失效，也违背了「用户端不与仓库绑定」的根本原则。

日常维护脚本只报告三类变化：

| 变化 | 含义 | 处理 |
| :--- | :--- | :--- |
| 新增 | 仓库出现了映射表里没有的英文 | 补译 |
| 删减 | 映射表里的英文在仓库中已消失 | 清理 |
| 修改 | 同一个键的英文原文变了 | 按新英文重译 |

未变化的条目原样保留，零操作。**升级成本与「官方改了多少」成正比，而不是与「汉化了多少」成正比。**

首次生成时，工具 schema 与提示词正文的汉化往往不在同一个提交里。用统一的基线提交去配对，会出现「工具映射生成 0 条」而提示词正常的结果——那个提交里的工具已经是汉化版，与当前版逐字相同，配对时被判为无差异。

更根本的问题是：写死提交号的脚本在官方升级后立即失效，每升一次级就要人工重新查提交。正确做法是让脚本自己找基线——沿 Git 历史逐版本回溯，找出「该版本含中文、其更早版本不含中文」的那个更早版本：

```text
版本 N     含中文   ← 汉化后的版本
版本 N-1   不含中文 ← 这就是英文基线，脚本自动选中它
```

这一条规则同时解决了「基线在哪」与「升级后基线变了」两个问题，不需要任何人工指定的参数。实现要点：

```python
def find_english_baseline(repo, rel):
    """沿历史回溯，找最近一次汉化之前的英文版。"""
    revs = git_revs_for(repo, rel)          # 该文件最近的 N 次提交，新→旧
    prev_has_cn = None
    for rev in revs:
        content = git_show(repo, rev, rel)
        cur_has_cn = has_cn(content)
        if prev_has_cn is True and cur_has_cn is False:
            return content                  # 中英切换点，找到了
        prev_has_cn = cur_has_cn
    return git_show(repo, "origin/main", rel)  # 兜底：官方版
```

兜底顺序固定为：中英切换点 → 历史最老的英文版 → `origin/main` → 跳过该文件并报告。**不得静默返回空**——静默取空会让该文件的映射条目无声消失，且不报错。

脚本还应提供 `--dry-run` 只报告不写文件，以及 `--base <目录>` 在特殊情况下手工指定基线。

### 映射表必须同时存英文原文与中文译文

解耦完成后仓库源码是英文原版，此时「只存中文侧」的映射表会彻底失去维护能力。

错误结构（只有中文）：

```json
{"terminal": {"description": "在当前运行环境指定的操作系统..."}}
```

维护脚本拿「仓库英文描述」与「映射表中文描述」对比，每条都不相等，于是把全部条目判成「已删减」。`--apply` 一跑，整张表被清空，且脚本报告「已清理 N 项删减条目」，看起来像正常工作。

正确结构（英文原文 + 中文译文）：

```json
{
  "terminal": {
    "en": "Execute shell commands on the OS, shell and backend...",
    "description": "在当前运行环境指定的操作系统与底层终端中执行命令行指令...",
    "params_en": {"command": "The command to run..."},
    "params": {"command": "需要执行的命令文本。"}
  }
}
```

- `en` 与 `params_en`：英文原文，**只用于升级后判断官方是否改了描述**，不送达模型；
- `description` 与 `params`：中文译文，中间件实际替换用的内容。

**补齐英文侧的脚本从当前仓库重新提取即可，不需要 Git 历史**——仓库此时就是英文原版。

**对比方向固定为「仓库英文 ↔ 映射表 en 字段」**：`--refresh` 刷新的是英文侧，`--apply` 新增条目时中文侧留空待译。方向搞反会让映射表变成英文副本，汉化整体失效且脚本仍报告成功。

**动态生成的工具描述拿不到英文原文，属正常缺口**：`browser_exec`、`clarify`、`execute_code`、`skill_manage` 的描述在运行时拼接，静态提取为空。补齐后仍缺这几条是预期结果，不要为此改动提取逻辑。

### 插件层的工具扫描必须排除测试目录并校验工具名形态

插件测试里常有 `{"name": "Create spec"}` 这类示例字典，会被当成真实工具收进映射表，表现为「插件工具新增 5 个」全是假名（`Create spec`、`Round trip`、`Round Trip Req`）。

两条过滤规则：

1. 跳过路径含 `tests/` 或文件名含 `test` 的文件；
2. 工具名必须全小写且只含字母、数字、下划线（`name.replace("_", "").isalnum() and name.islower()`）。

### 同步脚本要能反向同步

工作目录与运行环境可能各自被改过（用户在运行环境里直接调过技能）。发现差异时先判断哪边新，不要一律「工作目录覆盖运行环境」，否则会把运行环境里的更新抹掉。

判据用 `sha256` 逐个文件比对，列出差异清单再决定方向。实测出现过 13 个技能文件在运行环境里比工作目录新，反向同步后才一致。

### 从源码提取工具 schema 时必须解析模块级常量引用

工具描述常写成模块级常量再被 schema 引用：

```python
TERMINAL_TOOL_DESCRIPTION = """Run shell commands on ..."""
TOOL_SCHEMA = {"name": "terminal", "description": TERMINAL_TOOL_DESCRIPTION, ...}
```

直接用 `ast` 遍历字典取 `description` 的值，拿到的是 `ast.Name` 节点而非字符串，提取结果为空。必须先扫一遍模块顶层赋值收集 `{常量名: 字符串值}`，再对字典里的值做一次 resolve：字面量直接取，`ast.Name` 查常量表。

参数描述同样如此。漏掉 resolve 这一步，表现为「映射表条目数远少于预期」，且不会报错。

### 映射表只覆盖模块级常量，函数内提示词会漏

按模块级常量提取时，函数体内直接写的提示词字符串提取不到。六个提示词模块的中文长字符串共 127 处，其中模块级常量只占 31 个，其余 96 处在函数体内。

表现为映射表条目数正常但某些模块明显偏少（例如会话压缩模块只有 1 段）。要覆盖函数内提示词，需把提取逻辑从「只扫模块顶层赋值」扩展为「遍历所有字符串常量并按英文原文配对」，代价是映射表体积增大、误配风险上升。

汇报覆盖范围时要说清这一层缺口，不要把「已生成映射表」等同于「已全覆盖」。

### 提示词常量提取：AST 求值会漏掉两类写法，必须改用导入

提示词模块里的常量有三种形态，覆盖范围逐级递减：

```python
DEFAULT_AGENT_IDENTITY = ("...", "...")           # 字面量拼接，AST 能求值
SKILLS_GUIDANCE = ("...", f"{HEADING}", "...")    # f-string 拼接，AST 求不出
MEMORY_GUIDANCE = build_memory_guidance(True, True) # 函数调用，AST 求不出
```

只用 `ast.literal_eval` 会静默漏掉后两类。实测影响：`prompt_builder.py` 的模块级长字符串常量本应 20 个，AST 方式只拿到 16 个，漏掉 `MEMORY_GUIDANCE`、`USER_PROFILE_GUIDANCE`、`SKILLS_GUIDANCE`、`STEER_CHANNEL_NOTE` 四个——恰好是记忆、用户档案、技能、纠偏这四类核心指引。

正确做法是导入模块后从 `vars(module)` 取全部大写长字符串：

```python
def _import_consts(source, module_name, workdir):
    tmp = workdir / f"{module_name}.py"
    tmp.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(module_name, tmp)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        return {}                      # 导入失败（缺依赖、语法错）→ 调用方退回 AST
    finally:
        sys.modules.pop(module_name, None)
    return {k: v for k, v in vars(module).items()
            if k.isupper() and isinstance(v, str) and len(v) > 40}
```

**导入方式必须配白名单，否则会把外来常量算进来。** `system_prompt.py` 从 `prompt_builder.py` 导入了十几个常量，导入后它们都出现在 `vars(module)` 里。不过滤的后果是映射表里同一段中文挂在两个模块名下，其中 `system_prompt` 那一份的英文侧为空，替换永远不命中。

白名单取「本文件模块级 `Assign` 与 `AnnAssign` 的目标名」：

```python
def _ast_all_names(source):
    names = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names

# 使用：只保留本文件自己定义的
return {k: v for k, v in imported.items() if k in own_names}
```

**英文基线也要用同一种提取方式。** 基线文件与当前文件必须用同一套逻辑取常量，否则「基线 16 个、当前 20 个」会让 4 个新增常量无法配对。

**排查信号**：映射表生成成功但某模块段数明显偏少，或出现「英文侧为空」的条目。前者是提取漏了写法，后者是白名单没做对。生成后必须检查英文侧为空的条目数，应为 0。

### 走中间件不等于放弃汉化

把中文文本从 `tools/*.py` 或 `agent/*.py` 挪到插件映射表，模型收到的仍是中文。用户若担心「工具描述不汉化会影响中文效果」，需说明这是存放位置变化而非取消汉化，汉化质量与覆盖面不变。

### 插件目录不在仓库内，升级不会动它

承载中间件的插件放在 `$HERMES_HOME/plugins/`，与主仓库 `$HERMES_HOME/hermes-agent/` 平级。实测 `Path.is_relative_to()` 返回 `False`，`hermes update` 只操作仓库目录。因此中间件插件**无需任何 Git 操作，升级后照常生效**。

验证命令：

```python
from hermes_constants import get_hermes_home
home = get_hermes_home()
print((home / 'plugins').is_relative_to(home / 'hermes-agent'))  # 应为 False
```

### 路线二之补充：插件在加载时替换模块常量（覆盖不全，慎用）

另一条思路是插件启动时直接改写 `agent.prompt_builder` 等模块的常量值。实测结论：**只能覆盖一部分，不可作为主方案。**

两个硬限制：

1. **常量被复制到各模块自己的命名空间**。`prompt_builder.DEFAULT_AGENT_IDENTITY` 与 `system_prompt.DEFAULT_AGENT_IDENTITY` 初始指向同一对象，但在 `prompt_builder` 里赋新值后，`system_prompt` 里的引用仍是旧值。每个常量必须在它被引用的每一个模块里分别替换，漏一个就有一处保持英文；
2. **只能改模块级常量，改不了函数内字符串**。六个提示词模块的模块级中文常量合计 31 个，而含中文的长字符串共 127 处，其余 96 处在函数体内，插件无法触及。

判定某常量是否可被此方案覆盖：`inspect.getsource()` 看引用它的函数是从模块全局取，还是函数内局部 import。局部 import 的取不到替换后的值。

### 路线三：Git 本地提交（仅在无法用用户层承载时使用）

汉化作为 `local:` 提交固化在本地分支，升级时处理合并冲突。代价集中在升级那一刻，运行时零开销。冲突面与汉化文件数成正比，六个文件约 1.1 万行。

**这条路线不应作为汉化方案的首选。** 用户端与主仓库绑定会带来两个结构性代价：升级时检出切到游离 HEAD，所有 `local:` 提交整体失效；每次升级都要人工解冲突。用户对这条路明确表达过拒绝（「用户端就不应该与仓库绑定」）。

只在确实无法用用户层承载时使用：例如必须改框架源码才能生效的缺陷修复。此时要接受升级后重放的维护成本。

### 取舍建议

先按注入频率排序再决定范围：`prompt_builder.py` 与 `system_prompt.py` 每轮必注入，收益最大；其余四个按触发条件（工程目录、会话压缩、每轮结束、空闲）决定是否纳入。

### 分层的推荐组合

不要对五层用同一种办法。全部优先选用户层覆盖，主仓库源码保持官方原版：

| 层面 | 推荐办法 | 理由 |
| :--- | :--- | :--- |
| 语言包 | 用户层只放差异键 | 官方内置覆盖机制，不影响升级 |
| 工具 schema | `llm_request` 中间件 + 路径索引映射表 | 插件在仓库外，升级不影响；措辞稳定，维护量小 |
| 核心提示词 | `llm_request` 中间件 + 首句匹配映射表 | 同上；失效时回落英文而非整层丢失 |
| 技能 | 直接改 `SKILL.md` | 在用户层，哈希保护 |
| 插件 | 直接改插件仓库并提交 | 独立仓库，与主程序无关 |

判据不是「官方多久改一次」，而是「能否放在用户层」。能放用户层的一律不放主仓库。

### 从 Git 提交迁移到中间件时的顺序

已经用 Git 提交过汉化、后来改主意要转中间件的，操作顺序固定：

1. 先从当前汉化版源码里导出映射表（工具按路径、提示词按首句）；
2. 写中间件插件并实测生效（构造假请求调 `apply_llm_request_middleware` 看 `res.payload`）；
3. 确认中间件能覆盖后，再把汉化提交从历史里去掉；
4. 去掉后重跑一次实测，确认汉化仍在生效。

**映射表没建好就撤回提交，等于丢失全部汉化成果。**

### 去掉汉化提交用重置历史，不要用 `git revert`

`git revert` 会在顶部追加一串 `Revert "..."` 提交，与原始汉化提交两两抵消。结果是：净效果为零，但历史里多出成串的反向提交，既难读也难判断哪些改动真正生效。用户对这类历史明确表达过不满（「撤销动作不能成为新的提交」）。

正确做法是把这些提交从历史里去掉，而不是在顶部追加反向提交：

```bash
# 1. 先打备份标签，出事可回退
git tag backup/before-zh-removal

# 2. 找到汉化开始前的提交
git log --oneline origin/main..HEAD | tail -1

# 3. 软重置到那个提交（保留工作区内容）
git reset --soft <汉化开始前的提交>

# 4. 只提交真正要保留的改动（非汉化的功能修复）
git add <逐个列出>
git commit -m "..."
```

**先算净效果再动手。** 一串汉化提交加一串 revert，净差异可能只剩几个文件：

```bash
git diff --stat <汉化开始前的提交> HEAD
```

汇报时给净效果（哪几个文件、多少行），不要给提交条数。提交条数会让人误以为改动很大。

### 压缩前逐个核验要保留的补丁是否真的在当前 HEAD 里

净效果只说明「有哪些文件不同」，不说明「该保留的补丁都在」。分支分叉后，某个功能补丁可能只提交在备份分支上，从未进入当前分支——它不会出现在净效果里，压缩后就永久丢失。

```bash
# 对每个要保留的补丁，用它的特征代码在目标文件里检索，而不是看提交标题
grep -q '<特征标识符>' <文件路径> && echo "在位" || echo "丢失"
```

排查顺序：先列出本地领先 `origin/main` 的全部提交，逐个用 `git show --stat --format="" <sha>` 看改动文件，按「汉化 / 撤销汉化 / 功能修复」三类归档；再对每个功能修复类提交做上面的在位检索。发现丢失的，从备份分支取回：

```bash
git show <备份分支上的提交>:<路径> > <路径>
```

备份分支（`backup/*`）与当前分支的共同祖先可能在很久以前，备份分支上可能有当前分支没有的补丁。压缩历史前先 `git log --format="%h %s" HEAD..<备份分支>` 看它多出哪些提交。

### 助手无法执行历史改写时，生成脚本交给用户在停机终端运行

在 Hermes 运行中改写历史会被拦截（与 `git stash`、`git checkout <分支>` 同一保护机制）。此时不要反复重试同一条命令，也不要降级成「追加 revert」——那正是要避免的做法。

正确做法是写一个 Python 脚本交给用户执行，脚本自带四道安全措施：

1. 执行前自动打备份标签（`backup-before-squash-<时间戳>`），并打印回退命令；
2. 用 `git reset --soft` 而不是 `--hard`，工作区内容不丢；
3. 提交信息里逐条写清每个补丁解决什么问题，便于日后回溯；
4. 任一步失败立即打印回退命令并退出，不继续后续步骤。

脚本里**不要硬编码 `origin/main` 作为重置目标**，必须是本地安装版本的起点（第一个本地提交的父提交）。用 `origin/main` 会把整套代码换成开发主线，程序无法启动。

脚本用 Python 写、不用 `.cmd`：`.cmd` 只能放纯 ASCII，中文提交信息写不进去；`script-guard` 也会拦截含非 ASCII 的 `.cmd` 写入。

## 四、 提交汉化成果时的两个陷阱

### 陷阱一：第三方插件仓库处于游离 HEAD

`$HERMES_HOME/plugins/` 下的第三方插件各自是独立 Git 仓库，安装后常停在游离 HEAD（`git status -sb` 显示 `## HEAD (no branch)`）。直接 `git commit` 会提交到游离头，切走即丢失引用。

提交前先确认并切回主分支：

```bash
git -C <插件目录> status -sb | head -1
git -C <插件目录> rev-parse --verify main >/dev/null 2>&1 && git -C <插件目录> checkout main || git -C <插件目录> checkout master
```

切分支前比对游离 HEAD 与主分支是否指向同一提交。相同则直接切；不同则先看主分支比当前新多少——差异很大时（例如插件已从 0.4 升到 0.6），汉化需要按新版本重做，不能把旧版汉化硬 cherry-pick 过去，冲突会集中在配置文件上。

### 陷阱二：活动检出上不能切分支或 stash

Hermes 运行时的源码检出目录（`$HERMES_HOME/hermes-agent`）禁止 `git stash` 与 `git checkout <分支>`，会被拦截并提示改用独立克隆。需要跑基线对照时：

```bash
git clone --shared <检出目录> <临时目录>
```

在克隆里跑测试得到基线数字，用完删除。**不要试图用 `git stash` 临时回退来对照**——拦截是保护机制，绕过它会让运行中的进程混用模块版本。

还原误改文件同样不能用 `git checkout -- <文件>`：先 `git show HEAD:<相对路径> > <临时文件>`，再复制回目标路径，最后比对哈希确认与 HEAD 一致。

### 陷阱三：`origin/main` 不是本地安装版的英文原版

这是本类任务里破坏力最大的一处误判：把「官方仓库的最新代码」当成「本地安装版的原始版本」。

本地安装版是某条**稳定发布线**（`hermes --version` 显示 `v0.22.4+20.g<sha>` 这类带版本号的形态），`origin/main` 是**开发主线**，两者常差数千个提交。

```bash
git rev-list --count HEAD..origin/main      # 本地落后多少
git rev-list --count origin/main..HEAD      # 本地领先多少
```

任一不为 0，就说明 `origin/main` 里的文件内容与本地运行版本不是同一代代码。实测差距 2688 个提交时：

| 文件 | 本地版本 | `origin/main` 版本 |
| :--- | ---: | ---: |
| `tools/browser_tool.py` | 1376 行（完整实现） | 11 行（废弃存根） |

`origin/main` 上那个 11 行文件是给旧版更新器留的兼容桩，函数体直接 `return False`。用它覆盖回去，整套浏览器工具消失，Hermes 启动即崩溃。

**正确参照点，按优先级：**

| 场景 | 参照点 | 命令 |
| :--- | :--- | :--- |
| 某次汉化之前的英文原版 | 该汉化提交的父提交 | `git show <汉化提交>^:<路径>` |
| 当前运行代码的原版状态 | 本地 `HEAD` | `git show HEAD:<路径>` |
| 需要完整历史对照 | 独立克隆 | `git clone --shared` |
| **绝不能用** | `origin/main` | — |

用父提交前先验证那个提交里该文件确实是英文版，不要假定「父提交就是英文原版」——相邻提交可能同时改了别的东西：

```bash
git show <sha>:<路径> | grep -c $'[\u4e00-\u9fff]'   # 应为 0
```

### 批量覆盖文件的前置校验

需要把一批文件恢复到某个版本时，不要整批执行后才发现某个文件被换成了完全不同的东西。执行前对每个文件比对行数：

```bash
while read f; do
  cur=$(wc -l < "$f")
  new=$(git show HEAD:"$f" | wc -l)
  # 差异超过 50% 就人工检查，不要直接覆盖
  echo "$f: 当前 $cur 行 → 目标 $new 行"
done < 文件清单
```

行数骤降（例如 1376 → 11）通常意味着目标版本里这个文件已经废弃或被拆分了，需要单独判断，而不是当作普通覆盖处理。

覆盖前还要确认这些文件没有未提交改动，否则会连带丢掉别的工作：

```bash
git status --short $(cat 文件清单)
```

## 五、 基线对照的判定口径

汉化改动后测试出现失败，必须先证明失败与汉化无关，再宣称完成。做法是在独立克隆里跑同一组测试，比较失败项集合。

汇报时区分两类：

- **基线就失败**：在未改动的克隆里同样失败。常见于跨年时区判断、测试隔离机制拦截真实配置目录读写。这类保持原样，并在汇报里明确标注「与本次改动无关」；
- **汉化引入**：只在改动后失败。检查项多为英文原文匹配，逐条改成对应中文特征词，不删检查、不改恒真，改完失败数应回到基线水平。

只改基线就失败的测试没有意义：把它的英文检查条件改成中文不会让结果变好，只是制造一份无用改动。

## 六、 已落地的中间件插件参考实现

`zh-localization-overlay` 插件已在本机验证可用，可作为后续同类需求的起点。目录结构：

```text
<工作目录>\
  ├─ 部署.py                    唯一部署入口（配置 + 插件 + 汉化 + 技能）
  ├─ 说明.md
  ├─ 核心配置与防线\            配置、SOUL.md、.env、14 个插件
  └─ 汉化覆盖层\
      ├─ 汉化库.py              公共函数库（路径、提取函数、锚点清单），不直接运行
      ├─ 汉化维护.py            对比差异，不部署
      ├─ 语言包差异.py          抽取语言包差异键到用户层
      ├─ 说明.md
      ├─ 核心\prompts-zh.json   提示词映射（按模块名 + 常量名，含 en/zh 对）
      ├─ 工具\tools-zh.json     核心工具映射（按工具名 + 参数名索引）
      ├─ 插件\tools-zh.json     插件工具映射
      ├─ 插件\zh-localization-overlay\   插件源码（含合并后的运行映射表）
      ├─ 语言包\zh*.yaml        四个差异键文件
      └─ 技能库\                汉化技能
```

### 脚本数量要精简，部署入口必须唯一

早期版本拆成六个脚本（配置、生成映射表、维护映射表、补齐英文侧、抽取语言包差异、同步），用户会直接质疑「为什么要这么多脚本」。合并原则：

| 保留 | 职责 | 何时用 |
| :--- | :--- | :--- |
| `部署.py`（根目录） | 全量部署，带 `--check` 与 `--only <部分>` | 新电脑移植、改完映射表 |
| `汉化库.py` | 公共函数库 | 不直接运行 |
| `汉化维护.py` | 只对比差异，带 `--apply` | 升级后看变化 |
| `语言包差异.py` | 抽语言包差异键 | 清洗语言包后 |

两条硬约束：

1. **部署只能有一个入口**。同名能力散在两个脚本（例如移植脚本与汉化脚本都能写映射表）会让用户直接问「这两个不冲突吗」。判定归属：凡是「把文件复制到运行环境」都归 `部署.py`，汉化维护脚本只负责读写磁盘上的映射表；
2. **不需要「生成映射表」脚本**。映射表生成后就它自己就是基线，后续只有两件事：对比差异（新移植或升级后）、部署。再保留一个每次都能重建全表的脚本，只会诱惑人误用它清空现有映射表。

### 临时目录必须用完即删

提取提示词常量时要把源码临时写盘再 `importlib` 导入，这个临时目录（如 `_probe/`）不收尾会累积到数 MB。在调用处用 `try/finally` 包住并在 `finally` 里 `shutil.rmtree(workdir, ignore_errors=True)`；单个临时文件用 `tmp.unlink(missing_ok=True)`。只靠「最后手动清理一次」不够——下次还会长回来。

运行时位置：`$HERMES_HOME/plugins/zh-localization-overlay/`。

**三份正本分目录，运行用的合并表由脚本拼装**：`核心/`、`工具/`、`插件/` 三份 JSON 是正本，可分别备份与比对；插件目录里的 `tools-zh.json` 是每次同步时把「核心 + 插件」重新合并写出的运行副本，不要手工维护它。

**工作目录不放英文原版备份**：系统本身就是英文原版，随时可从仓库或 `hermes update` 取回。另存一份只会让目录膨胀，并在迁移时无法判断哪些是资产、哪些是备份。

**两个脚本分工不可合并**：`生成映射表.py` 只在首次建表时跑一次，此时才需要回头看 Git；`维护映射表.py` 是日常入口，只对比当前仓库与映射表。把两者写成一个脚本、每次升级都重跑基线识别，等于把映射表绑回仓库。

### 中间件的三个改写位点

```python
def llm_request_middleware(request, original_request, **context):
    # 1. 工具描述：request["tools"][n]["description"] 与 ["parameters"]["properties"][p]["description"]
    # 2. Responses 协议：request["instructions"]
    # 3. Chat 协议：request["messages"] 中 role == "system" 的 content
    return {"request": new_request}   # 无改动时返回 None
```

三种协议位置的覆盖必须全部实现：只改 `instructions` 时，走 chat 协议的通道不会生效。

### 提示词替换必须长串优先

把映射对按英文长度降序排序后再逐条替换。短串先命中会把长串拆碎，导致长段落永远匹配不上：

```python
pairs.sort(key=lambda p: len(p[0]), reverse=True)
```

### 映射表懒加载

映射表只在首次请求时读一次并缓存到模块级变量。每次请求重读 JSON 会带来不必要的 IO；若需热更新映射表，要重启网关或重新加载插件。

### 验证脚本

逐个验证映射表条目是否真的能命中，比抽查几个更有说服力：

```python
# 工具：构造只含目标工具的假请求，看 description 是否变成映射表里的值
# 提示词：拿映射表里的 en 字段当输入，看输出是否包含 zh 字段的前 30 字
```

本机实测结果：核心工具 52 个 + 插件工具 27 个，合并后 79 个，全部命中；提示词 31 段全部命中，英文侧为空条目 0 条。工具条目数会随官方增删与合并变化（早期一度是 49，补齐后到 62，官方合并浏览器系列并删旧条目后回落到 52），汇报时以当次实测为准并说明变化原因，不要沿用历史数字。

### 映射表只收录「与基线不同」的条目，未汉化的工具不会自动进入

生成逻辑是逐条对比「中文版 vs 英文基线」，相同即跳过。因此某类工具整批仍是英文时，它们不会出现在映射表里，而脚本依然报告「生成成功」。

发现覆盖不完整的正确做法：先补汉化那批工具，再重跑生成脚本。不要因为「映射表生成成功」就认为覆盖完整——条目数才是判据。

本机曾出现的情况：浏览器系列 12 个工具长期未汉化，映射表只有 34 条；补齐汉化后重跑脚本，条目增至 46 条。

### 映射表改完后必须手工同步到插件目录

`maintain_maps.py --apply` 只改工作目录里的映射表，插件运行时读的是 `$HERMES_HOME/plugins/<插件名>/` 下的副本。忘了复制会表现为「脚本报告已补齐 N 项，但中间件仍只替换旧条目数」，不报错。

验证方式：分别读两处的映射表条目数，必须相等：

```python
import json
from pathlib import Path
for base in [r"<工作目录>\汉化覆盖层", r"C:\Users\<用户>\AppData\Local\hermes\plugins\zh-localization-overlay"]:
    m = json.loads((Path(base) / "tools-zh.json").read_text(encoding="utf-8"))
    print(f"{base}: {len(m)} 个工具")
```

### 语言包差异键的抽取

对比「仓库版」与「官方 `origin/main` 版」，逐键取差异，写入用户层。实测四个文件合计 169 个差异键，`zh.yaml` 从完整副本 255 KB 降到差异键 7 KB。

抽取脚本两个实现要点：

1. **能处理嵌套 YAML**：摊平成 `a.b.c` 键再还原，否则无法逐键比对；
2. **优先用 `ruamel.yaml` 保序**，缺失时退回 PyYAML——官方语言包依赖顺序可读，重排后 diff 会变成全文件重写。

抽取后必须双向验证：差异键走用户层、未覆盖键走仓库版。只验一边会漏掉「用户层文件写坏、整层回落仓库」的情形。

### 差异键建好后，仓库版回退不会影响实际生效

把语言包差异键抽到用户层之后，仓库里的 `locales/zh*.yaml` 回退成官方版不会造成任何功能损失：运行时用户层优先，实际取到的仍是清洗后的译法。

验证方式（回退后重跑）：

```python
from agent import i18n
i18n.reset_language_cache()
from agent.i18n import t
print(t('gateway.hooks.command_blocked', command='x'))   # 应仍为本地清洗版
```

这一条让「仓库保持官方原样」与「本地清洗持续生效」同时成立，也是语言包不需要 Git 提交的原因。汇报时要把「仓库版已回官方」与「运行时仍是本地译法」分开说，否则容易被误认为汉化丢失。
