from __future__ import annotations

import asyncio
import json
import socket
import time
from pathlib import Path
from typing import Any
from urllib import request as urllib_request

from .runtime import ensure_dir


async def api_json(context: Any, url: str, body: Any, headers: dict[str, str] | None = None) -> Any:
    response = await context.fetch(
        url,
        method="POST",
        headers={
            "content-type": "application/json",
            **(headers or {}),
        },
        data=json.dumps(body),
    )
    if not response.ok:
        raise RuntimeError(f"API request failed: {response.status} {response.status_text} {url}")
    return await response.json()


def _download_file(url: str, output_path: Path, timeout: int = 30) -> None:
    """下载文件，支持超时和重试"""
    for attempt in range(3):
        try:
            req = urllib_request.Request(url, method="GET")
            with urllib_request.urlopen(req, timeout=timeout) as response:
                data = response.read()
            ensure_dir(output_path.parent)
            output_path.write_bytes(data)
            return
        except (socket.timeout, urllib_request.URLError) as e:
            if attempt < 2:
                wait = 2 ** attempt  # 指数退避: 1s, 2s
                time.sleep(wait)
            else:
                raise RuntimeError(f"下载失败 (重试{attempt + 1}次): {url}") from e


async def download_file(url: str, output_path: str | Path, timeout: int = 30) -> Path:
    path = Path(output_path).resolve()
    await asyncio.to_thread(_download_file, url, path, timeout)
    return path
