from __future__ import annotations

import subprocess


def _wait_for_key() -> None:
    try:
        input("按回车继续...")
    except (KeyboardInterrupt, EOFError):
        return


def cmd_check_updates() -> None:
    from media_tools.douyin.core.update_checker import check_all_updates

    result = check_all_updates() or {}
    total_new = int(result.get("total_new") or 0)
    if total_new <= 0:
        print("已是最新")
    else:
        print(f"发现更新: {total_new} 个新视频")
    _wait_for_key()


def cmd_download_updates() -> None:
    from media_tools.douyin.core.update_checker import check_all_updates

    result = check_all_updates() or {}
    total_new = int(result.get("total_new") or 0)
    if total_new <= 0:
        print("已是最新")
        _wait_for_key()
        return
    try:
        confirm = input("发现新视频，是否下载? (y/n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("取消")
        return
    if confirm not in {"y", "yes"}:
        print("取消")
        _wait_for_key()
        return
    print("开始下载...")
    _wait_for_key()


def cmd_download_menu() -> None:
    print("视频下载")
    try:
        url = input("请输入链接: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("取消")
        return
    if not url:
        print("取消")
        _wait_for_key()
        return
    from media_tools.douyin.core.downloader import download_by_url

    try:
        download_by_url(url, None, False, True)
        print("开始下载")
    except Exception as exc:
        print(f"下载失败: {exc}")
    _wait_for_key()
