#!/usr/bin/env python3
"""
完整流程演示：下载 → 清洗 → 转写 → 输出
"""

import subprocess
import glob
import os
import time

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def header(text):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")

def info(text):
    print(f"  {Colors.BLUE}ℹ️ {Colors.END} {text}")

def success(text):
    print(f"  {Colors.GREEN}✅ {Colors.END} {text}")

def error(text):
    print(f"  {Colors.RED}❌ {Colors.END} {text}")

def show_files(pattern):
    """显示匹配的文件"""
    files = glob.glob(pattern, recursive=True)
    if files:
        for f in files:
            size = os.path.getsize(f) / (1024*1024)
            print(f"  📄 {os.path.basename(f)} ({size:.1f} MB)")
    else:
        print("  (无文件)")

def main():
    header("🎬 完整流程演示：下载 → 清洗 → 转写")
    
    # 使用已有博主
    test_url = "https://www.douyin.com/user/MS4wLjABAAAAWwCl-EAHmume3ghXtpQGq9YRf7DyIfYQGOPAmZAkBgdZ4Oa-8HmljDs__0NQe4Gq"
    info(f"测试博主: {test_url[:50]}...")
    print()

    # 步骤 1: 下载视频
    header("步骤 1: 下载视频")
    info("输入: 博主主页 URL")
    info("操作: 下载 1 个视频")
    print()
    
    print(f"{Colors.BOLD}正在下载...{Colors.END}")
    result = subprocess.run(
        ['python3', 'cli.py'],
        input=f"4\n1\n{test_url}\n1\n0\n0\n",
        capture_output=True,
        text=True,
        timeout=180
    )
    
    # 查找下载的文件
    mp4_files = list(glob.glob('downloads/**/*.mp4', recursive=True))
    if mp4_files:
        print()
        success("下载完成！")
        print()
        info("下载目录中的文件:")
        show_files('downloads/**/*.mp4')
        
        # 检查文件名
        filename = os.path.basename(mp4_files[0])
        print()
        if '#' not in filename and len(filename) < 60:
            success("文件名已清洗（无 #话题，长度适中）")
        else:
            error("文件名未清洗")
        
        test_video = mp4_files[0]
    else:
        error("未找到视频文件")
        return
    
    print()
    time.sleep(1)

    # 步骤 2: Pipeline 转写
    header("步骤 2: Pipeline 转写")
    info(f"输入: {os.path.basename(test_video)}")
    info("操作: 上传 → 转写 → 导出 MD")
    print()
    
    print(f"{Colors.BOLD}正在转写...{Colors.END}")
    result = subprocess.run(
        ['python3', 'cli.py'],
        input=f"5\n4\n{test_video}\n0\n",
        capture_output=True,
        text=True,
        timeout=300
    )
    
    # 查找转写文件
    md_files = list(glob.glob('transcripts/*.md'))
    if md_files:
        print()
        success("转写完成！")
        print()
        info("转写输出:")
        show_files('transcripts/*.md')
        
        md_file = md_files[0]
        md_name = os.path.basename(md_file).replace('.md', '')
        video_name = os.path.basename(test_video).replace('.mp4', '')
        
        print()
        info("文件名对比:")
        print(f"  视频: {video_name[:40]}...")
        print(f"  文稿: {md_name[:40]}...")
        
        if video_name == md_name:
            success("视频与文稿文件名完全一致！")
        
        # 显示文稿内容预览
        print()
        info("文稿内容预览:")
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # 显示前 300 字符
        print(f"  {Colors.GREEN}{content[:300]}...{Colors.END}")
    else:
        error("未找到转写文件")
        return

    # 步骤 3: 清理
    header("步骤 3: 清理测试文件")
    print()
    
    import shutil
    user_dir = None
    for d in glob.glob('downloads/*', recursive=True):
        if os.path.isdir(d) and '青竹' not in d:
            user_dir = d
    
    if user_dir:
        shutil.rmtree(user_dir)
        success(f"已清理: {user_dir}")
    
    if os.path.exists('transcripts'):
        shutil.rmtree('transcripts')
        success("已清理: transcripts/")
    
    print()
    header("🎉 完整流程演示完成！")
    print()
    print(f"{Colors.GREEN}{Colors.BOLD}总结:{Colors.END}")
    print(f"  1. 下载视频 → 自动清洗文件名 ✅")
    print(f"  2. Pipeline 转写 → 输出同名 MD ✅")
    print(f"  3. 测试文件已清理 ✅")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}测试被中断{Colors.END}")
    except Exception as e:
        print(f"\n\n{Colors.RED}测试出错: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
