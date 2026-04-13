#!/usr/bin/env python3
"""后台下载+转写脚本"""
import sys
sys.path.insert(0, '.')

from scripts.core.downloader import download_by_uid
from scripts.core.ui import success, error, info

uid = '676898254629515'
print('='*60)
print('开始下载: 大厂洋姐职场咨询_求职陪跑')
print('='*60)
print()

try:
    download_by_uid(uid)
    print()
    print('='*60)
    print('✅ 任务完成')
    print('='*60)
except Exception as e:
    print()
    print('='*60)
    print(f'❌ 任务失败: {e}')
    print('='*60)
    import traceback
    traceback.print_exc()
