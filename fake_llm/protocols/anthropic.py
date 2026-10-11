from __future__ import annotations

import asyncio
import json
import random
from typing import Any, AsyncIterator

from ..core import (
    Answer,
    ChatMessage,
    ChatRequest,
    ContentPart,
    ImagePart,
    TextAnswer,
    TextPart,
    data_uri,
    estimate_request,
    media_type_of,
    tool_result_annotation,
    tool_use_annotation,
)
from ..settings import Settings
from .base import new_id


class AnthropicAdapter:
    name = "anthropic"
    path = "/v1/messages"

    def parse(self, body: dict[str, Any]) -> ChatRequest:
        messages = []
        system = body.get("system")
        if system:
            messages.append(ChatMessage(role="system", parts=_content_parts(system)))
        for m in body.get("messages", []):
            messages.append(
                ChatMessage(
                    role=m.get("role", "user"), parts=_content_parts(m.get("content"))
                )
            )
        return ChatRequest(messages=messages, model=body.get("model", "fake-claude"))

    def response(self, request: ChatRequest, answer: Answer) -> dict[str, Any]:
        if isinstance(answer, TextAnswer):
            content: list[dict[str, Any]] = [{"type": "text", "text": answer.text}]
            stop = "end_turn"
        else:
            content = [
                {
                    "type": "tool_use",
                    "id": new_id("toolu_"),
                    "name": answer.name,
                    "input": answer.input,
                }
            ]
            stop = "tool_use"
        input_tokens = estimate_request(request)
        return {
            "id": new_id("msg_"),
            "type": "message",
            "role": "assistant",
            "model": request.model,
            "content": content,
            "stop_reason": stop,
            "stop_sequence": None,
            "usage": {"input_tokens": input_tokens, "output_tokens": _completion_tokens(answer)},
        }

    async def stream(
        self, request: ChatRequest, answer: Answer, settings: Settings
    ) -> AsyncIterator[str]:
        mid = new_id("msg_")
        input_tokens = estimate_request(request)
        yield _sse(
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": mid,
                    "type": "message",
                    "role": "assistant",
                    "model": request.model,
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": input_tokens, "output_tokens": 1},
                },
            },
        )
        if isinstance(answer, TextAnswer):
            yield _sse(
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                },
            )
            for ch in answer.text:
                yield _sse(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {"type": "text_delta", "text": ch},
                    },
                )
                await asyncio.sleep(random.uniform(settings.text_delay_min, settings.text_delay_max))
            yield _sse("content_block_stop", {"type": "content_block_stop", "index": 0})
            stop = "end_turn"
        else:
            yield _sse(
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {
                        "type": "tool_use",
                        "id": new_id("toolu_"),
                        "name": answer.name,
                        "input": {},
                    },
                },
            )
            yield _sse(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": json.dumps(answer.input, ensure_ascii=False),
                    },
                },
            )
            yield _sse("content_block_stop", {"type": "content_block_stop", "index": 0})
            stop = "tool_use"
        yield _sse(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": stop, "stop_sequence": None},
                "usage": {"output_tokens": _completion_tokens(answer)},
            },
        )
        yield _sse("message_stop", {"type": "message_stop"})


def _content_parts(content: Any) -> list[ContentPart]:
    if isinstance(content, str):
        return [TextPart(content)]
    parts: list[ContentPart] = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(TextPart(block))
            continue
        btype = block.get("type")
        if btype == "text":
            parts.append(TextPart(block.get("text", "")))
        elif btype == "image":
            image = _image_part(block.get("source") or {})
            if image:
                parts.append(image)
        elif btype == "tool_use":
            parts.append(
                TextPart(tool_use_annotation(block.get("name", ""), block.get("input", {})))
            )
        elif btype == "tool_result":
            parts.append(TextPart(tool_result_annotation(block.get("content", ""))))
    return parts


def _image_part(source: dict[str, Any]) -> ImagePart | None:
    stype = source.get("type")
    if stype == "base64":
        media_type = source.get("media_type", "image/png")
        data = source.get("data", "")
        if data:
            return ImagePart(url=data_uri(media_type, data), media_type=media_type)
        return None
    if stype == "url":
        url = source.get("url", "")
        if url:
            return ImagePart(url=url, media_type=media_type_of(url))
    return None


def _completion_tokens(answer: Answer) -> int:
    if isinstance(answer, TextAnswer):
        return (len(answer.text) + 3) // 4
    return (len(json.dumps(answer.input, ensure_ascii=False)) + 3) // 4


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
