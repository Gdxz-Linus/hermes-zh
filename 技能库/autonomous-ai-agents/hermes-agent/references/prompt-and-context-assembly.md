# 系统提示词装配、上下文压缩与思考链重放的实测判定

本文件回答一类反复出现的提问：模型这一轮到底收到了什么、上下文什么时候压缩、历史思考链还在不在。三件事都不能靠读配置或读源码注释下结论，必须走本文件给出的取证路径。

## 一、 系统提示词的三层装配

`agent/system_prompt.py :: build_system_prompt_parts` 返回三个有序层，`build_system_prompt` 按 stable → context → volatile 顺序拼接：

| 层 | 内容 | 变化频率 |
| :--- | :--- | :--- |
| stable | 身份（SOUL.md 或默认身份）、执行纪律指引、技能指针、编码姿态 | 会话内恒定 |
| context | 调用方传入的 system_message、项目上下文文件（AGENTS.md 等）、工作区快照 | 随工作目录变 |
| volatile | 技能索引、记忆与用户画像、插件段落、配置档行、时间行、运行环境说明 | 最易变 |

分层的目的是让不变的部分留在服务端最长公共前缀缓存里。volatile 放最后，技能索引一变就从那里重新预填充，前面的前缀仍可复用。

**会话内不重建**：结果缓存在 `agent._cached_system_prompt`，只有上下文压缩后才 `invalidate_system_prompt` 重建一次。因此改 SOUL.md、改提示词源码、改技能索引，都只对**新会话**生效，当前会话不受影响。汇报时必须区分「已写入」与「已生效」。

## 二、 SOUL.md 的注入位置与截断规则

身份槽位在 stable 层第一位，由 `_identity_parts` → `agent/prompt_builder.py :: load_soul_md(ctx_len, home_override=...)` 产出：

1. 路径固定为 `$HERMES_HOME/SOUL.md`；`home_override` 把读取范围钉在 agent 自己的 profile 目录，避免线程丢失 `HERMES_HOME` 上下文变量时读到别的档；
2. 读文本后依次做：去首尾空白 → `strip_legacy_protocol`（剥掉旧版桌面端追加的冻结段落）→ 注入扫描；
3. **注入扫描对用户自己的文件是警告放行**：命中危险模式只记一条警告，文件仍加载。项目目录里的 AGENTS.md / .cursorrules 命中则整段替换为 `[BLOCKED: ...]`。SOUL.md 若由 `hermes profile install <git-url>` 装进发行档（`distribution.yaml` 拥有它），按非用户文件处理，命中即拦截；
4. 读不到或内容为空时回落 `DEFAULT_AGENT_IDENTITY`（英文身份行）。

**截断上限**（`_get_context_file_max_chars`）：配置项 `context_file_max_chars` 优先；未配置时按 `context_length × 4 × 0.06` 计算，下限 20000、上限 500000 字符。超限时保留头 70% + 尾 20%，中间插入标记并列出被省略的 Markdown 标题，同时把警告推到聊天状态行。

据此可估算：窗口 100 万 token 时上限约 25 万字符，正常规模的 SOUL.md 远不会触及；窗口小于约 8.3 万 token 时下限 20000 生效。

## 三、 取证：读 state.db 的 system_prompts 快照

回答「实际注入的内容是什么」时，源码只能说明「会拼什么」，要说明「拼出来的字节」必须读快照。

```python
import sqlite3
c = sqlite3.connect(r"<HERMES_HOME>/state.db")
cur = c.cursor()
cur.execute("select hash, length(prompt), prompt from system_prompts")
for h, n, p in cur.fetchall():
    print(h[:12], n, p[:80].replace("\n", "\\n"))
```

判读要点：

- 表结构是 `system_prompts(hash, prompt)`，每次装配落一份，历史快照会累积，按 `length(prompt)` 或内容特征挑最新那份；
- **定位 SOUL.md 段边界**：在快照里检索 Hermes 自带英文块的起点（例如 `# Finishing the job`），它之前的字符数就是 SOUL.md 段长度。SOUL.md 段永远在最前面；
- 快照里同时能看出各段顺序，可用来验证「用户写的规范排在英文默认块之前」这类判断；
- 只统计 `prompt` 长度不足以说明结构，必须按标题行逐行打印（`line.startswith('#')`）才能看出段落顺序。

## 四、 上下文压缩的触发线与尾部保留量

配置在 `compression` 段，但真正生效的数值由公式算出，不要拿配置百分比直接当 token 数。

**触发线**（`ContextCompressor._compute_threshold_tokens`）：

