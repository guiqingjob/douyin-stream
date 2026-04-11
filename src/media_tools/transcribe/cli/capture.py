from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime

from playwright.async_api import Page, async_playwright

from ..accounts import resolve_auth_state_path
from ..config import load_config
from ..runtime import as_absolute, enable_live_output, ensure_dir, load_dotenv, now_stamp
from .common import ensure_auth_state_exists


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qwen-transcribe capture",
        description="Capture Qwen browser traffic into a local JSONL log.",
    )
    parser.add_argument("--account", default=load_config().default_account, help="Use a specific account id")
    parser.add_argument(
        "--output",
        default="",
        help="Optional explicit output file. Defaults to QWEN_NETWORK_LOG_DIR/<timestamp>-manual-capture.jsonl",
    )
    return parser


def should_capture(resource_type: str) -> bool:
    return resource_type in {"document", "fetch", "xhr"}


def truncate_body(body: str | None, limit: int = 20000) -> str | None:
    if body is None or len(body) <= limit:
        return body
    return f"{body[:limit]}...<truncated>"


def event_time() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def attach_page_listeners(page: Page, *, label: str, lines: list[str]) -> None:
    page.on(
        "request",
        lambda request: lines.append(
            json.dumps(
                {
                    "kind": "request",
                    "pageLabel": label,
                    "time": event_time(),
                    "method": request.method,
                    "url": request.url,
                    "resourceType": request.resource_type,
                    "headers": request.headers,
                    "body": truncate_body(request.post_data),
                },
                ensure_ascii=False,
            )
        )
        if should_capture(request.resource_type)
        else None,
    )

    async def on_response(response) -> None:
        request = response.request
        if not should_capture(request.resource_type):
            return
        body = None
        try:
            content_type = response.headers.get("content-type", "")
            if any(item in content_type.lower() for item in ("json", "text", "javascript", "xml")):
                body = truncate_body(await response.text())
        except Exception:
            body = None

        lines.append(
            json.dumps(
                {
                    "kind": "response",
                    "pageLabel": label,
                    "time": event_time(),
                    "method": request.method,
                    "url": response.url,
                    "resourceType": request.resource_type,
                    "status": response.status,
                    "ok": response.ok,
                    "headers": response.headers,
                    "body": body,
                },
                ensure_ascii=False,
            )
        )

    page.on("response", on_response)


async def run(argv: list[str] | None = None) -> int:
    load_dotenv()
    enable_live_output()
    parser = build_parser()
    args = parser.parse_args(argv)

    app_config = load_config()
    app_url = app_config.app_url
    account = resolve_auth_state_path(account_id=args.account)
    ensure_auth_state_exists(account)
    network_log_dir = app_config.paths.network_log_dir
    output_path = as_absolute(args.output) if args.output else network_log_dir / f"{now_stamp()}-manual-capture.jsonl"
    lines: list[str] = []
    tracked_pages: set[int] = set()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="chrome", headless=False)
        context = await browser.new_context(storage_state=str(account.auth_state_path))

        def watch_page(page: Page, label: str) -> None:
            page_id = id(page)
            if page_id in tracked_pages:
                return
            tracked_pages.add(page_id)
            attach_page_listeners(page, label=label, lines=lines)

        context.on("page", lambda page: watch_page(page, f"page-{len(context.pages)}"))

        page = await context.new_page()
        watch_page(page, "page-1")
        await page.goto(app_url, wait_until="domcontentloaded")

        print("")
        print("浏览器已经打开，并开始记录网络请求。")
        if account.account_id:
            print(f"当前账号: {account.account_label} ({account.account_id})")
        print("请手动执行完整流程：上传、开始转写、等待完成、导出、删除记录。")
        print("完成后回到终端按一次回车保存日志。")
        print("")

        await asyncio.to_thread(input, "完成网页操作后按回车保存网络日志...")

        ensure_dir(output_path.parent)
        output_path.write_text("\n".join(lines), encoding="utf-8")

        print("")
        print(f"网络日志已保存到: {output_path}")
        print("")

        await context.close()
        await browser.close()

    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
