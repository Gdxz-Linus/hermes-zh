# 图片输入与推理参数的路由判定

本文件说明两件事：用户附带的图片最终以什么形式送进模型，以及思考链开关实际由哪个参数控制。两者都容易「配置写了但没生效」，判定必须靠实测而非读配置。

## 一、 图片输入的两道独立判定

图片送进模型要过两道关，两道都通过才是真正的原图直传。

| 判定函数 | 决定什么 | 位置 |
| :--- | :--- | :--- |
| `decide_image_input_mode(provider, model, cfg)` | 发原图（`native`）还是先转成文字描述（`text`） | `agent/image_routing.py` |
| `_lookup_supports_vision(provider, model, cfg)` | 图片是否会被从消息里剥离替换 | `agent/image_routing.py` |

`agent.image_input_mode` 取 `auto`（默认）、`native`、`text` 三值。`auto` 的判定顺序：

1. 配了具体的 `auxiliary.vision` 后端（provider 不是 `auto`/空，或有 model、有 base_url），直接返回 `text`——辅助视觉后端优先于主模型的视觉能力；
2. 否则查主模型的 `supports_vision`，为 `True` 才返回 `native`。

`native` 是绝对覆盖，跳过第 1 步。但即使 `native`，第二道 `_lookup_supports_vision` 仍会独立执行：它为 `False` 时，`_prepare_messages_for_non_vision_model()` 会把图片部分替换成 `vision_analyze` 的文字描述。

### 声明主模型支持视觉的写法

`supports_vision` 的解析顺序（`_supports_vision_override`）：`model.supports_vision` → `providers.<名称>.models.<模型名>.supports_vision` → 旧式 `custom_providers[].models.<模型名>`。

注意 `providers.<名称>.models` 必须是**字典**才能承载逐模型能力，写成列表时无法声明：

```yaml
providers:
  jk-deepseek:
    models:
      deepseek-v4.1-flash:
        supports_vision: true
```

### 每个通道都要单独声明，未声明即按不支持处理

视觉能力是**逐通道、逐模型**声明的，没有继承，也没有「后端能看图就自动放行」。只给一个通道写了 `models.<模型>.supports_vision: true`，其余通道仍然走三层探测（本地运行时 → models.dev 目录 → Ollama 探测），三层全返回「未知」就按不支持处理，图片被静默换成文字描述。

因此「修好了某个通道的图片」不等于「所有通道都好了」。修好一个通道时，**主动把其余通道的状态列出来**，不要只报修好的那一个——用户切到另一个通道发现图片仍然不行时，会回头问「上次是不是没修完」。用户问「某通道有什么问题」时同样一次把全部通道的两列都查出来，不要只答被问到的那一个：

| 通道 | 后端实测能看图 | 配置是否声明 | 发送前原图是否保留 |
| :--- | :--- | :--- | :--- |
| 逐项填 | 逐项填 | 逐项填 | 逐项填 |

后端实测用直接发图（不经 Hermes），并核对响应里的 `model` 字段确实是目标模型，排除被改道的可能：

```python
import base64, json, os, urllib.request
b64 = base64.b64encode(open("probe.png", "rb").read()).decode()
body = {"model": "<模型名>", "store": False, "input": [{"type": "message", "role": "user", "content": [
    {"type": "input_text", "text": "只回答图中数字。"},
    {"type": "image_url", "image_url": "data:image/png;base64," + b64}]}]}
req = urllib.request.Request("<base_url>/responses", data=json.dumps(body).encode(),
                             headers={"Authorization": "Bearer <key>", "Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=60))
print(r.get("model"))   # 必须等于请求的模型名，否则说明后端改道了
```

`chat_completions` 接口把 `input` 换成 `messages`、`input_text`/`input_image` 换成 `text`/`image_url`。部分本地反代对非流式请求返回的结构不完整（缺 `choices` 键），加 `"stream": True` 后逐行读 SSE 才能拿到正文。

