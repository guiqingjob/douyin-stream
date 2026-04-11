#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤2: 采样下载 - 下载1个视频
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.core.downloader import download_sample

UID = "1921577119390755"

def test_step2_download_sample():
    """步骤2: 采样下载"""
    print("=" * 60)
    print("步骤2: 采样下载(下载1个视频)")
    print("=" * 60)
    print()
    
    # 采样下载会下载所有博主的1个视频
    success_count, failed_count = download_sample(auto_confirm=True)
    
    print(f"\n采样结果: 成功 {success_count}，失败 {failed_count}")
    return success_count > 0

if __name__ == "__main__":
    try:
        success = test_step2_download_sample()
        if success:
            print("\n✅ 采样下载完成")
        else:
            print("\n❌ 采样下载失败")
            sys.exit(1)
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
