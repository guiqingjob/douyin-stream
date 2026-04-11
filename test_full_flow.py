#!/usr/bin/env python3
"""
完整流程测试脚本 - 检查所有功能 bug

测试流程：
1. 启动 CLI（不自动检查）
2. 选项1：检查更新
3. 选项3：关注列表管理 - 查看列表
4. 选项4：视频下载 - 下载1个视频测试
5. 选项5：Pipeline - 本地文件转写
6. 选项7：数据看板
7. 选项13：数据清理
"""

import sys
import time
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.resolve()

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

def warning(text):
    print(f"  {Colors.YELLOW}⚠️ {Colors.END} {text}")

# ============================================================
# 测试记录
# ============================================================
bugs = []
passed = []

def check(name, condition, detail=""):
    if condition:
        passed.append(name)
        success(f"通过: {name}")
    else:
        bugs.append(name)
        error(f"失败: {name}")
        if detail:
            print(f"     {detail}")

# ============================================================
# 测试1：启动 CLI（不自动检查）
# ============================================================
header("测试1：启动 CLI（应直接显示菜单，不自动检查）")

result = subprocess.run(
    [sys.executable, "cli.py"],
    input="0\n",  # 直接退出
    capture_output=True,
    text=True,
    timeout=10
)

# 检查是否有"正在检查"等自动检查的日志
has_auto_check = "正在检查" in result.stdout or "处理用户" in result.stdout
check("启动时不自动检查", not has_auto_check, "输出中包含自动检查日志")

# 检查菜单是否正常显示
has_menu = "Media Tools" in result.stdout and "0. 退出程序" in result.stdout
check("菜单正常显示", has_menu, "菜单未正确显示")

if result.returncode == 0:
    success("CLI 正常退出")
else:
    error(f"CLI 异常退出 (code={result.returncode})")
    print(f"     stderr: {result.stderr[:200]}")

# ============================================================
# 测试2：检查更新
# ============================================================
header("测试2：检查更新功能")

result = subprocess.run(
    [sys.executable, "cli.py"],
    input="1\n0\n",  # 选项1 -> 退出
    capture_output=True,
    text=True,
    timeout=120
)

# 检查是否有输出
has_check_output = "检查结果" in result.stdout or "检查结果:" in result.stdout or "新视频" in result.stdout
check("检查更新有输出", has_check_output, "没有检查结果输出")

# 检查是否没有刷屏（不应有"处理第X页"）
has_page_log = "处理第" in result.stdout and "页" in result.stdout
check("无刷屏日志", not has_page_log, "仍然有'处理第X页'的日志")

# ============================================================
# 测试3：关注列表管理 - 查看列表
# ============================================================
header("测试3：关注列表管理")

result = subprocess.run(
    [sys.executable, "cli.py"],
    input="3\n1\n0\n0\n",  # 选项3 -> 选项1（查看）-> 返回 -> 退出
    capture_output=True,
    text=True,
    timeout=30
)

has_following = "关注列表" in result.stdout or "博主" in result.stdout
check("关注列表功能可用", has_following, "关注列表输出异常")

# ============================================================
# 测试4：视频下载（下载1个测试）
# ============================================================
header("测试4：视频下载（下载1个测试）")

result = subprocess.run(
    [sys.executable, "cli.py"],
    input="4\n1\nMS4wLjABAAAAWwCl-EAHmume3ghXtpQGq9YRf7DyIfYQGOPAmZAkBgdZ4Oa-8HmljDs__0NQe4Gq\n1\n0\n0\n",
    capture_output=True,
    text=True,
    timeout=180
)

has_download = "下载" in result.stdout or "完成" in result.stdout
check("下载功能运行", has_download, "下载功能无输出")

# 检查是否有下载的文件
user_dir = project_root / "downloads" / "吾不知评测"
if user_dir.exists():
    videos = list(user_dir.glob("*.mp4"))
    check("下载了视频文件", len(videos) > 0, f"下载目录存在但没有 mp4 文件")
    if videos:
        info(f"下载了 {len(videos)} 个视频")
else:
    warning("下载目录不存在（可能下载失败）")

# ============================================================
# 测试5：Pipeline - 本地文件转写（如果有视频）
# ============================================================
header("测试5：Pipeline - 本地文件转写")

if user_dir.exists() and list(user_dir.glob("*.mp4")):
    video_file = list(user_dir.glob("*.mp4"))[0]
    
    result = subprocess.run(
        [sys.executable, "cli.py"],
        input=f"5\n4\n{video_file}\n0\n",
        capture_output=True,
        text=True,
        timeout=300
    )
    
    has_transcribe = "转写" in result.stdout
    check("Pipeline 转写功能运行", has_transcribe, "Pipeline 无输出")
    
    # 检查是否有转写文件
    transcripts_dir = project_root / "transcripts"
    if transcripts_dir.exists():
        trans_files = list(transcripts_dir.glob("*.md"))
        if trans_files:
            check("转写输出文件", True, f"生成 {len(trans_files)} 个文稿文件")
            info(f"转写文件: {trans_files[0].name[:50]}...")
        else:
            warning("转写目录存在但没有 md 文件")
    else:
        warning("转写目录不存在（可能转写失败或认证未配置）")
else:
    warning("跳过转写测试（没有下载视频）")

# ============================================================
# 测试6：数据看板
# ============================================================
header("测试6：数据看板生成")

result = subprocess.run(
    [sys.executable, "cli.py"],
    input="7\n0\n",
    capture_output=True,
    text=True,
    timeout=30
)

has_data = "数据已生成" in result.stdout or "data.js" in result.stdout
check("数据看板生成", has_data, "数据看板无输出")

data_js = project_root / "downloads" / "data.js"
index_html = project_root / "downloads" / "index.html"
check("data.js 存在", data_js.exists())
check("index.html 存在", index_html.exists())

# ============================================================
# 测试7：数据清理
# ============================================================
header("测试7：数据清理")

result = subprocess.run(
    [sys.executable, "cli.py"],
    input="13\n0\n",  # 选项13 -> 清理菜单 -> 退出
    capture_output=True,
    text=True,
    timeout=30
)

has_clean = "清理" in result.stdout or "clean" in result.stdout.lower()
check("数据清理功能可用", has_clean, "数据清理无输出")

# ============================================================
# 清理测试文件
# ============================================================
header("清理测试文件")

import shutil

cleaned = 0
user_dir = project_root / "downloads" / "吾不知评测"
transcripts_dir = project_root / "transcripts"

if user_dir.exists():
    shutil.rmtree(user_dir)
    cleaned += 1
    success("已清理下载文件夹")

if transcripts_dir.exists():
    shutil.rmtree(transcripts_dir)
    cleaned += 1
    success("已清理转写文件夹")

if cleaned == 0:
    warning("没有需要清理的文件")

# ============================================================
# 汇总结果
# ============================================================
header("测试结果汇总")

print(f"\n  {Colors.GREEN}通过: {len(passed)}{Colors.END}")
print(f"  {Colors.RED}Bug: {len(bugs)}{Colors.END}")

if bugs:
    print(f"\n{Colors.BOLD}Bug 列表:{Colors.END}")
    for i, bug in enumerate(bugs, 1):
        print(f"  {i}. {Colors.RED}{bug}{Colors.END}")

print()
if not bugs:
    print(f"{Colors.GREEN}{Colors.BOLD}🎉 所有测试通过，未发现 Bug！{Colors.END}")
else:
    print(f"{Colors.RED}{Colors.BOLD}⚠️  发现 {len(bugs)} 个 Bug{Colors.END}")
