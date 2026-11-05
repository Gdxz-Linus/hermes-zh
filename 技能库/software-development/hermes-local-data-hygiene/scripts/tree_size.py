"""按顶层条目统计 Hermes 主目录占用空间，跳过体积巨大且无需统计的子树。

用法（git-bash，Windows）：
    python tree_size.py [--home <HERMES_HOME>] [--skip installs,node,hermes-agent] [--min-mb 0.05]

为什么不用 du -sh：Windows 上对含 venv / node_modules 的树递归会超时（实测 300 s 未返回）。
输出按体积降序，格式为“体积 / 文件数 / 名称”，可直接贴进核对报告。
"""
import argparse
import os

DEFAULT_SKIP = "installs,node,hermes-agent"


def size(path):
    """返回 (字节数, 文件数)；单文件按自身计。"""
    if os.path.isfile(path):
        return os.path.getsize(path), 1
    total = files = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
                files += 1
            except OSError:
                pass
    return total, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--home",
        default=os.environ.get("HERMES_HOME") or os.path.expanduser("~/AppData/Local/hermes"),
        help="Hermes 主目录（默认取 HERMES_HOME，否则 Windows 默认路径）",
    )
    ap.add_argument("--skip", default=DEFAULT_SKIP, help="逗号分隔的跳过项（顶层名称）")
    ap.add_argument("--min-mb", type=float, default=0.05, help="只显示不小于该体积的条目")
    args = ap.parse_args()

    skip = {s for s in args.skip.split(",") if s}
    rows = []
    for name in sorted(os.listdir(args.home)):
        if name in skip:
            continue
        total, files = size(os.path.join(args.home, name))
        if total / 1048576 >= args.min_mb:
            rows.append((total, files, name))

    print(f"# {args.home}  跳过: {sorted(skip) if skip else '无'}")
    for total, files, name in sorted(rows, reverse=True):
        print(f"{total / 1048576:9.2f} MB  {files:7d} 个文件  {name}")


if __name__ == "__main__":
    main()
