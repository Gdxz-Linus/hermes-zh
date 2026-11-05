# 自建服务端型后端：部署与运维实录

适用于服务型后端（记忆族的 openviking，以及 mem0 / supermemory 的自建形态）。下列数值与路径来自本机实测，换机器时按同方法复测，不要当成永久事实。

## 一、先分清「插件内置 ≠ 服务内置」

插件目录（`hermes-agent/plugins/memory/<name>/`）里只含客户端接入代码。判据：

```bash
grep -n "shutil.which" hermes-agent/plugins/memory/<name>/__init__.py
```

命中形如 `server_cmd = shutil.which("<入口>")`，下一行就是 `return _LOCAL_SERVER_FAILED, "... was not found on PATH. Start it manually"` —— 即插件**不会替你装服务端**，只在 PATH 上找。

## 二、装进独立环境

```bash
UV="$LOCALAPPDATA/hermes/bin/uv.exe"
"$UV" venv --python 3.13 "$LOCALAPPDATA/hermes/tools/<name>-venv"
"$UV" pip install --python "$LOCALAPPDATA/hermes/tools/<name>-venv/Scripts/python.exe" "<包>[<可选依赖>]"
```

- 版本钉住。服务端可能要求特定解释器（例：火山引擎 Ark SDK 在 3.14 上仍吐 Pydantic V1 兼容告警，官方建议 3.13 及以下）。
- 可选依赖里带需要编译的包时，预留分钟级时间并确认本机有 C++ 工具链；无预编译轮子会在这一步卡住（本机实测：一个可选依赖源码编译耗时 7 分钟）。
- 装完 `Scripts/` 下会同时出现服务端入口、CLI、SDK 入口三个 exe，分别是给服务端、命令行、脚本用的。

## 三、让插件找得到入口

```bash
cp "$LOCALAPPDATA/hermes/tools/<name>-venv/Scripts/<入口>.exe" "$LOCALAPPDATA/hermes/bin/"
```

**不要写 `.cmd` / `.bat` 包装**：包装会多一层 `cmd.exe` 常驻（进程链从三层变四层），且 `shutil.which()` 返回的路径后缀会变成 `.EXE`，路径不再可靠。真实 exe 放上去即可，不需要改 PATH。

验：`shutil.which("<入口>")` 应返回 `...\bin\<入口>.EXE`，且进程链只有「入口 → 工作进程 → 监听进程」。

## 四、配置模板（openviking 实测）

`~/.openviking/ov.conf`：分四大块 —— `storage` / `embedding` / `vlm` / `server`。

```json
{
  "server":    { "host": "127.0.0.1", "port": 1933 },
  "storage":   { "workspace": "C:/openviking/data",
                 "vectordb": { "name": "context", "backend": "local" },
                 "agfs":    { "backend": "local" } },
  "embedding": { "dense": { "provider": "local", "model": "bge-small-zh-v1.5-f16", "dimension": 512 } },
  "vlm":       { "provider": "openai", "model": "<模型名>",
                 "api_base": "http://<自有网关>/v1", "api_key": "<密钥>" }
}
```

- `workspace` 必须是纯 ASCII 路径（见铁律 3）。`agfs` / `vectordb` 若显式写了 `path`，服务端会告警「deprecated and will be ignored」并改用 `workspace`，写与不写等价，不如只写 `workspace`。
- `provider: "local"` 走本地 GGUF 嵌入，显式声明 `dimension` 且必须与该模型的固定维度一致（不一致直接抛错）。模型自动下载到家目录缓存，首次启动前可先手工下载以区分「网络问题」与「配置问题」。
  - 下载源与文件名是硬编码在 `openviking/models/embedder/local_embedders.py` 的 `LOCAL_DENSE_MODEL_SPECS`（缓存目录常量 `DEFAULT_LOCAL_MODEL_CACHE_DIR = "~/.cache/openviking/models"`，默认模型只有一个，维度与文件名都写死）。手工预拉时按那张表构造 URL，不要猜文件名。
  - **huggingface.co 直连在本机不可达，经代理也只拿到 206 空 body（`size_download=0`）——别把「HTTP 200/000 + 0 字节」当成下载成功。** 可用的是镜像 `hf-mirror.com`（直连，实测 47.9 MB / 5.3 s）：
    ```bash
    curl -sL --max-time 300 -o "$HOME/.cache/openviking/models/<文件名>" \
      "https://hf-mirror.com/<repo>/resolve/main/<文件名>" -w "HTTP %{http_code}  %{size_download} 字节\n"
    ```
    落盘后用 `ls -la` 核对字节数；零字节文件会让后续 `embedding` 校验失败且错误直接抛在配置层，不易回溯到下载源。
