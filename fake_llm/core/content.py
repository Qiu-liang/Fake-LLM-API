from __future__ import annotations

import json
from typing import Any

from .types import (
    Answer,
    ChatRequest,
    ContentPart,
    ImagePart,
    TextAnswer,
    TextPart,
    ToolAnswer,
)

IMAGE_TOKENS = 85


def data_uri(media_type: str, data: str) -> str:
    return f"data:{media_type or 'application/octet-stream'};base64,{data}"


def media_type_of(url: str) -> str:
    if url.startswith("data:"):
        header = url[5:].split(",", 1)[0]
        return header.split(";")[0] if header else ""
    return ""


def tool_use_annotation(name: str, payload: Any) -> str:
    return f"[调用 {name}] {json.dumps(payload, ensure_ascii=False)}"


def tool_result_annotation(content: Any) -> str:
    if isinstance(content, list):
        texts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        joined = "\n".join(t for t in texts if t)
        content = joined or content
    return f"[工具返回] {json.dumps(content, ensure_ascii=False)}"


def tool_calls_annotation(names: str) -> str:
    return f"[助手请求调用工具: {names}]"


def estimate_tokens(text: str) -> int:
    return (len(text) + 3) // 4 if text else 0


def estimate_parts(parts: list[ContentPart]) -> int:
    total = 0
    for part in parts:
        if isinstance(part, TextPart):
            total += estimate_tokens(part.text)
        elif isinstance(part, ImagePart):
            total += IMAGE_TOKENS
    return total


def estimate_request(request: ChatRequest) -> int:
    return sum(estimate_parts(m.parts) for m in request.messages)


def part_to_json(part: ContentPart) -> dict[str, Any]:
    if isinstance(part, ImagePart):
        return {"type": "image", "url": part.url, "media_type": part.media_type}
    return {"type": "text", "text": part.text}


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
