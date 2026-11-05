# Codex 自定义模型通道完整配置

接入自定义模型后，Codex 内置清单里没有这个模型，会退回保守默认值并每次启动告警。本文件给出完整可用的配置模板与字段含义。

## 一、 三份文件的关系

| 文件 | 作用 | 位置 |
| :--- | :--- | :--- |
| `config.toml` | 默认通道、通道定义、指向模型目录 | `~/.codex/config.toml` |
| 模型目录 JSON | 声明该模型的上下文窗口与推理挡位 | 任意路径，由 `model_catalog_json` 指向 |
| 环境变量 | 存放密钥本体 | 系统环境或 `.env` |

## 二、 config.toml 模板

```toml
model = "<模型标识>"
model_provider = "<通道名称>"
model_context_window = 1048576
model_catalog_json = "<绝对路径>/model-catalogs/<名称>.json"
model_reasoning_effort = "high"

[model_providers.<通道名称>]
name = "<显示名称>"
base_url = "http://<主机>:<端口>/v1"
wire_api = "responses"          # 或 chat_completions，必须与上游实际接口一致
env_key = "<密钥环境变量名>"     # 密钥本体不写进配置文件
```

顶层 `model_provider` 的值必须与 `[model_providers.<名称>]` 方括号内的名称逐字一致，大小写敏感。

## 三、 模型目录 JSON 模板

```json
{
  "models": [
    {
      "slug": "<模型标识，与 config.toml 的 model 一致>",
      "display_name": "<界面显示名>",
      "description": "<一句话说明>",
      "default_reasoning_level": "high",
      "supported_reasoning_levels": [
        { "effort": "low", "description": "快速响应" },
        { "effort": "medium", "description": "中等思考" },
        { "effort": "high", "description": "深度思考" }
      ],
      "shell_type": "default",
      "visibility": "list",
      "supported_in_api": true,
      "priority": 0,
      "base_instructions": "<该模型的角色设定>",
      "supports_reasoning_summaries": false,
      "default_reasoning_summary": "none",
      "support_verbosity": false,
      "truncation_policy": { "mode": "tokens", "limit": 10000 },
      "supports_parallel_tool_calls": true,
      "experimental_supported_tools": [],
      "prefer_websockets": false,
      "apply_patch_tool_type": "freeform",
      "web_search_tool_type": "text",
      "supports_image_detail_original": false,
      "input_modalities": ["text"],
      "context_window": 1048576,
      "max_context_window": 1048576,
      "effective_context_window_percent": 95,
      "auto_compact_token_limit": null,
      "supports_search_tool": true
    }
  ]
}
```

## 四、 字段含义与取值约束

| 字段 | 说明 | 取值约束 |
| :--- | :--- | :--- |
| `slug` | 模型标识，Codex 用它匹配 `config.toml` 的 `model` | 必须与上游接受的模型名一致 |
| `context_window` / `max_context_window` | 客户端认为的上下文窗口 | 不超过上游真实能力 |
| `effective_context_window_percent` | 实际可用比例，留出余量 | 常用 95 |
| `supported_reasoning_levels` | 界面可选的推理挡位 | 只能列上游真正支持的挡位 |
| `shell_type` | 工具调用的 shell 类型 | `default` 或 `shell_command` |
| `apply_patch_tool_type` | 补丁工具类型 | **只能 `freeform`** |
| `truncation_policy` | 内容截断策略 | `mode` 取 `tokens` 或 `bytes` |
| `input_modalities` | 支持的输入类型 | `["text"]` 或 `["text", "image"]` |

## 五、 四个必踩的字段陷阱

**`apply_patch_tool_type` 写 `function` 会直接拒绝启动。** 报错形如 `unknown variant \`function\`, expected \`freeform\``。该字段只有 `freeform` 一个合法值，不要按字面推断还有 `function` 这种对称选项。

**`shell_type` 取错导致工具调用报 `incompatible payload`。** 现象是模型反复尝试执行命令，每次都以 `Fatal error: tool exec invoked with incompatible payload` 失败，最终模型放弃并回复「环境只读」。这类报错看起来像沙箱权限问题，实际是 shell 类型与模型能力声明不匹配。

**`supported_reasoning_levels` 列了上游不支持的挡位会被拒。** 声明挡位前先确认上游真能接受该值，否则选中该挡位时请求直接失败。

**`input_modalities` 加 `image` 前必须先实测上游的带图请求。** 该字段不只是能力声明，它会改变客户端发出的请求内容。声明后 Codex 才开始在请求里附带图片数据；而上游若在未收到输出上限时按剩余上下文推算输出上限，带图请求就会因总数超窗被拒。判定方法与抓包步骤见 `SKILL.md` 第三节第 7 条。

## 六、 输出上限不受模型目录控制

模型目录里的 `truncation_policy`、`output_token_limit`、`max_output_tokens` 三个键都**不会**让 Codex 在请求体里发送输出上限字段。抓包可见请求体顶层只有 `model`、`stream`、`input`、`tools`、`tool_choice`、`parallel_tool_calls`、`reasoning`、`store`、`include`、`prompt_cache_key`、`client_metadata`。

要控制输出上限，只能改上游服务端的默认值。客户端侧反复试这几个键是无效功。

## 七、 验证顺序

1. `codex exec --strict-config --skip-git-repo-check "test"` —— 未知字段与 JSON 解析错误在这一步暴露，报错会指出文件与行号；
2. 简单问答 —— 确认通道连通、密钥有效、模型名被接受；
3. 实际编码任务 —— 确认工具调用链路正常。

第 3 步失败时先换一个已知可用的通道跑同一任务做对照，再判断故障属于模型通道还是沙箱层。

## 八、 运行后会改写配置文件

Codex 运行时会把 `config.toml` 的行尾统一为 LF，并自动追加 `[projects.'<工作目录>'] trust_level = "trusted"`。同步备份前先删掉指向已删除目录的 `[projects.*]` 条目，再以系统版为准回写工作目录，否则哈希永远对不上。
