import asyncio
from openai import AsyncOpenAI
import logging

async def test():
    base_url = "http://192.168.127.8/v1"
    api_key = "gpustack_b7df8bb9a25a510d_4bb1f5487707d07b2d7e1098c6034c1c"
    
    print(f"Testing {base_url} ...")
    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=20.0)
    try:
        res = await client.models.list()
        print(f"Success! Found {len(res.data)} models.")
    except Exception as e:
        print(f"Error fetching models: {e}")

if __name__ == "__main__":
    asyncio.run(test())
