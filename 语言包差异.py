# -*- coding: utf-8 -*-
"""语言包差异抽取：从安装版语言包中抽出与官方英文版不同的键。

为什么需要
----------
Hermes 语言包加载顺序是：插件 > 用户层 locales/ > 仓库 locales/ > 英文 > 裸键。
用户层优先级高于仓库层，所以用户层只应放「与仓库官方版不同的键」，
否则会覆盖掉仓库的更新。

用法
----
    python 语言包差异.py            # 抽取并写入 语言包/
    python 语言包差异.py --dry-run  # 只报告
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import 汉化库 as lib  # noqa: E402

LOCALE_FILES = ("zh.yaml", "zh.tui.yaml", "zh-hant.yaml", "zh-hant.tui.yaml")


def parse_yaml_flat(path: Path) -> dict[str, str]:
    """把 YAML 摊平成「点分键 → 值」。"""
    if not path.exists():
        return {}

    result: dict[str, str] = {}
    stack: list[tuple[int, str]] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if ":" not in stripped:
            continue

        key, _, value = stripped.partition(":")
        key = key.strip().strip('"').strip("'")
        value = value.strip()

        while stack and stack[-1][0] >= indent:
            stack.pop()

        prefix = ".".join(k for _, k in stack)
        full = f"{prefix}.{key}" if prefix else key

        if not value:
            stack.append((indent, key))
            continue

        if value.startswith(('"', "'")):
            value = value[1:-1] if len(value) > 1 else ""
        result[full] = value

    return result


def write_yaml_flat(path: Path, flat: dict[str, str]) -> None:
    """把点分键写回嵌套 YAML。"""
    tree: dict = {}
    for key, value in flat.items():
        parts = key.split(".")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                break
        else:
            node[parts[-1]] = value

    lines: list[str] = []
    _emit(tree, 0, lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _emit(node: dict, indent: int, lines: list[str]) -> None:
    pad = " " * indent
    for key, value in node.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            _emit(value, indent + 2, lines)
        else:
            escaped = str(value).replace('"', '\\"')
            lines.append(f'{pad}{key}: "{escaped}"')


def main() -> int:
    parser = argparse.ArgumentParser(description="抽取语言包差异键")
    parser.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    args = parser.parse_args()

    repo_locales = lib.REPO / "locales"
    total = 0

    for name in LOCALE_FILES:
        base_path = repo_locales / name
        zh_path = lib.RUNTIME_LOCALES / name

        if not base_path.exists():
            print(f"  {name:20} 仓库版不存在，跳过")
            continue
        if not zh_path.exists():
            print(f"  {name:20} 用户层不存在，跳过")
            continue

        zh = parse_yaml_flat(zh_path)
        base = parse_yaml_flat(base_path)
        diff = {k: v for k, v in zh.items() if base.get(k) != v}

        print(f"  {name:20} 汉化 {len(zh)} 键，差异 {len(diff)} 键")
        total += len(diff)

        if not args.dry_run:
            write_yaml_flat(lib.LOCALES_DIR / name, diff)

    print()
    print(f"合计 {total} 个差异键")

    if args.dry_run:
        print("dry-run，未写文件")
        return 0

    print(f"已写入 {lib.LOCALES_DIR}")
    print("下一步：python 部署汉化.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())