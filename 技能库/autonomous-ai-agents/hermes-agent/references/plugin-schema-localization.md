# 插件工具 Schema 与元数据汉化：边界与校验

`$HERMES_HOME/plugins/<id>/` 下的工具 Schema 与 `plugin.yaml` 直接进入模型上下文，是提示词汉化的第二个面。它与 `agent/` 下的提示词源码共享同一套语言规范，但锚点与禁改边界完全不同。

## 零、 先分类：自定义插件与仓库插件

两类插件的汉化落点不同，分类错了后续全白做。

### 判定方法

```bash
cd "$HERMES_HOME/plugins"
for d in */; do
  n="${d%/}"
  if [ -d "$n/.git" ]; then
    echo "[仓库] $n  $(git -C "$n" remote get-url origin 2>/dev/null)"
  else
    echo "[自定义] $n"
  fi
done
```

**必须逐个数清，不要凭印象。** 实测本机 17 个插件里 5 个是仓库插件、12 个是自定义插件，远超「印象中的 5 个」。汉化备份目录里的插件清单可作为交叉核对依据，但以运行时目录为准。

### 两类插件的落点

| 类型 | 判定 | 汉化落点 | 升级影响 |
| :--- | :--- | :--- | :--- |
| 自定义插件（含防线插件） | 无 `.git` | 直接改插件目录文件 | 无。插件目录在 `hermes-agent` 仓库之外 |
| 仓库插件 | 有 `.git`，有 `git pull` 升级链路 | 映射表（与工具、核心同一套） | 插件自身升级会覆盖 Git 提交，故不能用 Git 保存 |

防线插件（`script-guard`、`skill-guard`、`swe-guard`、`zh-jargon-guard`）属于自定义插件，一次性汉化即可。

### 插件自带技能不属于映射表范围

仓库插件常带 `skills/*/SKILL.md`。技能是独立文件、不进请求结构，工具描述映射表改不到它。

正确落点是用户层 `$HERMES_HOME/skills/`：技能同步靠哈希比对保护（`tools/skills_sync.py` 比对 `dir_hash` 与 `.bundled_manifest` 的 `origin_hash`，用户改过的跳过），放用户层天然不受插件升级影响。

## 零点五、 映射表必须扫插件目录

映射表生成器只扫 `repo / "tools"` 时，插件工具一个都进不了表，且脚本报告成功、不报错。

**判定方法**：取几个插件工具名在映射表里查，全部缺失即证明扫描范围不全。

```python
import json
m = json.load(open('tools-zh.json', encoding='utf-8'))
for t in ['plan_mode', 'diff_review', 'codex_delegate',
          'openspec_task_list', 'ha_call_service', 'pdf_to_office']:
    print(f'{t:28} {"已收录" if t in m else "缺失"}')
```

插件工具名与核心工具名同处一个命名空间，按工具名索引的映射表天然能容纳两者，不需要改中间件逻辑，只需扩大采集范围到插件目录的 `tools.py` 与 `schemas.py`。

### 源码已回英文原版时，只能增量合并

一旦仓库源码回退到英文原版（汉化与仓库解耦后必然如此），全量生成器扫不到任何中文，条目数为零，直接覆盖会把现有映射表清空。此时必须用增量合并：

1. 读现有 `tools-zh.json` 作为基线，不重新生成；
2. 只扫**仓库插件**目录（无 `.git` 的自定义插件不进表，它们直接改文件即可）；
3. 用插件自己的 `git show origin/HEAD:<相对路径>` 取英文基线做对照；
4. 只补映射表里不存在的工具名，已有键一律不动（`if name in base_map: continue`）；
5. 只收中文描述与中文参数说明（`has_cn()` 过滤），避免把英文条目写进去；
6. 写回后复制到插件运行目录。

### 合并后的验证必须调中间件函数

只看 JSON 里有键证明不了运行时生效。直接调中间件的内部函数，传入英文假数据看返回值：

```python
import importlib.util, json
spec = importlib.util.spec_from_file_location('ov', '__init__.py')
ov = importlib.util.module_from_spec(spec); spec.loader.exec_module(ov)
ov._tools_map = json.load(open('tools-zh.json', encoding='utf-8'))
tools = [{'name': 'plan_mode', 'description': 'Use action=on to enter plan mode.',
          'parameters': {'properties': {}}},
         {'name': 'diff_review', 'description': 'Review a git diff.',
          'parameters': {'properties': {}}}]
new, n = ov._rewrite_tools(tools)
print(n)  # 替换计数应大于 0
for t in new:
    print(t['name'], t['description'][:60])  # 应输出中文
```

### 插件解耦后的完整验证序列

