# Hermes 安装布局与环境残留判据（Windows 本机）

## 布局

- 运行副本：`$LOCALAPPDATA/hermes/installs/<install_id>/environments/<env_hash>/`
  - `venv/`：uv 建，常不含 `pip.exe`；`hermes doctor` 的 `Runtime venv staged` 行指向它；`site-packages/hermes_agent-*.dist-info` 为可编辑安装（版本可能报 `0.0.0`）。
  - `workspace/`：源码副本，可编辑安装的落点；无 `.git`，不含 `activate`、`.python-version`。
  - `bootstrap/`、`pm-runtime/`、`facts.json`（记录 extras 与 `uv.lock` 路径）。
- 源码母本：`$LOCALAPPDATA/hermes/hermes-agent/`（git 仓库，升级时被 pull）。判据：`git -C <dir> log -1 --format='%h %cd %s'` 的 sha 与 `hermes --version` 的 `upstream <sha>` 一致 → 保留。
- 启动器：`$LOCALAPPDATA/hermes/bin/`（`hermes.exe`、`hermes-acp.exe`、`hermes.cmd`）。`.cmd` 是 base64 包裹的 Python 引导，解码后可见插入 `sys.path` 的源码树与 `hermes_cli.main:main`。
- 工具链：`tools/<name>-<version>-win32-x64/`（chromium、ffmpeg、node、npm、python、uv、ripgrep、agent-browser）、`node/`、`lsp/node_modules/`、`cache/uv/`。

## 残留判据（可清）

| 对象 | 判据 | 机制 |
|---|---|---|
| `hermes-agent/venv/` | 内含 `hermes_agent-<旧版本>.dist-info`，且不是 doctor 报的生效环境 | 新布局不再使用它，但它在 PATH 中会接管 `pip`，造成 `python` 与 `pip` 来自不同 Python 版本 |
| `hermes-agent/.hermes-runtime/python/cpython-*` | 旧 Python 运行时目录 | 启动器已改用 `tools/python-<版本>` |
| `bin/*.deleteme` | 升级替换时改名待删 | 无进程持有即可删 |
| `tools/<name>-<旧版本>-win32-x64/` | 该工具的 `-v` 报另一版本，被 PATH 靠前的同名目录遮蔽 | 不生效，仅占体积 |
| `config.yaml` 中 `platform_toolsets.<平台>` | 平台键不在运行源码 `hermes_cli/platforms.py :: PLATFORMS` | 每轮启动写一条 tools_config WARNING，工具集不可用 |

## 保留判据

- 源码树 `hermes-agent/`、`cache/uv/`（承担离线安装能力）、`skills/`、`memories/`、`.env`、`auth.json`、`logs/`（诊断依据）、`.hermes_history`、`skills/.curator_ledger.jsonl`。
- 被 PATH 引用的 `tools/` 工具链、`lsp/node_modules/`。
- 状态库：`state.db`、`kanban.db`、`projects.db`、`shared-state.db`、`cron/executions.db`（按会话残留清理流程处理，不整体删除）。
- 体积大 ≠ 残留：`tools/`、`cache/uv/`、`lsp/node_modules/` 属运行数据，报告中单列并说明性质，不计入残留。

## 清理顺序与约束

1. 先停掉全部 Hermes 进程（按 PID 逐个确认）；运行中进程持有 PATH 指向的 venv 与各状态库句柄。
2. 清环境与文件类残留（上表第 1–4 项），删目录用绝对路径，逐项记录回收体积。
3. 配置类残留用 `hermes tools` 重配或 `hermes config unset platform_toolsets.<平台>`，不手改 YAML。
4. 复核：`hermes --version`；`hermes doctor`（Runtime venv staged 指向新环境、Config version up to date）；`hermes chat -Q -q "reply: ok"` 加一次工具调用（`运行 echo <token> 并只回复它的输出`）；`python -c "import sys; print(sys.executable)"` 与 `pip -V` 指向同一环境；`grep -c "no valid toolsets configured" logs/agent.log` 不再增长。

## 陷阱

- `du -sh` 在含 venv / node_modules 的 Windows 树上会超时；改用 `scripts/tree_size.py`。
- MSYS 下对已随父 shell 退出的后台进程 `kill <pid>` 会报 `No such process`；用 `ps -W | grep -c <name>` 复核而非看 kill 返回值。
- 体积与条数是强校验项，一律取实测输出（`ls -la`、脚本输出、`grep -c`），不估算。
- 报告中的「旧版残留」必须区分环境/配置残留与正常运行数据；把运行数据报成垃圾，或把运行环境当残留，都会导致错误处理。
