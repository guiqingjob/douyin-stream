from __future__ import annotations
"""OSS 请求签名工具"""

import base64
import hashlib
import hmac
import re
from typing import Any, Optional, Union


def md5_base64(input_bytes: bytes) -> str:
    return base64.b64encode(hashlib.md5(input_bytes).digest()).decode("ascii")


def hmac_base64(secret: str, input_value: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), input_value.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def subresource_string(params: dict[str, str]) -> str:
    entries = sorted(
        (key, value) for key, value in params.items() if value is not None
    )
    if not entries:
        return ""
    query = "&".join(key if value == "" else f"{key}={value}" for key, value in entries)
    return f"?{query}"


def canonicalized_oss_headers(headers: dict[str, str]) -> str:
    normalized = []
    for key, value in headers.items():
        if key.lower().startswith("x-oss-"):
            normalized.append((key.lower(), str(value).strip()))
    normalized.sort(key=lambda item: item[0])
    return "".join(f"{key}:{value}\n" for key, value in normalized)


def sign_oss_request(
    *,
    method: str,
    bucket: str,
    object_key: str,
    access_key_id: str,
    access_key_secret: str,
    content_md5: str = "",
    content_type: str = "",
    date_value: str = "",
    oss_headers: dict[str, str] | None = None,
    subresources: dict[str, str] | None = None,
) -> str:
    headers = oss_headers or {}
    resources = subresources or {}
    canonical_headers = canonicalized_oss_headers(headers)
    resource = f"/{bucket}/{object_key}{subresource_string(resources)}"
    string_to_sign = "\n".join(
        [
            method,
            content_md5,
            content_type,
            date_value,
            canonical_headers + resource,
        ]
    )
    signature = hmac_base64(access_key_secret, string_to_sign)
    return f"OSS {access_key_id}:{signature}"


def build_oss_url(bucket: str, endpoint: str, object_key: str, query: dict[str, str] | None = None) -> str:
    endpoint_host = re.sub(r"^https?://", "", endpoint)
    base = f"https://{bucket}.{endpoint_host}/{object_key}"
    if not query:
        return base
    return f"{base}{subresource_string(query)}"
