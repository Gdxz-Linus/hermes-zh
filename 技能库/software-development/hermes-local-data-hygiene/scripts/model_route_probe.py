#!/usr/bin/env python
"""在指定 HERMES_HOME 上离屏核对模型路由：配置面 / 凭据池 / 目录缓存 / 切换落点。

只读：不写 config.yaml，不发起推理请求。用于核对「切模型后是否回落到厂商端点」。

用法（两点都是硬要求）：
  1. HERMES_HOME 必须传 Windows 原生路径（C:/Users/...），不能是 MSYS 风 /c/... —— 否则
     源码读不到该 home 的 .env/config.yaml，会误判为「未配置」。
  2. 必须用依赖环境的解释器：<home>/installs/*/environments/*/venv/Scripts/python.exe。
     tools/python-* 不含三方依赖，import hermes_cli.config 会因缺 ruamel 失败。

    HERMES_HOME=C:/Users/<user>/AppData/Local/hermes \
      <home>/installs/<id>/environments/<hash>/venv/Scripts/python.exe model_route_probe.py

可选：HERMES_SRC 指定 hermes-agent 源码树（默认 <HERMES_HOME>/hermes-agent）。
建议先在 scratch 副本 home 上跑，跑完比对副本与原文件。
"""
import json
import os
import sys


def _die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception as exc:  # 缺失或损坏都不影响主结论
        print("  (读取失败 %s: %s)" % (path, exc))
        return {}


def main():
    home = os.environ.get("HERMES_HOME", "")
    norm = home.replace("\\", "/")
    if not home:
        _die("未设置 HERMES_HOME")
    if norm.startswith("/") and not norm.startswith("//"):
        _die("HERMES_HOME 必须是 Windows 原生路径（C:/Users/...），当前是: %s" % home)
    src = os.environ.get("HERMES_SRC") or os.path.join(home, "hermes-agent")
    if not os.path.isdir(src):
        _die("找不到源码树: %s（用 HERMES_SRC 指定）" % src)
    sys.path.insert(0, src)

    from hermes_cli.config import load_config
    from hermes_cli.model_switch import switch_model

    cfg = load_config()
    model_cfg = cfg.get("model") if isinstance(cfg.get("model"), dict) else {}
    cur_provider = str(model_cfg.get("provider") or "")
    cur_model = str(model_cfg.get("default") or model_cfg.get("model") or "")
    cur_base = str(model_cfg.get("base_url") or "")

    print("== 配置面 ==")
    print("  model    :", json.dumps(model_cfg, ensure_ascii=False))
    print("  providers:", json.dumps(cfg.get("providers") or {}, ensure_ascii=False))
    print("  当前路由 : provider=%s model=%s base_url=%s" % (cur_provider, cur_model, cur_base))

    pool = (_load_json(os.path.join(home, "auth.json")).get("credential_pool") or {})
    if pool:
        print("== 凭据池（auth.json: credential_pool）==")
        print("  同名厂商条目在自己的 base_url 上不代表回退到官方端点；比对地址与指纹。")
        for name, entries in pool.items():
            for entry in entries or []:
                print("  %-12s base_url=%-38s fingerprint=%s" % (
                    name, entry.get("base_url") or "-", entry.get("secret_fingerprint") or "-"))

    cache = _load_json(os.path.join(home, "provider_models_cache.json"))
    if cache:
        print("== 目录缓存（provider_models_cache.json）==")
        for name, blob in cache.items():
            print("  %-40s models=%s" % (name, json.dumps((blob or {}).get("models"), ensure_ascii=False)))

    # 起点：会话当前 provider 快照、bare custom，以及凭据池/缓存里出现的其它 provider 名。
    starts = [cur_provider or "auto", "custom"]
    for name in list(pool.keys()) + list(cache.keys()):
        if name not in starts:
            starts.append(name)
    probes = [cur_model] if cur_model else []
    for name in starts:
        for mid in ((cache.get(name) or {}).get("models") or []):
            if mid not in probes:
                probes.append(mid)

    user_providers = cfg.get("providers") if isinstance(cfg.get("providers"), dict) else {}
    print("== 切换落点（switch_model，只读）==")
    print("  explicit 非空 = WebUI/PUT /api/model/set 路径；explicit 为空 = TUI /model 路径。")
    for start in starts:
        for raw in probes:
            for explicit in ("", cur_provider):
                try:
                    r = switch_model(
                        raw_input=raw, explicit_provider=explicit or "", is_global=True,
                        current_provider=start, current_model=cur_model,
                        current_base_url=cur_base, user_providers=user_providers)
                    note = "" if r.success else (r.error_message or "")
                    print("  start=%-10s explicit=%-10s raw=%-28s -> %s/%s ok=%s %s" % (
                        start, explicit or "-", raw, r.target_provider, r.new_model, r.success, note))
                except Exception as exc:
                    print("  start=%-10s explicit=%-10s raw=%-28s -> ERROR %s: %s" % (
                        start, explicit or "-", raw, type(exc).__name__, exc))

    print("（本探针不写配置；在副本 home 上跑时，请比对副本文件确认未被改写）")


if __name__ == "__main__":
    main()
