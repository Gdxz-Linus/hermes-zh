---
name: codebase-inspection
description: "代码仓库规模分析与多语言代码统计：统计代码行数（LOC）、注释率、空行与多语言分布。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [代码统计, LOC, 代码行数, 语言分布, 代码度量, pygount]
    category: software-development
    related_skills: [code-audit, requesting-code-review, github]
---

# 代码仓库规模分析与代码统计技能（Codebase Inspection）

## 概述

使用 Python 原生统计引擎 `pygount`，对工程代码仓库开展全方位的代码规模统计与结构分析。精确统计有效可执行代码行数（SLOC）、注释行数、空行数、文档占比以及多编程语言构成比例，为项目代码审计、架构重构评估与工作量测算提供客观数据支撑。

**核心红线**：
```
执行统计时必须显式排除依赖项与构建输出目录
```
严禁无过滤全局扫描整个磁盘目录，否则扫描引擎会深入遍历 `node_modules`、`target`、`.venv`、`.git` 等海量第三方缓存文件，导致耗时过长甚至系统停止响应。

## 适用场景

- “统计一下这个项目总共有多少行代码，各语言占比如何”
- “排查项目的代码注释率与文档完整度”
- 在实施大版本重构或审计前，建立代码资产与文件规模基线
- 识别仓库中是否存在非预期的大型第三方复制文件（Vendored Code）

---

## 一、 快速汇总统计（标准用法）

进入项目根目录，调用带有依赖排除参数的命令进行语言构成汇总：

```bash
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,target,.next,vendor,third_party" \
  .
```

### 必须排除的常见目录清单：
- **通用底层目录**：`.git`、`.svn`、`.idea`、`.vscode`
- **Rust 项目**：`target`
- **Python 项目**：`venv`、`.venv`、`__pycache__`、`.mypy_cache`、`dist`、`build`
- **前端项目**：`node_modules`、`.next`、`dist`、`.turbo`、`coverage`
- **内嵌第三方依赖**：`vendor`、`third_party`

---

## 二、 专项与高级统计模式

### 1. 过滤单一指定编程语言
```bash
# 仅统计 Rust 语言源文件
pygount --suffix=rs --format=summary .

# 同时统计 C、C++ 与头文件规模
pygount --suffix=c,cpp,cc,h,hpp --format=summary .
```

### 2. 导出逐文件详细明细并排序
按有效代码行数从高到低排序，快速识别系统中最庞大、最复杂的源文件：
```bash
pygount --folders-to-skip=".git,node_modules,target,venv" . | sort -t$'\t' -k1 -nr | head -25
```

### 3. 结构化 JSON 输出（供脚本自动化解析）
```bash
pygount --format=json \
  --folders-to-skip=".git,node_modules,target,venv" \
  . > codebase_metrics.json
```

---

## 三、 统计结果指标解读标准

汇总报表中各列的物理含义与健康参考标准：

| 指标列名 | 物理含义 | 参考标准与分析说明 |
| :--- | :--- | :--- |
| **Language** | 检测到的编程语言种类 | 用于识别项目技术栈纯度与多语言混合程度。 |
| **Files** | 该语言包含的源文件总数量 | 辅助评估模块拆分粒度是否适中。 |
| **Code** | **有效可执行代码行数（SLOC）** | 排除纯注释与空行后的真实业务逻辑规模，是测算工作量与缺陷密度的核心依据。 |
| **Comment** | 注释行数 | 结合 Code 计算注释率（建议保持在 15% 至 30% 之间）。 |
| **Empty** | 空行数 | 占总行数比例（通常在 15%~20% 为合理留白）。 |
| **Ratio** | 代码与注释比例 | 注释占比过低（$<5\%$）意味着维护成本高，过高（$>50\%$）需排查是否有大量大段废弃代码被注释。 |

---

## 四、 自检核对清单

- [ ] 是否显式配置了 `--folders-to-skip` 排除第三方依赖与构建产物目录？
- [ ] 统计结论是否给出了总有效代码行数（SLOC）与主要语言占比确切数字？
- [ ] 是否指出了单文件行数过大（如单文件超过 1000 行）的异常核心模块？
