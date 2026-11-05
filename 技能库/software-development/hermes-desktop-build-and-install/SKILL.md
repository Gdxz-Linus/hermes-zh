---
name: hermes-desktop-build-and-install
description: "用于在 Windows 环境下评估、构建、安装与排查 Hermes 桌面客户端。"
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, 桌面客户端, electron, 源码编译, 安装排障, 快捷方式, 依赖排查]
    category: software-development
    related_skills: [hermes-agent, inspecting-hermes-desktop-dom, hermes-local-data-hygiene]
---

# Hermes 桌面端评估、编译与安装指南（Windows 环境）

## 概述

指导在 Windows 操作系统中评估、编译、安装和维护 Hermes 桌面客户端（基于 Electron 和 Next.js 构建），并提供依赖源加速配置与常见运行故障的排查方法。

**核心约束**：
```
仅执行只读排查并提供方案，由用户决定是否进行实际编译与安装
```
编译过程会向工程根目录的 `node_modules` 和 `apps/desktop/` 目录写入大量生成文件，属于对本地代码目录的修改。在用户明确确认之前，只收集系统环境和依赖信息，不擅自启动编译任务。

## 适用场景

- 用户希望了解或使用桌面图形界面，评估是否需要安装桌面端
- 运行 `hermes desktop` 或编译脚本时长时间无响应、报错或中断
- 评估当前计算机适合使用官方预编译安装包还是直接从本地源码编译

---

## 一、 基本技术事实

1. **共享底层数据与配置**：
   - 桌面客户端与命令行终端（CLI）、后台网关服务共用同一份配置文件、API 密钥、长久记忆、会话记录与技能文件；
   - 桌面端仅改变了交互操作形态，底层的配置项和系统功能完全相同。
2. **源码安装环境的编译行为**：
   - 若 `hermes --version` 显示安装方式为 Git 源码（`Install method: git`），运行 `hermes desktop` 默认会从本地源码开始编译，并非下载打包好的成品程序。
3. **免编译预编译包（MSIX）的条件**：
   - 官方提供的预编译 MSIX 安装包自带运行环境，安装后可直接打开，无需本地编译；
   - 运行要求为 Windows 11 22H2 及以上版本；若计算机已安装源码版本，两个入口可能产生调用冲突，可以使用 `Get-Command hermes -All` 查看当前命令的优先级。

---

## 二、 命令行启动参数说明

`hermes desktop` 命令常用参数如下：

| 参数 | 功能说明 |
| :--- | :--- |
| `--source` | 开发调试模式：直接以开发状态运行 `apps/desktop/dist`，不执行最终打包 |
| `--skip-build` | **日常启动推荐**：直接启动已编译完成的程序。日常使用带此参数启动，不必每次重新编译 |
| `--force-build` / `--build-only` | 强制重新编译 / 仅编译生成程序产物，不启动图形窗口 |
| `--ignore-existing` | 忽略本地现有的 Hermes 运行环境，进入连接远程网关或全新配置引导页 |

---

## 三、 源码编译前置条件检查

在开始编译前，必须逐项核对以下三项条件：

1. **检查核心依赖包是否完整**：
   - 编译检查脚本 `apps/desktop/scripts/assert-root-install.mjs` 会强制检查仓库根目录下是否包含 `vite`、`katex`、`electron` 和 `electron-builder` 四个核心工具包；
   - 依赖文件集中存放在工程根目录的 `node_modules/` 下，子目录 `apps/desktop/node_modules` 通常为空，属于正常现象；
   - 如果根目录缺少上述依赖，编译过程会停留在安装依赖阶段，表现为长时间无任何输出。
2. **核对产物目录状态**：
   - 如果 `apps/desktop/dist` 和 `apps/desktop/release` 目录均不存在，说明该环境此前从未编译成功过，不必搜寻损坏的文件。
3. **确认代码仓库状态干净**：
   - 编译前应执行 `git -C <代码目录> status --porcelain`；
   - 如果存在未提交的代码修改，应当先提交到本地 Git 分支，防止后续版本更新时发生代码冲突。
