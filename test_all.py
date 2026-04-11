#!/usr/bin/env python3
"""
全功能测试脚本

测试内容：
1. 模块导入测试
2. CLI 路由测试
3. 配置加载测试
4. 核心功能测试
"""

import sys
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

passed = 0
failed = 0
warnings = 0

def test(name, func):
    global passed, failed, warnings
    try:
        result = func()
        if result == 'skip':
            print(f"  {Colors.YELLOW}⚠️  SKIP{Colors.END}  {name}")
            warnings += 1
        elif result is True:
            print(f"  {Colors.GREEN}✅ PASS{Colors.END}  {name}")
            passed += 1
        else:
            print(f"  {Colors.RED}❌ FAIL{Colors.END}  {name}")
            failed += 1
    except Exception as e:
        print(f"  {Colors.RED}❌ FAIL{Colors.END}  {name} - {e}")
        failed += 1

def header(title):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}  {title}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")

# ============================================================
# 1. 模块导入测试
# ============================================================
header("1. 模块导入测试")

def test_douyin_ui():
    from scripts.core.ui import bold, header
    return True
test("抖音 UI 模块", test_douyin_ui)

def test_douyin_downloader():
    from scripts.core.downloader import download_by_url
    return True
test("抖音下载模块", test_douyin_downloader)

def test_douyin_following():
    from scripts.core.following_mgr import display_users
    return True
test("抖音关注管理模块", test_douyin_following)

def test_douyin_compressor():
    from scripts.core.compressor import compress_all
    return True
test("抖音视频压缩模块", test_douyin_compressor)

def test_douyin_data_gen():
    from scripts.core.data_generator import generate_data
    return True
test("抖音数据看板模块", test_douyin_data_gen)

def test_douyin_cleaner():
    from scripts.core.cleaner import interactive_clean_menu
    return True
test("抖音数据清理模块", test_douyin_cleaner)

def test_douyin_env_check():
    from scripts.core.env_check import check_all
    return True
test("抖音环境检测模块", test_douyin_env_check)

def test_douyin_auth():
    from scripts.core.auth import login_sync
    return True
test("抖音认证模块", test_douyin_auth)

# 转写模块
def test_transcribe_flow():
    from src.media_tools.transcribe.flow import run_real_flow
    return True
test("转写核心流程模块", test_transcribe_flow)

def test_transcribe_config():
    from src.media_tools.transcribe.config import load_config
    return True
test("转写配置模块", test_transcribe_config)

def test_transcribe_cli_main():
    from src.media_tools.transcribe.cli.main import main
    return True
test("转写 CLI 主模块", test_transcribe_cli_main)

def test_transcribe_cli_run():
    from src.media_tools.transcribe.cli.run_api import run
    return True
test("转写 CLI run 命令", test_transcribe_cli_run)

def test_transcribe_cli_batch():
    from src.media_tools.transcribe.cli.run_batch import run
    return True
test("转写 CLI batch 命令", test_transcribe_cli_batch)

def test_transcribe_cli_auth():
    from src.media_tools.transcribe.cli.auth import run
    return True
test("转写 CLI auth 命令", test_transcribe_cli_auth)

def test_transcribe_cli_accounts():
    from src.media_tools.transcribe.cli.accounts_status import run
    return True
test("转写 CLI accounts 命令", test_transcribe_cli_accounts)

def test_transcribe_cli_quota():
    from src.media_tools.transcribe.cli.claim_needed import run
    return True
test("转写 CLI quota 命令", test_transcribe_cli_quota)

# Pipeline 模块
def test_pipeline_orchestrator():
    from src.media_tools.pipeline.orchestrator import run_pipeline_single
    return True
test("Pipeline 编排模块", test_pipeline_orchestrator)

def test_pipeline_config():
    from src.media_tools.pipeline.config import load_pipeline_config
    return True
test("Pipeline 配置模块", test_pipeline_config)

# 主 CLI
def test_main_cli():
    import cli
    return True
test("主 CLI 模块", test_main_cli)

# ============================================================
# 2. CLI 路由测试
# ============================================================
header("2. CLI 路由测试")

def test_main_menu_exists():
    import cli
    return hasattr(cli, 'main_menu')
test("主菜单函数存在", test_main_menu_exists)

def test_pipeline_menu_exists():
    import cli
    return hasattr(cli, 'cmd_pipeline_menu')
test("Pipeline 菜单函数存在", test_pipeline_menu_exists)

