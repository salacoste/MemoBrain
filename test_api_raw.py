#!/usr/bin/env python3
"""
Raw API test to see what GLM returns
"""

import asyncio
from openai import AsyncOpenAI

import os
API_KEY = os.environ.get("ZAI_API_KEY", "your_api_key_here")
BASE_URL = "https://open.bigmodel.cn/api/paas/v4"  # BigModel (Zhipu AI) endpoint
MODEL = "glm-4.5-air"  # lowercase

async def test_raw_api():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON."},
        {"role": "user", "content": "Return a simple JSON object with fields 'status' and 'message'. Example: {\"status\": \"ok\", \"message\": \"Hello\"}"}
    ]

    print(f"Testing API call to {BASE_URL}")
    print(f"Model: {MODEL}")
    print("-" * 50)

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )

        print("Response object type:", type(response))
        print("Response:", response)
        print("-" * 50)
        print("Content:", response.choices[0].message.content)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_raw_api())
