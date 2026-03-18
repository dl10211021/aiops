import asyncio
from openai import AsyncOpenAI
from core.agent import get_available_models
import json

async def run():
    # Update providers.json to reproduce issue
    with open('providers.json', 'w') as f:
        json.dump([
            {
                "id": "custom_1",
                "name": "Local VLLM",
                "protocol": "openai",
                "base_url": "http://192.168.127.8/v1",
                "api_key": "gpustack_b7df8bb9a25a510d_4bb1f5487707d07b2d7e1098c6034c1c",
                "models": ""
            }
        ], f)
    print("Testing get_available_models with local endpoint...")
    res = await get_available_models()
    print("Result:", res)

asyncio.run(run())
