"""多模态接入示例：发送图片，操作员在控制台看图作答。"""

import base64
import pathlib

from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="fake")

# 换成任意本地图片；也可以直接用 http(s) URL
image_path = pathlib.Path(__file__).parent / "sample.png"
b64 = base64.b64encode(image_path.read_bytes()).decode() if image_path.exists() else "AAAA"

resp = client.chat.completions.create(
    model="fake-gpt",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "图里是什么？"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }
    ],
)
print(resp.choices[0].message.content)