**声明前先实测、实测过才声明**：只给实测答对的模型加声明，不要按厂商或参数表推断。同一通道里未实测的模型先不加，等真要用再测。

### 排查前先确认当前默认模型是哪一条

`config.yaml` 的 `model` 段会被界面上的模型切换改写（`default`、`provider`、`base_url`、`api_mode` 四项一起换，`agent.reasoning_effort` 也可能被改挡位）。排查图片或通道问题前先读这一段，不要假定配置还是上次看到的样子——默认模型变了会直接改变候选查询名单，也会改变网关 warm 的是哪个模型。发现与预期不符时如实指出并请用户确认，不要当成自己改的或当成故障。

### 铁律：`providers` 键名必须全小写，否则声明静默失效

运行时会把 provider 身份强制小写化：`agent/auxiliary_client.py` 的 `_normalize_main_runtime` 对 `provider` 与 `requested_provider` 两个字段都执行 `identity.lower()`。而 `_supports_vision_override` 拿这个已小写的名字去查 `config.yaml` 的 `providers` 字典，Python 字典查找区分大小写。

配置里写成 `JK-deepseek`、`DeepSeek` 这类含大写字母的键，`supports_vision` 永远查不到，函数返回 `None`（未知能力），第二道判定随即按「不支持」处理，图片被剥掉，**全程不报错、不告警**。

对照实测（`cfg` 为真实配置）：

```python
from agent.image_routing import _lookup_supports_vision
from hermes_cli.config import load_config_readonly
cfg = load_config_readonly()
# 运行时实际传入的是 custom + 已小写的 requested_provider
print(_lookup_supports_vision("custom", "<模型名>", cfg, requested_provider="jk-deepseek"))  # None，失效
print(_lookup_supports_vision("custom", "<模型名>", cfg, requested_provider="JK-deepseek"))  # True，仅大小写不同
```

两个结果不一致即坐实键名问题。

**修法（已定）：把 `providers` 键改成全小写，显示名靠条目内的 `name:` 保留大写。** 这是长期形态，因为逐模型声明 `supports_vision` 更精确，不会误伤不支持视觉的通道。

`model.supports_vision: true` 只当临时排障手段用：它是全局键，实测加上后纯文本模型也被判为支持视觉，切到不支持视觉的通道时图片会被硬塞过去、上游返回 400。用它验证完根因后必须撤掉。

撤掉前的验收标准是两组返回值同时成立：目标模型为 `True`（来自逐模型声明），另一个纯文本模型为 `None`（未知，而不是 `True`）。只查目标模型不够——全局键在时两者都是 `True`，看不出区别。

改键名的完整流程：

1. 先备份：`cp config.yaml config.yaml.bak-<时间戳>`；
2. 用 Python 逐行读改写，只替换形如 `^  <旧键>:` 的行，`providers` 与 `model_overrides` 两处都要改；不要用 sed 正则一把梭，也不要指望 `hermes config set`（它只能改单值，不能改键名）；
3. `yaml.safe_load` 解析确认结构完好，打印两处的键名列表；
4. `diff` 与备份比对，确认只动了预期行数；
5. 四处验证，缺一不可：

```python
import sys; sys.path.insert(0, 'hermes-agent')
from hermes_cli.config import load_config_readonly
from agent.image_routing import _lookup_supports_vision
from agent.models_dev import _override_context_window
from hermes_cli.runtime_provider import resolve_runtime_provider

cfg = load_config_readonly()
print(_lookup_supports_vision("custom", "<模型名>", cfg))            # 期望 True
print(_override_context_window("<小写键>", "<模型名>"))               # 期望配置里的真实窗口
print(resolve_runtime_provider(requested="<小写键>")["base_url"])     # 期望正确端点
```

界面显示名另用 `build_model_options_payload` 核一次，确认 `name` 仍是大写、`slug` 已小写。

