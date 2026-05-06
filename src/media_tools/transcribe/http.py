from __future__ import annotations

import asyncio
import json
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union
from urllib import request as urllib_request

import requests

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


@dataclass(frozen=True)
class RequestsApiResponse:
    ok: bool
    status: int
    status_text: str
    _payload: Any

    async def json(self) -> Any:
        return self._payload


class RequestsApiContext:
    def __init__(
        self,
        *,
        cookie_string: str,
        base_headers: dict[str, str] | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self._cookie_string = cookie_string.strip()
        self._timeout_seconds = timeout_seconds
        self._base_headers = dict(base_headers or {})
        self._session = requests.Session()

    async def dispose(self) -> None:
        await asyncio.to_thread(self._session.close)

    def _build_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        merged = dict(self._base_headers)
        if headers:
            merged.update(headers)
        if self._cookie_string and "cookie" not in {k.lower() for k in merged}:
            merged["cookie"] = self._cookie_string
        merged.setdefault("accept", "application/json, text/plain, */*")
        merged.setdefault(
            "user-agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        )
        return merged

    def _request(self, url: str, *, method: str, headers: dict[str, str] | None, data: Optional[str]) -> RequestsApiResponse:
        merged = self._build_headers(headers)
        try:
            resp = self._session.request(
                method=method,
                url=url,
                headers=merged,
                data=data.encode("utf-8") if isinstance(data, str) else data,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as error:
            raise RuntimeError(f"API request failed: {error}") from error

        payload: Any
        status_text = str(resp.reason or "")
        if resp.content:
            try:
                payload = resp.json()
            except ValueError:
                payload = resp.text
        else:
            payload = None
        return RequestsApiResponse(
            ok=bool(resp.ok),
            status=int(resp.status_code),
            status_text=status_text,
            _payload=payload,
        )

    async def fetch(
        self,
        url: str,
        *,
        method: str = "POST",
        headers: dict[str, str] | None = None,
        data: Optional[str] = None,
    ) -> RequestsApiResponse:
        return await asyncio.to_thread(self._request, url, method=method, headers=headers, data=data)


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


async def download_file(url: str, output_path: Union[str, Path], timeout: int = 30) -> Path:
    path = Path(output_path).resolve()
    await asyncio.to_thread(_download_file, url, path, timeout)
    return path
