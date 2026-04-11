#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
登录认证模块 - 扫码登录与 Cookie 管理
"""

import asyncio
import os
import sys
from pathlib import Path

from .ui import (
    error,
    info,
    print_header,
    print_status,
    success,
    warning,
)
from .config_mgr import get_config


async def douyin_login(persist=False, cookies_path=None):
    """
    执行抖音扫码登录

    Args:
        persist: 是否启用持久化模式
        cookies_path: Cookie 保存路径

    Returns:
        (success, cookie_str) 元组
    """
    print_header("抖音扫码登录")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print(error("Playwright 未安装"))
        print(info("请先执行: pip install playwright"))
        print(info("然后执行: python -m playwright install chromium"))
        return False, ""

    # 确定 Cookie 保存路径
    if cookies_path is None:
        config = get_config()
        cookies_path = config.config_path

    # 切换到脚本所在目录
    skill_dir = Path(__file__).parent.parent.parent
    os.chdir(skill_dir)

    print(info("📱 正在启动浏览器..."))
    print(info("请使用手机抖音 APP 扫描二维码登录"))
    print(info("最久等待 5 分钟，按 Ctrl+C 可取消"))
    print()

    if persist:
        print(info("💾 持久化模式已启用，登录状态将自动保存"))
        user_data_dir = skill_dir / ".playwright-data"
        print(info(f"   数据目录：{user_data_dir}"))
        print()

    browser = None

    try:
        async with async_playwright() as p:
            # 创建浏览器实例
            if persist:
                user_data_dir = skill_dir / ".playwright-data"
                context = await p.chromium.launch_persistent_context(
                    str(user_data_dir),
                    headless=False,
                    args=[
                        "--no-sandbox",
                        "--disable-web-security",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                browser = context
            else:
                browser = await p.chromium.launch(
                    headless=False,
                    args=[
                        "--no-sandbox",
                        "--disable-web-security",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800}
                )

            # 获取页面对象
            if persist:
                page = context.pages[0] if context.pages else await context.new_page()
            else:
                page = await context.new_page()

            # 导航到抖音
            await page.goto("https://www.douyin.com")

            print(info("⏳ 等待登录..."))

            # 等待登录
            logged_in = False
            cookies = None

            for i in range(60):
                await asyncio.sleep(2)
                cookies = await context.cookies()
                cookie_names = {c["name"] for c in cookies}

                # 严格检测登录状态
                has_strong_login = "sessionid" in cookie_names and (
                    "passport_csrf_token" in cookie_names
                    or "sid_guard" in cookie_names
                )

                if has_strong_login:
                    logged_in = True
                    break

                if (i + 1) % 10 == 0:
                    print(info(f"   等待登录中... ({i+1}/60)"))

            if not logged_in:
                print(error("✗ 登录超时，请重试"))
                return False, ""

            print(success("✓ 登录成功！"))

            # 提取抖音 Cookies
            dy_cookies = {}
            if cookies:
                for cookie in cookies:
                    domain = cookie.get("domain", "")
                    if "douyin.com" in domain or ".douyin.com" in domain:
                        dy_cookies[cookie["name"]] = cookie["value"]

            cookie_str = "; ".join([f"{k}={v}" for k, v in dy_cookies.items()])

            # 验证 Cookie
            try:
                from utils.auth_parser import AuthParser

                parser = AuthParser()
                success_validate, msg, _ = parser.validate_data(
                    cookie_str, "cookie", "douyin"
                )
                if success_validate:
                    print(success("✓ Cookie 格式及有效性验证通过"))
                else:
                    print(warning(f"⚠ Cookie 验证未通过: {msg}"))
            except ImportError:
                pass

            # 保存 Cookie 到配置文件
            if cookie_str:
                import yaml

                config = {}
                config_path = Path(cookies_path)
                if config_path.exists():
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f) or {}

                config["cookie"] = cookie_str

                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(config, f, allow_unicode=True)

                print(success(f"✓ Cookie 已保存到: {cookies_path}"))

            return True, cookie_str

    except KeyboardInterrupt:
        print()
        print(warning("⚠ 已取消登录"))
        return False, ""
    except Exception as e:
        print(error(f"✗ 发生错误: {e}"))
        return False, ""
    finally:
        # 确保浏览器总是被关闭
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass


def login_sync(persist=False):
    """
    同步登录包装器

    Args:
        persist: 是否持久化模式

    Returns:
        (success, cookie_str) 元组
    """
    skill_dir = Path(__file__).parent.parent.parent
    os.chdir(skill_dir)
    return asyncio.run(douyin_login(persist=persist))
