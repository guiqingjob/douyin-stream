#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音扫码登录工具（精简版）
只负责打开浏览器和获取 cookies
"""

import asyncio
import sys
from pathlib import Path
import os

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright 未安装，请先安装：")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)

# 强制使用脚本所在目录作为工作目录
SKILL_DIR = Path(__file__).parent.parent.resolve()
# 切换到脚本目录（确保相对路径正确）
os.chdir(SKILL_DIR)


async def douyin_login(cookies_path: str = None, persist: bool = False):
    """
    打开浏览器等待用户扫码登录抖音，然后获取 cookies

    Args:
        cookies_path: 保存 cookies 的配置文件路径
        persist: 是否启用持久化模式（保存登录状态，下次无需重新扫码）
    """
    print("📱 抖音扫码登录")
    print("=" * 40)

    browser = None

    try:
        # 创建 Playwright 实例并使用 async with
        async with async_playwright() as p:
            # 持久化数据目录（保存登录状态）
            user_data_dir = Path(__file__).parent.parent / ".playwright-data"

            if persist:
                # 持久化模式：使用持久化上下文，自动保存登录状态
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=[
                        "--no-sandbox",
                        "--disable-web-security",
                        "--disable-blink-features=AutomationControlled",
                    ]
                )
                browser = context  # 持久化模式中 browser 就是 context
            else:
                # 普通模式：每次重新扫码
                browser = await p.chromium.launch(
                    headless=False,
                    args=[
                        "--no-sandbox",
                        "--disable-web-security",
                        "--disable-blink-features=AutomationControlled",
                    ]
                )

                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800}
                )


            # 获取页面对象
            if persist:
                # 持久化模式：使用现有页面或创建新页面
                if len(context.pages) > 0:
                    page = context.pages[0]
                else:
                    page = await context.new_page()
            else:
                # 普通模式：创建新页面
                page = await context.new_page()

            # 导航到抖音首页
            douyin_url = "https://www.douyin.com"
            await page.goto(douyin_url)

            # 持久化模式提示
            if persist:
                print("   💾 持久化模式已启用，登录状态将自动保存")
                print(f"   数据目录：{user_data_dir}")
                print("   💡 首次使用需要扫码，后续启动将自动使用已保存的登录状态")
            else:
                print("   登录成功后脚本会自动检测并获取 cookies")
            print("   最久等待 5 分钟，按 Ctrl+C 可取消\n")

            # 等待登录（严格检测：需要同时有多个登录特征 cookie）
            logged_in = False
            cookies = None
            for i in range(60):
                await asyncio.sleep(2)

                # 获取当前 cookies 进行检查
                cookies = await context.cookies()
                cookie_names = {c["name"] for c in cookies}

                # 严格检测：需要同时有 sessionid 和其他登录 cookie
                has_strong_login = (
                    "sessionid" in cookie_names and
                    ("passport_csrf_token" in cookie_names or "sid_guard" in cookie_names)
                )

                if has_strong_login:
                    print("\n✅ 登录成功！")
                    logged_in = True
                    break
                else:
                    # 每 10 秒显示一次进度（每 2 秒检查一次）
                    if (i + 1) % 5 == 0:
                        print(f"   等待登录中... ({i+1}/60)")

            # 提取抖音相关的 cookies
            dy_cookies = {}
            if cookies:
                for cookie in cookies:
                    if "douyin.com" in cookie.get("domain", "") or ".douyin.com" in cookie.get("domain", ""):
                        dy_cookies[cookie["name"]] = cookie["value"]

            print(f"\n   获取到 {len(dy_cookies)} 个 cookies")

            # 关闭浏览器（在 async with 块内）
            if not persist:
                await browser.close()
                browser = None  # 标记已关闭
            else:
                print("   💾 持久化模式：浏览器状态已保存，下次无需扫码")
                print("   提示：首次使用需要扫码，后续将自动使用已保存的登录状态")

        # 生成 cookies 字符串（在 async with 块外）
        cookie_str = "; ".join([f"{k}={v}" for k, v in dy_cookies.items()])

        # 验证获取到的 Cookie 质量
        if cookie_str:
            from utils.auth_parser import AuthParser
            parser = AuthParser()
            success, msg, _ = parser.validate_data(cookie_str, "cookie", "douyin")
            if not success:
                print(f"⚠️ 提取到的 Cookie 验证未通过: {msg}")
                print("这可能会影响后续的数据抓取，请考虑重新扫码。")
            else:
                print("✅ Cookie 格式及有效性验证通过")

        print("\n" + "=" * 40)
        print("✅ Cookies 已获取！")
        print("=" * 40)

        # 保存到文件
        if cookies_path:
            config_dir = Path(cookies_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)

            # 读取现有配置
            import yaml
            config = {}
            if Path(cookies_path).exists():
                with open(cookies_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}

            # 更新 cookies
            config["cookie"] = cookie_str

            # 保存
            with open(cookies_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True)

            print(f"   💾 已保存到：{cookies_path}")

        # 输出 cookies 字符串
        print("\n📋 Cookies 字符串（可直接复制）：")
        print("-" * 40)
        print(cookie_str)
        print("-" * 40)

        return True

    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        print("\n📋 详细错误：")

        # 注意：持久化模式下不需要手动关闭 browser
        # 只在非持久化模式下才尝试关闭
        if 'browser' in locals() and browser and hasattr(browser, 'close'):
            try:
                await browser.close()
            except:
                pass

        return False


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="抖音扫码登录工具 - 打开浏览器获取登录态 Cookies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--output", "-o",
        help="输出配置文件路径（保存到 config.cookie 字段）"
    )

    parser.add_argument(
        "--persist", "-p",
        action="store_true",
        help="启用持久化模式（保存登录状态，下次无需重新扫码）"
    )

    args = parser.parse_args()

    # 默认配置文件路径
    cookies_path = args.output
    if not cookies_path:
        # 尝试使用默认配置
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        # 无论如何都使用默认路径（不需要等待 config.yaml 存在）
        cookies_path = str(config_path)

    try:
        success = await douyin_login(cookies_path, args.persist)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