```
effective_window = context_length - max_tokens      # max_tokens 为 None 时取整个窗口
pct_value        = effective_window × threshold_percent
floored          = max(pct_value, MINIMUM_CONTEXT_LENGTH=64000)
trigger_cap      = effective_window × 0.85
若 floor 生效且超过 trigger_cap：floored = max(pct_value, trigger_cap)
若 floored >= effective_window：返回 min(trigger_cap, effective_window - 1)
```

**输出预留来自 `agent.max_tokens`，而它在主会话路径上恒为 `None`**。这个值只能通过 `AIAgent` 构造参数传入，而主会话的三条构造路径（`hermes_cli/cli_agent_setup_mixin.py`、`gateway/`、`tui_gateway/agent_factory.py`）都不传它，`config_defaults.py` 的 `agent` 段也没有这个键。

**`providers.<名>.extra_body.max_output_tokens` 压缩器读不到**。它由 `_merge_custom_provider_extra_body` 原样塞进 `request_overrides.extra_body`，只影响实际请求体，与压缩器的 `max_tokens` 是两条独立链路。因此「provider 配了 65536 输出上限，所以触发线会自动下降」是错的推断：实测窗口 1048576、`threshold` 0.75 时，触发线仍是 786432（按全窗口算），不是 737280。要确认必须看 `agent.max_tokens` 的实际取值，不要看 provider 配置。

用户问「为什么不配输出预留」时，正确答法是：这不是漏配，是 Hermes 没有这个配置入口；差额只有 4.7% 量级，对百万窗口不改变任何决策，真正决定压缩早晚的是 `threshold` 百分比。补这个值需要改产品源码或走 `request_overrides` 绕行，成本高于收益。

**尾部保留量**（`tail_token_budget`）：

| 尾部模式 | 公式 |
| :--- | :--- |
| `lean`（默认） | `clamp(context_length × 0.025, 10000, 25000)` |
| `legacy` | `threshold_tokens × summary_target_ratio` |

两者最后都再取 `min(该值, context_length × 0.20)`。

**摘要上限**：`min(context_length × 0.05, 10000)`。

**条数保护**：`protect_last_n` 是「至少保留的条数」，实际封顶 `_MAX_TAIL_MESSAGE_FLOOR = 8`，防止大工具输出把尾部撑爆；`protect_first_n` 在首次压缩后自动衰减为 0，避免早期轮次永久固化。

验证方式：直接调静态方法，不要心算——

```python
import sys; sys.path.insert(0, "<hermes-agent 仓库>")
from agent.context_compressor import ContextCompressor
print(ContextCompressor._compute_threshold_tokens(1048576, 0.75, None))    # 786432（主会话实际值）
print(ContextCompressor._compute_threshold_tokens(1048576, 0.75, 65536))   # 737280（假设预留 65536 的对照值，非实际）
```

大窗口配高 `threshold` 的后果要说清楚：触发点极高意味着单次压缩要处理极长历史，耗时与摘要质量风险集中在那一刻。调低 `threshold` 能让压缩更早、更平缓地发生，代价是次数变多。

## 五、 中文思考链引导：两条通道必须分清

用户说「中文前导词」时，指的可能是两件完全不同的事，答错对象会被直接纠正。先分清再答：

| 通道 | 机制 | 位置 | 效果 |
| :--- | :--- | :--- | :--- |
| SOUL.md 身份块 | 提示层文字约束 | 系统提示词 stable 层第一位 | 概率性，靠开头注意力权重 |
| `prefill_messages` | 请求层预置消息 | 系统提示词之后、历史最前面 | 本机未启用，且语义不是首字引导 |

**`prefill_messages` 的真实语义**（`agent/turn_request_assembly.py`）：

```python
sys_offset = 1 if api_messages[0].get("role") == "system" else 0
api_messages.insert(sys_offset + idx, _clone_message_for_send(pfm))
```

它插在**整段历史的最前面**，不是末尾。这等于告诉模型「这段助手发言发生在很久以前」，而不是「请你从这里接着往下写」。首字引导依赖后者，所以这条通道做不到锁死思考链首字。

配置入口三选一，按优先级：环境变量 `HERMES_PREFILL_MESSAGES_FILE` → `config.yaml` 的 `prefill_messages_file` → 旧键 `agent.prefill_messages_file`。三处都没有即该通道为空。

内容过滤（实测 `_chat_messages_to_responses_input`）：空字符串与纯空白会被丢弃、不出现在请求里；只有非空文本才会作为 input 的第一条 assistant 消息发出。

