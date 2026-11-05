# WSL 镜像网络模式故障（3.0.x 已知问题家族）

## 症状判别

- `.wslconfig` 配了 `networkingMode=Mirrored`，但 WSL 内 `ip -br addr` 只剩 `lo`（正常应见与主机同名网卡与 `loopback0`）。
- 启动横幅报 `CreateInstance/CreateVm/ConfigureNetworking/0x8007054f`，随后静默退到**无网络**模式——不是退回 NAT，是完全没有网卡、没有 DNS。
- 间歇性发作：同一份配置有时正常有时失败，与虚拟机创建那一刻主机网卡状态有关（VPN 虚拟网卡状态变化、系统代理都是已知触发因素）。
- 本机伴生横幅：`检测到 localhost 代理配置，但未镜像到 WSL`（系统代理 127.0.0.1:xxxx 被识别为干扰因素）。

## 处置顺序（实测有效）

1. 完整 `wsl --shutdown`，等 4 秒以上再启动；多试两次——间歇性故障常就此恢复。
2. 不行则管理员 PowerShell 重启 HNS 服务（`Restart-Service hns -Force`）再 shutdown 重启。
3. 再不行：临时切 `.wslconfig` 为 `networkingMode=NAT` 保底（NAT 不受此缺陷影响，WSL 内拿 172.x 地址、外网可达），恢复镜像等后续 WSL 升级。

## 排查时先排除两个非成因

- TCP 动态端口范围被改宽：`netsh int ipv4 show dynamicport tcp` 应为默认 49152/16384。
- 系统代理：横幅会点名 localhost 代理，但实测启动时关掉代理**不一定**恢复——关代理只是候选项之一。

## 使用注意

- 判“故障复发”前先确认虚拟机真的重建过：闲置自动关停后再启动时最容易发作；长会话中途 WSL 网卡可能消失（实测：会话早段镜像正常，闲置关停重启后只剩 lo）。
- 验证恢复用最小探针：WSL 内 `ip -br addr` + `curl -m 5 --noproxy '*' http://www.baidu.com`；主机侧 `netstat -ano | grep :<port>` 确认监听。
- 依赖 WSL 真内核的验证任务开工前先跑一次探针，别编到一半才发现网络没了（实测 WSL 内 cargo build 因此中断过）。

## 验证脚本传递与迭代的坑

- **多文件验证脚本向 WSL 传递时用 base64 编码内容**：外层 Python → wsl bash -c → 内嵌 Python 的多层引号嵌套会互相污染（症状：SyntaxError unexpected character after line continuation、变量展开为空串）；把脚本与探针内容 base64 编码后传给 WSL 侧 `echo <b64> | base64 -d > /tmp/<task>/x.py` 解码落地，执行前先确认文件存在。
- **批量验证脚本失败时先核对脚本磁盘内容**：多次写入/覆盖同一个验证脚本后，执行结果与预期不符时先 cat 磁盘上的脚本确认内容是最新版本——stale-write 保护拒绝覆盖时旧版本还在磁盘上，执行的可能是旧逻辑；三个验证项里只有一项失败时，先查失败探针自己的输出（超时＝服务没响应或没监听）再下结论。
- **内嵌 Python 探针的 base64 载荷先在 Windows 侧自译码回读核对**：长 base64 串经多层引号拼接后可能被截断或变形（症状：WSL 侧解码出的探针报语法错、字段名残缺），先在 Windows 侧把同一串 base64 译码回读，确认与原文一致再传；落地后再用 `python3 -m py_compile` 验语法。直接手写短探针（十几行）比长 base64 串更不易错。
- **手写报文的常量区编码先查协议常量表**：DNS class 线上编码 IN=1、CH=3、HS=4——把 CH(3) 当 IN 读反，会让每层探针证据互相矛盾，引着人去追不存在的覆盖点；假对端打印常量名而非裸数字，解码正确性不再变量。
- **WSL 是 Unix 专属编译错误的唯一本机验证口**：`cfg(unix)` 块内的错误（变量名对不上、libc 签名按平台不同）在 Windows 上永远编不出来——推送前在 WSL 跑 `RUSTFLAGS='-D warnings' cargo check`（与 CI 兼容性检查同门槛），补丁改动里凡有平台条件编译，两端各验一遍；WSL 侧真连外网的测试用例可能因本机出站限制超时（如直接查 8.8.8.8 的用例），这类失败先判网络环境再判代码。