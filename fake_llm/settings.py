from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8000
    text_delay_min: float = 0.01
    text_delay_max: float = 0.04
    tool_delay: float = 0.002
    operator_poll_ms: int = 1500

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            host=os.environ.get("FAKE_LLM_HOST", "0.0.0.0"),
            port=int(os.environ.get("FAKE_LLM_PORT", "8000")),
            text_delay_min=float(os.environ.get("FAKE_LLM_TEXT_DELAY_MIN", "0.01")),
            text_delay_max=float(os.environ.get("FAKE_LLM_TEXT_DELAY_MAX", "0.04")),
            tool_delay=float(os.environ.get("FAKE_LLM_TOOL_DELAY", "0.002")),
            operator_poll_ms=int(os.environ.get("FAKE_LLM_OPERATOR_POLL_MS", "1500")),
        )
