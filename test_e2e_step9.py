#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤9: 重新下载所有视频
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.core.downloader import download_by_uid

UID = "1921577119390755"

def test_step9_redownload():
    """步骤9: 重新下载所有视频"""
    print("=" * 60)
    print("步骤9: 重新下载所有视频(验证清理后可以重新下载)")
    print("=" * 60)
    print()
    
    # 下载该博主的所有视频(max_counts=1只下载1个用于测试)
    success = download_by_uid(UID, max_counts=1)
    
    if success:
        print(f"\n✅ 重新下载成功!")
    else:
        print(f"\n❌ 重新下载失败")
    
    return success

if __name__ == "__main__":
    try:
        success = test_step9_redownload()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
