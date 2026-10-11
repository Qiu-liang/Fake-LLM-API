"""Anthropic 阵营 Agent 接入示例：claude SDK / claude-agent-sdk 均可这样配置。"""

from anthropic import Anthropic

client = Anthropic(base_url="http://localhost:8000", api_key="fake")

resp = client.messages.create(
    model="fake-claude",
    max_tokens=1024,
    messages=[{"role": "user", "content": "你好"}],
)
print(resp.content)

# 同一个操作台（/operator）也会收到这条请求，操作员的纯文本回答会包装成 Anthropic content block 返回