改完必须重启网关才生效（配置在进程启动时读取）。

### 为什么这个缺陷只在特定条件下暴露

`_supports_vision_override` 的候选查询名是三个：`requested_provider`、`provider`、`model.provider`。前两个在运行时已被强制小写（`_normalize_main_runtime` 的 `identity.lower()`），只有 `model.provider` 保留配置里的原始大小写。

于是同一个大写键名会出现两种结果：

| 场景 | 候选名单 | 结果 |
| :--- | :--- | :--- |
| 该 provider 就是当前默认模型 | 含 `model.provider` 的原始大小写 | 命中，一切正常 |
| 会话切到别的模型后看图 | 全小写，无原始大小写 | 落空，图片被剥 |

这解释了一个反复出现的疑问：「配置一直没改，以前图片是好的」。默认模型是它时确实好，切走后才坏。

用户追问「为何别的大写就可以」时，不要只重复结论，做对照实验：把当前能用的 provider 键改成大写、查询名固定小写，看是否同样失败。

```python
import copy
from agent.image_routing import _supports_vision_override
from hermes_cli.config import load_config_readonly

base = load_config_readonly()
base["model"].pop("supports_vision", None)   # 排除全局键干扰，单看键名影响
for key in ("llm-gw", "LLM-GW", "Llm-Gw"):
    cfg = copy.deepcopy(base)
    cfg["providers"] = {key: {"name": key, "api": "http://x/v1",
                              "models": {"<模型名>": {"supports_vision": True}}}}
    print(key, _supports_vision_override(cfg, "custom", "<模型名>", requested_provider="llm-gw"))
```

只有全小写键返回 `True`，大小写混合的两种都返回 `None`——证明这是通用机制，不是某个 provider 的特例。

### 界面上的大写是样式，不是配置键名

用户看到模型选择列表里所有 provider 名都是大写，据此质疑「别的大写为何没问题」时，先分清显示值与存储值，不要照截图推断键名。

分组标题统一套了 `text-transform: uppercase`，定义在 `apps/desktop/src/app/shell/model-catalog-menu.tsx` 的 `catalogGroupLabel` 常量里。屏幕上全大写不代表配置里含大写字母。另有一部分显示名来自内置标签表 `hermes_cli/models.py` 的 `_PROVIDER_LABELS`（键名 `llm-gw` 显示为 `LLM Gateway`），同样与键名无关。

判据是后端返回的真实数据。调生成该列表的函数取真实值：

```python
from hermes_cli.config import load_config_readonly
from hermes_cli.config_providers import get_compatible_custom_providers
from hermes_cli.inventory import build_model_options_payload, ConfigContext

cfg = load_config_readonly()
ctx = ConfigContext(
    current_provider="<当前 provider>", current_model="<当前模型>",
    current_base_url="<当前 base_url>",
    user_providers=cfg.get("providers", {}),
    custom_providers=get_compatible_custom_providers(cfg),
)
for row in build_model_options_payload(ctx).get("providers", []):
    print(row.get("slug"), row.get("name"), row.get("is_user_defined"))
```

`slug` 是配置键（判定用的就是它，大小写敏感），`name` 是显示名。逐个比对 `slug == slug.lower()` 即可列出真正含大写的键。

另一个可解释的现象：`providers.<名>` 里同时写了 `api` 字段时，该后端会既作为内置 provider 行出现一次，又作为 `custom:<名>` 自定义端点行出现一次。列表里看到同一后端两行属于这个原因，不是配置重复。

### 同一个大小写缺陷也影响 `model_overrides`

`agent/models_dev.py` 的 `_provider_override_section` 同样按原始键名查字典，不走别名表。配置里写 `model_overrides.JK-deepseek` 时：

| 查询用的 provider 名 | 是否命中 |
| :--- | :--- |
| `JK-deepseek`（原始大小写） | 命中 |
| `jk-deepseek`（运行时小写） | 不命中 |
| `custom` | 不命中 |

