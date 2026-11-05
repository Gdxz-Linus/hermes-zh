# Hermes 核心提示词简体中文汉化

有没有发现使用hermes的时候，很多大模型突出的中文充满了行话、黑化、口语？还有机械英文翻译，理解你的意图有问题？你再怎么用提示词要求效果也不是很好，经过我的

详细研究发现最根本的原因在hermes的核心系统提示词以及工具、技能等提示词的英文不规范，很多语言能力差的模型会被hermes的提示词带偏，故写了这个工具解决此问题，

经使用效果还不错。此工具使用操作系统包括windows、linux、macos；cli、tui、desktop均可使用。

---

## 功能

Hermes 的核心提示词和工具说明写死在源码里，全是英文。直接改源码，`hermes update` 一升级就被覆盖，而且不稳定。

本项目装一个中间件插件，在请求发出去之前把英文换成中文：

源码一个字节没动，升级不受影响。映射表里没有的条目保持英文，不报错，也不影响任何功能使用。

### 汉化范围

分五个层面，各有对应文件：

| 层面 | 内容 | 数量 | 存放 |
| :--- | :--- | ---: | :--- |
| **核心提示词** | 模型的角色设定、行为准则、执行纪律、记忆与技能指引、会话压缩摘要 | 31 段 | `核心/prompts-zh.json` |
| **核心工具** | Hermes 自带工具的说明与参数描述 | 52 个 | `工具/tools-zh.json` |
| **插件工具** | 第三方插件提供的工具说明与参数描述 | 27 个 | `插件/tools-zh.json` |
| **界面中文** | 菜单、按钮、状态提示、报错信息 | 4 个文件 | `语言包/*.yaml` |
| **技能文档** | 技能的使用说明与操作步骤 | 79 个 | `技能库/` |

工具合计 79 个（核心 52 + 插件 27）。

技能库中 11 个是 OpenSpec 插件的汉化技能，4 个是 macOS 专用技能（备忘录、提醒事项、查找、iMessage），其余为 Hermes 内置技能。

---

## 怎么装

前提：已装好 Hermes，`hermes --version` 能输出版本号；Python 3.8 或更高。

Windows、Linux、macOS 都可以用，脚本不依赖特定系统。用 Hermes 自带的 Python 运行最稳妥。

```bash
python 部署汉化.py --check      # 先看会改什么
python 部署汉化.py              # 部署
hermes plugins enable zh-localization-overlay
hermes gateway restart
```

macOS 与 Linux 上把 `python` 换成 `python3`。

Hermes 不在默认位置时加参数：

```bash
# Windows
python 部署汉化.py --target "D:\你的路径\hermes"

# macOS 与 Linux
python3 部署汉化.py --target ~/.hermes
```

**验证**：重启后查日志

```bash
# Windows
grep 汉化覆盖层 "$LOCALAPPDATA\hermes\logs\gateway.log" | tail -3

# macOS 与 Linux
grep 汉化覆盖层 ~/.hermes/logs/gateway.log | tail -3
```

看到这两行就成功了：

```text
汉化覆盖层：已加载 79 个工具的中文映射
汉化覆盖层：已加载 31 段提示词映射
```

---

## 怎么维护

映射表就是基线。装了什么版本，那个版本就是基线，官方没改的部分不用管。

### 升级 Hermes 之后

```bash
hermes update                  # 升级
python 汉化维护.py             # 看官方改了什么
```

报告分三类：

| 类型 | 意思是 | 要做 |
| :--- | :--- | :--- |
| 新增 | 官方加了新工具或新提示 | 补中文 |
| 删减 | 官方删了 | 跑 `--apply` 清理 |
| 变化 | 英文原文改了 | 按新英文重译 |

按报告改完 `核心/prompts-zh.json`、`工具/tools-zh.json`、`插件/tools-zh.json` 的中文侧，然后：

```bash
python 汉化维护.py --apply     # 清理已删减的条目
python 部署汉化.py             # 部署
hermes gateway restart
```

### 升级第三方插件之后

插件升级会换一套英文说明，映射表里还是旧译文，必须重新检查：

```bash
python 汉化维护.py
```

报告里「插件工具」一栏就是需要重译的部分。

插件如果带了新的技能文档，`技能库/` 里对应的汉化版也要同步更新。

---

## 说明

- 只含简体中文汉化文本，不含 Hermes 源码、第三方插件代码、配置文件。
- 提示词常量被 Hermes 用来解析会话历史，翻译会导致识别失败，因此保持英文。
- 由程序运行时动态生成英文不做汉化。
- 汉化文本基于 Hermes Agent 官方内容翻译，以版本 0.22.7 为基础制作。遵循上游许可。
