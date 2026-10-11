from __future__ import annotations

import asyncio
import json
import random
from typing import Any, AsyncIterator

from ..core import Answer, ChatMessage, ChatRequest, TextAnswer, estimate_tokens, norm_content
from ..settings import Settings
from .base import new_id


class AnthropicAdapter:
    name = "anthropic"
    path = "/v1/messages"

    def parse(self, body: dict[str, Any]) -> ChatRequest:
        messages = []
        system = body.get("system")
        if system:
            messages.append(ChatMessage(role="system", content=norm_content(system)))
        for m in body.get("messages", []):
            messages.append(
                ChatMessage(role=m.get("role", "user"), content=norm_content(m.get("content")))
            )
        return ChatRequest(messages=messages, model=body.get("model", "fake-claude"))

    def response(self, request: ChatRequest, answer: Answer) -> dict[str, Any]:
        if isinstance(answer, TextAnswer):
            content: list[dict[str, Any]] = [{"type": "text", "text": answer.text}]
            stop = "end_turn"
            output_tokens = estimate_tokens(answer.text)
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
            output_tokens = estimate_tokens(json.dumps(answer.input, ensure_ascii=False))
        input_tokens = estimate_tokens("".join(m.content for m in request.messages))
        return {
            "id": new_id("msg_"),
            "type": "message",
            "role": "assistant",
            "model": request.model,
            "content": content,
            "stop_reason": stop,
            "stop_sequence": None,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        }

    async def stream(
        self, request: ChatRequest, answer: Answer, settings: Settings
    ) -> AsyncIterator[str]:
        mid = new_id("msg_")
        input_tokens = estimate_tokens("".join(m.content for m in request.messages))
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
            output_tokens = estimate_tokens(answer.text)
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
            output_tokens = estimate_tokens(json.dumps(answer.input, ensure_ascii=False))
        yield _sse(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": stop, "stop_sequence": None},
                "usage": {"output_tokens": output_tokens},
            },
        )
        yield _sse("message_stop", {"type": "message_stop"})


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
