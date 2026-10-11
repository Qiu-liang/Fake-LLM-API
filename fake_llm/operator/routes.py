from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ..core import AnswerParseError, Bridge, parse_operator_answer
from ..settings import Settings

_STATIC_DIR = Path(__file__).parent / "static"


def register_operator(app: FastAPI, bridge: Bridge, settings: Settings) -> None:
    html = (_STATIC_DIR / "operator.html").read_text(encoding="utf-8").replace(
        "__POLL_MS__", str(settings.operator_poll_ms)
    )

    @app.get("/operator", response_class=HTMLResponse)
    async def operator_page() -> str:
        return html

    @app.get("/operator/next")
    async def operator_next() -> dict:
        payload = bridge.next_for_operator() or {}
        return {**payload, "queued": bridge.pending_count}

    @app.post("/operator/answer", response_model=None)
    async def operator_answer(req: Request) -> JSONResponse:
        body = await req.json()
        request_id = body.get("request_id", "")
        try:
            answer = parse_operator_answer(body.get("answer") or "")
        except AnswerParseError as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        if not bridge.submit(request_id, answer):
            return JSONResponse(
                {"ok": False, "error": "请求不存在或已回答"}, status_code=404
            )
        return JSONResponse({"ok": True})

    @app.post("/operator/skip")
    async def operator_skip() -> dict:
        return {"ok": bridge.requeue_current()}