| 验证项 | 命令要点 | 合格标准 |
| :--- | :--- | :--- |
| 本地提交已清 | `git -C <插件> rev-list --count origin/HEAD..HEAD` | 结果为 0 |
| 源码无中文残留 | Python 逐文件判字符区间 | 含中文文件数为 0 |
| 语法完好 | `py_compile` 逐文件 | 无错误 |
| 映射表已收录 | 取插件工具名查表 | 全部命中 |
| 中间件生效 | 调 `_rewrite_tools` | 替换计数大于 0 且输出中文 |

**中文残留判断不能用 bash 的 `grep '[\u4e00-\u9fff]'`**：该写法在 MSYS/git-bash 下不生效，会把纯英文文件误报为含中文。用 Python：

```python
from pathlib import Path
for f in plugin_dir.rglob('*'):
    if f.is_file() and f.suffix in ('.py', '.yaml', '.md', '.json') and '__pycache__' not in f.parts:
        t = f.read_text(encoding='utf-8', errors='ignore')
        if any('\u4e00' <= c <= '\u9fff' for c in t):
            print(f)
```

注意：官方原版里也可能天然带中文或日文（测试用例里的多语言路径、`plans/日本語.md`），这类命中不是汉化残留，要看具体行内容再判定。

## 零点六、 撤销仓库插件提交前先分离功能代码

仓库插件的本地改动里常混着功能修复。直接撤销 Git 提交会连带丢掉功能代码。

**分类方法**：逐文件统计「新增行总数」与「其中含中文字符的行数」。

```python
import subprocess

d = subprocess.check_output(['git', '-C', n, 'diff', 'origin/HEAD'],
                            stderr=subprocess.DEVNULL).decode('utf-8', 'replace')
cur = None; stat = {}
for line in d.splitlines():
    if line.startswith('diff --git'):
        cur = line.split(' b/')[-1]; stat[cur] = [0, 0]
    elif cur and line.startswith('+') and not line.startswith('+++'):
        stat[cur][0] += 1
        if any('\u4e00' <= c <= '\u9fff' for c in line):
            stat[cur][1] += 1
for f, (a, c) in stat.items():
    kind = '汉化' if c == a and a > 0 else ('功能' if c == 0 else '混合')
    print(f'{kind:4} {f:50} 新增{a:4} 中文{c:4}')
```

| 中文字数 | 性质 | 处理方式 |
| :--- | :--- | :--- |
| 等于新增行数 | 纯汉化 | 进映射表，Git 提交可撤 |
| 为零 | 纯功能改动 | 按补丁流程备份到仓库外，**不可撤** |
| 介于两者之间 | 混合 | 拆开：汉化进映射表，功能进补丁备份 |

实测某插件的 122 行新增全部是 Windows 兼容功能代码（`psutil` 回退、系统进程白名单、`/proc` 不存在时的分支），零汉化；只有 `plugin.yaml` 1 行是汉化。若按「插件汉化提交」整体撤销，会连带丢掉 Windows 兼容修复。

另需注意：`git diff` 输出里会出现 `__pycache__/*.pyc` 与 `.hermes-catalog.json`，这些是运行时产物，不计入汉化或功能分类。

### 撤销流程：功能代码先备份再放回工作区

纯汉化插件直接 `git reset --hard origin/HEAD` 即可；混有功能代码的插件必须分三步：

1. 导出功能 diff 与完整文件副本到仓库外（`git diff origin/HEAD -- <文件>`，新增文件先 `git add -N`）；
2. `git reset --hard origin/HEAD` 清掉提交，`git clean -fd` 清掉未跟踪的运行时产物；
3. 把备份的功能文件写回工作区（不提交）。这样当前运行仍有功能，而 Git 与官方一致，可直接 `git pull` 升级。

每个插件撤销前打备份标签 `backup-zh-<时间戳>-<插件名>`，并在输出里打印回退命令。

## 零点七、 插件升级后重译工具描述

插件升级等于换了一套英文描述，映射表里的旧中文译文会继续替换新英文，模型看到的就是与新版功能脱节的说明。升级流程固定为四步，缺一不可。

### 第一步：先看新版改了什么，再决定要不要动映射

```bash
cd "$HERMES_HOME/plugins"
for n in diff-review plan-mode homeassistant openspec; do
  echo "=== $n ==="
  git -C "$n" fetch origin 2>&1 | tail -2
done
```

`fetch --dry-run` 只列不拉，看不出实际差异；要真正 `fetch` 之后才能 `log HEAD..origin/<分支>` 与 `diff --stat`。

