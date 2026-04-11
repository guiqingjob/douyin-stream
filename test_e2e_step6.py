#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤6: 清理已删除视频的数据库记录
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.core.cleaner import clean_deleted_videos

def test_step6_clean():
    """步骤6: 清理已删除视频记录"""
    print("=" * 60)
    print("步骤6: 清理已删除视频的数据库记录")
    print("=" * 60)
    print()
    
    # 自动确认清理
    cleaned, skipped = clean_deleted_videos(auto_confirm=True)
    
    print(f"\n清理结果: 已清理 {cleaned} 条, 跳过 {skipped} 条")
    return cleaned > 0

if __name__ == "__main__":
    try:
        success = test_step6_clean()
        if success:
            print("\n✅ 清理功能正常")
        else:
            print("\n⚠️  没有需要清理的记录")
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
