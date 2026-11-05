# -*- coding: utf-8 -*-
"""汉化映射表：公共函数库。

所有脚本都从这里取路径与提取函数，改目录结构只需改这一个文件。

目录约定
--------
    本仓库根目录/
      核心/prompts-zh.json      核心提示词映射
      工具/tools-zh.json        核心工具映射
      插件/tools-zh.json        插件工具映射
      语言包/zh*.yaml           语言包差异键
      技能库/                   汉化技能
      插件/zh-localization-overlay/   插件本体
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

# ── 工作目录（本仓库） ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent

CORE_DIR = ROOT / "核心"
TOOLS_DIR = ROOT / "工具"
PLUGINS_DIR = ROOT / "插件"
LOCALES_DIR = ROOT / "语言包"
SKILLS_DIR = ROOT / "技能库"

CORE_PROMPTS = CORE_DIR / "prompts-zh.json"
CORE_TOOLS = TOOLS_DIR / "tools-zh.json"
PLUGIN_TOOLS = PLUGINS_DIR / "tools-zh.json"

PLUGIN_BODY = PLUGINS_DIR / "zh-localization-overlay"

# ── 运行环境（Hermes 安装位置） ────────────────────────────────────
def _detect_hermes_home() -> Path:
    """探测 Hermes 数据目录，三级依次尝试。

    1. 环境变量 HERMES_HOME；
    2. `hermes config path` 的输出——它返回 config.yaml 文件路径，取父目录；
    3. 各平台默认位置，取实际存在的那一个。

    适用于 Windows、Linux、macOS：路径构造全部用 pathlib，不拼接分隔符。
    """
    env = os.environ.get("HERMES_HOME", "").strip()
    if env:
        return Path(env).expanduser()

    try:
        out = subprocess.check_output(
            ["hermes", "config", "path"], stderr=subprocess.DEVNULL, timeout=20
        ).decode("utf-8", "replace").strip()
        if out:
            p = Path(out).expanduser()
            home = p.parent if p.is_file() or p.suffix in (".yaml", ".yml") else p
            if home.is_dir():
                return home
    except Exception:
        pass

    if os.name == "nt":
        default = Path.home() / "AppData" / "Local" / "hermes"
    else:
        default = Path.home() / ".hermes"

    for cand in (Path.home() / ".hermes", Path.home() / "AppData" / "Local" / "hermes"):
        if (cand / "config.yaml").is_file() or (cand / "hermes-agent").is_dir():
            return cand
    return default


HERMES_HOME = _detect_hermes_home()
REPO = HERMES_HOME / "hermes-agent"
RUNTIME_PLUGIN = HERMES_HOME / "plugins" / "zh-localization-overlay"
RUNTIME_LOCALES = HERMES_HOME / "locales"
RUNTIME_SKILLS = HERMES_HOME / "skills"
RUNTIME_PLUGINS_ROOT = HERMES_HOME / "plugins"

# ── 提示词模块清单 ─────────────────────────────────────────────────
PROMPT_MODULES = (
    "prompt_builder",
    "system_prompt",
    "coding_context",
    "context_compressor",
    "background_review",
    "curator",
)

# ── 提示词锚点：被代码用于解析，不能翻译 ──────────────────────────
# 这些常量既用来生成文本，也用来 find/split/startswith 解析文本。
# 翻译后生成中文、解析找英文，会话历史会识别失败。
PROMPT_ANCHORS = frozenset({
    "prompt_builder.STEER_MARKER_OPEN",
    "prompt_builder._BACKEND_PROBE_CMD",
    "coding_context.WORKSPACE_BLOCK_HEADER",
    "context_compressor.SUMMARY_PREFIX",
    "context_compressor._NO_USER_TASK_SENTINEL",
    "context_compressor.COMPRESSION_CONTINUATION_USER_CONTENT",
    "context_compressor._LEGACY_COMPRESSION_CONTINUATION_USER_CONTENT",
    "context_compressor._SUMMARY_END_MARKER",
    "context_compressor._MERGED_PRIOR_CONTEXT_HEADER",
    "context_compressor._MERGED_SUMMARY_DELIMITER",
    "context_compressor._INFLIGHT_TASK_REPLAY_HEADER",
    "context_compressor._PRUNED_TOOL_PLACEHOLDER",
    "context_compressor._LEAN_USER_MESSAGES_HEADING",
    "context_compressor._LEAN_ANCHOR_HEADING",
    "context_compressor._CLARIFY_QUOTED_TEXT",
})

# 插件工具的判定：这些前缀或名称属于插件层
PLUGIN_TOOL_PREFIXES = ("openspec_", "ha_")
PLUGIN_TOOL_NAMES = frozenset({
    "plan_mode",
    "diff_review",
    "codex_delegate",
    "codex_review",
    "opencode_delegate",
    "pdf_to_office",
})

MIN_LEN = 40


# ── 基础工具 ──────────────────────────────────────────────────────
def has_cn(text: str) -> bool:
    """判断文本是否含中文字符。"""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def is_plugin_tool(name: str) -> bool:
    """判断工具名是否属于插件层。"""
    return name.startswith(PLUGIN_TOOL_PREFIXES) or name in PLUGIN_TOOL_NAMES


def load_json(path: Path) -> dict:
    """读 JSON，文件不存在时返回空字典。"""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    """写 JSON，自动建父目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def merged_tools() -> dict:
    """把核心工具与插件工具合并成运行用映射表。"""
    merged = dict(load_json(CORE_TOOLS))
    merged.update(load_json(PLUGIN_TOOLS))
    return merged