| 改动文件 | 映射影响 |
| :--- | :--- |
| 只有 `README.md`／`CHANGELOG.md` | 无，不必动映射 |
| `plugin.yaml` 只改 `version` | 无 |
| `tools.py`／`schemas.py` | **必有描述变化**，每一条都要重译 |

### 第二步：升级用 `merge --ff-only`，不用 `pull`

```bash
cp -a "$n" "<备份目录>/$n"          # 先带 .git 完整备份
git -C "$n" merge --ff-only origin/<分支>
```

`--ff-only` 保证只做快进合并，不会产生意料外的合并提交。出问题有两条回退路：`git reset --hard <旧提交>`，或直接用备份覆盖整个目录。

### 第三步：重跑差异对比，逐条重译

```bash
cd <工作目录>\汉化覆盖层
python 汉化维护.py
```

报告里「插件工具」一栏就是需要处理的部分：

```text
插件工具: 新增 0，删减 0，内容变化 4
    变化  diff_review.description
    变化  diff_review.base
    变化  diff_review.target
    变化  diff_review.diff_text
```

取新旧对照时不要只看「描述变了」，要把参数说明逐条列出——参数语义变动的破坏力比描述更大，模型会按旧语义传参：

```python
cur = hm.scan_installed_plugin_tools(lib.RUNTIME_PLUGINS_ROOT)
plug = lib.load_json(lib.PLUGIN_TOOLS)
old, new = plug['diff_review'], cur['diff_review']
print(old.get('en', ''))
print(new.get('description', ''))
for p in ['base', 'target', 'diff_text']:
    print(p, old.get('params_en', {}).get(p, ''), '->', new.get('params', {}).get(p, ''))
```

重译后必须在同一次写入里同时更新 `en`／`params_en`，否则下次对比仍会报「变化」，且英文侧与真实源码不一致。

### 第四步：部署与实测

```bash
cd <工作目录>
python 部署.py --only 汉化
```

部署后直接调中间件函数验证，不要只看 JSON：

```python
new, n = ov._rewrite_tools([{'name': 'diff_review',
    'description': 'Review git changes for common code quality issues on added lines.',
    'parameters': {'properties': {'base': {'description': 'Commit to review from'}}}}])
print(n, new[0]['description'][:60])
```

### 同时要查的两件易漏事项

1. **插件技能是否脱节**：升级若带上新的或改过的 `SKILL.md`，用户层那份汉化技能不跟随（用户层优先 + 哈希保护）。需要重新对比并补译。
2. **备份副本是否同步**：升级后要把新版本复制回备份目录，否则备份是旧版，移植到新电脑时装的是旧代码，而映射表却是按新版写的，两边对不上。

### 上游仓库已不可访问时

`git fetch` 报 `Repository not found` 或要求输入用户名，说明上游已删除或改名。先查 `hermes-agent/plugin-catalog/<插件名>.yaml` 里锁定的 `version` 与 `sha`：与本地一致即说明官方也停在旧版，不必升级，也不影响使用。此时不要把它当成异常去修。

## 一、 先判定目录性质

审计一个插件目录前，先分清里面是什么：

| 内容 | 是否汉化 | 理由 |
| :--- | :--- | :--- |
| `tools.py` 的 `description` 字符串 | 是 | 直接注入模型上下文 |
| `plugin.yaml` 的 `description`、`requires_env[].description`、`prompt` | 是 | 展示给用户、注入模型 |
| `schemas.py` 的工具描述与参数描述 | 是 | 同上 |
| 独立配置文件（如 `ov.conf`） | 否 | 服务进程按字面读取，汉化会导致启动失败 |
| 工具名、参数键名、`type`／`required`／`enum`／`default` | 否 | 模型按字面调用，改动即失效 |

配置文件不是汉化对象。发现插件目录下挂着某个服务的配置文件时，先确认它是否被服务进程读取，再决定纳入范围。

## 二、 必须保持英文的清单

### plugin.yaml

`name`、`version`、`kind`、`manifest_version`、`provides_tools`、`provides_hooks`、`requires_env[].name`、`optional_env[].name`、`password` 等全部键名与枚举取值。可汉化的是 `description`、`requires_env[].description`、`requires_env[].prompt`、`optional_env[].description`、`optional_env[].prompt`。

### 工具 Schema

| 保持英文 | 可汉化 |
| :--- | :--- |
| `name` | `description` |
| `parameters.properties` 的键名 | 每个参数的 `description` |
| `type`、`required`、`enum`、`default`、`items` | 参数描述里的举例说明 |

举例内容（`'light'`、`'turn_on'`、`{"brightness": 255}` 这类）保持原文，只汉化包裹它们的说明文字。这类举例属于引文，按语言规范不替换。

## 三、 逐项列全，不要抽样

