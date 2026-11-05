# 会话内容在本机的保存位置

路径均相对 `$LOCALAPPDATA/hermes`。删除会话只清库内行，下列位置不会同步。

## 库内（state.db）

| 对象 | 说明 | 处理 |
|---|---|---|
| `sessions` / `messages` | 会话本体，`hermes sessions delete` 会删 | 无需处理 |
| `messages_fts*` | 全文索引，随行删除；trigram 不索引 `role='tool'` | 双向孤儿为 0 即一致 |
| 空闲页 | `secure_delete=0` 导致正文以旧字节形式留在空闲页 | `hermes sessions optimize` 回收 |
| `async_delegations` | 多列引用来源会话（`origin_session`、`parent_session_id` 等），删除会话不清理 | 只删已完成且已投递的行 |
| `session_turn_leases` | 已删会话的过期租约行仍在 | 按 `conversation_id` 过滤删除 |
| `gateway_heartbeats` | 历史进程心跳，进程退出不清理 | 删非活动 PID 行 |
| `system_prompts` | 按 hash 存储，`sessions.system_prompt_hash` 引用 | 不单独删 |

`state.db-wal` 保存删除前的页镜像（实测同一会话编号出现上万次），`pragma wal_checkpoint(TRUNCATE)` 后归零。

## 库外（文件）

| 路径 | 内容 | 处理 |
|---|---|---|
| `sessions/` | 会话导出/附属文件 | 删除会话后应为空 |
| `runtime/active_sessions.json` | 运行期租约（pid、session_id、live_session_id） | 移除已删会话条目，保留当前会话 |
| `desktop/interrupted_turns.json` | 未完成轮次（含提示词正文） | 仅当前会话时应为单条 |
| `logs/agent.log`、`logs/gui.log`、`logs/errors.log` | 运行日志，含完整会话内容 | 截断即丢失历史诊断，需在报告中说明 |
| `logs/process-results/*.json` | 工具调用产物缓存 | 可直接删除（属旧会话） |
| `logs/curator/` | 技能整理运行记录 | 按内容判定 |
| `images/*.png`、`pastes/*.txt` | 会话内截图与粘贴正文，文件名带会话时间戳前缀 | 按时间戳归属旧会话即删 |
| `spawn-trees/<ui_session_id>/` | 子代理派生记录与索引 | 随所属会话删除 |
| `skills/.curator_ledger.jsonl` | 技能变更审计，`evidence.session_id` 为来源字段 | 保留（删则失去溯源），列保留项 |
| `.hermes_history` | 命令行输入历史 | 保留（非会话内容），列保留项 |
| `pending/memory/*.json` | 待确认的记忆变更 | 独立子系统，保留 |
| `backups/`、`cron/output/`、`state/` | 配置备份、定时任务输出、心跳文件 | 无会话正文，通常不动 |

## 复核命令速查

```bash
cd "$LOCALAPPDATA/hermes"
hermes sessions list; hermes sessions stats
ls sessions | wc -l
cat runtime/active_sessions.json
python -c "import sqlite3;c=sqlite3.connect('file:state.db?mode=ro',uri=True);print(c.execute('pragma quick_check').fetchone(),c.execute('pragma freelist_count').fetchone(),c.execute('pragma page_count').fetchone())"
rg -l --hidden --no-messages -g '!hermes-agent/**' -g '!node/**' -g '!bin/**' -g '!state.db*' '<session_id_regex>' .
ps -W | grep -i hermes
```
