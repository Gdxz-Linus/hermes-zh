#!/usr/bin/env bash
# 只读：Hermes 本机可用性核查。用法：bash hermes_health_check.sh [dashboard_port]
# 输出为「项目 / 实测值」两列，可直接作为回复中的对照表。
# 不写任何文件（--output、--stdout /dev/null 均不落临时文件）。
set -u

H="${HERMES_HOME:-$HOME/AppData/Local/hermes}"
PORT="${1:-9119}"

hr() { printf -- '--- %s\n' "$1"; }
verdict() { # verdict <code> <含义>  401=在监听但拒匿名; 200=凭据可用
  case "$1" in
    200) echo "HTTP 200 —— 可达且凭据可用" ;;
    401) echo "HTTP 401 —— 服务在监听，拒匿名（预期）" ;;
    000) echo "无响应 —— 需查进程/端口" ;;
    *)   echo "HTTP $1" ;;
  esac
}

echo "=== 本机时间 ==="
date '+%Y-%m-%d %H:%M:%S %Z'

hr '会话'
(cd "$H" && hermes sessions list 2>&1 | head -8)

hr '主模型配置（config.yaml）'
grep -nE '^  (default|provider|base_url|api_mode|key_env):' "$H/config.yaml" | head -6

hr 'providers 段'
grep -n -A 6 '^providers:' "$H/config.yaml"

hr '凭据键计数（.env，非注释）'
for k in LLM_GW_API_KEY DEEPSEEK_API_KEY; do
  printf '%-20s %s\n' "$k" "$(grep -cE "^${k}=" "$H/.env" 2>/dev/null)"
done

BASE_URL=$(sed -n 's/^  base_url: *//p' "$H/config.yaml" | head -1 | tr -d "'\"")
hr "端点连通：$BASE_URL/models（裸请求 / 带凭据）"
printf '裸请求   %s\n' "$(verdict "$(curl -s -o /dev/null -w '%{http_code}' "${BASE_URL%/}/models" --max-time 10)")"
KEY=$(grep -E '^LLM_GW_API_KEY=' "$H/.env" 2>/dev/null | head -1 | cut -d= -f2-)
if [ -n "$KEY" ]; then
  printf '带凭据   %s\n' "$(verdict "$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $KEY" "${BASE_URL%/}/models" --max-time 10)")"
else
  echo '带凭据   跳过（.env 无 LLM_GW_API_KEY）'
fi

hr "dashboard（127.0.0.1:$PORT）"
printf '首页     HTTP %s\n' "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/" --max-time 8)"
printf 'model/info '; curl -s "http://127.0.0.1:$PORT/api/model/info" --max-time 10 | head -c 400; echo

hr '本会话实际调用（agent.log 最近 6 条）'
grep 'API call #' "$H/logs/agent.log" 2>/dev/null | tail -6 | grep -oE 'model=[^ ]+ provider=[a-z-]+'

hr '会话记账（state.db）'
python - <<PY 2>/dev/null || echo '（无法读取 state.db）'
import sqlite3, os
p = os.path.join(os.path.expanduser(r"$H"), "state.db")
c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
for r in c.execute("select id, model, billing_provider, billing_base_url from sessions"):
    print("  ", r)
PY

echo
echo '注：curl 取状态码时退出码 23（写 body 失败）属正常，HTTP 状态码仍可信。'
