# -*- coding: utf-8 -*-
"""部署汉化到 Hermes 运行环境。

本脚本只做汉化，不处理配置、插件、技能库以外的东西。

部署内容
--------
    映射表     核心/提示词 + 工具/工具 + 插件/插件工具  → 合并后写入汉化插件目录
    插件本体   __init__.py、plugin.yaml                 →  HERMES_HOME/plugins/zh-localization-overlay
    语言包     *.yaml                                   →  HERMES_HOME/locales
    技能库     全部技能                                 →  HERMES_HOME/skills

用法
----
    python 部署汉化.py --check    # 只检查，不动文件
    python 部署汉化.py            # 实际部署
    python 部署汉化.py --target "D:\\你的路径\\hermes"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

CORE_PROMPTS = HERE / "核心" / "prompts-zh.json"
CORE_TOOLS = HERE / "工具" / "tools-zh.json"
PLUGIN_TOOLS = HERE / "插件" / "tools-zh.json"
PLUGIN_BODY = HERE / "插件" / "zh-localization-overlay"
LOCALES_DIR = HERE / "语言包"
SKILLS_DIR = HERE / "技能库"

PLUGIN_NAME = "zh-localization-overlay"


def detect_hermes_home() -> Path:
    """探测 Hermes 数据目录。"""
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env)
    try:
        out = subprocess.check_output(
            ["hermes", "config", "path"], stderr=subprocess.DEVNULL, timeout=20
        ).decode("utf-8", "replace").strip()
        if out and Path(out).exists():
            return Path(out)
    except Exception:
        pass
    return Path.home() / "AppData" / "Local" / "hermes"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def copy_file(src: Path, dst: Path, *, check: bool) -> str:
    if not src.exists():
        return "源缺失"
    if dst.exists() and sha256(src) == sha256(dst):
        return "无变化"
    if check:
        return "需更新"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return "已复制"


def copy_tree(src: Path, dst: Path, *, check: bool) -> tuple[int, int]:
    updated = skipped = 0
    if not src.exists():
        return 0, 0
    for item in src.rglob("*"):
        if not item.is_file():
            continue
        if "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        rel = item.relative_to(src)
        status = copy_file(item, dst / rel, check=check)
        if status in ("已复制", "需更新"):
            updated += 1
        else:
            skipped += 1
    return updated, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="部署汉化到 Hermes")
    parser.add_argument("--check", "--dry-run", action="store_true", dest="check",
                        help="只检查，不动文件")
    parser.add_argument("--target", default=None, help="目标 HERMES_HOME（默认自动探测）")
    args = parser.parse_args()

    check = args.check
    target = Path(args.target) if args.target else detect_hermes_home()

    print("=" * 60)
    print("  汉化部署" + ("（检查模式）" if check else ""))
    print("=" * 60)
    print(f"源目录：{HERE}")
    print(f"目标：  {target}")
    print()

    if not target.exists():
        print(f"目标目录不存在：{target}")
        print("请先安装 Hermes，或用 --target 指定正确路径。")
        return 1

    plugin_dir = target / "plugins" / PLUGIN_NAME

    # ── 1. 映射表 ──────────────────────────────────────────────────
    print("[1/4] 映射表")
    core_tools = load_json(CORE_TOOLS)
    plugin_tools = load_json(PLUGIN_TOOLS)
    prompts = load_json(CORE_PROMPTS)

    if not core_tools and not plugin_tools:
        print("  ! 映射表为空，请确认目录结构完整")
        return 1

    merged = dict(core_tools)
    merged.update(plugin_tools)
    prompt_count = sum(len(v) for v in prompts.values() if isinstance(v, dict))

    print(f"  核心工具 {len(core_tools)} 个")
    print(f"  插件工具 {len(plugin_tools)} 个")
    print(f"  合计     {len(merged)} 个")
    print(f"  提示词   {prompt_count} 段")

    if check:
        print("  检查模式，未写入")
    else:
        dump_json(plugin_dir / "tools-zh.json", merged)
        dump_json(plugin_dir / "prompts-zh.json", prompts)
        print(f"  已写入 {plugin_dir}")
    print()

    # ── 2. 插件本体 ────────────────────────────────────────────────
    print("[2/4] 插件本体")
    for name in ("__init__.py", "plugin.yaml"):
        status = copy_file(PLUGIN_BODY / name, plugin_dir / name, check=check)
        print(f"  {name:16} {status}")
    print()

    # ── 3. 语言包 ──────────────────────────────────────────────────
    print("[3/4] 语言包差异键")
    if not LOCALES_DIR.exists() or not any(LOCALES_DIR.glob("*.yaml")):
        print("  语言包目录为空，跳过")
    else:
        for src in sorted(LOCALES_DIR.glob("*.yaml")):
            status = copy_file(src, target / "locales" / src.name, check=check)
            print(f"  {src.name:20} {status}")
    print()

    # ── 4. 技能 ────────────────────────────────────────────────────
    print("[4/4] 汉化技能")
    if not SKILLS_DIR.exists():
        print("  技能库目录不存在，跳过")
    else:
        updated, skipped = copy_tree(SKILLS_DIR, target / "skills", check=check)
        print(f"  更新 {updated} 个文件，跳过 {skipped} 个")
    print()

    print("=" * 60)
    if check:
        print("  检查完成，未改动任何文件")
        print("  去掉 --check 参数即可实际部署")
    else:
        print("  部署完成")
        print()
        print("  后续步骤：")
        print(f"    1. 启用插件：hermes plugins enable {PLUGIN_NAME}")
        print("    2. 重启网关：hermes gateway restart")
        print("    3. 验证日志：")
        print("       grep 汉化覆盖层 <Hermes 数据目录>/logs/gateway.log")
        print()
        print("  期望输出：")
        print(f"    汉化覆盖层：已加载 {len(merged)} 个工具的中文映射")
        print(f"    汉化覆盖层：已加载 {prompt_count} 段提示词映射")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())