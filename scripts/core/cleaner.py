#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地清理模块 - 清理已删除视频的数据库记录

功能:
- 扫描本地视频文件
- 对比数据库记录
- 清理已删除视频的元数据
- 可选:清理整个博主的记录
"""

import sqlite3
from pathlib import Path

from .ui import (
    bold,
    error,
    info,
    print_header,
    print_status,
    separator,
    success,
    warning,
)
from .config_mgr import get_config
from .following_mgr import list_users


def scan_local_videos():
    """
    扫描本地所有视频文件

    Returns:
        dict: {uid: {video_files: set, folder: str}}
    """
    config = get_config()
    downloads_path = config.get_download_path()

    users = list_users()
    local_data = {}

    # 先构建uid到user的映射
    uid_to_user = {user.get("uid"): user for user in users}

    # 遍历下载目录下的所有子目录
    if not downloads_path.exists():
        return local_data

    try:
        for folder in downloads_path.iterdir():
            if not folder.is_dir():
                continue

            # 跳过非用户目录
            if folder.name in ["douyin", ".git", "__pycache__"]:
                continue

            folder_name = folder.name

            # 尝试匹配用户
            matched_uid = None
            
            # 方法1: 通过folder字段匹配
            for user in users:
                user_folder = user.get("folder")
                if user_folder and user_folder == folder_name:
                    matched_uid = user.get("uid")
                    break
            
            # 方法2: 如果没匹配到,尝试通过uid匹配
            if not matched_uid and folder_name.isdigit():
                if folder_name in uid_to_user:
                    matched_uid = folder_name
            
            # 方法3: 遍历所有用户,通过实际存在的目录匹配
            if not matched_uid:
                for uid, user in uid_to_user.items():
                    name = user.get("nickname", user.get("name", ""))
                    if name == folder_name or str(uid) == folder_name:
                        matched_uid = uid
                        break

            # 统计视频数量
            if matched_uid:
                try:
                    video_files = set(f.name for f in folder.glob("*.mp4"))
                    local_data[matched_uid] = {
                        "folder": folder_name,
                        "video_files": video_files,
                        "count": len(video_files),
                    }
                except (PermissionError, OSError):
                    local_data[matched_uid] = {
                        "folder": folder_name,
                        "video_files": set(),
                        "count": 0,
                    }

    except (PermissionError, OSError) as e:
        print(error(f"扫描目录失败: {e}"))
        return local_data

    return local_data


def get_db_video_records():
    """
    获取数据库中所有视频记录

    Returns:
        dict: {uid: {aweme_ids: set, records: list}}
    """
    config = get_config()
    db_path = config.get_db_path()

    if not db_path.exists():
        return {}

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT aweme_id, uid, desc, local_filename FROM video_metadata")
        rows = cursor.fetchall()

        db_data = {}
        for aweme_id, uid, desc, local_filename in rows:
            if uid not in db_data:
                db_data[uid] = {
                    "aweme_ids": set(),
                    "records": [],
                }
            db_data[uid]["aweme_ids"].add(aweme_id)
            db_data[uid]["records"].append({
                "aweme_id": aweme_id,
                "desc": desc,
                "local_filename": local_filename,
            })

        return db_data

    except Exception as e:
        print(error(f"数据库读取失败: {e}"))
        return {}
    finally:
        conn.close()


def clean_deleted_videos(auto_confirm=False):
    """
    清理已删除视频的数据库记录

    Args:
        auto_confirm: 是否自动确认

    Returns:
        (cleaned_count, skipped_count) 元组
    """
    print_header("🗑️  清理已删除视频记录")

    local_data = scan_local_videos()
    db_data = get_db_video_records()

    if not db_data:
        print(info("数据库中没有视频记录"))
        return 0, 0

    total_cleaned = 0
    total_skipped = 0

    for uid, db_info in db_data.items():
        db_aweme_ids = db_info["aweme_ids"]

        if uid not in local_data:
            # 用户不在本地，可能是：
            # 1. 还未添加该用户到关注列表
            # 2. 用户已被从关注列表移除但数据库还有记录
            # 这里跳过，不自动清理（保留历史数据）
            continue

        local_files = local_data[uid]["video_files"]
        db_count = len(db_aweme_ids)
        local_count = local_data[uid]["count"]

        if db_count > local_count:
            # 数据库记录比本地文件多，说明有视频被删除了
            deleted_count = db_count - local_count

            # 获取该用户的博主信息
            user_name = _get_user_name(uid)

            print()
            print(info(f"📝 {user_name} (UID: {uid})"))
            print(f"   数据库记录: {db_count} 个 | 本地文件: {local_count} 个")
            print(f"   需要清理: {bold(str(deleted_count))} 条记录")

            if not auto_confirm:
                confirm = input("   是否清理？(Y/n): ").strip().lower()
                if confirm == "n":
                    total_skipped += deleted_count
                    continue

            # 清理多余的数据库记录
            cleaned = _clean_user_videos(uid, deleted_count, db_info["records"], local_files)
            total_cleaned += cleaned
            print(success(f"   ✓ 已清理 {cleaned} 条记录"))
        elif db_count == local_count:
            # 完全匹配，无需清理
            pass
        else:
            # 本地文件比数据库多，可能是新下载但还没更新数据库
            # 这种情况下不应该清理，反而应该更新数据库
            pass

    print()
    print(separator("─", 60))
    print()
    print(bold("📊 清理结果:"))
    print(f"  已清理: {bold(str(total_cleaned))} 条记录")
    print(f"  已跳过: {bold(str(total_skipped))} 条记录")
    print()

    return total_cleaned, total_skipped


def _get_user_name(uid):
    """获取博主名称"""
    users = list_users()
    for user in users:
        if user.get("uid") == uid:
            return user.get("nickname", user.get("name", "未知"))
    return uid


def _clean_user_videos(uid, count_to_remove, db_records, local_files):
    """
    清理指定用户的多余视频记录

    Args:
        uid: 用户 UID
        count_to_remove: 要删除的记录数量
        db_records: 数据库记录列表
        local_files: 本地文件集合

    Returns:
        实际删除的记录数量
    """
    config = get_config()
    db_path = config.get_db_path()

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 优先删除本地不存在的文件对应的记录
        # 通过文件名匹配（假设local_filename字段存储了文件名）
        deleted = 0

        for record in db_records:
            if deleted >= count_to_remove:
                break

            aweme_id = record["aweme_id"]
            local_filename = record["local_filename"]

            # 如果本地文件名不在本地文件集合中，说明该记录对应的文件已被删除
            should_delete = False
            if local_filename and local_filename not in local_files:
                should_delete = True
            elif not local_filename:
                # 如果local_filename为空，我们也删除（无法判断对应文件）
                should_delete = True

            if should_delete:
                cursor.execute(
                    "DELETE FROM video_metadata WHERE aweme_id = ?",
                    (aweme_id,),
                )
                deleted += 1

        # 如果还是不够，继续删除剩余记录
        if deleted < count_to_remove:
            cursor.execute(
                "SELECT aweme_id FROM video_metadata WHERE uid = ? LIMIT ?",
                (uid, count_to_remove - deleted + 10),  # 多获取一些
            )
            remaining = [row[0] for row in cursor.fetchall()]

            for aweme_id in remaining:
                if deleted >= count_to_remove:
                    break
                cursor.execute(
                    "DELETE FROM video_metadata WHERE aweme_id = ?",
                    (aweme_id,),
                )
                deleted += 1

        conn.commit()

        return deleted

    except Exception as e:
        print(error(f"   清理失败: {e}"))
        return 0
    finally:
        conn.close()


def clean_all_user_data(uid, user_name):
    """
    清理指定用户的所有数据库记录（视频元数据和用户信息）

    Args:
        uid: 用户 UID
        user_name: 用户名称

    Returns:
        是否成功
    """
    config = get_config()
    db_path = config.get_db_path()

    if not db_path.exists():
        print(warning("数据库文件不存在"))
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 删除视频元数据
        cursor.execute("DELETE FROM video_metadata WHERE uid = ?", (uid,))
        video_deleted = cursor.rowcount

        # 删除用户信息
        cursor.execute("DELETE FROM user_info_web WHERE uid = ?", (uid,))
        user_deleted = cursor.rowcount

        conn.commit()

        print(success(f"  ✓ 已清理 {user_name} 的数据库记录"))
        print(f"    视频记录: {video_deleted} 条 | 用户信息: {user_deleted} 条")

        return True

    except Exception as e:
        print(error(f"  清理失败: {e}"))
        return False
    finally:
        conn.close()


def interactive_clean_menu():
    """交互式清理菜单"""
    while True:
        print_header("🗑️  数据清理工具")
        print(f"  {bold('1')}. 清理已删除视频的数据库记录")
        print(f"  {bold('2')}. 清理指定博主的所有数据库记录")
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
            clean_deleted_videos()
            input("按回车键继续...")
        elif choice == "2":
            _clean_single_user_interactive()
        else:
            print()
            print(warning("无效的选项，请重新选择"))


def _clean_single_user_interactive():
    """交互式清理单个用户"""
    users = list_users()
    if not users:
        print(info("关注列表为空"))
        input("按回车键继续...")
        return

    print()
    print(info("选择要清理的博主（输入序号，q=返回）"))
    print()

    for i, user in enumerate(users, 1):
        uid = user.get("uid", "未知")
        name = user.get("nickname", user.get("name", "未知"))
        print(f"  {i:2}. {name}")

    print()
    try:
        choice = input("请选择: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "q" or not choice:
        return

    try:
        idx = int(choice)
        if 1 <= idx <= len(users):
            user = users[idx - 1]
            uid = user.get("uid")
            name = user.get("nickname", user.get("name", "未知"))

            print()
            confirm = input(f"确认清理 {name} 的所有数据库记录？(y/N): ").strip().lower()
            if confirm == "y":
                clean_all_user_data(uid, name)
        else:
            print(warning("无效的序号"))
    except ValueError:
        print(error("无效的输入，请输入数字"))

    input("按回车键继续...")
