from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any, AsyncIterator

from ..core import Answer, ChatMessage, ChatRequest, TextAnswer, ToolAnswer, estimate_tokens, norm_content
from ..settings import Settings
from .base import new_id


class OpenAIAdapter:
    name = "openai"
    path = "/v1/chat/completions"

    def parse(self, body: dict[str, Any]) -> ChatRequest:
        messages = []
        for m in body.get("messages", []):
            content = norm_content(m.get("content"))
            tool_calls = m.get("tool_calls") or []
            if tool_calls:
                names = ", ".join(
                    tc.get("function", {}).get("name", "?") for tc in tool_calls
                )
                note = f"[助手请求调用工具: {names}]"
                content = f"{content}\n{note}" if content else note
            messages.append(ChatMessage(role=m.get("role", "assistant"), content=content))
        return ChatRequest(messages=messages, model=body.get("model", "fake-gpt"))

    def response(self, request: ChatRequest, answer: Answer) -> dict[str, Any]:
        if isinstance(answer, TextAnswer):
            message: dict[str, Any] = {"role": "assistant", "content": answer.text}
            finish = "stop"
            completion_tokens = estimate_tokens(answer.text)
        else:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [_tool_call(answer)],
            }
            finish = "tool_calls"
            completion_tokens = estimate_tokens(json.dumps(answer.input, ensure_ascii=False))
        prompt_tokens = estimate_tokens("".join(m.content for m in request.messages))
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


def _tool_call(answer: ToolAnswer) -> dict[str, Any]:
    return {
        "id": new_id("call_", 8),
        "type": "function",
        "function": {
            "name": answer.name,
            "arguments": json.dumps(answer.input, ensure_ascii=False),
        },
    }
