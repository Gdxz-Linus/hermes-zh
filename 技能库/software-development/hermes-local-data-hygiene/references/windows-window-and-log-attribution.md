# Windows 上「哪个窗口在刷屏 / 谁的日志在涨」的取证配方

适用于用户报「运行某个工具时跳出一堆窗口 / 某个窗口大量输出 / 分不清是谁的」，以及需要区分「日志文件增长」与「终端窗口刷屏」两种情况。

## 一、两件事先分清

| 现象 | 真实来源 | 取证位置 |
|---|---|---|
| 终端窗口持续输出 | TUI 重绘，或子进程的 stdout/stderr | 窗口枚举 + 进程父链 |
| 磁盘上日志文件变大 | 写文件的 logger | `ls -lS <hermes_home>/logs/` |

高日志量 **不会** 往终端窗口打印——它是文件。反过来，界面重绘也不写日志。用户把两者混为一谈时，先各自量一次再回答。

## 二、窗口枚举（含不可见）

只看「可见窗口」会漏掉隐藏的伪控制台；只看窗口标题会漏掉标题为空的 ConsoleWindowClass。一次枚举拿到四元组：`ProcId` / `IsWindowVisible` / `GetClassName` / `Title`，再把 `ProcId` 接上进程父链。

```powershell
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint procid);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
}
'@
$rows = New-Object System.Collections.Generic.List[object]
[W]::EnumWindows({ param($h,$l)
  $sb = New-Object System.Text.StringBuilder 512; [void][W]::GetWindowText($h,$sb,512)
  $cn = New-Object System.Text.StringBuilder 256; [void][W]::GetClassName($h,$cn,256)
  [uint32]$procid = 0; [void][W]::GetWindowThreadProcessId($h,[ref]$procid)
  $r = New-Object W+RECT; [void][W]::GetWindowRect($h,[ref]$r)
  $rows.Add([pscustomobject]@{ ProcId=$procid; Vis=[W]::IsWindowVisible($h); Class=$cn.ToString()
                               Title=$sb.ToString(); Size="$(($r.R-$r.L))x$(($r.B-$r.T))" })
  return $true
}, [IntPtr]::Zero) | Out-Null
$rows | Format-Table -AutoSize | Out-String -Width 170
```

写这段脚本的两个坑：

- **循环变量不要叫 `$pid`**——它是 PowerShell 的只读自动变量，赋值即 `VariableNotWritable`，且异常会在 `Add-Type` 委托内部发生，报错位置看着像 `GetWindowThreadProcessId` 调用失败，容易误判。用 `$procid`。
- **传给 `[ref]` 出参的变量要先声明类型**（`[uint32]$procid = 0`），否则报“无法用 2 个参数调用”的转换异常。
- 用 `execute_code` 起 PowerShell 时，`Add-Type` 的 here-string 与 `$` 变量经 bash 都会被吃；把整段写进 Python 三引号字符串再传 `-Command`，不要拼 shell 单引号。

## 三、按父链归因（关键）

窗口类名说明**类型**，父链说明**归属**。本机实测过的一棵树：

```
wt.exe (WindowsTerminal)                      → CASCADIA_HOSTING_WINDOW_CLASS 窗口
  └─ pwsh.exe (管理员)
      └─ hermes.exe dashboard
          └─ python.exe
              ├─ node.exe  ui-tui/dist/entry.js    → PseudoConsoleWindow（0×0）
              └─ python.exe → bash → 每条 terminal 命令
```

结论：那个「管理员:PowerShell」窗口就是 TUI 的宿主，刷屏是设计行为。

常见类名对照：

| 类名 | 含义 |
|---|---|
| `CASCADIA_HOSTING_WINDOW_CLASS` | Windows Terminal 窗口（`wt.exe`） |
| `ConsoleWindowClass` | 独立 conhost 控制台窗口（`cmd`/`node`/第三方服务都有） |
| `PseudoConsoleWindow` | ConPTY 伪控制台，宿主是起了 PTY 的那个进程；尺寸常为 0×0 |
| `Chrome_WidgetWin_1` | Chromium 系（Edge/Chrome）窗口，含 dashboard 网页 |

另：`Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'conhost.exe' }` 能列出所有控制台宿主，再用 `ParentProcessId` 归因。conhost 数量多不等于有问题——VPN 客户端、下载器扩展宿主、驱动服务都会各留一个。

## 四、日志体量的测量与处理

```bash
ls -lS <hermes_home>/logs/ | head -20     # 按体积排，一眼看出轮转规模
find <hermes_home>/logs -type f | wc -l   # 文件总数
```

判读：单文件上限 × 轮转份数决定稳态占用。本机实测 `gui.log` 单文件 10 MB（`.log.1`/`.log.2`/`.log.3` 各一份，均满）+ 现行 6.9 MB、`agent.log` 5 MB × 3 份，一天合计约 60 MB——这个量级说明有高频重复写入，值得单独查写入方，而不只是清理。

处理：已轮转的 `.log.N` 可安全删除（现行文件别动）。**但不要顺手清零现行的 `agent.log`/`gui.log`/`errors.log`**——`hermes-local-data-hygiene` 第五节已记录该影响：会连带丢失清理之前的历史诊断信息，报出去前必须明确写为影响项。
