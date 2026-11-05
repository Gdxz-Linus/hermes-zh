# 系统提示词源码汉化：锚点清单与判别方法

汉化 `agent/` 下生成系统提示词的源码时，有一批字符串被其他代码按字面解析。汉化它们不会引发语法错误，却会让解析器静默失效。本文件给出完整锚点清单与判别方法。

## 一、 判别方法

对每个待改字符串先执行：

```bash
rg --fixed-strings "<待改字符串>" -g '*.py' -g '*.ts' --glob '!tests' --glob '!node_modules'
```

排除目标文件自身后，若命中行出现下列任一特征，该字符串**必须保持英文原样**，只汉化其后的说明文字：

| 特征 | 含义 |
| :--- | :--- |
| `re.compile` / `re.search` / `re.match` | 正则匹配 |
| `.startswith(` / `.endswith(` / `.index(` / `.rfind(` / `.split(` / `.rsplit(` | 前缀或分隔符定位 |
| `in <字符串>` 判断（相等或包含） | 内容相等比较 |
| `SUBSTR` / `INSTR` / `_sql_starts_with` / `_sql_after_marker` | 数据库 SQL 字面匹配 |
| `hermes_state_common.py` | 会话预览与持久化层 |

## 二、 prompt_builder.py 的锚点

| 锚点 | 解析方 |
| :--- | :--- |
| `[names only]` | `agent/skills_index_delta.py`、`hermes_cli/prompt_size.py` 正则 |
| `# Project Context` | `evals/token_accounting/worktree_prompt_prefix.py` |
| `Host:` / `User home directory:` / `Current working directory:` / `Scratch directory:` | `agent/surface_switch.py` 逐行前缀匹配 |
| `<available_skills>` / `</available_skills>` | `agent/context_breakdown.py` 正则 |
| `<tool_persistence>` 等 XML 段落标签 | 提示词结构化解析 |
| `## Skill Safety Rule` | `hermes_cli/sessions_cmd.py` 会话修复判定 |
| `RUNTIME_ENVIRONMENT_HEADING` / `RUNTIME_ENVIRONMENT_END` | 提示词持久化边界校验 |
| `STEER_MARKER_OPEN` / `STEER_MARKER_CLOSE` | 纠偏消息识别，桌面端端到端用例 |

## 三、 system_prompt.py 的锚点

| 锚点 | 解析方 |
| :--- | :--- |
| `Conversation started:` | 自身插件段位置校验 |
| `Today's date (as of the last context rebuild):` | 同上 |
| `Timezone:` | 时间行生成 |
| `Session ID` / `Model` / `Provider` | `agent/conversation_loop.py` 提示词一致性校验 |
| `Platform` | `agent/surface_switch.py` 会话界面读取 |
| `Current working directory` / `User home directory` | `agent/surface_switch.py` 宿主行读取 |

## 四、 coding_context.py 的锚点

| 锚点 | 解析方 |
| :--- | :--- |
| `Workspace (snapshot at session start` | `evals/token_accounting/worktree_prompt_prefix.py` |
| `- Root: ` | `agent/system_prompt.py` 解析工作区根路径 |
| `- Worktree:` / `- Branch:` / `- Status:` | 提示词结构校验 |

注意：`_EDIT_FORMAT_GUIDANCE` 字典的键是模型名子串（`gpt`、`codex`、`claude` 等），只汉化其值，键绝不可动。

## 五、 context_compressor.py 的持久化常量

以下常量会被写入数据库并被 SQL 按字面匹配，**全部保持英文原样**：

