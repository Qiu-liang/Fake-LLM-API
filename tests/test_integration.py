from __future__ import annotations

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient

from fake_llm.app import create_app
from fake_llm.settings import Settings

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client(settings: Settings):
    transport = ASGITransport(app=create_app(settings))
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _answer_when_ready(client: AsyncClient, answer: str, timeout: float = 2.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        nxt = (await client.get("/operator/next")).json()
        if nxt.get("request_id"):
            resp = await client.post(
                "/operator/answer",
                json={"request_id": nxt["request_id"], "answer": answer},
            )
            assert resp.json() == {"ok": True}
            return
        await asyncio.sleep(0.01)
    raise AssertionError("超时：请求未进入操作台队列")


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.json() == {"ok": True, "queued": 0}


async def test_openai_text_roundtrip(client: AsyncClient) -> None:
    task = asyncio.create_task(
        client.post(
            "/v1/chat/completions",
            json={
                "model": "fake-gpt",
                "messages": [{"role": "user", "content": "北京天气如何？"}],
            },
        )
    )
    await _answer_when_ready(client, "北京晴，25度")
    resp = await task
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "北京晴，25度"
    assert data["choices"][0]["finish_reason"] == "stop"


async def test_anthropic_tool_roundtrip(client: AsyncClient) -> None:
    task = asyncio.create_task(
        client.post(
            "/v1/messages",
            json={
                "model": "fake-claude",
                "max_tokens": 1024,
                "system": "你是助手",
                "messages": [{"role": "user", "content": "北京天气如何？"}],
            },
        )
    )
    await _answer_when_ready(client, '!tool get_weather {"city": "北京"}')
    resp = await task
    data = resp.json()
    assert data["stop_reason"] == "tool_use"
    block = data["content"][0]
    assert block["type"] == "tool_use"
    assert block["name"] == "get_weather"
    assert block["input"] == {"city": "北京"}


async def test_same_console_serves_both_protocols(client: AsyncClient) -> None:
    task_oai = asyncio.create_task(
        client.post(
            "/v1/chat/completions",
            json={"model": "gpt", "messages": [{"role": "user", "content": "一"}]},
        )
    )
    await asyncio.sleep(0.05)
    task_claude = asyncio.create_task(
        client.post(
            "/v1/messages",
            json={"model": "claude", "max_tokens": 16, "messages": [{"role": "user", "content": "二"}]},
        )
    )
    await asyncio.sleep(0.05)
    nxt = (await client.get("/operator/next")).json()
    assert nxt["queued"] == 2
    assert nxt["messages"][0]["content"] == "一"
    await client.post("/operator/answer", json={"request_id": nxt["request_id"], "answer": "A"})
    nxt = (await client.get("/operator/next")).json()
    assert nxt["messages"][0]["content"] == "二"
    await client.post("/operator/answer", json={"request_id": nxt["request_id"], "answer": "B"})
    assert (await task_oai).json()["choices"][0]["message"]["content"] == "A"
    assert (await task_claude).json()["content"][0]["text"] == "B"


async def test_operator_next_stable_until_answered(client: AsyncClient) -> None:
    task = asyncio.create_task(
        client.post(
            "/v1/chat/completions",
            json={"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        )
    )
    await asyncio.sleep(0.05)
    first = (await client.get("/operator/next")).json()
    second = (await client.get("/operator/next")).json()
    assert first["request_id"] == second["request_id"]
    await client.post("/operator/answer", json={"request_id": first["request_id"], "answer": "ok"})
    await task
    assert (await client.get("/operator/next")).json() == {"queued": 0}


async def test_operator_skip_requeues(client: AsyncClient) -> None:
    task1 = asyncio.create_task(
        client.post("/v1/chat/completions", json={"model": "m", "messages": [{"role": "user", "content": "一"}]})
    )
    await asyncio.sleep(0.05)
    task2 = asyncio.create_task(
        client.post("/v1/messages", json={"model": "m", "max_tokens": 8, "messages": [{"role": "user", "content": "二"}]})
    )
    await asyncio.sleep(0.05)
    nxt = (await client.get("/operator/next")).json()
    assert (await client.post("/operator/skip")).json() == {"ok": True}
    nxt2 = (await client.get("/operator/next")).json()
    assert nxt2["request_id"] != nxt["request_id"]
    await client.post("/operator/answer", json={"request_id": nxt2["request_id"], "answer": "B"})
    nxt3 = (await client.get("/operator/next")).json()
    assert nxt3["request_id"] == nxt["request_id"]
    await client.post("/operator/answer", json={"request_id": nxt["request_id"], "answer": "A"})
    assert (await task1).json()["choices"][0]["message"]["content"] == "A"
    assert (await task2).json()["content"][0]["text"] == "B"


async def test_operator_bad_answer(client: AsyncClient) -> None:
    task = asyncio.create_task(
        client.post("/v1/chat/completions", json={"model": "m", "messages": [{"role": "user", "content": "hi"}]})
    )
    await asyncio.sleep(0.05)
    nxt = (await client.get("/operator/next")).json()
    bad = await client.post(
        "/operator/answer", json={"request_id": nxt["request_id"], "answer": "!tool broken {"}
    )
    assert bad.status_code == 400
    missing = await client.post("/operator/answer", json={"request_id": "nope", "answer": "x"})
    assert missing.status_code == 404
    await client.post("/operator/answer", json={"request_id": nxt["request_id"], "answer": "ok"})
    await task


async def test_openai_stream_roundtrip(client: AsyncClient) -> None:
    task = asyncio.create_task(
        client.post(
            "/v1/chat/completions",
            json={
                "model": "m",
                "stream": True,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    )
    await _answer_when_ready(client, "你好")
    resp = await task
    lines = [line for line in resp.iter_lines() if line]
    assert lines[-1] == "data: [DONE]"
    chunks = [json.loads(line[len("data: ") :]) for line in lines if line.startswith("data: ") and line != "data: [DONE]"]
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    assert text == "你好"


async def test_anthropic_stream_roundtrip(client: AsyncClient) -> None:
    task = asyncio.create_task(
        client.post(
            "/v1/messages",
            json={
                "model": "m",
                "stream": True,
                "max_tokens": 8,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    )
    await _answer_when_ready(client, "你好")
    resp = await task
    text = "".join(
        json.loads(line[len("data: ") :])["delta"]["text"]
        for line in resp.iter_lines()
        if line.startswith("data: ") and '"text_delta"' in line
    )
    assert text == "你好"


async def test_models(client: AsyncClient) -> None:
    resp = await client.get("/v1/models")
    ids = {m["id"] for m in resp.json()["data"]}
    assert ids == {"fake-gpt", "fake-claude"}


async def test_invalid_json_body(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/chat/completions", content=b"not json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 400