def prompt_count(prompts: dict) -> int:
    """统计提示词映射的段数。"""
    return sum(len(v) for v in prompts.values() if isinstance(v, dict))


# ── 工具 schema 提取 ──────────────────────────────────────────────
def extract_tool_schemas(source: str) -> dict:
    """从源码文本提取工具名、描述与参数描述，解析模块级常量引用。"""
    out: dict = {}
    try:
        tree = ast.parse(source)
    except Exception:
        return out

    consts: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception:
                        continue
                    if isinstance(value, str):
                        consts[target.id] = value

    def resolve(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id in consts:
            return consts[node.id]
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        fields: dict = {}
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant):
                fields[key.value] = value
        name = resolve(fields.get("name"))
        if not name:
            continue
        desc = resolve(fields.get("description"))
        if desc:
            out.setdefault(name, {})["description"] = desc
        params = fields.get("parameters")
        if isinstance(params, ast.Dict):
            for pk, pv in zip(params.keys, params.values):
                if not (
                    isinstance(pk, ast.Constant)
                    and pk.value == "properties"
                    and isinstance(pv, ast.Dict)
                ):
                    continue
                for prop, propv in zip(pv.keys, pv.values):
                    if not (isinstance(prop, ast.Constant) and isinstance(propv, ast.Dict)):
                        continue
                    for kk, vv in zip(propv.keys, propv.values):
                        if isinstance(kk, ast.Constant) and kk.value == "description":
                            resolved = resolve(vv)
                            if resolved:
                                out.setdefault(name, {}).setdefault("params", {})[
                                    prop.value
                                ] = resolved
    return out


# ── 提示词常量提取 ────────────────────────────────────────────────
def _ast_consts(source: str) -> dict[str, str]:
    """AST 方式：只取能用 literal_eval 求值的模块级常量。"""
    out: dict[str, str] = {}
    try:
        tree = ast.parse(source)
    except Exception:
        return out
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception:
                        continue
                    if isinstance(value, str) and len(value) > MIN_LEN:
                        out[target.id] = value
    return out


def _ast_all_names(source: str) -> set[str]:
    """本文件在模块级定义或赋值的全部名字。"""
    names: set[str] = set()
    try:
        tree = ast.parse(source)
    except Exception:
        return names
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _import_consts(source: str, module_name: str, workdir: Path) -> dict[str, str]:
    """导入方式：执行模块，取所有模块级长字符串常量。

    临时文件用完即删，避免累积。
    """
    workdir.mkdir(parents=True, exist_ok=True)
    tmp = workdir / f"{module_name}.py"
    tmp.write_text(source, encoding="utf-8")
    saved = sys.modules.get(module_name)
    try:
        spec = importlib.util.spec_from_file_location(module_name, tmp)
        if spec is None or spec.loader is None:
            return {}
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception:
        if saved is not None:
            sys.modules[module_name] = saved
        else:
            sys.modules.pop(module_name, None)
        return {}
    finally:
        # 无论导入成功与否都删掉临时文件
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
    out: dict[str, str] = {}
    for name, value in vars(module).items():
        if name.isupper() and isinstance(value, str) and len(value) > MIN_LEN:
            out[name] = value
    sys.modules.pop(module_name, None)
    return out


def extract_prompt_consts(
    source: str,
    *,
    module_name: str | None = None,
    workdir: Path | None = None,
) -> dict[str, str]:
    """提取提示词模块的长字符串常量。

    给了 module_name 与 workdir 时优先用导入方式（能取到拼接与函数调用的结果），
    否则退回 AST 方式。导入方式会取到从别处 import 的常量，因此用 AST 收集
    本文件定义的名字做白名单。
    """
    own_names = _ast_all_names(source)
    if module_name and workdir is not None:
        imported = _import_consts(source, module_name, workdir)
        if imported:
            return {k: v for k, v in imported.items() if k in own_names}
    return _ast_consts(source)