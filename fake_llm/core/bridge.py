from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

from .types import Answer, ChatRequest


@dataclass
class PendingRequest:
    request: ChatRequest
    event: asyncio.Event
    answer: Answer | None = None


class Bridge:
    """协议无关的人类排队桥梁：Agent 请求在此阻塞，直到操作员作答。"""

    def __init__(self) -> None:
        self._pending: dict[str, PendingRequest] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._current: str | None = None

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    async def ask(self, request: ChatRequest) -> Answer:
        rid = "req_" + uuid.uuid4().hex[:8]
        pending = PendingRequest(request=request, event=asyncio.Event())
        self._pending[rid] = pending
        await self._queue.put(rid)
        await pending.event.wait()
        del self._pending[rid]
        assert pending.answer is not None
        return pending.answer

    def next_for_operator(self) -> dict[str, Any] | None:
        """返回当前待作答请求（同一 rid 在被作答前可被反复拉取，页面刷新不丢任务）。"""
        if self._current is not None and self._current in self._pending:
            return self._payload(self._current)
        self._current = None
        while True:
            try:
                rid = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return None
            if rid in self._pending:
                self._current = rid
                return self._payload(rid)

    def submit(self, request_id: str, answer: Answer) -> bool:
        pending = self._pending.get(request_id)
        if pending is None:
            return False
        pending.answer = answer
        pending.event.set()
        if self._current == request_id:
            self._current = None
        return True

    def requeue_current(self) -> bool:
        """把当前展示中的请求放回队尾（操作员跳过）。"""
        if self._current is None or self._current not in self._pending:
            return False
        self._queue.put_nowait(self._current)
        self._current = None
        return True

    def _payload(self, rid: str) -> dict[str, Any]:
        pending = self._pending[rid]
        return {
            "request_id": rid,
            "model": pending.request.model,
            "messages": [{"role": m.role, "content": m.content} for m in pending.request.messages],
        }
