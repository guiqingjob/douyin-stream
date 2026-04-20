from __future__ import annotations

import asyncio
import base64
import socket
import time
from email.utils import formatdate
import hashlib
import hmac
import os
import re
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib import request as urllib_request
from xml.sax.saxutils import escape as xml_escape


ProgressCallback = Callable[[dict[str, Any]], None]


def normalize_oss_token(token: dict[str, Any]) -> dict[str, Any]:
    """兼容新版 token 结构：把 data.sts 里的字段平铺到顶层。"""
    normalized = dict(token or {})
    sts = normalized.get("sts")
    if isinstance(sts, dict):
        for key in ["bucket", "endpoint", "fileKey", "accessKeyId", "accessKeySecret", "securityToken"]:
            if key not in normalized and key in sts:
                normalized[key] = sts[key]
    return normalized


def md5_base64(input_bytes: bytes) -> str:
    return base64.b64encode(hashlib.md5(input_bytes).digest()).decode("ascii")


def hmac_base64(secret: str, input_value: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), input_value.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def parse_upload_id(xml_text: str) -> str:
    match = re.search(r"<UploadId>([^<]+)</UploadId>", xml_text)
    if not match:
        raise RuntimeError("Unable to parse UploadId from OSS initiate response.")
    return match.group(1)


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


def _read_error_body(error: Exception) -> str:
    body = getattr(error, "read", None)
    if callable(body):
        try:
            data = body()
        except (OSError, IOError):
            return ""
        if isinstance(data, bytes):
            return data.decode("utf-8", errors="replace")
        return str(data)
    return ""


def _open_request(req: urllib_request.Request, timeout: int = 30) -> Any:
    """打开请求，支持超时和重试"""
    last_error = None
    for attempt in range(3):
        try:
            return urllib_request.urlopen(req, timeout=timeout)
        except (socket.timeout, urllib_request.URLError) as e:
            last_error = e
            if attempt < 2:
                wait = 2 ** attempt
                time.sleep(wait)
            else:
                break
    # 所有重试失败
    detail = _read_error_body(last_error)
    message = str(last_error)
    if detail:
        message = f"{message} {detail}"
    raise RuntimeError(f"请求失败 (重试3次): {message}") from last_error


CHUNK_SIZE = 8 * 1024 * 1024  # 8MB chunks


class _ChunkedFileReader:
    """流式文件读取器，避免大文件一次性读入内存"""
    def __init__(self, file_path: Path, chunk_size: int = CHUNK_SIZE):
        self.file_path = file_path
        self.chunk_size = chunk_size
        self._file = None

    def __enter__(self):
        self._file = open(self.file_path, 'rb')
        return self

    def __exit__(self, *args):
        if self._file:
            self._file.close()

    def __iter__(self) -> Iterable[bytes]:
        while True:
            chunk = self._file.read(self.chunk_size)
            if not chunk:
                break
            yield chunk


def initiate_multipart_upload(sts: dict[str, Any], mime_type: str) -> str:
    oss_date = formatdate(usegmt=True)
    headers = {
        "x-oss-date": oss_date,
        "x-oss-security-token": sts["securityToken"],
        "x-oss-user-agent": "qwen-web-capture/0.1",
    }
    authorization = sign_oss_request(
        method="POST",
        bucket=sts["bucket"],
        object_key=sts["fileKey"],
        access_key_id=sts["accessKeyId"],
        access_key_secret=sts["accessKeySecret"],
        content_type=mime_type,
        date_value=oss_date,
        oss_headers=headers,
        subresources={"uploads": ""},
    )
    req = urllib_request.Request(
        build_oss_url(sts["bucket"], sts["endpoint"], sts["fileKey"], {"uploads": ""}),
        method="POST",
        headers={
            **headers,
            "authorization": authorization,
            "content-type": mime_type,
        },
    )
    with _open_request(req) as response:
        return parse_upload_id(response.read().decode("utf-8", errors="replace"))


def direct_upload_with_presigned_url(url: str, file_buffer: bytes, mime_type: str) -> None:
    req = urllib_request.Request(
        url,
        data=file_buffer,
        method="PUT",
        headers={"content-type": mime_type},
    )
    with _open_request(req):
        return


