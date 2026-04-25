"""B站用户昵称获取服务"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_bilibili_semaphore: asyncio.Semaphore | None = None


def _get_bilibili_semaphore() -> asyncio.Semaphore:
    global _bilibili_semaphore
    if _bilibili_semaphore is None:
        _bilibili_semaphore = asyncio.Semaphore(5)
    return _bilibili_semaphore


async def fetch_bilibili_nickname(mid: str, retries: int = 3) -> str:
    """
    异步获取 B 站用户昵称

    - 超时控制: connect=5s, read=10s
    - 重试: 最多 3 次，指数退避
    - 异常: 返回 mid 作为后备
    """
    import httpx

    url = f"https://api.bilibili.com/x/web-interface/card?mid={mid}"
    timeout = httpx.Timeout(timeout=10.0, connect=5.0)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://space.bilibili.com/",
    }

    for attempt in range(retries):
        try:
            async with _get_bilibili_semaphore():
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    resp = await client.get(url, headers=headers)
                    logger.info(f"B站API响应: mid={mid}, status={resp.status_code}")
                    if resp.status_code == 200:
                        json_data = resp.json()
                        code = json_data.get("code")
                        data = json_data.get("data", {})
                        if code == 0 and data.get("card"):
                            name = data["card"].get("name")
                            logger.info(f"B站昵称获取成功: mid={mid}, name={name}")
                            return name or mid
                        else:
                            logger.warning(f"B站API业务错误: code={code}, mid={mid}")
                    elif resp.status_code == 404:
                        logger.warning(f"B站用户不存在: mid={mid}")
                        return mid
                    else:
                        logger.warning(f"B站API返回非200: {resp.status_code}, body={resp.text[:200]}, mid={mid}")
        except httpx.TimeoutException:
            wait = 2 ** attempt
            logger.warning(f"B站API超时 (attempt {attempt + 1}/{retries}), 重试等待 {wait}s: mid={mid}")
            if attempt < retries - 1:
                await asyncio.sleep(wait)
        except httpx.HTTPError as e:
            wait = 2 ** attempt
            logger.warning(f"B站API错误 (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(wait)
        except (RuntimeError, OSError, ValueError) as e:
            logger.error(f"B站API异常: {e}")
            break

    return mid