同一个 Schema 文件里常见「大部分已汉化、少数仍是英文」的混合状态。抽样检查必然漏项。正确做法是用抽象语法树遍历枚举全部 `description` 键，逐个判定是否含中文字符：

```python
import ast
from pathlib import Path

tree = ast.parse(Path("tools.py").read_text(encoding="utf-8"))
for node in ast.walk(tree):
    if not isinstance(node, ast.Dict):
        continue
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and k.value == "description" and isinstance(v, ast.Constant):
            s = str(v.value)
            if not any("\u4e00" <= c <= "\u9fff" for c in s):
                print(f"L{node.lineno}: 仍是英文 -> {s[:80]}")
```

收尾时该脚本的输出必须是零行。

## 四、 校验五项

汉化后逐项完成，缺一不可：

1. **语法编译**：`py_compile` 通过。
2. **模块真实导入**：`importlib` 加载并读取 Schema 对象，确认描述含中文、工具名未变。插件依赖 Hermes 运行时时导入可能失败，此时退回抽象语法树静态校验，并在汇报里说明原因。
3. **参数契约完整守恒**：必须比对参数名列表、`required` 必填项列表以及 **`enums` 枚举值列表**，三者缺一不可（漏检 enum 可能导致大模型调用时触发 schema 校验异常）。若插件属于 Git 仓库，可通过 `git show HEAD:<file>` 直接提取原版进行 AST 字段级逐项自动比对。
4. **行话黑话双重扫描**：用《行话参照表》词条加隐性黑话清单（工件、门禁、结项、开工、深入推演、全量等）逐文件检索，命中数必须为零。
5. **自带测试基线比对**：先执行一遍记录基线，汉化后再执行。插件测试常因缺依赖（如 `aiohttp`）在原版就失败，这类失败与汉化无关，汇报时必须明确区分，不要含糊成「测试全部通过」。

临时验证汉化版与基线的差异时，用 `git stash push <文件列表>` 暂存汉化改动、执行测试、再 `git stash pop` 恢复。比来回复制文件安全，也不会把汉化版丢在暂存目录里找不回来。

## 五、 翻译质量三审查（通俗精准、杜绝套话、防约束丢失）

机翻直译或由大模型二次润色时极易产生三类严重质量退化，审查时必须逐条核验：

1. **通俗易懂，杜绝生硬直译与大厂套话**：
   - 避免生硬直译：例如 OpenSpec 中的 `artifact` 机械直译为“工件”十分晦涩，应结合语境译为“规范文件”（规格、提议、任务清单）；
   - 坚决剔除假大空套话：严禁出现“前置强校验门禁”、“带缺陷结项”、“推进至待办就绪状态”、“使其符合正式开工条件”、“深入推演”等扩写废话；原文是状态机流转就写状态机（如“转为待办状态 todo”），原文是拒绝归档就写拒绝归档。
2. **严防关键技术约束与上下文丢失**：
   - 描述不能只保留一句概括而把细节剪裁掉。必须核验原英文中包含的**枚举取值**（如 `type 取值为 GIVEN/WHEN/THEN/AND/BUT`）、**参数别名**（如 `'spec' 为 'specs' 的别名`）、**底层运行特征**（如“直接操作文件系统，无需依赖外部 CLI 命令行”）、以及**有参/无参分支逻辑**（如“传入 change 时……；省略 change 时……”）；漏掉这些信息会导致模型调用工具时不知道取值范围与默认行为。
3. **主谓完整，理顺从句与句式**：
   - 消除欧化从句和多层定语堆叠（如“适用于把提议与任务的推进情况同步为看板状态更新” -> “用于将提议与任务的推进进度同步至看板”）；
   - 改掉多余的“把……”字句，一个短句陈述一件事。

## 六、 符号表比对与功能升级的区分

比对函数名集合时发现新版本少了某个函数，不等于损坏。先看是否有函数承接了同一职责——把只校验 create 的函数扩展为校验 create／patch／write_file 三者，属于功能升级。判定依据是职责覆盖而非名字相同。

行数差异也要同样解释：汉化会改变换行位置，行数小幅增减属正常，但函数数、常量数、参数签名必须严格一致。

## 六、 双向同步与哈希确认

汉化稿写在备份目录，确认后复制到线上运行目录，然后逐文件比对 SHA256。只复制不比对，等于没有确认——复制命令成功不代表目标文件内容正确（路径拼错时可能静默失败或写到别处）。

## 七、 全量清点

单个插件改完后，遍历全部插件目录读取 `plugin.yaml`，统计每个插件描述的中文字符数，列出仍为零的插件。这一步把「我以为改完了」变成可核验的数字，也避免下一轮重复审计已完成的插件。
