from __future__ import annotations


def _wait_for_key() -> None:
    try:
        input("按回车继续...")
    except (KeyboardInterrupt, EOFError):
        return


def cmd_env_check() -> None:
    from media_tools.douyin.core.env_check import check_all

    check_all()


def cmd_login() -> None:
    print("扫码登录")


def cmd_pipeline_config() -> None:
    print("Pipeline 配置")


def cmd_config_manager() -> None:
    print("统一配置管理")


def cmd_clean_data() -> None:
    from media_tools.douyin.core.cleaner import interactive_clean_menu

    interactive_clean_menu()


def cmd_system_settings() -> None:
    while True:
        print("环境检测")
        print("扫码登录")
        print("Pipeline 配置")
        print("统一配置管理")
        print("返回主菜单")
        try:
            choice = input("请选择: ").strip()
        except (KeyboardInterrupt, EOFError):
            return
        if choice == "0":
            return
        if choice == "1":
            cmd_env_check()
            _wait_for_key()
            continue
        if choice == "2":
            cmd_login()
            _wait_for_key()
            continue
        if choice == "3":
            cmd_pipeline_config()
            _wait_for_key()
            continue
        if choice == "4":
            cmd_config_manager()
            _wait_for_key()
            continue
        print("无效")
