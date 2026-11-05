# dsh 会话日志取证

## 文件结构

- 位置：`$DSH_HOME/sessions/<cwd-slug>/session-<id>/session.v3.jsonl.zstd`（新）与 `session.jsonl.zstd`（旧）。`<cwd-slug>` 是会话工作目录的转义形式，同一工作目录的所有会话在同一目录下。
- 内容：一行一个 JSON 事件，**但整个文件是一串拼接的 zstd 帧**（每批追加写一帧）。因此：
  - `zlib.zstdDecompressSync(buf)` 只解出第一帧——1 MB 的日志会"成功"返回约 200 字节（只有 `{"type":"session",...}` 头），看起来像日志是空的。
  - `zlib.createZstdDecompress()` 流式解压同样在首帧结束后停止。
  - 正确做法：扫描帧魔数 `28 B5 2F FD`，逐帧解压后拼接（见 `scripts/dump-dsh-session.js`）。若一个魔数都没有，则文件是未压缩的 jsonl，按文本处理。
  - 写入中的帧可能被截断：单帧解压失败就跳过它，保留其余帧。
- 同一会话在 `$DSH_HOME/storages/session_projcache/sessions/<id>.json` 还有一份投影缓存，可作交叉印证，但**不完整**：以 `.zstd` 为准。

## 检索

导出到文件后用 Python 逐行 `json.loads`，按 `type` 分派后再打印；不要用 `grep + sort | uniq -c` 统计含中文的行（GNU sort 的多字节比较会失败）。

```python
for l in open(dump, encoding='utf-8', errors='replace'):
    o = json.loads(l)          # 多数行很大，按需截断再打印
```

## 事件类型速查

| type | 用途 |
|---|---|
| 首行 `{"type":"session",...}` | 会话头：id、createdAt、cwd、agentPreset |
| `user/message`、`agent/inbox/spliced` | 用户输入（含 rpcId、clientTimeZone） |
| `request/header` | 该轮实际生效的 provider / model / reasoningEffort / 工具清单——判断设置是否被应用的一手依据 |
| `assistant/attempt` | 流式尝试；`chunk.type == "finish"` 且 `reason.kind == "error"` 时带 `failure.{message,code,status}` |
| `tool/call`、`tool/result` | 工具调用与结果；`isError: true` 时正文即失败详情 |
| `turn/end` | 轮次终止原因：`error` / `interrupted` / 正常 |
| `step/start`、`step/end` | 步进边界，用于定位轮次 |

## 时间戳与叙述

`time` 为毫秒 epoch（UTC），换算到本机时区后再写进结论。定位失败时先看最后几个 `assistant/attempt` 的 `failure.message`，它会指明适配器与协议层（例如文案里出现 `Messages` 而不是 `API` 说明走的是 messages 协议），再回头对照 `request/header` 与 `settings.yaml`。
