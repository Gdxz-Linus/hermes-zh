---
name: github
description: "GitHub 协同与项目管理：通过 gh CLI 管理 Issue、拉取请求（PR）、代码审查与持续集成验证。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, gh, git, pull-request, issues, 代码审查, ci-cd, 项目协同]
    category: software-development
    related_skills: [requesting-code-review, code-audit, codebase-inspection]
---

# GitHub 协同与项目管理技能（GitHub Workflow）

## 概述

使用 GitHub 官方命令行工具（`gh` CLI）在本地终端高效管理远程代码仓库。涵盖用户身份鉴权、Issue 缺陷建单与分类追踪、特性分支拉取、拉取请求（PR）全流程提交、代码审查评语与持续集成（CI）自动化状态核验。

**核心准则**：
1. **证据驱动，严禁凭记忆臆断远端状态**：严禁在未运行 `gh pr checks` 亲自核查前口头宣称“CI 全通过”；严禁在未校验 `state,mergedAt` 属性前宣称“已成功合并”；
2. **读懂全貌再动笔**：在回复或修改 Issue / PR 前，必须使用 `--comments` 完整阅读历史讨论记录，核心定论往往体现在具体讨论细节中，而非单纯查看标题；
3. **查重先行**：在创建任何新 Issue 或新 PR 前，必须先执行搜索检索，杜绝产生重复工单。

---

## 一、 常用核心操作流程与指令

### 1. 身份鉴权与状态巡检
```bash
# 检查当前 GitHub 鉴权状态与登录账号
gh auth status

# 检查当前仓库关联信息与默认远端
gh repo view
```

### 2. Issue 缺陷工单管理
```bash
# 检索现有工单（查重）
gh issue list --search "DNS cache timeout" --state all

# 创建包含明确证据的缺陷工单
gh issue create --title "修复：双栈网络环境下 UDP 超时未释放问题" \
  --body "### 缺陷描述\n在双栈网络环境下...\n\n### 复现步骤\n1. ...\n\n### 预期行为\n..." \
  --label "bug,network"

# 完整阅读特定工单及其全部历史讨论留言
gh issue view 42 --comments
```

### 3. 拉取请求（PR）全生命周期驱动
```bash
# 基于当前分支创建拉取请求
gh pr create --title "特性：优化长文本注意力计算模块并降低显存占用" \
  --body "## 变更目的\n支持百万级上下文处理...\n\n## 核心修改\n- 替换注意力内核...\n\n## 验证依据\n本地 8 卡物理集群测试全部通过。" \
  --base main

# 严格核查持续集成流水线（CI Checks）真实状态
gh pr checks 105

# 审查 PR 代码差异并提取逐文件变动
gh pr diff 105

# 核验并执行安全合并（压缩并合并）
gh pr merge 105 --squash --delete-branch
```

---

## 二、 中文 PR 提交说明标准模板

提交拉取请求时，必须使用结构严密、层次清晰的书面中文模板，杜绝随意一句话带过：

```markdown
## 变更目的与背景
[清晰陈述本次变更解决的核心问题，或满足了什么具体业务诉求。关联相关工单：Closes #42]

## 核心改动清单
- **模块 A**：重构了前置条件检查逻辑，消除了多层分支嵌套；
- **模块 B**：在接口层增加了针对输入参数的非空强校验；
- **配置层**：更新了默认超时阈值，由原本的 30 秒调整为 60 秒。

## 真实测试与验证依据
- [x] 本地全量单元测试已全部运行通过（共计 86 项，全部成功）；
- [x] 已在宿主真实环境完成双平台（Windows 原生与 WSL Linux）物理二进制全链路真实测试；
- [x] 静态差异审查（Diff Review）确认无任何临时打印代码与硬编码机密。

## 升级与兼容性说明
- 本次改动完全向下兼容，既有配置文件与接口契约不受影响。
```

---

## 三、 自检核对清单

- [ ] 在创建 Issue 或 PR 前，是否已执行搜索排查并确认无重复项？
- [ ] PR 描述中是否清晰陈述了变更目的、修改清单与具体的实测数据？
- [ ] 是否通过 `gh pr checks` 实测确认了 CI 状态，没有口头编造结果？
- [ ] 涉及代码审查时，评语是否具体针对文件行号并附带修改方案？
