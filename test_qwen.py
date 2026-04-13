import asyncio
from playwright.async_api import async_playwright
import json

async def test():
    async with async_playwright() as p:
        with open(".auth/qwen-storage-state.json") as f:
            state = json.load(f)
        
        ctx = await p.request.new_context(storage_state=state)
        resp = await ctx.get("https://www.qianwen.com/zhiwen/api/equity/get_quota?c=tongyi-web", headers={"referer": "https://www.qianwen.com/discover/audioread"})
        text = await resp.text()
        print(f"Full state Response: {text[:100]}")

asyncio.run(test())
