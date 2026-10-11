from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any, AsyncIterator

from ..core import (
    Answer,
    ChatMessage,
    ChatRequest,
    ContentPart,
    ImagePart,
    TextAnswer,
    TextPart,
    ToolAnswer,
    estimate_request,
    media_type_of,
    tool_calls_annotation,
)
from ..settings import Settings
from .base import new_id


class OpenAIAdapter:
    name = "openai"
    path = "/v1/chat/completions"

    def parse(self, body: dict[str, Any]) -> ChatRequest:
        messages = []
        for m in body.get("messages", []):
            parts = _content_parts(m.get("content"))
            tool_calls = m.get("tool_calls") or []
            if tool_calls:
                names = ", ".join(
                    tc.get("function", {}).get("name", "?") for tc in tool_calls
                )
                parts.append(TextPart(tool_calls_annotation(names)))
            messages.append(ChatMessage(role=m.get("role", "assistant"), parts=parts))
        return ChatRequest(messages=messages, model=body.get("model", "fake-gpt"))

    def response(self, request: ChatRequest, answer: Answer) -> dict[str, Any]:
        if isinstance(answer, TextAnswer):
            message: dict[str, Any] = {"role": "assistant", "content": answer.text}
            finish = "stop"
            completion_tokens = _completion_tokens(answer)
        else:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [_tool_call(answer)],
            }
            finish = "tool_calls"
            completion_tokens = _completion_tokens(answer)
        prompt_tokens = estimate_request(request)
        return {
            "id": new_id("chatcmpl-"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    async def stream(
        self, request: ChatRequest, answer: Answer, settings: Settings
    ) -> AsyncIterator[str]:
        cid = new_id("chatcmpl-")
        created = int(time.time())

        def chunk(delta: dict[str, Any], finish: str | None = None) -> str:
            return (
                "data: "
                + json.dumps(
                    {
                        "id": cid,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )

        yield chunk({"role": "assistant", "content": ""})
        if isinstance(answer, TextAnswer):
            for ch in answer.text:
                yield chunk({"content": ch})
                await asyncio.sleep(random.uniform(settings.text_delay_min, settings.text_delay_max))
            yield chunk({}, finish="stop")
        else:
            yield chunk(
                {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": new_id("call_", 8),
                            "type": "function",
                            "function": {"name": answer.name, "arguments": ""},
                        }
                    ]
                }
            )
            for ch in json.dumps(answer.input, ensure_ascii=False):
                yield chunk({"tool_calls": [{"index": 0, "function": {"arguments": ch}}]})
                await asyncio.sleep(settings.tool_delay)
            yield chunk({}, finish="tool_calls")
        yield "data: [DONE]\n\n"


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
        elif btype in ("image_url", "input_image"):
            url = block.get("image_url", "")
            if isinstance(url, dict):
                url = url.get("url", "")
            if url:
                parts.append(ImagePart(url=url, media_type=media_type_of(url)))
    return parts


def _completion_tokens(answer: Answer) -> int:
    if isinstance(answer, TextAnswer):
        return (len(answer.text) + 3) // 4
    return (len(json.dumps(answer.input, ensure_ascii=False)) + 3) // 4


def _tool_call(answer: ToolAnswer) -> dict[str, Any]:
    return {
        "id": new_id("call_", 8),
        "type": "function",
        "function": {
            "name": answer.name,
            "arguments": json.dumps(answer.input, ensure_ascii=False),
        },
    }
