from __future__ import annotations

import pytest

from fake_llm.core import (
    AnswerParseError,
    TextAnswer,
    ToolAnswer,
    estimate_tokens,
    norm_content,
    parse_operator_answer,
)


def test_norm_content_plain_string() -> None:
    assert norm_content("你好") == "你好"


def test_norm_content_blocks() -> None:
    blocks = [
        {"type": "text", "text": "第一段"},
        {"type": "tool_use", "name": "get_weather", "input": {"city": "北京"}},
        {"type": "tool_result", "content": "晴"},
        {"type": "image", "source": {}},
    ]
    assert norm_content(blocks) == (
        '第一段\n[调用 get_weather] {"city": "北京"}\n[工具返回] "晴"\n[图片]'
    )


def test_norm_content_empty() -> None:
    assert norm_content(None) == ""
    assert norm_content([]) == ""


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 2


def test_parse_operator_text() -> None:
    assert parse_operator_answer("  北京晴，25度 ") == TextAnswer(text="北京晴，25度")


def test_parse_operator_tool() -> None:
    answer = parse_operator_answer('!tool get_weather {"city": "北京"}')
    assert answer == ToolAnswer(name="get_weather", input={"city": "北京"})


def test_parse_operator_tool_invalid() -> None:
    with pytest.raises(AnswerParseError):
        parse_operator_answer("!tool get_weather {bad json}")
    with pytest.raises(AnswerParseError):
        parse_operator_answer("!tool get_weather")
    with pytest.raises(AnswerParseError):
        parse_operator_answer("!tool get_weather [1,2]")
    with pytest.raises(AnswerParseError):
        parse_operator_answer("   ")
