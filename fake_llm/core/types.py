from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatRequest:
    messages: list[ChatMessage] = field(default_factory=list)
    model: str = ""


@dataclass(frozen=True)
class TextAnswer:
    text: str


@dataclass(frozen=True)
class ToolAnswer:
    name: str
    input: dict[str, Any]


Answer = Union[TextAnswer, ToolAnswer]
