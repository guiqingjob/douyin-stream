from __future__ import annotations

import argparse
import asyncio

from playwright.async_api import async_playwright

from ..accounts import resolve_auth_state_path
from ..config import load_config
from ..runtime import enable_live_output, ensure_dir, load_dotenv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qwen-transcribe auth",
        description="Open Qwen in a browser and save Playwright storage state.",
    )
    parser.add_argument("--account", default=load_config().default_account, help="Use a specific account id")
    return parser


async def run(argv: list[str] | None = None) -> int:
    load_dotenv()
    enable_live_output()
    parser = build_parser()
    args = parser.parse_args(argv)

    app_url = load_config().app_url
    account = resolve_auth_state_path(account_id=args.account)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="chrome", headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(app_url, wait_until="domcontentloaded")

        print("")
        print("浏览器已经打开。请在页面里完成扫码登录。")
        if account.account_id:
            print(f"当前账号: {account.account_label} ({account.account_id})")
        print("登录成功并确认页面已经进入登录态后，回到这个终端按一次回车。")
        print("如果想取消，按 Ctrl+C。")
        print("")

        await asyncio.to_thread(input, "登录完成后按回车继续保存 storageState...")

        ensure_dir(account.auth_state_path.parent)
        await context.storage_state(path=str(account.auth_state_path))

        print("")
        if account.account_id:
            print(f"账号 {account.account_id} 的 storageState 已保存到: {account.auth_state_path}")
        else:
            print(f"storageState 已保存到: {account.auth_state_path}")
        print("")

        await browser.close()

    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
