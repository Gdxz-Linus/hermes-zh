# -*- coding: utf-8 -*-
"""汉化映射表维护：对比当前安装版本与映射表，报告差异。

映射表即基线
------------
映射表不回头看 Git 历史，也不与仓库任何提交绑定。它自己就是汉化的完整基线。
升级到哪个版本，那个版本就是新的基线。只处理有变化的条目，未变化的原样保留。

用法
----
    python 汉化维护.py            # 看差异（只报告，不改文件）
    python 汉化维护.py --apply    # 清理删减项，补齐新增项（中文留空待译）

典型流程
--------
    hermes update                 升级
    python 汉化维护.py            看有哪些变化
    按报告补译新增与变化的条目
    python 汉化维护.py --apply    清理已删减的条目
    python 部署汉化.py            部署到运行环境
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import 汉化库 as lib  # noqa: E402

# ── 扫描当前安装版本 ──────────────────────────────────────────────


def scan_installed_tools(repo: Path) -> dict:
    """扫描当前安装版本的 tools/，提取英文工具描述。"""
    tools: dict = {}
    tools_dir = repo / "tools"
    if not tools_dir.exists():
        return tools
    for path in sorted(tools_dir.glob("*.py")):
        source = path.read_text(encoding="utf-8", errors="ignore")
        for name, data in lib.extract_tool_schemas(source).items():
            entry: dict = {}
            if data.get("description"):
                entry["description"] = data["description"]
            if data.get("params"):
                entry["params"] = data["params"]
            if entry:
                tools[name] = entry
    return tools


def scan_installed_plugin_tools(plugins_root: Path) -> dict:
    """扫描当前安装的外部安装插件，提取英文工具描述。

    跳过测试目录：插件测试里常有 {"name": "Create spec"} 这类示例字典。
    """
    tools: dict = {}
    if not plugins_root.exists():
        return tools
    for plugin_dir in sorted(p for p in plugins_root.iterdir() if p.is_dir()):
        if not (plugin_dir / ".git").exists():
            continue
        for py in sorted(plugin_dir.rglob("*.py")):
            parts = py.parts
            if "__pycache__" in parts or "tests" in parts or "test" in py.name:
                continue
            source = py.read_text(encoding="utf-8", errors="ignore")
            for name, data in lib.extract_tool_schemas(source).items():
                # 真实工具名只用小写字母、数字与下划线
                if not name.replace("_", "").isalnum() or not name.islower():
                    continue
                if name in tools:
                    continue
                entry: dict = {}
                if data.get("description"):
                    entry["description"] = data["description"]
                if data.get("params"):
                    entry["params"] = data["params"]
                if entry:
                    tools[name] = entry
    return tools


def scan_installed_prompts(repo: Path, workdir: Path) -> dict:
    """扫描当前安装版本的提示词模块，提取英文常量。"""
    prompts: dict = {}
    for module in lib.PROMPT_MODULES:
        path = repo / "agent" / f"{module}.py"
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        consts = lib.extract_prompt_consts(
            source, module_name=f"probe_{module}", workdir=workdir
        )
        for name, value in consts.items():
            prompts.setdefault(module, {})[name] = value
    return prompts


# ── 差异对比 ──────────────────────────────────────────────────────


def diff_tools(current: dict, mapping: dict) -> dict:
    """对比英文原文与映射表英文侧。"""
    added, removed, changed = [], [], []
    for name, data in current.items():
        if name not in mapping:
            added.append(name)
            continue
        old = mapping[name]
        old_en = old.get("en", "")
        new_en = data.get("description", "")
        if old_en and new_en and old_en != new_en:
            changed.append(f"{name}.description")
        old_ps = old.get("params_en", {})
        for pname, pdesc in data.get("params", {}).items():
            if pname in old.get("params", {}) and pname in old_ps and old_ps[pname] != pdesc:
                changed.append(f"{name}.{pname}")
    for name in mapping:
        if name not in current:
            removed.append(name)
    return {"added": added, "removed": removed, "changed": changed}


def diff_prompts(current: dict, mapping: dict) -> dict:
    """对比英文原文与映射表英文侧。"""
    added, removed, changed = [], [], []
    for module, consts in current.items():
        for name, value in consts.items():
            key = f"{module}.{name}"
            if module not in mapping or name not in mapping[module]:
                added.append(key)
            else:
                old_en = mapping[module][name].get("en", "")
                if old_en and old_en != value:
                    changed.append(key)
    for module, consts in mapping.items():
        for name in consts:
            if module not in current or name not in current[module]:
                removed.append(f"{module}.{name}")
    return {"added": added, "removed": removed, "changed": changed}


def report(label: str, result: dict, *, skip_anchors: bool = False) -> int:
    """打印一类差异，返回需处理的数量。"""
    added = result["added"]
    if skip_anchors:
        added = [k for k in added if k not in lib.PROMPT_ANCHORS]

    total = len(added) + len(result["removed"]) + len(result["changed"])
    if not total:
        print(f"  {label}: 无变化")
        return 0

    print(
        f"  {label}: 新增 {len(added)}，删减 {len(result['removed'])}，"
        f"内容变化 {len(result['changed'])}"
    )
    for name in added[:20]:
        print(f"      新增  {name}")
    if len(added) > 20:
        print(f"      …… 另有 {len(added) - 20} 项新增")
    for name in result["removed"][:20]:
        print(f"      删减  {name}")
    if len(result["removed"]) > 20:
        print(f"      …… 另有 {len(result['removed']) - 20} 项删减")
    for name in result["changed"][:20]:
        print(f"      变化  {name}")
    if len(result["changed"]) > 20:
        print(f"      …… 另有 {len(result['changed']) - 20} 项变化")
    return total


# ── 主流程 ────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="汉化映射表差异对比")
    parser.add_argument("--apply", action="store_true", help="清理删减项，补齐新增项")
    parser.add_argument("--repo", default=str(lib.REPO), help="Hermes 安装路径")
    args = parser.parse_args()

    repo = Path(args.repo)
    if not repo.exists():
        print(f"安装路径不存在：{repo}")
        return 1

    core_tools = lib.load_json(lib.CORE_TOOLS)
    plugin_tools = lib.load_json(lib.PLUGIN_TOOLS)
    prompts_map = lib.load_json(lib.CORE_PROMPTS)

    if not core_tools and not plugin_tools and not prompts_map:
        print("映射表不存在。")
        return 1

    print(
        f"映射表基线：核心工具 {len(core_tools)} 个，"
        f"插件工具 {len(plugin_tools)} 个，"
        f"提示词 {lib.prompt_count(prompts_map)} 段"
    )
    print()

    workdir = lib.ROOT / "_probe"
    try:
        return _run_compare(repo, core_tools, plugin_tools, prompts_map, workdir, args)
    finally:
        # 临时目录用完即删，不留垃圾
        shutil.rmtree(workdir, ignore_errors=True)


def _run_compare(repo, core_tools, plugin_tools, prompts_map, workdir, args) -> int:
    """对比差异并可选应用。"""
    cur_core = scan_installed_tools(repo)
    cur_plug = scan_installed_plugin_tools(lib.RUNTIME_PLUGINS_ROOT)
    cur_prompts = scan_installed_prompts(repo, workdir)

    print("对比当前安装版本与映射表：")
    t_core = diff_tools(cur_core, core_tools)
    t_plug = diff_tools(cur_plug, plugin_tools)
    p_diff = diff_prompts(cur_prompts, prompts_map)
    total = (
        report("核心工具", t_core)
        + report("插件工具", t_plug)
        + report("提示词", p_diff, skip_anchors=True)
    )
    print()

    if not total:
        print("映射表与当前安装版本一致，无需维护。")
        return 0

    if args.apply:
        removed = 0
        for name in t_core["removed"]:
            core_tools.pop(name, None)
            removed += 1
        for name in t_plug["removed"]:
            plugin_tools.pop(name, None)
            removed += 1
        for key in p_diff["removed"]:
            module, _, name = key.partition(".")
            if module in prompts_map:
                prompts_map[module].pop(name, None)
                if not prompts_map[module]:
                    prompts_map.pop(module, None)
                removed += 1

        added = 0
        for name in t_core["added"]:
            src = cur_core[name]
            core_tools[name] = {
                "en": src.get("description", ""),
                "description": "",
                "params_en": src.get("params", {}),
                "params": {},
            }
            added += 1
        for name in t_plug["added"]:
            src = cur_plug[name]
            plugin_tools[name] = {
                "en": src.get("description", ""),
                "description": "",
                "params_en": src.get("params", {}),
                "params": {},
            }
            added += 1
        for key in p_diff["added"]:
            if key in lib.PROMPT_ANCHORS:
                continue  # 锚点不翻译，也不入映射表
            module, _, name = key.partition(".")
            prompts_map.setdefault(module, {})[name] = {
                "en": cur_prompts[module][name],
                "zh": "",
            }
            added += 1

        lib.save_json(lib.CORE_TOOLS, core_tools)
        lib.save_json(lib.PLUGIN_TOOLS, plugin_tools)
        lib.save_json(lib.CORE_PROMPTS, prompts_map)
        print(f"已清理 {removed} 项删减条目，补齐 {added} 项新增条目。")
        print("新增条目的中文侧为空，需补译后运行 部署汉化.py 部署。")
        return 0

    print("这是报告模式，未改动文件。")
    print("  --apply    清理删减项并补齐新增项")
    print("  补译完成后运行 部署汉化.py 部署到运行环境")
    return 0


if __name__ == "__main__":
    sys.exit(main())