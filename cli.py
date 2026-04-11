#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音下载管家 CLI - 统一交互式入口

用法:
    python cli.py

功能:
    交互式菜单，用户只需选择序号即可执行对应功能
"""

import os
import sys
from pathlib import Path

# 切换到脚本所在目录
SKILL_DIR = Path(__file__).parent.resolve()
os.chdir(SKILL_DIR)

# 添加 scripts 目录到路径
sys.path.insert(0, str(SKILL_DIR / "scripts"))


def main_menu():
    """主菜单"""
    from scripts.core.ui import (
        bold,
        header,
        info,
        print_header,
        separator,
        success,
        warning,
    )

    # 启动时自动检查更新
    _check_updates_on_startup()

    while True:
        print_header("🎬 抖音下载管家")
        print("  请选择功能：")
        print()
        print(f"  {bold('1')}. 🔍 检查博主更新")
        print(f"  {bold('2')}. 📥 下载所有更新")
        print(f"  {bold('3')}. 👤 关注列表管理")
        print(f"  {bold('4')}. 📺 视频下载")
        print(f"  {bold('5')}. 🗜️  视频压缩")
        print(f"  {bold('6')}. 📊 生成数据看板")
        print(f"  {bold('7')}. ⚙️  系统设置")
        print()
        print(f"  {bold('0')}. 退出程序")
        print()

        try:
            choice = input("请输入选项 (0-7): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print(success("感谢使用，再见！"))
            return

        if choice == "0":
            print()
            print(success("感谢使用，再见！"))
            print()
            return
        elif choice == "1":
            cmd_check_updates()
        elif choice == "2":
            cmd_download_updates()
        elif choice == "3":
            cmd_following_menu()
        elif choice == "4":
            cmd_download_menu()
        elif choice == "5":
            cmd_compress()
        elif choice == "6":
            cmd_generate_data()
        elif choice == "7":
            cmd_system_settings()
        else:
            print()
            print(warning("无效的选项，请重新选择"))
            print()


def _check_updates_on_startup():
    """启动时自动检查更新"""
    from scripts.core.update_checker import check_all_updates
    from scripts.core.ui import separator, dim

    try:
        result = check_all_updates()

        if result["has_updates_count"] > 0:
            print()
            print(dim(separator("─", 60)))
            print(f"  💡 提示: 有 {result['has_updates_count']} 位博主更新了内容")
            print(f"     选择 '2' 可快速下载所有更新")
            print(dim(separator("─", 60)))
            print()
        else:
            print()
            print("  ✓ 所有博主均为最新状态")
            print()

    except Exception as e:
        print()
        print(f"  ⚠️  检查更新时出错: {e}")
        print()


def cmd_check_updates():
    """检查更新"""
    from scripts.core.update_checker import check_all_updates

    print()
    check_all_updates()
    print()
    _wait_for_key()


def cmd_download_updates():
    """下载所有更新"""
    from scripts.core.update_checker import check_all_updates
    from scripts.core.downloader import download_by_uid
    from scripts.core.ui import info, success, error

    print()
    result = check_all_updates()

    if result["total_new"] == 0:
        print(info("✓ 所有博主均为最新，无需下载更新"))
        print()
        _wait_for_key()
        return

    print()
    confirm = input(f"确认下载 {result['total_new']} 个新视频？(y/N): ").strip().lower()
    if confirm != "y":
        print(info("已取消"))
        print()
        _wait_for_key()
        return

    success_count = 0
    failed_count = 0

    for user in result["users"]:
        if user["has_update"]:
            uid = user["uid"]
            name = user["name"]
            new_count = user["new_count"]

            print()
            print(info(f"下载: {name} ({new_count} 个新视频)"))
            ok = download_by_uid(uid)
            if ok:
                success_count += 1
            else:
                failed_count += 1

    print()
    print_header("更新下载完成")
    print(success(f"成功: {success_count} 位博主"))
    print(error(f"失败: {failed_count} 位博主"))
    print()
    _wait_for_key()


def cmd_system_settings():
    """系统设置子菜单"""
    from scripts.core.ui import bold, info, print_header, warning

    while True:
        print_header("⚙️  系统设置")
        print(f"  {bold('1')}. 🔍 环境检测与初始化")
        print(f"  {bold('2')}. 🔑 扫码登录获取 Cookie")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-2): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "0":
            return
        elif choice == "1":
            cmd_env_check()
        elif choice == "2":
            cmd_login()
        else:
            print()
            print(warning("无效的选项，请重新选择"))


def cmd_env_check():
    """环境检测"""
    from scripts.core.env_check import check_all

    print()
    all_passed, _ = check_all()
    _wait_for_key()


def cmd_login():
    """登录认证"""
    from scripts.core.auth import login_sync

    print()
    try:
        persist_input = input("是否启用持久化模式？(y/N): ").strip().lower()
        persist = persist_input == "y"
    except (EOFError, KeyboardInterrupt):
        persist = False
    success_flag, _ = login_sync(persist=persist)

    if success_flag:
        _wait_for_key()


def cmd_following_menu():
    """关注列表管理子菜单"""
    from scripts.core.ui import bold, info, print_header, warning

    while True:
        print_header("关注列表管理")
        print(f"  {bold('1')}. 查看关注列表")
        print(f"  {bold('2')}. 添加博主链接")
        print(f"  {bold('3')}. 移除博主")
        print(f"  {bold('4')}. 批量导入")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "0":
            return
        elif choice == "1":
            _cmd_list_users()
        elif choice == "2":
            _cmd_add_user()
        elif choice == "3":
            _cmd_remove_user()
        elif choice == "4":
            _cmd_batch_add()
        else:
            print()
            print(warning("无效的选项，请重新选择"))


def _cmd_list_users():
    """查看关注列表"""
    from scripts.core.following_mgr import display_users

    print()
    display_users()
    print()
    _wait_for_key()


def _cmd_add_user():
    """添加博主"""
    from scripts.core.following_mgr import add_user

    print()
    try:
        url = input("请粘贴抖音主页链接: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not url:
        return

    add_user(url)
    print()
    _wait_for_key()


def _cmd_remove_user():
    """移除博主"""
    from scripts.core.following_mgr import display_users, remove_user

    print()
    users = display_users()
    if not users:
        _wait_for_key()
        return

    print()
    try:
        uid = input("请输入要移除的博主 UID: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not uid:
        return

    try:
        delete_local = (
            input("是否同时删除本地视频文件？(y/N): ").strip().lower() == "y"
        )
    except (EOFError, KeyboardInterrupt):
        delete_local = False

    remove_user(uid, delete_local=delete_local)
    print()
    _wait_for_key()


def _cmd_batch_add():
    """批量导入"""
    from scripts.core.following_mgr import batch_add_urls

    print()
    print("请粘贴多个抖音主页 URL（逗号、空格或换行分隔，输入空行结束）")
    print()

    lines = []
    while True:
        try:
            line = input()
            if not line.strip():
                break
            lines.append(line)
        except EOFError:
            break

    all_text = " ".join(lines)
    urls = [u.strip() for u in all_text.replace(",", " ").split() if u.strip()]

    if not urls:
        print("未检测到有效的 URL")
        _wait_for_key()
        return

    batch_add_urls(urls)
    print()
    _wait_for_key()


def cmd_download_menu():
    """视频下载子菜单"""
    from scripts.core.ui import bold, info, print_header, warning

    while True:
        print_header("视频下载")
        print(f"  {bold('1')}. 下载单个博主（输入 URL）")
        print(f"  {bold('2')}. 从关注列表选择下载")
        print(f"  {bold('3')}. 下载所有关注（全量下载）")
        print(f"  {bold('4')}. 采样下载（每个博主1个视频）")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "0":
            return
        elif choice == "1":
            _cmd_download_by_url()
        elif choice == "2":
            _cmd_download_select()
        elif choice == "3":
            _cmd_download_all()
        elif choice == "4":
            _cmd_download_sample()
        else:
            print()
            print(warning("无效的选项，请重新选择"))


def _cmd_download_by_url():
    """通过 URL 下载"""
    from scripts.core.downloader import download_by_url

    print()
    try:
        url = input("请粘贴抖音主页链接: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not url:
        return

    try:
        max_counts_input = input("最大下载数量（直接回车表示不限制）: ").strip()
        max_counts = int(max_counts_input) if max_counts_input.isdigit() else None
    except (EOFError, KeyboardInterrupt):
        max_counts = None

    download_by_url(url, max_counts)
    print()
    _wait_for_key()


def _cmd_download_select():
    """交互式选择下载"""
    from scripts.core.downloader import interactive_select

    print()
    interactive_select()
    print()
    _wait_for_key()


def _cmd_download_all():
    """全量下载"""
    from scripts.core.downloader import download_all

    print()
    download_all()
    print()
    _wait_for_key()


def _cmd_download_sample():
    """采样下载"""
    from scripts.core.downloader import download_sample

    print()
    download_sample()
    print()
    _wait_for_key()


def cmd_compress():
    """视频压缩"""
    from scripts.core.compressor import compress_all

    print()
    try:
        crf_input = input("压缩质量 CRF (0-51，默认32，越小质量越好): ").strip()
        crf = int(crf_input) if crf_input.isdigit() else 32
    except (EOFError, KeyboardInterrupt):
        crf = 32

    try:
        preset_input = input(
            "压缩速度 (ultrafast/fast/medium/slow，默认fast): "
        ).strip().lower()
        preset = preset_input if preset_input in ["ultrafast", "fast", "medium", "slow"] else "fast"
    except (EOFError, KeyboardInterrupt):
        preset = "fast"

    try:
        replace_input = input("是否直接替换原文件？(Y/n): ").strip().lower()
        replace = replace_input != "n"
    except (EOFError, KeyboardInterrupt):
        replace = True

    compress_all(crf=crf, preset=preset, replace=replace)
    print()
    _wait_for_key()


def cmd_generate_data():
    """生成数据看板"""
    from scripts.core.data_generator import generate_data

    print()
    generate_data()
    print()
    _wait_for_key()


def _wait_for_key():
    """等待用户按键返回"""
    try:
        input("按回车键返回...")
    except (EOFError, KeyboardInterrupt):
        print()
        pass


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print()
        print("\n已取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)