def test_transcribe_run_exists():
    import cli
    return hasattr(cli, 'cmd_transcribe_run')
test("转写 run 函数存在", test_transcribe_run_exists)

def test_transcribe_batch_exists():
    import cli
    return hasattr(cli, 'cmd_transcribe_batch')
test("转写 batch 函数存在", test_transcribe_batch_exists)

def test_transcribe_auth_exists():
    import cli
    return hasattr(cli, 'cmd_transcribe_auth')
test("转写认证函数存在", test_transcribe_auth_exists)

def test_transcribe_accounts_exists():
    import cli
    return hasattr(cli, 'cmd_transcribe_accounts')
test("转写账号函数存在", test_transcribe_accounts_exists)

# ============================================================
# 3. 配置加载测试
# ============================================================
header("3. 配置加载测试")

def test_douyin_config():
    from pathlib import Path
    config = Path("config/config.yaml")
    return config.exists() or Path("config/config.yaml.example").exists()
test("抖音配置文件存在", test_douyin_config)

def test_following_json():
    from pathlib import Path
    return Path("config/following.json").exists() or Path("config/following.json.example").exists()
test("关注列表文件存在", test_following_json)

def test_transcribe_env_example():
    from pathlib import Path
    return Path("config/transcribe/.env.example").exists()
test("转写环境变量模板存在", test_transcribe_env_example)

def test_transcribe_accounts_example():
    from pathlib import Path
    return Path("config/transcribe/accounts.example.json").exists()
test("转写账号配置模板存在", test_transcribe_accounts_example)

def test_auth_dir():
    from pathlib import Path
    return Path(".auth").exists()
test(".auth 目录存在", test_auth_dir)

# ============================================================
# 4. 核心功能测试
# ============================================================
header("4. 核心功能测试")

def test_ui_output():
    from scripts.core.ui import bold
    return "test" in bold("test")
test("UI 输出功能", test_ui_output)

def test_pipeline_config_load():
    from src.media_tools.pipeline.config import load_pipeline_config
    config = load_pipeline_config()
    return config.export_format in ["md", "docx"]
test("Pipeline 配置加载", test_pipeline_config_load)

def test_transcribe_runtime():
    from src.media_tools.transcribe.runtime import now_stamp, guess_mime_type
    stamp = now_stamp()
    mime = guess_mime_type("test.mp4")
    return len(stamp) > 0 and mime == "video/mp4"
test("转写运行时功能", test_transcribe_runtime)

def test_pipeline_result():
    from src.media_tools.pipeline.orchestrator import PipelineResult
    from pathlib import Path
    r = PipelineResult(success=True, video_path=Path("test.mp4"), transcript_path=Path("test.md"))
    return r.success and "转写成功" in str(r)
test("Pipeline 结果对象", test_pipeline_result)

# ============================================================
# 5. 文档测试
# ============================================================
header("5. 文档测试")

def test_plan_md():
    return Path("PLAN.md").exists()
test("PLAN.md 存在", test_plan_md)

def test_deliverables_md():
    return Path("DELIVERABLES.md").exists()
test("DELIVERABLES.md 存在", test_deliverables_md)

def test_features_md():
    return Path("FEATURES.md").exists()
test("FEATURES.md 存在", test_features_md)

def test_readme_md():
    return Path("README.md").exists()
test("README.md 存在", test_readme_md)

# ============================================================
# 6. 测试文件测试
# ============================================================
header("6. 测试文件检查")

def test_tests_dir():
    tests = Path("tests")
    return tests.exists() and len(list(tests.glob("*.py"))) >= 10
test("测试文件数量 >= 10", test_tests_dir)

# ============================================================
# 打印结果
# ============================================================
print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
print(f"{Colors.BOLD}  测试结果汇总{Colors.END}")
print(f"{Colors.BOLD}{'='*60}{Colors.END}")
print(f"  {Colors.GREEN}✅ 通过: {passed}{Colors.END}")
print(f"  {Colors.RED}❌ 失败: {failed}{Colors.END}")
print(f"  {Colors.YELLOW}⚠️  跳过: {warnings}{Colors.END}")
print(f"  {Colors.BLUE}📊 总计: {passed + failed + warnings}{Colors.END}")
print(f"{Colors.BOLD}{'='*60}{Colors.END}")

if failed == 0:
    print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 所有测试通过！{Colors.END}")
    sys.exit(0)
else:
    print(f"\n{Colors.RED}{Colors.BOLD}❌ 有 {failed} 个测试失败{Colors.END}")
    sys.exit(1)