def _direct_upload_with_presigned_url_from_path(url: str, file_path: Path, mime_type: str) -> None:
    """从文件路径直接上传到预签名URL，使用流式上传避免大文件 OOM"""
    with _ChunkedFileReader(file_path) as reader:
        req = urllib_request.Request(
            url,
            data=reader,
            method="PUT",
            headers={"content-type": mime_type},
        )
        with _open_request(req):
            return


def abort_multipart_upload(sts: dict[str, Any], upload_id: str) -> None:
    """取消分片上传，清理已上传的分片"""
    oss_date = formatdate(usegmt=True)
    headers = {
        "x-oss-date": oss_date,
        "x-oss-security-token": sts["securityToken"],
        "x-oss-user-agent": "qwen-web-capture/0.1",
    }
    authorization = sign_oss_request(
        method="DELETE",
        bucket=sts["bucket"],
        object_key=sts["fileKey"],
        access_key_id=sts["accessKeyId"],
        access_key_secret=sts["accessKeySecret"],
        date_value=oss_date,
        oss_headers=headers,
        subresources={"uploadId": upload_id},
    )
    req = urllib_request.Request(
        build_oss_url(
            sts["bucket"],
            sts["endpoint"],
            sts["fileKey"],
            {"uploadId": upload_id},
        ),
        method="DELETE",
        headers={
            **headers,
            "authorization": authorization,
        },
    )
    with _open_request(req):
        return


def upload_part(sts: dict[str, Any], upload_id: str, part_number: int, chunk: bytes, mime_type: str) -> str:
    oss_date = formatdate(usegmt=True)
    content_md5 = md5_base64(chunk)
    headers = {
        "x-oss-date": oss_date,
        "x-oss-security-token": sts["securityToken"],
        "x-oss-user-agent": "qwen-web-capture/0.1",
    }
    authorization = sign_oss_request(
        method="PUT",
        bucket=sts["bucket"],
        object_key=sts["fileKey"],
        access_key_id=sts["accessKeyId"],
        access_key_secret=sts["accessKeySecret"],
        content_md5=content_md5,
        content_type=mime_type,
        date_value=oss_date,
        oss_headers=headers,
        subresources={
            "partNumber": str(part_number),
            "uploadId": upload_id,
        },
    )
    req = urllib_request.Request(
        build_oss_url(
            sts["bucket"],
            sts["endpoint"],
            sts["fileKey"],
            {
                "partNumber": str(part_number),
                "uploadId": upload_id,
            },
        ),
        data=chunk,
        method="PUT",
        headers={
            **headers,
            "authorization": authorization,
            "content-md5": content_md5,
            "content-type": mime_type,
        },
    )
    with _open_request(req) as response:
        etag = response.headers.get("ETag")
    if not etag:
        raise RuntimeError(f"OSS upload part {part_number} missing ETag.")
    return etag


def complete_multipart_upload(sts: dict[str, Any], upload_id: str, parts: list[dict[str, Any]]) -> None:
    xml = "".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<CompleteMultipartUpload>",
            *[
                (
                    "<Part>"
                    f"<PartNumber>{part['partNumber']}</PartNumber>"
                    f"<ETag>{xml_escape(str(part['etag']))}</ETag>"
                    "</Part>"
                )
                for part in parts
            ],
            "</CompleteMultipartUpload>",
        ]
    ).encode("utf-8")
    content_md5 = md5_base64(xml)
    content_type = "application/xml"
    oss_date = formatdate(usegmt=True)
    headers = {
        "x-oss-date": oss_date,
        "x-oss-security-token": sts["securityToken"],
        "x-oss-user-agent": "qwen-web-capture/0.1",
    }
    authorization = sign_oss_request(
        method="POST",
        bucket=sts["bucket"],
        object_key=sts["fileKey"],
        access_key_id=sts["accessKeyId"],
        access_key_secret=sts["accessKeySecret"],
        content_md5=content_md5,
        content_type=content_type,
        date_value=oss_date,
        oss_headers=headers,
        subresources={"uploadId": upload_id},
    )
    req = urllib_request.Request(
        build_oss_url(
            sts["bucket"],
            sts["endpoint"],
            sts["fileKey"],
            {"uploadId": upload_id},
        ),
        data=xml,
        method="POST",
        headers={
            **headers,
            "authorization": authorization,
            "content-md5": content_md5,
            "content-type": content_type,
        },
    )
    with _open_request(req):
        return


