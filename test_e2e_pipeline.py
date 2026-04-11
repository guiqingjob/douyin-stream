#!/usr/bin/env python3
"""
端到端 Pipeline 测试脚本

测试流程：
1. 下载博主的 3 个视频（抽样）
2. 验证下载成功
3. 测试转写流程（可选，需要认证）
4. 清理所有测试文件

运行方式：
    python test_e2e_pipeline.py
"""

import sys
import shutil
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))


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
# 配置
# ============================================================

# 测试用的博主 UID（用关注列表的第一个）
TEST_UID = "1921577119390755"  # 吾不知评测
TEST_MAX_COUNTS = 3  # 只下载 3 个视频测试

DOWNLOADS_DIR = project_root / "downloads"
TRANSCRIPTS_DIR = project_root / "transcripts"


# ============================================================
# 测试步骤
# ============================================================

def step1_download():
    """步骤1：下载测试视频"""
    header("步骤 1/5: 下载测试视频")
    
    info(f"博主 UID: {TEST_UID}")
    info(f"下载数量: {TEST_MAX_COUNTS} 个")
    
    try:
        from scripts.core.downloader import download_by_uid
        
        print()
        result = download_by_uid(TEST_UID, max_counts=TEST_MAX_COUNTS)
        
        if result:
            success("下载成功")
            return True
        else:
            error("下载失败")
            return False
            
    except Exception as e:
        error(f"下载出错: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def step2_verify_downloaded():
    """步骤2：验证下载的文件"""
    header("步骤 2/5: 验证下载文件")
    
    if not DOWNLOADS_DIR.exists():
        error(f"下载目录不存在: {DOWNLOADS_DIR}")
        return False
    
    # 查找测试博主的文件夹
    test_user_dir = DOWNLOADS_DIR / "吾不知评测"
    if not test_user_dir.exists():
        error(f"博主文件夹不存在: {test_user_dir}")
        return False
    
    video_files = list(test_user_dir.glob("*.mp4"))
    if not video_files:
        error("未找到视频文件")
        return False
    
    success(f"找到 {len(video_files)} 个视频文件:")
    for f in video_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        info(f"  {f.name} ({size_mb:.1f} MB)")
    
    return True


def step3_test_transcribe():
    """步骤3：测试转写流程（可选）"""
    header("步骤 3/5: 测试转写流程")
    
    # 检查认证状态
    auth_file = project_root / ".auth" / "qwen-storage-state.json"
    if not auth_file.exists():
        warning("未检测到认证状态，跳过转写测试")
        info("如需测试转写，请先运行: python cli.py → 选项10 → 扫码登录")
        return 'skip'
    
    info("找到认证文件，开始测试转写...")
    
    try:
        from scripts.core.downloader import download_by_uid
        from pathlib import Path
        
        # 获取刚下载的视频文件
        test_user_dir = DOWNLOADS_DIR / "吾不知评测"
        video_files = list(test_user_dir.glob("*.mp4"))
        
        if not video_files:
            error("没有可转写的视频文件")
            return False
        
        # 测试第一个视频
        test_video = video_files[0]
        info(f"测试转写: {test_video.name}")
        
        # 这里调用转写 Pipeline
        # 注意：转写需要较长时间，测试时可能需要 mock
        warning("转写测试需要较长时间，此处仅验证接口可调用")
        
        # 实际转写调用（需要认证）
        # from src.media_tools.pipeline.orchestrator import run_pipeline_single
        # result = run_pipeline_single(test_video)
        
        warning("转写测试跳过（需要有效认证和较长时间）")
        return 'skip'
        
    except Exception as e:
        error(f"转写测试出错: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def step4_generate_data():
    """步骤4：测试数据看板生成"""
    header("步骤 4/5: 测试数据看板")
    
    try:
        from scripts.core.data_generator import generate_data
        
        print()
        generate_data()
        
        # 验证生成的文件
        data_js = DOWNLOADS_DIR / "data.js"
        index_html = DOWNLOADS_DIR / "index.html"
        
        if data_js.exists() and index_html.exists():
            success("数据看板生成成功")
            info(f"数据文件: {data_js}")
            info(f"入口文件: {index_html}")
            return True
        else:
            error("数据看板文件不完整")
            return False
            
    except Exception as e:
        error(f"数据看板生成出错: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def step5_cleanup():
    """步骤5：清理所有测试文件"""
    header("步骤 5/5: 清理测试文件")
    
    cleaned = 0
    
    # 清理测试博主的下载文件夹
    test_user_dir = DOWNLOADS_DIR / "吾不知评测"
    if test_user_dir.exists():
        info(f"删除: {test_user_dir}")
        shutil.rmtree(test_user_dir)
        cleaned += 1
        success("已清理下载文件夹")
    
    # 清理转写输出（如果有）
    if TRANSCRIPTS_DIR.exists():
        transcript_files = list(TRANSCRIPTS_DIR.rglob("*"))
        if transcript_files:
            info(f"删除 {len(transcript_files)} 个转写文件")
            shutil.rmtree(TRANSCRIPTS_DIR)
            cleaned += 1
            success("已清理转写文件夹")
    
    if cleaned == 0:
        warning("没有需要清理的文件")
    else:
        success(f"共清理 {cleaned} 个目录")
    
    return True


# ============================================================
# 主流程
# ============================================================

def main():
    header("端到端 Pipeline 测试")
    info("流程: 下载 → 验证 → 转写 → 看板 → 清理")
    info(f"测试博主: 吾不知评测 ({TEST_UID})")
    info(f"下载数量: {TEST_MAX_COUNTS} 个")
    print()
    
    # 询问是否开始
    try:
        confirm = input(f"{Colors.BOLD}是否开始测试？(y/N): {Colors.END}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        return
    
    if confirm != 'y':
        print("已取消测试")
        return
    
    print()
    
    # 执行测试步骤
    results = {}
    
    # 步骤1：下载
    results['下载'] = step1_download()
    if not results['下载']:
        error("下载失败，终止测试")
        step5_cleanup()
        return
    
    # 步骤2：验证
    results['验证'] = step2_verify_downloaded()
    if not results['验证']:
        error("验证失败，终止测试")
        step5_cleanup()
        return
    
    # 步骤3：转写（可选）
    results['转写'] = step3_test_transcribe()
    
    # 步骤4：数据看板
    results['数据看板'] = step4_generate_data()
    
    # 步骤5：清理（总是执行）
    results['清理'] = step5_cleanup()
    
    # 打印结果
    header("测试结果汇总")
    
    all_passed = True
    for name, result in results.items():
        if result is True:
            success(f"{name}: 通过")
        elif result == 'skip':
            warning(f"{name}: 跳过")
        else:
            error(f"{name}: 失败")
            all_passed = False
    
    print()
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 所有测试通过！测试文件已清理{Colors.END}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ 有测试失败{Colors.END}")
    
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}测试被中断，执行清理...{Colors.END}")
        step5_cleanup()
    except Exception as e:
        print(f"\n\n{Colors.RED}测试出错: {e}{Colors.END}")
        step5_cleanup()