| 常量 | 依赖方 |
| :--- | :--- |
| `SUMMARY_PREFIX` | `hermes_state_common.py` 用 `split("Do NOT answer")` 切分 |
| `LEGACY_SUMMARY_PREFIX` | SQL 前缀匹配 |
| `HISTORICAL_TASK_HEADING` | 摘要模板章节名，被任务快照正则匹配 |
| `_SUMMARY_END_MARKER` | SQL 定位摘要结束位置 |
| `_MERGED_PRIOR_CONTEXT_HEADER` | 按长度切片 |
| `_MERGED_SUMMARY_DELIMITER` | SQL `INSTR` 定位 |
| `_PRUNED_TOOL_PLACEHOLDER` | 内容相等比较判定是否已裁剪 |
| `_NO_USER_TASK_SENTINEL` | 摘要归属校验的比对基准 |
| `_INFLIGHT_TASK_REPLAY_HEADER` | 自身 `rsplit` 定位 |
| `_PRUNED_SKILLS_SECTION_HEADING` | 章节重复检测 |
| `COMPRESSION_CONTINUATION_USER_CONTENT` | 合成用户行识别集合 |
| `_LEGACY_COMPRESSION_CONTINUATION_USER_CONTENT` | 同上 |
| `_LEAN_USER_MESSAGES_HEADING` | 自身 `in` 定位（3 处） |
| `_LEAN_ANCHOR_HEADING` | 自身 `in` 定位（3 处） |
| `_LEGACY_ACTIVE_TASK_HEADING` | 正则匹配 |
| `_HISTORICAL_SUMMARY_PREFIXES`（元组，多条） | 旧版本会话兼容，逐字节固定 |

可汉化的相邻项：`_LEAN_RECOVERY_HEADING`、`_LEAN_SESSION_LOG_HEADING`、`_COMPRESSION_NOTE`、摘要模板各章节标题、摘要生成提示词正文、`MAX_ITERATIONS_SUMMARY_REQUEST`。

**两个容易判反的项，已实测确认：**

- `_LEAN_USER_MESSAGES_HEADING`、`_LEAN_ANCHOR_HEADING` 看着像纯展示的章节标题，实际被自身代码用 `in` 定位（各 3 处），属于锚点。不要因为「它只是个小标题」就当成可翻。
- `MAX_ITERATIONS_SUMMARY_REQUEST` 看着像内部请求常量，实际只作为请求正文送入模型（`append_message(..., {"content": MAX_ITERATIONS_SUMMARY_REQUEST})`），无任何解析方，**可翻**。

判别不能靠名字或直觉，必须逐个 `grep -n "<常量名>"` 看引用行是否出现 `find`／`split`／`startswith`／`in`／`==`／正则。

## 六、 background_review.py 的锚点

该文件有三个提示词由共享块拼接而成：`_MEMORY_ROUTING_BLOCK`、`_LESSON_LAYER_BLOCK`、`_DO_NOT_CAPTURE_BLOCK`。汉化必须同时改共享块与引用它的提示词，否则三个提示词里会出现中英混排。

| 锚点 | 解析方 |
| :--- | :--- |
| `Nothing to save.` | 模型约定回复，测试用例以此字符串判定「无内容可存」 |
| `USER.md` / `MEMORY.md` | 记忆文件名，模型据此选择 `target='user'` 或 `target='memory'` |
| `SKILL.md` / `references/` / `templates/` / `scripts/` | 技能目录结构，`skill_manage` 的 `file_path` 前缀 |
| `skill_view` / `skill_manage` / `skills_list` / `read_file` / `search_files` | 工具名，提示词据此约束可用工具 |
| `_PROMPT_NAME_BY_SCOPE` 映射表 | 四种作用域到提示词常量名的映射，键为布尔元组，绝不可动 |

`Nothing to save.` 属于一类容易被忽略的锚点：**模型约定回复标记**。模型被要求在无内容可存时原样回复某个固定字符串，测试与后续流程据此判定。同类标记还有 `None`、`[REDACTED]`。汉化时这类标记必须逐字保留，只译其周围的说明文字。

## 六之二、 curator.py 的锚点

该文件的提示词要求模型输出一段 YAML 供下游代码解析，因此锚点密度最高。汉化正文时下列内容逐字保留：

