#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试清理功能
"""

import sqlite3
import tempfile
from pathlib import Path
import sys

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from scripts.core.cleaner import clean_deleted_videos, scan_local_videos, get_db_video_records


def test_cleaner():
    """测试清理功能"""
    print("=" * 60)
    print("测试清理功能")
    print("=" * 60)

    # 1. 扫描本地视频
    print("\n1. 扫描本地视频...")
    local_data = scan_local_videos()
    print(f"   找到 {len(local_data)} 个本地用户目录")
    for uid, data in local_data.items():
        print(f"   - UID {uid}: {data['count']} 个视频")

    # 2. 获取数据库记录
    print("\n2. 获取数据库记录...")
    db_data = get_db_video_records()
    print(f"   找到 {len(db_data)} 个用户的数据库记录")
    for uid, data in db_data.items():
        print(f"   - UID {uid}: {len(data['aweme_ids'])} 条记录")

    # 3. 对比差异
    print("\n3. 对比差异...")
    for uid in db_data:
        if uid in local_data:
            db_count = len(db_data[uid]["aweme_ids"])
            local_count = local_data[uid]["count"]
            if db_count > local_count:
                print(f"   ⚠️  UID {uid}: 数据库 {db_count} 条，本地 {local_count} 个文件")
                print(f"      需要清理 {db_count - local_count} 条记录")
            elif db_count == local_count:
                print(f"   ✓  UID {uid}: 完全匹配")
            else:
                print(f"   ℹ️  UID {uid}: 数据库 {db_count} 条，本地 {local_count} 个文件（可能刚下载）")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        test_cleaner()
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
