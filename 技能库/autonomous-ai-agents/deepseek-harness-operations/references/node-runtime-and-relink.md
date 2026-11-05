# Node 运行时迁移与 profile 载荷重指向（dsh）

适用：本机 Node 运行时变化（新增 pm 管理的 node 组件、旧自带 node 退役、要把 dsh 移出 Hermes 目录），需要让 dsh 的启动器与 profile 载荷指向目标运行时环境。

## 本机现状（目标形态，非永久状态）

- 唯一 Node：`%LOCALAPPDATA%\hermes\tools\node-26.7.0-win32-x64`（pm 组件，PATH 里排第一）。
- dsh 全局安装：同目录 `node_modules\@deepseek-ai\dsh`；`dsh`（无扩展名的 shell 脚本）/ `dsh.cmd` / `dsh.ps1` 三个入口也在该目录。**命中哪个取决于 shell**：cmd.exe 取 `.cmd`，PowerShell 取 `.ps1`（受执行策略约束，见下），git-bash 取无扩展名脚本。
- profile 载荷 junction：`$DSH_HOME\profiles\node_modules\@deepseek-ai\*`（283 条）→ 指向 `<node 目录>\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai`。
- 旧运行时 `%LOCALAPPDATA%\hermes\node`（Node 22 + 老依赖树）已删除，用户 PATH 里对应条目也已移除。

## 下一步的判据：这套布置随时会被组件替换抹掉

上面四条只在「pm 组件目录未被替换」期间成立。node 组件版本一变，pm 会另起新目录并把旧的改名成 `.previous-node-…`，上面的第二条与第三条同时失效（全局安装记录与自带依赖树一起消失、283 条 junction 全部悬空）。**因此再次遇到 `dsh` 不可解析时，先跑这三条只读判定，不要先怀疑 PATH 或执行策略：**

1. `npm ls -g --depth=0` 里还有没有 `@deepseek-ai/dsh`。
2. `$DSH_HOME\profiles\node_modules\@deepseek-ai` 下 283 条里可解析几条（实测曾为 0）。
3. `Get-Item <junction> | Select LinkType,Target` 的目标是否存在；`.previous-node-…\node_modules\@deepseek-ai\dsh` 是否还有完整副本可作对照。

恢复步骤与安全安装位置见 SKILL.md 的「0.1.7 升级」节。

## 迁移步骤（实测）

1. **装到目标运行时**：用目标 node 自带的 npm —— `npm i -g @deepseek-ai/dsh@<版本> --prefer-offline`。实测 518 包、46 秒、全程本地缓存命中。
2. **补 pnpm**：**Node 25 起发行包不再捆绑 corepack**，目标运行时里没有 `pnpm`；而 dsh 的插件管理是**从 PATH 调用 pnpm**（源码里找不到时打印 `dsh: pnpm was not found; install pnpm and make it available on PATH.` 并返回 127）。做法是把 corepack 缓存里的原生二进制复制成目标 node 全局 bin 下的入口：
   ```
   cp "%LOCALAPPDATA%\node\corepack\v1\pnpm\<ver>\pnpm-native.exe" "<目标 node 目录>\pnpm.exe"
   ```
   该 exe 自包含（不需要 node 运行时，实测 44.3 MB）。验证：`pnpm --version` 与 `dsh plugin --profile web --version` 都返回版本号。
3. **重指向载荷**：`scripts/relink-profile-load.ps1 -Profile web -TargetRoot <目标 node>\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai`（实测 moved=283），再跑 `scripts/verify-profile-links.ps1 -TargetRoot <同上>`，期望 `links=283 / target_expected_root=283 / broken=0 / nonlink=0`。两个脚本都要 `-ExecutionPolicy Bypass`。
4. **验证通过后再删旧运行时目录**，并移除用户 PATH 里指向它的条目（做法见 hermes-local-data-hygiene 的 PATH 闸门规则）。删除顺序不可颠倒：先能跑通，再回收空间。**同一次改动必须确认目标 node 目录本身在用户 PATH 中**：npm 的全局入口就装在该目录下，旧条目删掉而新目录不在 PATH 时，新开终端报 `术语 'dsh' 不会被识别为 cmdlet、函数、脚本文件或可执行程序的名称`，且 `node`/`npm`/`pnpm` 同时失效。PATH 改动只对新开终端生效，已开窗口里仍报这句时先换新窗口复测再判故障。
5. **布置完成后把「目标形态」写下来，并标明它不是永久状态**：迁移这四步只解决“现在能不能跑”，dsh 的载荷仍在 pm 组件目录里，下一次组件替换会再做一次同样的事（见本文开头「下一步的判据」）。需要一次到位就把 dsh 装到 pm 管不到的 prefix。

