from __future__ import annotations


def _wait_for_key() -> None:
    try:
        input("按回车继续...")
    except (KeyboardInterrupt, EOFError):
        return


def cmd_generate_data() -> None:
    from media_tools.douyin.core.data_generator import generate_data

    generate_data()
    _wait_for_key()
