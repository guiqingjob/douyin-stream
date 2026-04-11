#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端真实测试 - 完整流程测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.core.following_mgr import add_user, list_users, remove_user, display_users

TEST_URL = "https://www.douyin.com/user/MS4wLjABAAAAWwCl-EAHmume3ghXtpQGq9YRf7DyIfYQGOPAmZAkBgdZ4Oa-8HmljDs__0NQe4Gq?from_tab_name=main"

def test_step1_add_user():
    """步骤1: 添加博主"""
    print("=" * 60)
    print("步骤1: 添加测试博主到关注列表")
    print("=" * 60)
    print(f"URL: {TEST_URL}\n")
    
    success, user_info = add_user(TEST_URL)
    
    if success:
        print(f"\n✅ 添加成功!")
        print(f"   UID: {user_info.get('uid')}")
        print(f"   昵称: {user_info.get('nickname')}")
        return True, user_info
    else:
        print(f"\n❌ 添加失败")
        return False, None

if __name__ == "__main__":
    try:
        success, user_info = test_step1_add_user()
        if success:
            print("\n请查看上方输出确认博主已添加")
        else:
            print("\n测试失败")
            sys.exit(1)
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