**产品本身规避末尾 assistant 消息**：`agent/moa_loop.py` 的注释写明 Anthropic 把尾部 assistant 当 prefill 直接 400，代码强制以 user 轮收尾。看到这个约束就知道 Hermes 没有设计「末尾预填」这条路，不要试图用 `prefill_messages` 模拟。

**要物理锁死思考链首字，只能在推理服务端做**（SGLang 的 chat template 或服务端 assistant prefill 参数）。`extra_body` 能原样转发参数，但 Responses 接口的 input 里放 assistant 消息不是 prefill 语义，SGLang 是否按 continuation 处理必须单独实测，不能凭配置推断。

## 六、 思考链是否随上下文重发：按协议分别判定

**数据库里存着明文思考链，不等于它被发出去。** `messages` 表的 `reasoning` 与 `reasoning_content` 列只服务于本地留存、界面展示与 token 计量。

| 协议 | 明文思考链 | 加密思考条目 |
| :--- | :--- | :--- |
| `codex_responses` | **完全不发** | 重放 `codex_reasoning_items` 中带 `encrypted_content` 的条目 |
| `chat_completions` | 只重放**最新一轮**，更早轮次丢弃 | 不适用 |
| `anthropic_messages` | 按端点策略保留签名块或剥离 | 不适用 |

判定依据 `agent/message_sanitization.py :: stale_thinking_reaches_wire(api_mode, provider, model, base_url)`：对 `codex_responses` 恒为假，因为该协议不读文本键，连续性走加密旁路。压缩的触发估算与尾部保留量遍历共用这一个判据，两边不一致会导致推理密集的会话反复压缩。

`codex_responses` 的重放细节（`_replay_reasoning_items`）：

- 只重放带 `encrypted_content` 的条目；
- 密文按**签发端点与签发模型**封存，跨端点或跨模型重放会 400 `invalid_encrypted_content`，因此不匹配的条目直接丢弃（会话中途换模型时会出现，日志有一条一次性警告）；
- `type: "compaction"` 检查点仅当本次请求真的带原生压缩参数（`context_management`）才重放，否则会误删检查点之前的历史；
- 同一 `id` 在一次请求里只重放一次。

`chat_completions` 的细节：

- 携带哪些字段由 `_REASONING_CARRIER_ROUTES` 决定，严格端点（mistral/groq/cerebras）一个都不带，其余默认只带 `reasoning_content`；
- 只重放最新一轮（`_NEWEST_TURN_ONLY_BUDGET_KEYS`），更早轮次的明文思考链一律丢弃；
- must-echo 家族（deepseek / kimi / mimo）的工具调用轮缺 `reasoning_content` 会 400，Hermes 补一个空格占位（空串被拒）。

## 七、 验证脚本：直接跑转换函数

比读源码更硬的证据是把真实转换函数跑一遍，看输出里还剩什么。

```python
import sys, json; sys.path.insert(0, "<hermes-agent 仓库>")
from agent.codex_responses_adapter import _chat_messages_to_responses_input

msgs = [
    {"role": "system", "content": "S"},
    {"role": "user", "content": "hi"},
    {"role": "assistant", "content": "answer",
     "reasoning": "明文思考链", "reasoning_content": "明文思考链"},
    {"role": "user", "content": "again"},
]
print(json.dumps(_chat_messages_to_responses_input(msgs), ensure_ascii=False, indent=1))
```

`codex_responses` 下输出里 `reasoning` 与 `reasoning_content` 两个字段消失，只剩正文——这就是「明文思考链不重发」的直接证据。

配套的数据库侧核对：

```python
cur.execute("select count(*) from messages where reasoning is not null and reasoning != ''")
cur.execute("select count(*) from messages where codex_reasoning_items is not null and codex_reasoning_items != ''")
```

两列都非零而请求里没有明文思考链，正说明「存着但不发」是设计而非遗漏。

## 八、 汇报口径

- 先给结论句（「明文思考链全部过滤，加密条目会重放」），再给机制，最后给数字；
- 数字必须是函数实跑出来的，不是按百分比心算的；
- 涉及「会不会影响缓存/成本」时，说清哪一项是可调的、调了代价是什么，把决定权交回用户，不要替他定值。
- **用户问「为什么不配某项」时，第一句先回答「有没有这个配置入口」**，再谈取值影响。直接跳到「配了会差多少」等于默认这个键存在，用户会追问「为何不配置下」，等于没答。
- **用户用一个可能指代多个对象的词提问时，先确认指代再展开**。本类问题里「中文前导词」既可能指 SOUL.md 身份块，也可能指引导思考链的首字预填；答错对象后用户会直接纠正，整轮工作作废。拿不准时两件都简短点到，让用户指定。
