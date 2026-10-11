from __future__ import annotations

import json
from typing import Any

from .types import Answer, TextAnswer, ToolAnswer


def norm_content(content: Any) -> str:
    """OpenAI 的 content 与 Anthropic 的 content block 数组统一转纯文本。"""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif block.get("type") == "tool_result":
            parts.append(f"[工具返回] {json.dumps(block.get('content', ''), ensure_ascii=False)}")
        elif block.get("type") == "tool_use":
            parts.append(
                f"[调用 {block.get('name')}] {json.dumps(block.get('input', {}), ensure_ascii=False)}"
            )
        elif block.get("type") == "image":
            parts.append("[图片]")
    return "\n".join(p for p in parts if p)


def estimate_tokens(text: str) -> int:
    return (len(text) + 3) // 4 if text else 0


class AnswerParseError(ValueError):
    """操作员输入无法解析为回答。"""


def parse_operator_answer(raw: str) -> Answer:
    text = raw.strip()
    if not text:
        raise AnswerParseError("回答不能为空")
    if text.startswith("!tool"):
        parts = text.split(None, 2)
        if len(parts) < 3:
            raise AnswerParseError('工具调用语法：!tool 名称 {"参数": "值"}')
        _, name, argstr = parts
        try:
            payload = json.loads(argstr)
        except json.JSONDecodeError as e:
            raise AnswerParseError(f"工具参数不是合法 JSON：{e}") from e
        if not isinstance(payload, dict):
            raise AnswerParseError("工具参数必须是 JSON 对象")
        return ToolAnswer(name=name, input=payload)
    return TextAnswer(text=text)
