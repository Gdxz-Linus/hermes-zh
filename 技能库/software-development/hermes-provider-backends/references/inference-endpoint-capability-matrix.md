# 自建推理引擎（vLLM / SGLang / 兼容网关）端点能力核验

接入或排查自建推理引擎时，配置文件写对不等于能力真实可用。本文件是逐项核验能力的判据集：哪些项目必须逐路测试、每项用什么请求形状测试、拿到数据后如何判定。数值来自本机实测，换部署需按同一方法复测，不作永久事实使用。

## 一、同一引擎的不同端口，能力可以完全不同

**核心规则：`/v1/models` 返回同一个模型名、`owned_by` 也相同，不能推出两个端点的能力一致。** 同一套推理引擎、同一个模型文件，因部署版本、启动参数或前置代理不同，接口实现可以出现分叉。多路通道必须逐路执行同一套能力核验，禁止只测一路就对全部通道下结论。

本机实测的两路同款引擎（模型名、`owned_by`、`max_model_len` 全部相同）差异如下：

| 能力 | A 路 | B 路 |
| :--- | :--- | :--- |
| `/v1/chat/completions` | 可用 | 可用 |
| `/v1/responses` 纯字符串输入 | 可用 | 可用 |
| `/v1/responses` 的 `content` 数组（`input_text` / `input_image`） | **拒绝：校验要求 input 为字符串** | 可用 |
| 图片（`chat/completions` + `image_url`） | 可用，能准确识别颜色 | 可用 |
| 图片（`responses` + `input_image`） | 不可用 | 可用 |
| 工具调用（两条路径） | 可用 | 可用 |
| 推理强度档位（`responses` 顶层 `reasoning.effort`） | 参数被接受但接口实现不完整 | `max` 生效 |

判定与决策：

- **Responses 接口只接受纯字符串、而对话接口图片可用时，该通道的 `api_mode` 应配置为 `chat_completions`**。协议统一带来的收益远小于丢失图片能力的代价；两路协议不同不是缺陷，而是各自最优。
- 判据是错误原文：`input should be a valid string` 表示该实现的 `input` 只支持字符串；`supports text and image content only; got 'input_text'` 表示它认可的是另一套内容类型词表。两者都是实现分叉的确定证据，不是请求写错。
- 工具调用必须单独测试，不能因为文本能返回就推定可用。字符串输入加 `tools` 能正常产生 `function_call` 才算通过。

## 二、推理强度档位只认顶层 `reasoning_effort`

**核心规则：OpenAI 兼容的 vLLM 端点只解析顶层 `reasoning_effort`；嵌套的 `reasoning: {enabled, effort}` 被当作未知字段静默忽略，表现为 HTTP 200、思考照常，档位完全不生效。**

这是档位配置写了却没有反应的最常见原因：请求成功了，因此不会有人去怀疑参数形状。

| 发送形状 | 是否生效 |
| :--- | :--- |
| 顶层 `reasoning_effort: "high"` | 生效 |
| 顶层 `chat_template_kwargs: {reasoning_effort: 100}` | 生效，且整数档比文字档差异更明显 |
| 嵌套 `reasoning: {enabled: true, effort: "high"}` | **不生效**（被忽略） |
| 嵌套 `reasoning: {enabled: false}` 意图关闭思考 | **不生效**，思考照常运行 |

Hermes 侧的分叉原因与对策：

- **先确定通道命中了哪份供应商配置，不要凭通道名推断形状**：`get_provider_profile(通道名)` 返回 `custom` 即走通用路径。注意 `custom` 配置在**对话接口**下发出的就是顶层 `reasoning_effort`（`build_api_kwargs_extras` 写入 `top_level`），不是嵌套形状——这一点容易误判，判定必须以实际构造结果为凖，不要以直觉推断。
- 真正的两个踩坑点是 `custom` 配置自己的默认行为：
  1. **`default_reasoning_config` 默认 `medium`**，而 `medium` 是 vLLM 的拒绝值（见下小节）。用户未显式指定档位时首次请求就 400。
  2. **Responses 模式下档位按 OpenAI 的 Codex 阶梯钳制**（`codex_supported_efforts` 最高只到 `xhigh`），`max` 被**静默降级**为 `xhigh`，不报错、不告警。
- **正确修法是在 `$HERMES_HOME/plugins/model-providers/<通道名>/` 建供应商配置插件**，不是改 `config.yaml`。插件在该目录下以通道名注册即覆盖默认解析（`aliases=(...)` 可让多路通道共用一份）；声明两件事就能同时堵住上面两个口子：
  - `supported_reasoning_efforts(model)` 返回服务端真实词表。Responses 传输拿它做钳制，不声明则退回 Codex 阶梯、`max` 降级；
  - `default_reasoning_config()` 换个服务端认的档位（如 `high`），消除 `medium` 首请求 400；
  - 对话接口另在 `build_api_kwargs_extras` 返回 `({}, {"reasoning_effort": <钳制后的值>})`。
