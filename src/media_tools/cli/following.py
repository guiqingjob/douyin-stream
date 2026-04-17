from __future__ import annotations


def _wait_for_key() -> None:
    try:
        input("按回车继续...")
    except (KeyboardInterrupt, EOFError):
        return


def cmd_following_menu() -> None:
    while True:
        print("查看关注列表")
        print("添加关注")
        print("删除关注")
        print("导出")
        print("导入")
        print("返回主菜单")
        try:
            choice = input("请选择: ").strip()
        except (KeyboardInterrupt, EOFError):
            return
        if choice == "0":
            return
        if choice == "1":
            from media_tools.douyin.core.following_mgr import display_users

            display_users()
            _wait_for_key()
            continue
        if choice == "2":
            try:
                url = input("请输入博主链接: ").strip()
            except (KeyboardInterrupt, EOFError):
                return
            if url:
                from media_tools.douyin.core.following_mgr import add_user

                add_user(url)
            _wait_for_key()
            continue
        if choice == "3":
            from media_tools.douyin.core.following_mgr import remove_user

            remove_user()
            _wait_for_key()
            continue
        if choice in {"4", "5"}:
            _wait_for_key()
            continue
        print("无效")
