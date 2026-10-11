from __future__ import annotations

from fastapi import FastAPI

from .core import Bridge
from .operator import register_operator
from .protocols import AnthropicAdapter, OpenAIAdapter, register_protocol
from .settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    bridge = Bridge()
    app = FastAPI(title="Fake LLM", version="0.1.0")

    for adapter in (OpenAIAdapter(), AnthropicAdapter()):
        register_protocol(app, adapter, bridge, settings)
    register_operator(app, bridge, settings)

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "queued": bridge.pending_count}

    @app.get("/v1/models")
    async def models() -> dict:
        return {
            "object": "list",
            "data": [
                {"id": "fake-gpt", "object": "model", "owned_by": "human"},
                {"id": "fake-claude", "object": "model", "owned_by": "human"},
            ],
        }

    return app


app = create_app()