- 插件目录是 Hermes 正式扩展点，`hermes update` 不会清除，优于改产品源码。内置 `deepseek` 配置（`DEEPSEEK_V4_EFFORTS`）同样把 `medium` 当合法值，直接借用它不能解决问题，必须自己声明词表。
- **验证请求构造时必须复刻生产参数集**：`build_kwargs` 不传 `provider=<通道名>` 时，档位声明整条失效、退回 Codex 阶梯，会测出「`max` 被降级」而生产路径其实是好的。生产调用（`agent/chat_completion_helpers.py`）确实传了 `provider`，所以验证脚本必须同样传齐 `provider`、`provider_profile`、`base_url`；缺一项结论即作废。

### `medium` 在 vLLM 上是拒绝值

错误原文：`reasoning_effort must be low, high, xhigh, max, or an integer within [1, 100]`。

**陷阱在于 Hermes 的 `DEEPSEEK_V4_EFFORTS` 把 `medium` 声明为合法值**（`("low", "medium", "high", "max")`）。即使请求成功命中了内置 deepseek 供应商配置、形状也正确，选到 `medium` 仍会被 vLLM 以 HTTP 400 拒绝。

- 可用档位只有 `low`、`high`、`xhigh`、`max` 以及 1 至 100 的整数。
- 内置配置的 `DEEPSEEK_V4_OVERRIDES = {"xhigh": "max"}` 会把 `xhigh` 改写为 `max` 再发送，但这只在走该配置时生效，通用路径不会改写。

## 三、思考 token 计入输出上限，上限不足时正文被截断

**核心规则：`max_output_tokens` 是思考 token 与正文 token 的合合计上限。思考量不可预测，上限偏小时思考先耗尽，正文被截断甚至为空。**

同一段要求写一千字的提示，输出上限与截断率实测：

| 输出上限 | 未完成次数 | 说明 |
| :--- | ---: | :--- |
| 4000 | 4 / 10 | 思考耗尽 4000，正文 0 至 1500 字 |
| 16000 | 0 / 6 | 思考峰值约 4000，余量充足 |
| 65536 | 0 / 6 | 配置实际取值 |

- 这是输出上限必须给足的实证理由，与风格层的「64K 留给核心推导」是两件事：前者是物理约束，后者是使用纪律。
- **`extra_body.max_output_tokens` 会覆盖请求自身的上限**。SDK 把 `extra_body` 并入请求体，实测显式传 `max_output_tokens: 200` 而 `extra_body` 写 65536 时，最终发出去的取值是 65536。好处是内部临时降低上限的逻辑无法覆盖它，代价是想做小上限测试时必须临时去掉这一项。

## 四、流式结束有四种结局，不要把正常截断误判为连接断裂

看到没有 `[DONE]`、没有 `response.completed` 就判定流中断，是错误的。逐个读取尾部事件：

| 尾部事件 | 含义 | 处理 |
| :--- | :--- | :--- |
| `response.completed` | 正常结束 | 读取 `usage` 记录用量 |
| `response.incomplete` | **输出上限耗尽的正常截断**，`incomplete_details` 给出原因 | 加大 `max_output_tokens`，不要当作网络故障 |
| 只有部分 delta 后连接异常或 `RemoteProtocolError` | 真实断裂 | 重试或排查服务端 |
| 全程无 `[DONE]`（vLLM 常态） | 正常，vLLM 用 `response.completed` 收尾即可 | 不要以 `[DONE]` 缺失作为失败判据 |

`response.incomplete` 且正文为空、`reasoning_tokens` 等于上限值，就是思考占用全部输出配额的确证。

## 五、测速方法：首字延迟与生成速率必须分开计算

- **首字延迟**是请求发出到第一个 delta 到达的时间。**生成速率**取第一个 delta 到最后一个 delta 的时间窗口，用 `output_tokens` 除以窗口秒数。把首字延迟算进速率会让短回答的速率被严重低估（30 token 的回答混入 1 秒等待，速率会从 150 降到 30）。
- **短输出不具代表性**：单次 30 至 50 token 的回答，启动开销占比过大，速率必然偏低。判断引擎吞吐量要用 1000 token 以上的输出。
- **同一提示必须多跑几次取中位数**：长回答速率在单次之间可差一倍（服务端负载波动），单次数字不能下结论。
- 思考过程（`reasoning_text.delta`）与正文（`output_text.delta`）是两类事件，统计首字延迟时要说明计算的是哪一种。

## 六、能力核验脚本

`scripts/inference_endpoint_probe.py` 把上述六组证据一次执行完毕：端点身份、两条协议路径、内容形状矩阵、图片实测（纯色 PNG 让模型报颜色）、推理档位中位数、输出上限截断率。修改通道或更换引擎后先运行它，不要读配置推断。

```bash
python scripts/inference_endpoint_probe.py --base http://<host>:<port> --key-env <密钥环境变量> --model <模型名>
```
