---
name: hermes-state-db-hygiene
description: "用于清理 Hermes 状态数据库（state.db）残留、执行空间压缩与配置安全删除。"
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, sqlite, state.db, 数据库维护, 磁盘空间回收, vacuum, secure_delete]
    category: software-development
    related_skills: [hermes-agent, hermes-local-data-hygiene]
---

# Hermes 状态数据库维护与磁盘空间回收指南（state.db）

## 概述

指导维护 Hermes Agent 核心状态数据库（`$HERMES_HOME/state.db`）的物理存储空间、清理已删除会话滞留在底层的历史碎片，并配置 SQLite 运行期安全擦除参数。

**基本事实**：
```
运行 hermes sessions delete 只删除数据记录，不会自动释放磁盘物理文件占用的空间
```
在 Windows 安装环境（`%LOCALAPPDATA%\hermes`）下，运行删除会话命令仅在数据库内部将对应的数据行标记为已删除。由于 SQLite 默认未开启物理数据擦除功能，已删除会话的明文内容依然保存在数据库的空闲数据页（Freelist）与临时操作日志（`state.db-wal`）中，物理文件体积完全不会缩小。必须按照标准清理步骤操作，才能彻底释放磁盘空间并清除历史数据残留。

## 适用场景

- 执行会话删除后，磁盘空间未见释放，`state.db` 依然占用数十甚至数百兆空间
- 彻底清除包含敏感信息或测试数据的旧会话，防止从物理空闲页中提取出文本碎片
- 整理全文检索（FTS5）索引碎片，收缩数据库文件体积并检查数据库文件完整性

---

## 一、 会话删除后的物理残留情况

通过命令 `hermes sessions delete <会话ID> --yes` 删除会话后，底层依然存在以下数据残留：

1. **`state.db` 空闲数据页（Freelist Pages）**：
   - SQLite 默认关闭安全删除功能（`secure_delete=off`），被删除的内容依然保留在数据库未回收的空闲页中；
   - 实际测量案例：一个 73 MB 大小的数据库文件，其中包含 50.8 MiB 的空闲数据页。直接对文件进行字符扫描，仍能检索到 2.4 万次已删除会话的特征码，而数据库活跃记录中实际只有 5 条。
2. **临时操作日志文件（`state.db-wal`）**：
   - 保存了删除操作执行前的数据页镜像。只有在数据库执行检查点操作（Checkpoint，即把临时日志中的数据正式写回主数据库文件并清空日志）之后，这些旧数据才会被覆盖；
   - 运行 `PRAGMA wal_checkpoint(TRUNCATE);` 指令，可以在不关闭其他进程的前提下，将临时操作日志安全清空。
3. **运行时租约文件（`runtime/active_sessions.json`）**：
   - 该文件中可能仍残留已删除会话的租约标记和进程编号。
4. **内部关联记录表**：
   - 异步派发记录表 `async_delegations`、轮次租约表 `session_turn_leases`，以及记录已退出进程的网关服务心跳表 `gateway_heartbeats`，不会随会话删除而自动级联清理。
5. **文件系统中的临时文件与日志**：
   - 包括 `logs/process-results/*.json`、`images/` 截图缓存、`pastes/` 剪贴板文本、`spawn-trees/` 树结构；
   - 运行日志文件 `logs/agent.log`、`gui.log`、`errors.log` 以及用户终端输入历史 `.hermes_history`。

---

## 二、 彻底清理与空间回收的标准操作步骤

为了彻底回收物理磁盘空间并杜绝数据残留，必须按如下顺序执行：

### 第一步：备份需要保留的会话
在开始清理前，先为需要继续保留的会话导出完整备份：
```bash
hermes sessions export --format jsonl --session-id <保留的会话ID> --yes <备份文件路径>
```

### 第二步：清理关联孤立记录并清空临时操作日志
通过 Python 连接本地 SQLite 数据库（设置合理的超时时间 `busy_timeout`），清理内部关联表中的无主记录，并清空临时操作日志：
```sql
-- 执行检查点操作（Checkpoint），将日志内容同步回主文件并清空 WAL 文件
PRAGMA wal_checkpoint(TRUNCATE);
```

### 第三步：合并全文索引并执行物理空间整理（VACUUM）
运行系统自带的优化命令：
```bash
hermes sessions optimize
```
- 该命令会自动合并全文检索（FTS）索引分段，并触发 SQLite 底层的 `VACUUM` 物理空间重组，将多余的空闲页真正归还给操作系统；
- 实测效果对比：优化后数据库文件体积由 **73.0 MB 降至 0.7 MB**，空闲数据页从 13,002 页彻底归零。

### 第四步：清理相关临时文件并清空日志
1. 清理临时缓存目录中已失效会话的残留文件；
2. 清空运行日志文件（在终端中执行 `: > logs/agent.log` 把日志文件大小归零）；
3. **默认保留的重要文件**：技能审计记录文件 `skills/.curator_ledger.jsonl`、终端输入历史 `.hermes_history` 以及长久记忆暂存文件 `pending/memory/*.json` 不得静默删除。

---

## 三、 清理效果与完整性检查标准

清理完成后，必须逐项核对以下指标：
1. **数据库结构完整性**：运行 `PRAGMA quick_check;`，返回结果必须为 `ok`；
2. **全文检索索引一致性**：
   ```sql
   -- 检查全文索引中的记录是否与真实消息表完全对应（孤立记录必须为 0）
   select count(*) from messages_fts where rowid not in (select id from messages);
   select count(*) from messages where id not in (select rowid from messages_fts);
   ```
3. **空闲数据页彻底归零**：运行 `PRAGMA freelist_count;`，结果必须为 `0`；
4. **底层二进制扫描核对**：直接在数据库物理文件中检索已删除会话的特征码，确认文件中已不再包含已删除会话的旧文本。

---

## 四、 配置持久化安全删除（`secure_delete`）

1. **工作原理**：
   - `PRAGMA secure_delete` 是数据库连接级别的运行期参数，不保存在数据库文件头中，每次打开数据库连接时都需要设置；
   - 开启该选项后，SQLite 在删除数据时会用零填充被删除的数据区域，防止物理磁盘残留；
   - 全文检索影子表（FTS3/FTS5）不受该参数控制，其物理空间的彻底释放依然依赖于运行 `VACUUM`。
2. **永久开启配置**：
   - Hermes 提供了配置项支持，可以通过命令行开启：
     ```bash
     hermes config set database.secure_delete on
     ```
   - 正在运行的网关或后台服务将在下次重新启动时应用该参数。

---

## 五、 检查核对清单

- [ ] 操作前是否已对重要会话导出了数据备份？
- [ ] 是否执行了 `PRAGMA wal_checkpoint(TRUNCATE)` 执行检查点（Checkpoint）操作并清空操作日志？
- [ ] 是否执行了 `hermes sessions optimize` 真正回收磁盘物理空间（VACUUM）？
- [ ] 完整性检查中 `quick_check` 是否返回 `ok`，且 `freelist_count` 为 `0`？
