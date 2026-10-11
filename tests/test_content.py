from __future__ import annotations

import pytest

from fake_llm.core import (
    AnswerParseError,
    ImagePart,
    TextAnswer,
    TextPart,
    ToolAnswer,
    data_uri,
    estimate_parts,
    media_type_of,
    parse_operator_answer,
    tool_result_annotation,
    tool_use_annotation,
)


def test_data_uri() -> None:
    assert data_uri("image/png", "AAAA") == "data:image/png;base64,AAAA"
    assert data_uri("", "AAAA") == "data:application/octet-stream;base64,AAAA"


def test_media_type_of() -> None:
    assert media_type_of("data:image/jpeg;base64,AAAA") == "image/jpeg"
    assert media_type_of("data:;base64,AAAA") == ""
    assert media_type_of("https://example.com/a.png") == ""


def test_tool_annotations() -> None:
    assert tool_use_annotation("get_weather", {"city": "北京"}) == '[调用 get_weather] {"city": "北京"}'
    assert tool_result_annotation("晴") == '[工具返回] "晴"'
    assert tool_result_annotation([{"type": "text", "text": "晴"}, {"type": "text", "text": "25度"}]) == '[工具返回] "晴\\n25度"'


def test_estimate_parts() -> None:
    assert estimate_parts([]) == 0
    assert estimate_parts([TextPart("abcd")]) == 1
    assert estimate_parts([TextPart("abcd"), ImagePart(url="data:image/png;base64,AAAA", media_type="image/png")]) == 86


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
