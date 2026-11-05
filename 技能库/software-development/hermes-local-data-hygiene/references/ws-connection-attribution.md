# 按 ESTABLISHED 连接数归因「谁在重连」

适用于连接风暴的归因环节：`logs/` 里每秒都在 accept/close，但窗口刷屏、logger 名不可信、`netstat` 抓不到瞬时连接（见 `hermes-local-data-hygiene` 六之一节）。

## 一、为什么不看 logger 名

`tui_gateway.ws` 是共享署名。dashboard 的内嵌 chat 侧边栏走的也是同一套处理器：

```
hermes_cli/web_routers/chat_ws.py :: @router.websocket("/api/ws")
  → await handle_ws(ws, auth_identity=..., subprotocol=...)
  → tui_gateway/ws.py :: handle_ws
```

所以两侧的 accept/close 行长得一模一样。实测踩坑：把风暴归给 TUI，下一轮用连接数一量，dashboard 与浏览器各 160+ 条、TUI gateway 个位数，数量级落差直接推翻该结论。

## 二、归因配方

按 PID 统计 ESTABLISHED 条数（不要按远端端口过滤——瞬时连接采不到）：

```python
import subprocess, collections
r = subprocess.run(["netstat","-ano","-p","TCP"], capture_output=True, text=True, errors="replace")
listen, est = collections.defaultdict(list), collections.Counter()
for l in r.stdout.splitlines():
    if not l.startswith("  TCP"):            # 过滤表头/尾巴
        continue
    p = l.split()
    if len(p) < 5:
        continue
    lp, rp, st, pid = p[1], p[2], p[3], p[4]
    if st == "LISTENING":
        listen[pid].append(lp)
    elif st == "ESTABLISHED":
        est[pid] += 1
for pid, n in est.most_common(8):
    name = subprocess.run(["tasklist","/FI",f"PID eq {pid}","/FO","CSV","/NH"],
                          capture_output=True, text=True, errors="replace").stdout.split(",")[0].strip('"')
    print(f"{pid:7s} {name:18s} est={n:4d} listen={listen.get(pid, [])}")
```

判读三条：

1. **两端数目咬合**即同一批连接的两端（实测 dashboard 服务 170 / 浏览器 164）。
2. **一方为 0**（TUI 前端 node、`Get-NetTCPConnection -OwningProcess <pid>` 返回空）说明它不是这一簇的连接方，别因为它在窗口父链上就归给它。
3. **自己连自己**（同一 PID 占两个回环端口且互为对端）是进程内部的固定握手，与风暴无关。

再看 `TIME_WAIT` 是否稳定不降：新建速率与回收速率持平即是长期泄漏，不是一次性抖动。两次采样间隔 5–6 秒即可看出是否在增长。

## 三、为什么 `netstat` 可能「看不到」

实测：反复采样 20 秒、对 gateway 监听端口命中 0 条，而日志里每秒都在 accept/close。原因有二——连接寿命短于采样间隔；以及**采样工具本身慢**：`Get-NetTCPConnection` 单次约 0.5 s，循环 400 次的 PowerShell 必然超时（实测 200 s 超时），循环里再嵌 `Get-Process` 更慢。

替代做法：① 用原生 `netstat -ano -p TCP` 每轮全量输出，在 Python 侧过滤 PID 列；② 若必须对照「刚 accept 的 peer 端口」，解析日志取最新 `ws accepted peer=127.0.0.1:<port>` 后立刻 `netstat` 搜 `:<port> `——但通常只会看到 `TIME_WAIT`/`pid=0`，因为连接已经死了。三条路都可能落空，所以**归因靠全局 ESTABLISHED 分布、不靠追单条连接**。
