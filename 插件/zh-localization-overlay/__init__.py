"""汉化覆盖层插件：在请求发出前把英文提示词与工具描述替换为中文。

设计原则
--------
本插件不改动 Hermes 仓库源码，全部汉化文本存放在插件目录的 JSON 映射表里。
程序升级时仓库源码正常更新，本插件不受影响；映射表未覆盖的新内容保持英文，
不会报错，也不会破坏功能。

替换机制
--------
1. 工具描述：按工具名与参数名精确索引，命中则替换。
2. 系统提示词：按英文原文做子串替换，命中则换成对应中文。

映射表由本汉化仓库的工具/、插件/、核心/ 下的映射文件生成，升级后可重新生成。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PLUGIN_DIR = Path(__file__).resolve().parent
TOOLS_MAP_FILE = PLUGIN_DIR / "tools-zh.json"
PROMPTS_MAP_FILE = PLUGIN_DIR / "prompts-zh.json"

# 懒加载缓存：映射表只在首次请求时读一次
_tools_map: dict[str, Any] | None = None
_prompt_pairs: list[tuple[str, str]] | None = None


def _load_tools_map() -> dict[str, Any]:
    global _tools_map
    if _tools_map is None:
        try:
            _tools_map = json.loads(TOOLS_MAP_FILE.read_text(encoding="utf-8"))
            logger.info("汉化覆盖层：已加载 %d 个工具的中文映射", len(_tools_map))
        except Exception as exc:
            logger.warning("汉化覆盖层：工具映射表加载失败（%s），工具描述保持英文", exc)
            _tools_map = {}
    return _tools_map


def _load_prompt_pairs() -> list[tuple[str, str]]:
    """把嵌套的 prompts-zh.json 摊平成 (英文, 中文) 列表，按英文长度降序。

    长串优先替换，避免短串先命中把长串拆碎。
    """
    global _prompt_pairs
    if _prompt_pairs is None:
        pairs: list[tuple[str, str]] = []
        try:
            raw = json.loads(PROMPTS_MAP_FILE.read_text(encoding="utf-8"))
            for _module, consts in raw.items():
                for _name, pair in consts.items():
                    en, zh = pair.get("en"), pair.get("zh")
                    if isinstance(en, str) and isinstance(zh, str) and en and zh:
                        pairs.append((en, zh))
            pairs.sort(key=lambda p: len(p[0]), reverse=True)
            logger.info("汉化覆盖层：已加载 %d 段提示词映射", len(pairs))
        except Exception as exc:
            logger.warning("汉化覆盖层：提示词映射表加载失败（%s），提示词保持英文", exc)
            pairs = []
        _prompt_pairs = pairs
    return _prompt_pairs


def _rewrite_tools(tools: list[Any]) -> tuple[list[Any], int]:
    """按工具名与参数名替换描述；返回 (新列表, 替换计数)。"""
    mapping = _load_tools_map()
    if not mapping:
        return tools, 0
    changed = 0
    result = []
    for tool in tools:
        if not isinstance(tool, dict):
            result.append(tool)
            continue
        name = tool.get("name")
        entry = mapping.get(name) if isinstance(name, str) else None
        if not entry:
            result.append(tool)
            continue
        new_tool = dict(tool)
        if isinstance(entry.get("description"), str):
            new_tool["description"] = entry["description"]
            changed += 1
        params = entry.get("params")
        if isinstance(params, dict) and params:
            schema = new_tool.get("parameters")
            if isinstance(schema, dict):
                props = schema.get("properties")
                if isinstance(props, dict):
                    new_props = {}
                    for pname, pschema in props.items():
                        if pname in params and isinstance(pschema, dict):
                            ps2 = dict(pschema)
                            ps2["description"] = params[pname]
                            new_props[pname] = ps2
                            changed += 1
                        else:
                            new_props[pname] = pschema
                    new_schema = dict(schema)
                    new_schema["properties"] = new_props
                    new_tool["parameters"] = new_schema
        result.append(new_tool)
    return result, changed


def _rewrite_text(text: str) -> tuple[str, int]:
    """对提示词正文做子串替换；返回 (新文本, 替换计数)。"""
    if not isinstance(text, str) or not text:
        return text, 0
    changed = 0
    for en, zh in _load_prompt_pairs():
        if en in text:
            text = text.replace(en, zh)
            changed += 1
    return text, changed


def llm_request_middleware(request: dict, original_request: dict, **context: Any) -> dict | None:
    """llm_request 中间件入口：改写工具描述与系统提示词。"""
    if not isinstance(request, dict):
        return None
    new_request = dict(request)
    total = 0

    tools = new_request.get("tools")
    if isinstance(tools, list) and tools:
        new_tools, n = _rewrite_tools(tools)
        if n:
            new_request["tools"] = new_tools
            total += n

    # 系统提示词字段名随协议不同：Responses 用 instructions，Chat 用 messages[0]
    instructions = new_request.get("instructions")
    if isinstance(instructions, str) and instructions:
        new_text, n = _rewrite_text(instructions)
        if n:
            new_request["instructions"] = new_text
            total += n

    messages = new_request.get("messages")
    if isinstance(messages, list) and messages:
        new_messages = []
        touched = False
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "system" and isinstance(msg.get("content"), str):
                new_text, n = _rewrite_text(msg["content"])
                if n:
                    m2 = dict(msg)
                    m2["content"] = new_text
                    new_messages.append(m2)
                    touched = True
                    total += n
                    continue
            new_messages.append(msg)
        if touched:
            new_request["messages"] = new_messages

    if not total:
        return None
    return {"request": new_request, "name": "zh-localization-overlay", "reason": f"替换 {total} 处英文为中文"}


def register(ctx: Any) -> None:
    """插件注册入口。"""
    ctx.register_middleware("llm_request", llm_request_middleware)
    logger.info("汉化覆盖层插件已注册 llm_request 中间件")