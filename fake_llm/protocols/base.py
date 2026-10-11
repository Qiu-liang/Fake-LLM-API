from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator, Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..core import Answer, Bridge, ChatRequest
from ..settings import Settings


class ProtocolAdapter(Protocol):
    name: str
    path: str

    def parse(self, body: dict[str, Any]) -> ChatRequest: ...

    def response(self, request: ChatRequest, answer: Answer) -> dict[str, Any]: ...

    def stream(
        self, request: ChatRequest, answer: Answer, settings: Settings
    ) -> AsyncIterator[str]: ...


def new_id(prefix: str, length: int = 12) -> str:
    return f"{prefix}{uuid.uuid4().hex[:length]}"


def register_protocol(
    app: FastAPI, adapter: ProtocolAdapter, bridge: Bridge, settings: Settings
) -> None:
    async def endpoint(req: Request) -> JSONResponse | StreamingResponse:
        try:
            body = await req.json()
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": {"message": "请求体不是合法 JSON", "type": "invalid_request_error"}},
                status_code=400,
            )
        request = adapter.parse(body)
        answer = await bridge.ask(request)
        if body.get("stream"):
            return StreamingResponse(
                adapter.stream(request, answer, settings), media_type="text/event-stream"
            )
        return JSONResponse(adapter.response(request, answer))

    app.post(adapter.path, response_model=None)(endpoint)
