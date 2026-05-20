#!/usr/bin/env python3
"""B站下载诊断脚本：直接用 yt-dlp 测试你的视频链接"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from media_tools.platform.bilibili import download_up_by_url
from media_tools.bilibili.core.url_parser import normalize_bilibili_url

url = sys.argv[1] if len(sys.argv) > 1 else input("请输入B站视频链接: ").strip()
if not url:
    print("错误: 未提供链接")
    sys.exit(1)

print(f"\n{'='*60}")
print(f"测试链接: {url}")
print(f"{'='*60}")

normalized = normalize_bilibili_url(url)
print(f"解析结果: kind={normalized.kind.value}, bvid={normalized.bvid}, mid={normalized.mid}")

print(f"\n开始下载 (skip_existing=False)...")
try:
    result = download_up_by_url(url, max_counts=1, skip_existing=False, task_id=None)
    print(f"\n{'='*60}")
    print(f"结果:")
    print(f"  success: {result.get('success')}")
    print(f"  new_files: {result.get('new_files', [])}")
    print(f"  uploader: {result.get('uploader')}")
    if result.get('error'):
        print(f"  error: {result.get('error')}")
    print(f"{'='*60}")

    if not result.get('new_files'):
        print("\n诊断: new_files 为空，可能原因:")
        print("  1. 视频被删除或不可访问")
        print("  2. 需要大会员才能观看")
        print("  3. 地区限制")
        print("  4. B站 Cookie 已过期")
        print("  5. 视频是番剧/电影等受版权保护内容")
except Exception as e:
    print(f"\n异常: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