4. **确认当前检出包含本地定制**：
   - 编译前先执行 `git -C <代码目录> rev-parse --abbrev-ref HEAD`，返回 `HEAD` 即处于游离状态；此时编译出的安装包不含任何 `local:` 补丁，即使源码目录里能看到修改；
   - 编译完成后用 `cat apps/desktop/release/win-unpacked/resources/install-stamp.json` 核对 `commit` 字段，再用 `grep -a -o -c '<前端补丁特征字符串>' apps/desktop/release/win-unpacked/resources/app.asar` 确认安装包真的带上了前端修改；源码在位不等于安装包在位；
   - 判定与重放方法见 `hermes-agent` 技能里的《本地补丁跨版本升级的判定、恢复与重放》。

---

## 四、 网络连接与国内镜像加速配置

编译涉及多个不同工具，各工具读取代理的方式不同，需要分别确认：

1. **Python 网络请求的代理机制**：
   - Windows 环境下 Python 的 `urllib.request` 默认读取系统注册表中的代理设置；
   - 在测试真实直连网络时，必须在代码中显式清空代理设置（使用 `ProxyHandler({})`），避免把使用代理的测试结果误判为直连成功。
2. **npm 与 Electron 下载工具的代理与镜像**：
   - npm 和 `@electron/get` 下载器不读取注册表，而是读取环境变量中的 `HTTP_PROXY` 和 `HTTPS_PROXY`；
   - 从官方源直接下载 Electron 运行时压缩包（约 132MB）容易因网络波动中断；
   - **配置国内镜像源地址**（建议添加到 Windows 用户环境变量）：
     ```bash
     ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
     ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/
     ```

---

## 五、 编译过程监控与状态判断

1. **输出日志记录方式**：
   - 执行长时间编译时，必须把输出重定向到独立的日志文件（例如重定向到 `build.log`），通过定期读取日志文件了解执行进度；
   - 严禁使用管道把日志传递给 tail 命令，因为管道缓冲会导致输出延迟，无法实时查看进展。
2. **多指标判断程序运行状态**：
   - 不要仅通过 5 秒内的 CPU 使用率波动判断程序停止响应。前端编译涉及上千个源文件，首次编译耗时通常在 10 到 30 分钟之间；
   - 满足以下三项中的两项，即可判定编译正在正常运行：
     - 父子进程链完整存在（`hermes` -> `npm` -> `node` -> 编译器）；
     - 产物目录中的文件修改时间不断更新；
     - 进程累计占用的 CPU 时间持续增加。

---

## 六、 桌面快捷方式与日常运行要求

1. **快捷方式目标配置**：
   - 快捷方式目标必须直接指向物理可执行程序文件：`%LOCALAPPDATA%\hermes\bin\hermes.exe`；
   - 严禁将快捷方式指向批处理文件，因为 Windows 资源管理器在双击批处理时存在权限隔离，容易导致双击没有任何反应；
   - 严禁将快捷方式指向虚拟环境内部的 `pythonw.exe` 启动器，否则容易被杀毒软件当作未知进程拦截；
   - 启动参数填写为：`desktop --skip-build`，起始位置填写为工程根目录。
2. **多端同时打开同一会话的保护机制**：
   - 如果桌面端打开了一个终端正在读写的活动会话，界面会提示该会话已在其他位置打开；
   - 这是防止两个程序同时写入导致数据损坏的保护机制。遇到该提示时，可在桌面端新建会话，或关闭终端里对应的会话。

---

## 七、 检查核对清单

- [ ] 是否已确认环境依赖完整，且未在未经用户同意前启动编译？
- [ ] Electron 镜像环境变量是否已正确配置为国内加速源？
- [ ] 编译任务是否重定向到了独立日志文件，并使用定期读取方式查看进度？
- [ ] 桌面快捷方式是否直接指向 `.exe` 文件，并附带了 `--skip-build` 参数？
