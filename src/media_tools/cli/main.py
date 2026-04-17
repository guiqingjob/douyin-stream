from __future__ import annotations

from media_tools.cli.data import cmd_generate_data
from media_tools.cli.download import cmd_check_updates, cmd_download_menu, cmd_download_updates
from media_tools.cli.following import cmd_following_menu
from media_tools.cli.system import cmd_clean_data, cmd_system_settings
from media_tools.cli.transcribe import (
    cmd_transcribe_accounts,
    cmd_transcribe_auth,
    cmd_transcribe_batch,
    cmd_transcribe_run,
)


def _check_updates_on_startup() -> None:
    return


def cmd_pipeline_menu() -> None:
    from media_tools.pipeline.orchestrator_v2 import run_pipeline_interactive

    run_pipeline_interactive()


def _print_menu() -> None:
    print("抖音功能")
    print("1 检查更新")
    print("2 下载更新")
    print("3 关注管理")
    print("4 视频下载")
    print("5 Pipeline")
    print("6 数据看板")
    print("转写功能")
    print("7 单文件转写")
    print("8 批量转写")
    print("9 转写认证")
    print("10 账号状态")
    print("系统设置")
    print("11 系统设置")
    print("12 数据清理")
    print("0 退出")


def main_menu() -> None:
    _check_updates_on_startup()
    while True:
        _print_menu()
        try:
            choice = input("请选择: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("感谢使用")
            return

        if choice == "0":
            print("感谢使用")
            return
        if choice == "1":
            cmd_check_updates()
            continue
        if choice == "2":
            cmd_download_updates()
            continue
        if choice == "3":
            cmd_following_menu()
            continue
        if choice == "4":
            cmd_download_menu()
            continue
        if choice == "5":
            cmd_pipeline_menu()
            continue
        if choice == "6":
            cmd_generate_data()
            continue
        if choice == "7":
            cmd_transcribe_run()
            continue
        if choice == "8":
            cmd_transcribe_batch()
            continue
        if choice == "9":
            cmd_transcribe_auth()
            continue
        if choice == "10":
            cmd_transcribe_accounts()
            continue
        if choice == "11":
            cmd_system_settings()
            continue
        if choice == "12":
            cmd_clean_data()
            continue

        if not choice:
            print("无效")
            continue
        print("无效")