| 类别 | 锚点 |
| :--- | :--- |
| 结构化输出契约 | `## Structured summary (required)`、`consolidations:`、`prunings:`、`from:`、`into:`、`name:`、`reason:`、` ```yaml ` 围栏 |
| 工具与参数名 | `skill_manage`、`skill_view`、`skills_list`、`absorbed_into`、`action=patch`／`create`／`delete`／`write_file`／`remove_file` |
| 目录与文件名 | `references/`、`templates/`、`scripts/`、`assets/`、`SKILL.md`、`run.json` |
| 候选清单标记 | `pinned=yes`、`cron=yes`、`use=0` |
| 命令行 | `hermes curator run`、`hermes curator restore`、`.archive/` |

`_parse_structured_summary` 用正则抓取 ` ```yaml ` 围栏后 `safe_load`，再按 `consolidations`／`prunings` 两个键取条目，字段名 `from`／`into`／`name`／`reason` 全部硬编码。汉化任何一项都会让解析结果变成空列表，且不报错——下游会把整轮整合误判为「什么都没做」。

验证方法：构造一段原版格式的 YAML 样本，直接调用 `_parse_structured_summary`，检查两类条目各解析出一条。这比读代码更能确认契约完好。

`_REPORT_SECTIONS` 的标题与说明文字可以汉化（无人解析），但五个元组的首元素键名（`consolidated`、`pruned`、`added`、`state_transitions`、`cron_rewrites`）是 payload 取值键，绝不可动。

## 七、 只认英文的正则防护

`context_compressor.py` 的 `_validate_summary_user_provenance` 用 `\bUser\s+asked\s*:` 检测摘要是否虚构了用户归属。摘要正文汉化后该正则失配，防护失效。须补中文分支：

```python
re.search(r"\bUser\s+asked\s*:|用户(?:要求|提出|询问|问)", summary, re.IGNORECASE)
```

实测三个用例：中文违规值被拦、英文违规值被拦、带章节标题的合法哨兵值不被误拦。

## 八、 测试基线比对

汉化前先在**原版文件**上跑目标测试，记录失败项数量。汉化后再跑，失败数必须回到同一水平。

若原版本身就有失败项，先查明原因（常见是测试隔离机制拦截了对真实配置目录的读写），不要把这些既有失败误判为汉化引入。

改写检查条件时用对应的中文特征词，不要删除检查、不要改成恒真。

**只改基线就失败的测试没有意义。** 若某测试在原版上就失败（常见原因是测试隔离机制拦截了对真实配置目录的读写），把它的英文检查条件改成中文不会让结果变好，只是制造了一份无用的改动。这类测试保持原样，并在汇报时明确说明「该项失败与本次改动无关」。

**还原误改文件时不要用 `git checkout --`。** 在 Hermes 线上源码检出目录内执行该命令会被拦截（防止运行中的进程混用模块版本）。改用两步：先 `git show HEAD:<相对路径> > <临时文件>`，再复制回目标路径，最后比对哈希确认与 HEAD 一致。

## 九、 验证脚本自身的两个写法陷阱

**陷阱一：用常量名而不是常量值做包含判断。** 校验「提示词是否包含共享块」时，写成 `"_MEMORY_ROUTING_BLOCK" in prompt` 必然失败——拼接进提示词的是常量的值，不是它的名字。正确写法是先 `importlib` 加载模块，再取 `mod._MEMORY_ROUTING_BLOCK in mod._MEMORY_REVIEW_PROMPT`。

**陷阱二：把带章节标题的合法值当成裸值传入校验函数。** 校验摘要归属的函数会先用正则提取章节内容再比对哨兵值；直接传裸哨兵值会被判为不匹配而抛错。构造用例时必须带上章节标题：`HISTORICAL_TASK_HEADING + "\n" + _NO_USER_TASK_SENTINEL`。原版行为可先跑一遍确认，避免把调用方式错误误判为汉化缺陷。

## 十、 长中文块替换后的读回确认

用局部替换工具改写大段中文提示词时，替换边界可能落在缩进敏感的代码结构上（字典分支、跨行字符串拼接）。替换后必须读回该区域确认缩进与结构完好，再跑抽象语法树校验。发现分支被整体缩进错乱时，用一次精确替换恢复原缩进，不要逐行微调。
