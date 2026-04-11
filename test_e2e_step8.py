#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤8: 清理该博主所有数据库记录
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.core.cleaner import clean_all_user_data

UID = "1921577119390755"
USER_NAME = "吾不知评测"

def test_step8_clean_all():
    """步骤8: 清理博主所有数据"""
    print("=" * 60)
    print("步骤8: 清理博主所有数据库记录(为重新下载做准备)")
    print("=" * 60)
    print()
    
    success = clean_all_user_data(UID, USER_NAME)
    
    if success:
        print(f"\n✅ 已清理 {USER_NAME} 的所有数据库记录")
    else:
        print(f"\n❌ 清理失败")
    
    return success

if __name__ == "__main__":
    try:
        success = test_step8_clean_all()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
