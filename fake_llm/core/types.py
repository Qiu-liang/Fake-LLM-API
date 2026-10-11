from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union


@dataclass(frozen=True)
class TextPart:
    text: str


@dataclass(frozen=True)
class ImagePart:
    url: str
    media_type: str = ""


ContentPart = Union[TextPart, ImagePart]


@dataclass(frozen=True)
class ChatMessage:
    role: str
    parts: list[ContentPart] = field(default_factory=list)

    @property
    def text(self) -> str:
        chunks = []
        for part in self.parts:
            if isinstance(part, TextPart) and part.text:
                chunks.append(part.text)
            elif isinstance(part, ImagePart):
                chunks.append("[图片]")
        return "\n".join(chunks)


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