不命中时上下文窗口静默退回 models.dev 默认值，数值偏差通常不大（实测差 48576 token），不影响功能，但会让「窗口到底多少」的排查得出错误结论。改 provider 键名时连同这一处一起核。

### 铁律：网关日志的 `Image routing: native` 不能证明原图进了模型

这条日志只是第一道判定（`decide_image_input_mode`）的结论，说明「打算按原图发」。发送前还有第二道 `_lookup_supports_vision`，由 `_prepare_messages_for_non_vision_model()` 独立执行；它为假时把图片部分换成 `vision_analyze` 的文字描述，**不会再打一行日志**。

两次判定结论不一致时，日志看上去一切正常，实际图片已被降级。真正的判据只有两个：

1. 调 `_prepare_messages_for_non_vision_model()` 看返回的消息里 `image_url` 还在不在：

```python
from agent.vision_message_prep import VisionMessagePrepMixin

class Probe(VisionMessagePrepMixin):
    provider, model = "custom", "<模型名>"
    _anthropic_image_fallback_cache = {}

msgs = [{"role": "user", "content": [
    {"type": "text", "text": "看图"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
]}]
out = Probe()._prepare_messages_for_non_vision_model(msgs)
kept = any(isinstance(c, dict) and c.get("type") == "image_url" for c in out[0]["content"])
print("原图保留:", kept)
```

注意 `_anthropic_image_fallback_cache` 必须初始化，否则降级分支抛 `AttributeError`，看起来像别的故障。

2. 在 `agent.log` 里检索 `vision_tools: Analyzing image`：出现即说明走了转述路径，原图没进模型。

### 降级链路是独立的一套，报错不要往图片本身查

第二道判定为假时，Hermes 会调 `auxiliary.vision` 配置的后端把图转成文字。`provider: auto` 时自动挑选，常见落到本地反代。这条链路与主模型完全独立，它失败时的日志形态是：

```
Auxiliary vision (async): connection error on <后端名> (Connection error.), trying fallback
Auxiliary vision (async): connection error on <后端名> and all fallbacks exhausted
resolve_provider_client: custom/main requested but no endpoint credentials found
tools.vision_tools: Error analyzing image: Connection error.
```

看到这组报错，第一反应应是确认降级后端端口有没有在监听（`netstat -an | grep <端口>` 或直接 `curl -m 5 http://127.0.0.1:<端口>/v1/models`），不要往「图片格式坏了」「上游不支持图片」的方向查。后者对应的是 `Could not decode image` / `image_url is not supported` 这类报错，形态完全不同。

用户明确要求原图直传时，启动降级后端只能算临时保底，不算修复——图片仍经文字转述，精度损失照旧。

### 声明之前先实测模型真的能看图

视觉能力不能靠模型名、厂商或参数表推断。声明前先发一张图，看它能不能准确读回。

生成带固定数字的测试图（不依赖任何图像库，用点阵字模直接拼 PNG）：

```python
import zlib, struct
from pathlib import Path

def make_png_text(text, w=240, h=60):
    FONT = {
        '4': ["10000","10000","10001","11111","00001","00001","00001"],
        '8': ["01110","10001","10001","01110","10001","10001","01110"],
        '2': ["01110","10001","00001","00110","01000","10000","11111"],
    }
    px = [[(255,255,255)]*w for _ in range(h)]
    x0, y0, s = 20, 15, 4
    for ch in text:
        pat = FONT.get(ch)
        if not pat:
            x0 += 6*s; continue
        for ry, row in enumerate(pat):
            for rx, bit in enumerate(row):
                if bit == '1':
                    for dy in range(s):
                        for dx in range(s):
                            yy, xx = y0+ry*s+dy, x0+rx*s+dx
                            if 0 <= yy < h and 0 <= xx < w:
                                px[yy][xx] = (0,0,0)
        x0 += 6*s
    raw = b"".join(b"\x00" + b"".join(bytes(c) for c in row) for row in px)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t+d) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")

Path("probe.png").write_bytes(make_png_text("482"))
```

