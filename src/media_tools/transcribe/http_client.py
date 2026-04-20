from __future__ import annotations

import json
from typing import Any

import httpx

from .auth_state import ResolvedQwenAuthState


def build_httpx_cookies(storage_state: dict[str, Any]) -> dict[str, str]:
    """从 Playwright storage state 格式中提取 cookies 字典"""
    cookies = storage_state.get("cookies", [])
    result: dict[str, str] = {}
    for cookie in cookies:
        if isinstance(cookie, dict):
            name = str(cookie.get("name", "")).strip()
            value = str(cookie.get("value", "")).strip()
            if name and value:
                result[name] = value
    return result


async def api_json(
    client: httpx.AsyncClient,
    url: str,
    body: Any,
    headers: dict[str, str] | None = None,
) -> Any:
    """发送 JSON POST 请求并返回 JSON 响应"""
    response = await client.post(
        url,
        json=body,
        headers={
            "content-type": "application/json",
            **(headers or {}),
        },
    )
    if response.status_code >= 400:
        raise RuntimeError(f"API request failed: {response.status_code} {response.reason_phrase} {url}")
    return response.json()


def create_qwen_client(resolved_auth: ResolvedQwenAuthState) -> httpx.AsyncClient:
    """创建带有 Qwen 认证的 httpx 客户端"""
    if isinstance(resolved_auth.storage_state, dict):
        cookies = build_httpx_cookies(resolved_auth.storage_state)
    else:
        cookies = {}

    return httpx.AsyncClient(
        cookies=cookies,
        base_url="https://api.qianwen.com",
        timeout=httpx.Timeout(30.0, connect=10.0),
        headers={
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        },
    )