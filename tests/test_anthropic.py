from __future__ import annotations

import json

import pytest

from fake_llm.core import ImagePart, TextAnswer, TextPart, ToolAnswer
from fake_llm.protocols.anthropic import AnthropicAdapter
from fake_llm.settings import Settings

pytestmark = pytest.mark.anyio

adapter = AnthropicAdapter()


def test_parse_lifts_system() -> None:
    body = {
        "model": "claude-x",
        "system": "你是助手",
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "你好"}]},
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "get_weather", "input": {"city": "北京"}},
                    {"type": "tool_result", "content": "晴"},
                ],
            },
        ],
    }
    req = adapter.parse(body)
    assert req.model == "claude-x"
    assert [m.role for m in req.messages] == ["system", "user", "assistant"]
    assert req.messages[1].text == "你好"
    assert req.messages[2].text == '[调用 get_weather] {"city": "北京"}\n[工具返回] "晴"'


def test_parse_multimodal() -> None:
    body = {
        "model": "claude-x",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "图里有什么"},
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": "AAAA"},
                    },
                    {"type": "image", "source": {"type": "url", "url": "https://example.com/a.png"}},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": ""}},
                ],
            }
        ],
    }
    parts = adapter.parse(body).messages[0].parts
    assert parts == [
        TextPart("图里有什么"),
        ImagePart(url="data:image/jpeg;base64,AAAA", media_type="image/jpeg"),
        ImagePart(url="https://example.com/a.png", media_type=""),
    ]


def test_response_text() -> None:
    req = adapter.parse({"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    resp = adapter.response(req, TextAnswer(text="你好！"))
    assert resp["content"] == [{"type": "text", "text": "你好！"}]
    assert resp["stop_reason"] == "end_turn"
    assert resp["usage"]["output_tokens"] > 0


def test_response_tool() -> None:
    req = adapter.parse({"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    resp = adapter.response(req, ToolAnswer(name="get_weather", input={"city": "北京"}))
    assert resp["stop_reason"] == "tool_use"
    block = resp["content"][0]
    assert block["type"] == "tool_use"
    assert block["name"] == "get_weather"
    assert block["input"] == {"city": "北京"}


def _parse_events(events: list[str]) -> list[dict]:
    out = []
    for e in events:
        for line in e.strip().split("\n"):
            if line.startswith("data: "):
                out.append(json.loads(line[len("data: ") :]))
    return out


async def test_stream_text() -> None:
    req = adapter.parse({"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    settings = Settings(text_delay_min=0.0, text_delay_max=0.0)
    events = [e async for e in adapter.stream(req, TextAnswer(text="你好"), settings)]
    names = [e.split("\n", 1)[0].removeprefix("event: ") for e in events]
    assert names == [
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    data = _parse_events(events)
    text = "".join(
        d["delta"]["text"] for d in data if d.get("type") == "content_block_delta"
    )
    assert text == "你好"
    message_delta = next(d for d in data if d.get("type") == "message_delta")
    assert message_delta["delta"]["stop_reason"] == "end_turn"


async def test_stream_tool() -> None:
    req = adapter.parse({"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    settings = Settings()
    events = [
        e
        async for e in adapter.stream(
            req, ToolAnswer(name="get_weather", input={"city": "北京"}), settings
        )
    ]
    data = _parse_events(events)
    start = next(d for d in data if d.get("type") == "content_block_start")
    assert start["content_block"]["name"] == "get_weather"
    delta = next(d for d in data if d.get("type") == "content_block_delta")
    assert json.loads(delta["delta"]["partial_json"]) == {"city": "北京"}
    message_delta = next(d for d in data if d.get("type") == "message_delta")
    assert message_delta["delta"]["stop_reason"] == "tool_use"
