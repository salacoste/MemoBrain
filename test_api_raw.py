#!/usr/bin/env python3
"""
Raw API test to see what GLM returns
"""

import asyncio
import os
from openai import AsyncOpenAI

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.environ.get("ZAI_API_KEY", "your_api_key_here")
BASE_URL = os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/anthropic")
MODEL = os.environ.get("ZAI_MODEL", "GLM-4.5-Air")

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
