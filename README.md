# Fake LLM — 真人冒充LLM服务

以 **OpenAI / Anthropic 双协议**对外提供接口，请求统一排队，由人类操作员在同一个控制台作答，服务器再把同一段回答包装回对应协议的格式。

```
Agent(OpenAI SDK)  ──→ /v1/chat/completions ─┐
                                              ├─→ 统一队列 ─→ 人类操作台 ─→ 统一答案
Agent(Anthropic SDK) ─→ /v1/messages ────────┘        (/operator)      ↓
                                                                格式适配回包
```

## 项目结构

```
fake_llm/
├── app.py                  # FastAPI 应用组装（create_app）
├── __main__.py             # 启动入口（fake-llm / python -m fake_llm）
├── settings.py             # 配置（环境变量）
├── core/                   # 协议无关的核心
│   ├── types.py            # ChatRequest / ChatMessage(parts) / TextAnswer / ToolAnswer 统一内部格式
│   ├── content.py          # 文本/图片 part 解析辅助、token 估算、操作员输入解析
│   └── bridge.py           # 排队桥梁：Agent 阻塞等待，操作台拉取/作答/跳过
├── protocols/              # 协议适配层（抹平两家差异）
│   ├── base.py             # ProtocolAdapter 接口 + 路由注册
│   ├── openai.py           # 解析 / 回包 / SSE 流式
│   └── anthropic.py        # 解析 / 回包 / SSE 事件流
└── operator/
    ├── routes.py           # /operator 页面与操作接口
    └── static/operator.html
tests/                      # 单测（协议层）+ 集成测试（全链路）
examples/                   # 两种 Agent 的接入示例
```

新增协议（如 Gemini）只需实现一个 `ProtocolAdapter`（`parse` / `response` / `stream`），在 `app.py` 注册即可，核心队列与操作台零改动。

## 快速开始

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
fake-llm            # 或 python -m fake_llm
```

- 操作台：http://localhost:8000/operator
- 健康检查：`GET /health`；模型列表：`GET /v1/models`

操作员输入规则：

- 普通文字 → 普通回答
- `!tool get_weather {"city": "北京"}` → 工具调用
- Ctrl+Enter 发送；「跳过该请求」把当前任务放回队尾

## 多模态（图片输入）

消息内容在内部统一为 parts：`{"type": "text"}` / `{"type": "image"}`，两家协议的图片块都会被解析，操作台直接内联显示图片。

- **OpenAI**：`{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}`（也支持 http(s) URL 与 Responses API 的 `input_image`）
- **Anthropic**：`{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}}` 或 `{"type": "url", "url": "..."}`

```python
client.chat.completions.create(
    model="fake-gpt",
    messages=[{"role": "user", "content": [
        {"type": "text", "text": "图里是什么？"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
    ]}])
```

操作员回答暂只支持纯文本 / `!tool`（两种协议的 assistant 回复本身也不返回图片）。图片按每张约 85 token 计入 usage。

## Agent 接入

OpenAI 阵营：

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="fake")
client.chat.completions.create(model="fake-gpt",
    messages=[{"role": "user", "content": "北京天气如何？"}])
```

Anthropic 阵营：

```python
from anthropic import Anthropic
client = Anthropic(base_url="http://localhost:8000", api_key="fake")
client.messages.create(model="fake-claude", max_tokens=1024,
    messages=[{"role": "user", "content": "你好"}])
```

## 配置（环境变量）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `FAKE_LLM_HOST` | `0.0.0.0` | 监听地址 |
| `FAKE_LLM_PORT` | `8000` | 监听端口 |
| `FAKE_LLM_TEXT_DELAY_MIN` / `_MAX` | `0.01` / `0.04` | 流式逐字延迟（秒） |
| `FAKE_LLM_TOOL_DELAY` | `0.002` | 工具参数逐字延迟（秒） |
| `FAKE_LLM_OPERATOR_POLL_MS` | `1500` | 操作台轮询间隔（毫秒） |

## 开发

```bash
pip install -e ".[dev]"
pytest
```

## 伪装提示

像模型一样分点作答、不说口头语、不用 emoji 泛滥——操作台越像 LLM，Agent 行为越真实。
