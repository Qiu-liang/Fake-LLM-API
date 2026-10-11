from __future__ import annotations

import json

import pytest

from fake_llm.core import TextAnswer, ToolAnswer
from fake_llm.protocols.openai import OpenAIAdapter
from fake_llm.settings import Settings

pytestmark = pytest.mark.anyio

adapter = OpenAIAdapter()


def test_parse() -> None:
    body = {
        "model": "gpt-x",
        "messages": [
            {"role": "system", "content": "你是助手"},
            {"role": "user", "content": [{"type": "text", "text": "天气如何"}]},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "c1", "type": "function", "function": {"name": "get_weather", "arguments": "{}"}}
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "晴"},
        ],
    }
    req = adapter.parse(body)
    assert req.model == "gpt-x"
    assert [m.role for m in req.messages] == ["system", "user", "assistant", "tool"]
    assert req.messages[1].content == "天气如何"
    assert req.messages[2].content == "[助手请求调用工具: get_weather]"
    assert req.messages[3].content == "晴"


def test_response_text() -> None:
    req = adapter.parse({"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    resp = adapter.response(req, TextAnswer(text="你好！"))
    choice = resp["choices"][0]
    assert choice["message"]["content"] == "你好！"
    assert choice["finish_reason"] == "stop"
    assert resp["usage"]["total_tokens"] > 0


def test_response_tool() -> None:
    req = adapter.parse({"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    resp = adapter.response(req, ToolAnswer(name="get_weather", input={"city": "北京"}))
    choice = resp["choices"][0]
    assert choice["message"]["content"] is None
    assert choice["finish_reason"] == "tool_calls"
    tool_call = choice["message"]["tool_calls"][0]
    assert tool_call["function"]["name"] == "get_weather"
    assert json.loads(tool_call["function"]["arguments"]) == {"city": "北京"}


async def test_stream_text() -> None:
    req = adapter.parse({"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    settings = Settings(text_delay_min=0.0, text_delay_max=0.0)
    events = [e async for e in adapter.stream(req, TextAnswer(text="你好"), settings)]
    data = [json.loads(e[len("data: ") :].strip()) for e in events[:-1]]
    assert events[-1] == "data: [DONE]\n\n"
    text = "".join(d["choices"][0]["delta"].get("content", "") for d in data)
    assert text == "你好"
    assert data[0]["choices"][0]["delta"]["role"] == "assistant"
    assert data[-1]["choices"][0]["finish_reason"] == "stop"


async def test_stream_tool() -> None:
    req = adapter.parse({"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    settings = Settings(tool_delay=0.0)
    events = [
        e
        async for e in adapter.stream(
            req, ToolAnswer(name="get_weather", input={"city": "北京"}), settings
        )
    ]
    data = [json.loads(e[len("data: ") :].strip()) for e in events[:-1]]
    args = "".join(
        tc.get("function", {}).get("arguments", "")
        for d in data
        for tc in d["choices"][0]["delta"].get("tool_calls", [])
    )
    assert json.loads(args) == {"city": "北京"}
    first_tc = next(d for d in data if d["choices"][0]["delta"].get("tool_calls"))
    assert first_tc["choices"][0]["delta"]["tool_calls"][0]["function"]["name"] == "get_weather"
    assert data[-1]["choices"][0]["finish_reason"] == "tool_calls"