async def upload_file_to_oss(
    *,
    token: dict[str, Any],
    file_buffer: bytes | None = None,
    file_path: str | Path | None = None,
    mime_type: str,
    part_size: int = 1024 * 1024,
    on_progress: ProgressCallback | None = None,
    upload_mode: str | None = None,
) -> None:
    """上传文件到OSS
    
    Args:
        token: OSS令牌
        file_buffer: 文件字节缓冲区（小文件使用）
        file_path: 文件路径（大文件使用，避免OOM）
        mime_type: MIME类型
        part_size: 分片大小
        on_progress: 进度回调
        upload_mode: 上传模式
    """
    token = normalize_oss_token(token)

    # 验证token的必需键
    required_keys = ["getLink", "sts", "bucket", "endpoint", "fileKey", "accessKeyId", "accessKeySecret", "securityToken"]
    for key in required_keys:
        if key not in token:
            raise ValueError(f"Token missing required key: {key}")
    
    callback = on_progress or (lambda _event: None)
    mode = (upload_mode or os.environ.get("QWEN_OSS_UPLOAD_MODE", "multipart")).strip().lower()
    if mode not in {"multipart", "auto", "direct"}:
        raise ValueError(f"Unsupported OSS upload mode: {mode}")

    # 确定使用文件路径还是字节缓冲
    use_file_path = file_path is not None and file_buffer is None
    if use_file_path:
        assert file_path is not None
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        file_size = file_path_obj.stat().st_size
    elif file_buffer is not None:
        assert file_buffer is not None
        file_size = len(file_buffer)
    else:
        raise ValueError("Either file_buffer or file_path must be provided")

    if mode in {"auto", "direct"}:
        try:
            if use_file_path:
                # 使用文件路径上传
                await asyncio.to_thread(_direct_upload_with_presigned_url_from_path, token["getLink"], file_path_obj, mime_type)
            else:
                assert file_buffer is not None
                await asyncio.to_thread(direct_upload_with_presigned_url, token["getLink"], file_buffer, mime_type)
            callback({"type": "direct-upload-complete"})
            return
        except Exception as error:
            callback({"type": "direct-upload-failed", "error": error, "mode": mode})
            if mode == "direct":
                raise

    upload_id = await asyncio.to_thread(initiate_multipart_upload, token["sts"], mime_type)
    callback({"type": "multipart-started", "uploadId": upload_id})

    parts: list[dict[str, Any]] = []
    part_number = 0

    try:
        if use_file_path:
            # 使用文件路径进行分片上传（避免OOM）
            total_parts = (file_size + part_size - 1) // part_size
            with open(file_path_obj, 'rb') as f:
                for part_number in range(1, total_parts + 1):
                    chunk = f.read(part_size)
                    if not chunk:
                        break
                    etag = await asyncio.to_thread(upload_part, token["sts"], upload_id, part_number, chunk, mime_type)
                    parts.append({"partNumber": part_number, "etag": etag})
                    callback({"type": "part-uploaded", "partNumber": part_number, "totalParts": total_parts})
        else:
            # 使用字节缓冲进行分片上传
            assert file_buffer is not None
            total_parts = (file_size + part_size - 1) // part_size
            buffer = file_buffer
            for offset, part_number in zip(range(0, len(buffer), part_size), range(1, total_parts + 1), strict=True):
                chunk = buffer[offset : offset + part_size]
                etag = await asyncio.to_thread(upload_part, token["sts"], upload_id, part_number, chunk, mime_type)
                parts.append({"partNumber": part_number, "etag": etag})
                callback({"type": "part-uploaded", "partNumber": part_number, "totalParts": total_parts})

        await asyncio.to_thread(complete_multipart_upload, token["sts"], upload_id, parts)
        callback({"type": "multipart-complete"})
    except Exception as e:
        # 修复：multipart上传失败时清理已上传的分片
        if upload_id:
            try:
                await asyncio.to_thread(abort_multipart_upload, token["sts"], upload_id)
                callback({"type": "multipart-aborted", "uploadId": upload_id})
            except Exception as abort_error:
                callback({"type": "multipart-abort-failed", "uploadId": upload_id, "error": abort_error})
        raise e
