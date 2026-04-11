#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频下载模块 - 单个/批量/交互下载
"""

import subprocess
import sys
import time
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
from .following_mgr import list_users


def download_by_url(url, max_counts=None):
    """
    通过 URL 下载单个博主的视频

    Args:
        url: 博主主页 URL
        max_counts: 最大下载数量

    Returns:
        是否成功
    """
    print_header("下载博主视频")
    print(info(f"博主 URL: {url}"))
    if max_counts:
        print(info(f"最大下载数量: {max_counts}"))
    print()

    skill_dir = Path(__file__).parent.parent.parent
    download_script = skill_dir / "scripts" / "download.py"

    cmd = [sys.executable, str(download_script), url]
    if max_counts:
        cmd.append(f"--max-counts={max_counts}")

    print(info("开始下载..."))
    print()

    result = subprocess.run(cmd, cwd=str(skill_dir))

    if result.returncode == 0:
        print(success("下载完成！"))
        return True
    else:
        print(error("下载失败，请检查日志"))
        return False


def download_by_uid(uid, max_counts=None):
    """
    通过 UID 下载博主视频

    Args:
        uid: 用户 UID
        max_counts: 最大下载数量

    Returns:
        是否成功
    """
    from utils.following import get_user

    user = get_user(uid)
    if not user:
        print(error(f"用户 {uid} 不在关注列表中"))
        return False

    # 构建 URL
    sec_user_id = user.get("sec_user_id", "")
    if sec_user_id and sec_user_id.startswith("MS4w"):
        url = f"https://www.douyin.com/user/{sec_user_id}"
    else:
        url = f"https://www.douyin.com/user/{uid}"

    name = user.get("nickname", user.get("name", "未知"))
    print(info(f"博主: {name} (UID: {uid})"))

    return download_by_url(url, max_counts)


def download_all(auto_confirm=False):
    """
    下载所有关注的博主

    Args:
        auto_confirm: 是否跳过确认

    Returns:
        (success_count, failed_count) 元组
    """
    print_header("全量下载")

    users = list_users()
    if not users:
        print(info("关注列表为空"))
        print(info("请先使用 '添加博主' 功能添加关注"))
        return 0, 0

    print(info(f"共 {len(users)} 位博主"))
    print()

    if not auto_confirm:
        confirm = input("确认开始下载？(y/N): ").strip().lower()
        if confirm != "y":
            print(info("已取消"))
            return 0, 0

    success_count = 0
    failed_count = 0

    for i, user in enumerate(users, 1):
        uid = user.get("uid")
        name = user.get("nickname", user.get("name", "未知"))

        print()
        print(info(f"[{i}/{len(users)}] 下载: {name}"))

        ok = download_by_uid(uid)
        if ok:
            success_count += 1
        else:
            failed_count += 1

    print()
    print_header("下载完成")
    print(success(f"成功: {success_count}"))
    print(error(f"失败: {failed_count}"))

    return success_count, failed_count


def interactive_select():
    """
    交互式选择博主下载

    Returns:
        (success_count, failed_count) 元组
    """
    print_header("选择下载")

    users = list_users()
    if not users:
        print(info("关注列表为空"))
        print(info("请先使用 '添加博主' 功能添加关注"))
        return 0, 0

    config = get_config()
    downloads_path = config.get_download_path()

    # 显示用户列表
    print(info("选择要下载的博主（输入序号，逗号分隔，all=全部，q=返回）"))
    print()

    for i, user in enumerate(users, 1):
        uid = user.get("uid", "未知")
        name = user.get("nickname", user.get("name", "未知"))
        folder = user.get("folder", name or uid)
        user_dir = downloads_path / folder
        local_count = len(list(user_dir.glob("*.mp4"))) if user_dir.exists() else 0

        status = f"已下载 {local_count} 个" if local_count > 0 else "未下载"
        print(f"  {i:2}. {name} ({status})")

    print()
    choice = input("请选择: ").strip().lower()

    if choice == "q" or not choice:
        print(info("已取消"))
        return 0, 0

    if choice == "all":
        return download_all(auto_confirm=True)

    # 解析选择
    try:
        indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
        selected = []
        for idx in indices:
            if 1 <= idx <= len(users):
                selected.append(users[idx - 1])
            else:
                print(warning(f"无效的序号: {idx}"))

        if not selected:
            print(error("没有有效的选择"))
            return 0, 0

        print()
        print(info(f"已选择 {len(selected)} 个博主"))

        success_count = 0
        failed_count = 0

        for i, user in enumerate(selected, 1):
            uid = user.get("uid")
            name = user.get("nickname", user.get("name", "未知"))

            print()
            print(info(f"[{i}/{len(selected)}] 下载: {name}"))

            ok = download_by_uid(uid)
            if ok:
                success_count += 1
            else:
                failed_count += 1

        print()
        print(success(f"下载完成: 成功 {success_count}，失败 {failed_count}"))
        return success_count, failed_count

    except ValueError:
        print(error("无效的输入，请输入数字"))
        return 0, 0


def download_sample(auto_confirm=False):
    """
    采样下载：每个博主只下载1个视频，用于快速更新统计数据

    Args:
        auto_confirm: 是否跳过确认

    Returns:
        (success_count, failed_count) 元组
    """
    print_header("采样下载")

    users = list_users()
    if not users:
        print(info("关注列表为空"))
        return 0, 0

    print(info(f"每个博主只下载 1 个视频"))
    print(info(f"共 {len(users)} 位博主"))
    print()

    if not auto_confirm:
        confirm = input("确认开始？(y/N): ").strip().lower()
        if confirm != "y":
            print(info("已取消"))
            return 0, 0

    success_count = 0
    failed_count = 0

    for i, user in enumerate(users, 1):
        uid = user.get("uid")
        name = user.get("nickname", user.get("name", "未知"))

        print(info(f"[{i}/{len(users)}] 采样: {name}"))

        ok = download_by_uid(uid, max_counts=1)
        if ok:
            success_count += 1
        else:
            failed_count += 1

    print()
    print(success(f"采样完成: 成功 {success_count}，失败 {failed_count}"))
    return success_count, failed_count