## 迁移前的兼容性取证（回答“能不能指向目标运行时”）

- **版本约束**：遍历依赖树所有 `package.json` 的 `engines.node`，确认**没有上界**（无 `<`、无 `~`）。本机 945 个包里 164 个有约束，最高下界 `>=22.19.0`，目标运行时满足。
- **原生模块 ABI 形态**：找 `*.node`；文件名不带 ABI 后缀、或显式 `napi-v9`，即 NAPI 预构建（跨 node 大版本稳定）。本机 4 类（sharp / koffi / node-pty / node-addon-require-builtin）全是 NAPI，故不存在“目标版本缺 ABI 预构建”。
- **直接 require**：在 dsh 的依赖上下文里逐个加载原生模块 —— `createRequire('<dsh>/lib/bin.js')` 后 `require('sharp'|'koffi'|'node-pty')`，新旧运行时结果必须**逐项一致**；某包在两套下都失败才是包自身的问题（本机 `@img/sharp-win32-x64` 即如此，无 `exports` main，与运行时无关）。
- **组合树等价性**：`dsh --profile <name> --dump-config` 在新旧运行时下的输出**逐行相同**（本机 1504 行）是最强的单条证据，比任何体积或版本号比对可靠。
- **兜底比对**：原生二进制逐字节（`conpty.node` / `koffi.node` / `sharp*.node`）+ 载荷总体积/文件数/包数（本机 237.92 MB / 5307 文件 / 282 包）。

## 已知无害告警

npm 11+ 的 `npm i -g` 会列出未执行的 install 脚本（`@deepseek-ai/dsh-subprocess-local`、`koffi`、`node-pty`、`protobufjs`、`@google/genai`）并要求 `--allow-scripts`。**实测无害**：prebuilt 随包发布，新旧树的原生二进制字节数完全相同、模块加载结果一致。不要为它放开 allow-scripts。

## 服务冒烟

- `dsh web --no-open --port <空闲端口>`；探本机端口必须 `curl --noproxy '*'`，否则请求经 `HTTP_PROXY` 打到代理拿到 503，会被误判成服务异常。`GET /` 返回 401 即服务与鉴权正常。
- 启动行里的 `?token=…` **只在 TTY 下打印**（用 pty 启动才看得到）；token 随实例关闭失效。
- 测试实例一律按 PID 收尾，并复核端口已释放、无残留 node 进程。
- 未做真实对话（CDP 发消息）验证时，要明确说明这一点，不要用“服务起来了”替代“功能正常”。

## 迁移后的入口可见性（“dsh 不被识别”类报错）

判定顺序（全部只读）：

1. 读注册表用户 PATH：`[Environment]::GetEnvironmentVariable('Path','User')` 是否含目标 node 目录。这一条决定新终端能不能解析 `dsh`，比在会话里试跑可靠。
2. 当前终端命中哪个适配脚本：PowerShell 用 `(Get-Command dsh).Source`。实测 PowerShell 命中 `dsh.ps1`，被本机执行策略拒绝（报“禁止运行脚本”，与“不被识别”是两类症状）——处置是显式调 `dsh.cmd …`，或删掉 `dsh.ps1` 让解析落到 `.cmd`；不要为此改全局执行策略。
3. **不要构造最小 PATH 去验证解析结果**：无扩展名的 `dsh` 是 shell 脚本，剥掉系统目录后 git-bash 报 `No such file or directory`，会被误读成入口缺失。判断 PATH 内容用第 1 步的注册表读取。
4. 报错文案直接对应病因：`术语 '<名>' 不会被识别…` = 名不在 PATH；`禁止运行脚本` = 命中了 `.ps1`；`No such file or directory`（git-bash）= 命中 shell 脚本但解释器不可用。
