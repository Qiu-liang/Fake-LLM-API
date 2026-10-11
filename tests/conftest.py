from __future__ import annotations

import pytest

from fake_llm.settings import Settings


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings() -> Settings:
    return Settings(text_delay_min=0.0, text_delay_max=0.0, tool_delay=0.0, operator_poll_ms=50)
