# Fake LLM

**用真人回答代替模型输出的本地 API 服务。** Fake LLM 接收兼容 OpenAI 或 Anthropic 的请求，将对话放进一个共享队列；操作员在网页控制台阅读请求并作答，服务再把答案包装成对应协议的响应。

它适合调试 Agent、观察 Agent 如何组织请求，以及在不调用真实模型的情况下手动控制模型输出。

## 功能

- 提供 OpenAI Chat Completions 和 Anthropic Messages 两种接口。
- 提供网页操作台查看、回答或跳过排队请求。
- 支持普通文本、工具调用格式和流式响应。
- 支持 OpenAI 与 Anthropic 请求中的图片输入，并在操作台显示图片。
- 无需模型 API 密钥；兼容 SDK 初始化时可填写任意占位值。

## 截图
<img width="2560" height="1322" alt="图片" src="https://github.com/user-attachments/assets/cde4b3d2-7607-453c-888c-e1afa97cff43" />


## 安全说明

操作台和推理接口目前都没有身份验证。服务默认监听 `0.0.0.0`，这会让同一网络中的其他设备也可能访问它。请只在可信的本机或网络中运行，不要直接暴露到公网；在本机使用时，建议将 `FAKE_LLM_HOST` 设为 `127.0.0.1`。

## 环境要求

- Python 3.10 或更高版本
- pip

## 安装与启动

```bash
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
fake-llm
```

将 `OWNER/REPOSITORY` 替换成你的 GitHub 用户名和仓库名。

服务默认运行在 `http://localhost:8000`。打开 [http://localhost:8000/operator](http://localhost:8000/operator) 使用操作台。

也可以使用仓库中的启动脚本 `./start.sh`。它会在需要时创建 `.venv` 并安装项目。

## 使用

安装对应的 SDK：

```bash
python -m pip install openai anthropic
```

### OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="fake",  # 服务不校验此值；SDK 要求提供非空值
)

response = client.chat.completions.create(
    model="fake-gpt",
    messages=[{"role": "user", "content": "你好！请介绍一下自己。"}],
)
print(response.choices[0].message.content)
```

### Anthropic SDK

```python
from anthropic import Anthropic

client = Anthropic(
    base_url="http://localhost:8000",
    api_key="fake",  # 服务不校验此值；SDK 要求提供非空值
)

response = client.messages.create(
    model="fake-claude",
    max_tokens=1024,
    messages=[{"role": "user", "content": "你好！"}],
)
print(response.content)
```

发起请求后，打开操作台输入回答并提交，调用方就会收到该回答。请求会一直等待，直到操作员作答。

## 工具调用

在操作台输入以下格式可返回一次工具调用：

```text
!tool get_weather {"city": "北京"}
```

调用方会收到对应协议的工具调用响应。Fake LLM 只负责返回工具调用，不会执行工具；Agent 收到响应后如何处理由调用方决定。

## 图片输入

OpenAI 风格的图片块和 Anthropic 风格的图片块都会显示在操作台。OpenAI SDK 示例：

```python
response = client.chat.completions.create(
    model="fake-gpt",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请描述这张图片。"},
                {
                    "type": "image_url",
                    "image_url": {"url": "https://example.com/image.png"},
                },
            ],
        }
    ],
)
```

本地图片也可以编码成 `data:image/...;base64,...` URL 传入。操作员的回复目前是纯文本或工具调用，不能返回图片。

## 接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `POST` | `/v1/chat/completions` | OpenAI Chat Completions 请求 |
| `POST` | `/v1/messages` | Anthropic Messages 请求 |
| `GET` | `/v1/models` | 列出示例模型 ID |
| `GET` | `/health` | 服务状态和等待中的请求数量 |
| `GET` | `/operator` | 网页操作台 |

`stream: true` 会返回 SSE 流式响应。流式内容由服务逐段发送，用于兼容客户端的流式处理；它不代表模型推理过程。

## 配置

通过环境变量配置服务。默认值见下表：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `FAKE_LLM_HOST` | `0.0.0.0` | 监听地址；本机使用建议设为 `127.0.0.1` |
| `FAKE_LLM_PORT` | `8000` | 监听端口 |
| `FAKE_LLM_TEXT_DELAY_MIN` | `0.01` | 流式文本最小字符间隔，单位秒 |
| `FAKE_LLM_TEXT_DELAY_MAX` | `0.04` | 流式文本最大字符间隔，单位秒 |
| `FAKE_LLM_TOOL_DELAY` | `0.002` | 流式工具参数字符间隔，单位秒 |
| `FAKE_LLM_OPERATOR_POLL_MS` | `1500` | 操作台轮询间隔，单位毫秒 |

例如，在 macOS 或 Linux 的 shell 中仅对当前进程设置本机监听：

```bash
FAKE_LLM_HOST=127.0.0.1 fake-llm
```

## 开发

```bash
python -m pip install -e ".[dev]"
pytest
```

## 当前范围

- 请求在进程内存中排队；服务重启后不会恢复，多个服务进程之间也不共享队列。
- 当前只实现上述两个对话端点，不是完整的 OpenAI 或 Anthropic API 替代品。
- Token 用量是粗略估算值，不适用于计费或模型性能评估。
- 请求会等待人工操作员回答；没有自动生成答案的模型。

## 许可证

[MIT License](LICENSE)
