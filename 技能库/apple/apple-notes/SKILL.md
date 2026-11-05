---
name: apple-notes
description: "用于通过 memo 命令行创建、检索与编辑苹果备忘录时。"
version: 1.0.1
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Notes, Apple, macOS, note-taking]
    related_skills: [obsidian]
prerequisites:
  commands: [memo]
---

# 苹果备忘录

用 `memo` 在终端直接管理苹果备忘录。备忘录经 iCloud 在各苹果设备之间同步。

## 前置条件

- **macOS**，且装有备忘录应用
- 安装：`brew tap antoniorodr/memo && brew install antoniorodr/memo/memo`
- 首次使用时按提示给备忘录应用授予自动化权限（系统设置 → 隐私与安全性 → 自动化）

## 适用场景

- 用户要求创建、查看或检索苹果备忘录
- 把信息存进备忘录应用，供其他设备读取
- 把备忘录归类到文件夹
- 把备忘录导出为 Markdown 或 HTML

## 不适用场景

- Obsidian 知识库管理 → 用 `obsidian` 技能
- Bear 笔记 → 是另一款应用，本技能不支持
- 仅智能体内部使用的临时记录 → 改用 `memory` 工具

## 常用命令

### 查看备忘录

```bash
memo notes                        # 列出全部备忘录
memo notes -f "文件夹名"           # 按文件夹筛选
memo notes -s "关键词"             # 模糊检索备忘录
```

### 新建备忘录

```bash
memo notes -a                     # 新建备忘录（打开 $EDITOR）
memo notes -a -f "文件夹名"        # 新建并放入指定文件夹
```

`-a`／`--add` 不带取值——它打开 `$EDITOR` 让你写正文，不接受标题参数。要指定文件夹用 `-f`／`--folder`。先设好 `$EDITOR`（例如 `export EDITOR=vim`）。

### 编辑备忘录

```bash
memo notes -e                     # 交互选择后编辑
```

### 删除备忘录

```bash
memo notes -d                     # 交互选择后删除
```

### 移动备忘录

```bash
memo notes -m                     # 交互选择后移动到其他文件夹
```

### 导出备忘录

```bash
memo notes -ex                    # 导出为 HTML 或 Markdown
```

## 限制

- 含图片或附件的备忘录无法编辑
- 交互式选择需要终端可交互（必要时用 pty=true）
- 仅限 macOS，依赖苹果备忘录应用

## 规则

1. 用户需要在 iPhone、iPad、Mac 之间同步时，优先用苹果备忘录
2. 智能体内部使用、不需要同步的记录，用 `memory` 工具
3. 以 Markdown 为原生格式的知识管理，用 `obsidian` 技能
