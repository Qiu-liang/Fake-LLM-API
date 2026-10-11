"""OpenAI 阵营 Agent 接入示例：LangChain / autogen / openai SDK 均可这样配置。"""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="fake")

resp = client.chat.completions.create(
    model="fake-gpt",
    messages=[{"role": "user", "content": "北京天气如何？"}],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                },
            },
        }
    ],
)
print(resp.choices[0].message)

# 人类操作员在后台输入: !tool get_weather {"city": "北京"}
# 之后 Agent 收到 finish_reason=tool_calls 的回答
