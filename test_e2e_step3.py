#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤3: 检查更新 - 应该显示无更新
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.core.update_checker import check_all_updates

def test_step3_check_updates():
    """步骤3: 检查更新"""
    print("=" * 60)
    print("步骤3: 检查更新(应该显示无更新)")
    print("=" * 60)
    print()
    
    result = check_all_updates()
    
    print(f"\n总新视频数: {result['total_new']}")
    print(f"有更新的博主数: {result['has_updates_count']}")
    
    # 检查吾不知评测的状态
    for user in result['users']:
        if '吾不知' in user['name']:
            print(f"\n吾不知评测:")
            print(f"  本地: {user['local_count']} 个")
            print(f"  数据库: {user['db_count']} 个")
            print(f"  有更新: {user['has_update']}")
            print(f"  新视频: {user['new_count']} 个")
            
            return user['has_update'] == False
    
    return True

if __name__ == "__main__":
    try:
        success = test_step3_check_updates()
        if success:
            print("\n✅ 检查更新功能正常 - 显示无更新")
        else:
            print("\n❌ 检查更新功能异常 - 显示有更新")
            sys.exit(1)
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