- 客户端连接文件 `~/.openviking/ovcli.conf`：`{"url": "http://127.0.0.1:1933"}`。
- Hermes 侧只认 `.env` 里的端点：`OPENVIKING_ENDPOINT=http://127.0.0.1:1933`。没这一行时 `is_available()` 返回假、`unavailable_reason()` 可能是空串，表现为「配置了却没用」。

## 五、CLI 首次使用要先设显示语言

任何子命令在未设语言时直接拒绝执行，提示 `Run one of: ov language en / ov language zh-CN`。先跑一次 `ov language zh-CN`，并把 `OPENVIKING_CLI_CONFIG_FILE` 指向 `ovcli.conf`，否则命令会连不上。

常用：`ls <viking:// 路径>`、`find "<查询>"`、`cat <uri>`、`tui`；`-o json` 换输出格式。

`viking_remember` 在服务端不可达时返回 `{"error": "content is required"}` —— 这条报错是**误导**的，真实原因是没连上服务端，别去检查参数。

## 六、模型侧能力边界

服务端要的两项能力在普通 OpenAI 兼容网关上未必提供，动手前各探一次：

| 能力 | 探测 | 缺了会怎样 |
|---|---|---|
| 嵌入 `POST /v1/embeddings` | 404 | 必须用本地 GGUF 嵌入（`provider: "local"`），且 `sparse` / `hybrid` 只对部分厂商实现，本地只有 dense |
| 重排 `POST /v1/rerank` | 404 | 精排留空，检索质量靠目录递归 + 分级加载（摘要 / 概览 / 全文）弥补 |
| 抽取用对话 `POST /v1/chat/completions` | 200 即有 | 没有则写入与自动抽取不工作 |

## 七、冰启动复验（必做）

服务端日志是**追加**写的，多次启动会叠加，直接统计必然误判。正确步骤：

```bash
# 1. 按监听端口拿 PID，按命令行特征收掉
netstat -ano | grep ":1933.*LISTENING"
# 2. 删除服务端日志（插件自动拉起时写在 $HERMES_HOME/logs/<name>-server.log）
# 3. 单跑一次初始化（走插件自己的路径，而不是直接跑 exe）
# 4. 数四项：初始化完成次数、监听就绪次数、锁冲突次数、噪音行数
# 5. curl /health，期望 {"status":"ok","healthy":true,"version":"..."}
```

四项都应满足：启动 1 次、就绪 1 次、锁冲突 0、噪音 0。任何一项大于 1 或非零，先怀疑「一次初始化派生了多个服务端」，不要先怀疑配置。

## 八、失败形态对照

| 现象 | 真实原因 |
|---|---|
| 每次新会话报「未在 60 秒内可达」，随后一切用不了 | 一次初始化派生多个服务端，在单实例锁上反复自杀重试 |
| 手动拉起报 `No module named 'pydantic_core._pydantic_core'` | 跨 Python 版本环境变量污染：父进程（如 3.14）的 `PYTHONPATH`、`PYTHONHOME` 或 `VIRTUAL_ENV` 泄漏进子虚拟环境（3.13）。拉起时必须显式 pop 掉这三个环境变量 |
| 服务端日志报 `long_term failed: Error code: 503` | 抽取用模型接口地址或端口失效（如配置了旧端口 8000，而网关已切换到 8006），检查 `ov.conf` 里的 `api_base` 与活动网关是否一致 |
| 日志刷 `The system cannot find the path specified.`（无时间戳、无级别，裸文本） | 每个短命派生进程临死前往共享日志写的；行数按派生次数叠加，不是固定配置 |
| 服务端日志出现 `DataDirectoryLocked: Another OpenViking process is already using the data directory` | 单实例保护生效，非故障；配合上两条一起看 |
| 启动即 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x..` | 数据目录路径含非 ASCII 字符 |
| 命令返回 `content is required` | 服务端不可达，不是参数问题 |
| 插件报「端口被占用但未通过 /health」 | 前一实例仍在跑，或监听者不是该服务；插件拒绝重叠启动是正确行为 |
| 桌面端报「Memory provider '<name>' is not installed」但插件目录明明存在 | 插件的 `__init__.py` 被裁剪过的文件覆盖，丢失了 `register_memory_provider` / `MemoryProvider` 接口——Hermes 靠扫描该文件前 8 KB 的文本来发现记忆提供方。严禁用 schema-only 桩文件覆盖插件 `__init__.py`：应从原版备份恢复完整文件，再对 schema 描述做定点替换；修复后用 `plugins.memory.find_provider_dir(name)` 验证返回真实路径 |
| 服务端手动重启成功但下次会话仍报不可用 | Hermes 记录了自动安装连续失败计数，按指数退避压制重试；修复根因后必须删除主目录下的失败计数戳，否则退避窗口内新会话继续被压制 |