发过去问「图中三位数字是什么，只回答数字」。答对了才声明 `supports_vision: true`。

三个容易踩的坑：

- **PNG 必须真的合法**。手拼的 base64 若字节不完整，上游报 `Could not decode image: broken data stream`，这个报错看起来像不支持图片，实际是图坏了；
- **纯色图不够**。问颜色只能区分「能不能接收图片」，区分不了「是不是真在看图」——答对颜色也可能只是猜的。带具体数字或文字才算证据；
- **一次答对不算稳定**。换一组数字再测一次，两次都对再下结论。

### 验证方法

```python
from agent.image_routing import decide_image_input_mode, _lookup_supports_vision
from hermes_cli.config import load_config_readonly

cfg = load_config_readonly()
print(decide_image_input_mode("<provider>", "<model>", cfg))   # 期望 native
print(_lookup_supports_vision("<provider>", "<model>", cfg))   # 期望 True
```

两个返回值必须分别是 `native` 与 `True`。只查第一个会漏掉图片被剥离的情况。

端到端确认：`hermes chat -q "..." --image <路径> --provider <名称> -m <模型> --oneshot`，输出里应出现「正在原生附加 N 张图片（模型支持视觉）」。出现「文字描述」或「视觉分析」字样说明走的是转述路径。

### 注意：`image_input_mode` 是全局开关

设成 `native` 后对所有模型生效，包括明确不支持视觉的通道（例如纯文本模型）。此类通道需要单独排除，否则图片直传会被上游拒绝。

## 二、 思考链开关的真实控制点

| 参数 | 作用接口 | 是否控制思考链 |
| :--- | :--- | :--- |
| `reasoning.effort` | `/v1/responses` | 是。取 `none` 关闭，其余挡位开启 |
| `chat_template_kwargs.enable_thinking` | `/v1/chat/completions` | 是（仅该接口） |
| `chat_template_kwargs.enable_thinking` | `/v1/responses` | **否，完全无效** |

SGLang 的 Responses 接口不读取 `chat_template_kwargs`，只认 `reasoning.effort`。在 `extra_body` 里写 `enable_thinking: false` 而实际走 Responses 接口时，思考链照常开启，且不产生任何告警。

### 全局挡位会覆盖单个 provider 的关闭意图

`agent.reasoning_effort` 是全局值，Hermes 每次请求都按它投影出 `reasoning.effort`。此时 provider 段里写什么 `enable_thinking` 都不影响结果。

只关某一个模型：

```yaml
agent:
  reasoning_overrides:
    <模型名>: false
```

`resolve_reasoning_config(cfg, model)` 的优先级是「逐模型覆盖 > 全局 `reasoning_effort`」。用 `False` 而非 `"none"` 表示关闭，因为 `or ""` 一类的空值兜底会把 `False` 变成空串从而静默重新开启。

### 验证方法

同一问题分两组请求，比较响应里有无 `reasoning` 输出项：

1. 只带待验证的参数；
2. 待验证参数 + `reasoning.effort`（复现 Hermes 实际发送的组合）。

Responses 接口的响应体里，思考内容在 `output[]` 中 `type == "reasoning"` 的项，正文在 `type == "message"` 的项。只看 `usage.output_tokens` 无法区分，因为思考 token 与正文 token 合并计数。

Chat Completions 接口的思考内容在 `choices[0].message.reasoning_content`；该字段为 `None` 只说明这个接口没返回，不能推断 Responses 接口也没开。

### 清理无效配置

确认某参数从未生效后，把它从配置里删掉，避免后续误判。保留一句「看似关闭实则开启」的配置，会让下一个人（或下一个会话）得出完全相反的结论。
