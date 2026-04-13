#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Media Tools CLI V2 - 场景化菜单布局

改进点：
1. 菜单按场景分组（快速开始/高级功能/设置管理）
2. 首次使用自动启动配置向导
3. 整合统计面板和配置预设
4. 更清晰的菜单结构，降低认知负荷
"""

import os
import sys
from pathlib import Path

# 切换到项目根目录
PROJECT_DIR = Path(__file__).parent.resolve()
os.chdir(PROJECT_DIR)

# 添加路径
sys.path.insert(0, str(PROJECT_DIR))


def check_and_run_wizard():
    """智能检测并自动配置"""
    from src.media_tools.wizard import check_first_run, mark_config_initialized
    from src.media_tools.config_presets import apply_preset

    if check_first_run():
        print("\n" + "="*60)
        print("🎉 欢迎使用 Media Tools！首次启动自动配置中...")
        print("="*60)

        # 1. 自动运行环境检测
        print("\n🔍 自动检测环境...")
        try:
            from scripts.core.env_check import check_all
            all_passed, _ = check_all()
            if all_passed:
                print("✅ 环境检测通过")
            else:
                print("⚠️  环境检测有问题，请查看上方提示")
        except Exception as e:
            print(f"⚠️  环境检测跳过: {e}")

        # 2. 自动应用新手预设
        print("\n⚙️  自动应用基础配置...")
        apply_preset("beginner", auto_apply=True)

        # 3. 标记配置完成
        mark_config_initialized()

        print("\n" + "="*60)
        print("✅ 配置完成！进入主菜单...")
        print("="*60 + "\n")
        return True

    return False


def main_menu_v2():
    """场景化版主菜单"""
    from scripts.core.ui import (
        bold, header, info, print_header, separator,
        success, warning, error
    )

    # 首次使用检测
    wizard_ran = check_and_run_wizard()

    while True:
        # 显示统计摘要（如果已有数据）
        _show_quick_stats()

        print_header("🎬 Media Tools 创作助手")
        print()
        print("  ━━ 🚀 快速开始 ━━")
        print(f"  {bold('1')}. 📎 一键转写（输入链接 → 输出文稿）")
        print(f"  {bold('2')}. 👥 批量处理（从关注列表）")
        print()
        print("  ━━ 🛠️  高级功能 ━━")
        print(f"  {bold('3')}. 📥 视频下载（单博主/全量/选择）")
        print(f"  {bold('4')}. 🎙️  单文件转写（本地视频/音频）")
        print(f"  {bold('5')}. 🗜️  视频压缩")
        print(f"  {bold('6')}. 📊 数据看板 & 统计")
        print()
        print("  ━━ ⚙️  设置与管理 ━━")
        print(f"  {bold('7')}. 🔑 账号认证（抖音/Qwen）")
        print(f"  {bold('8')}. ⚙️  配置中心")
        print(f"  {bold('9')}. 👤 关注列表管理")
        print(f"  {bold('10')}. 🗑️  数据清理")
        print()
        print(f"  {bold('0')}. 退出程序")
        print()

        try:
            choice = input("请输入选项 (0-10): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print(success("感谢使用，再见！"))
            return

        if choice == "0":
            print()
            print(success("感谢使用，再见！"))
            print()
            return
        elif choice == "1":
            cmd_quick_transcribe()
        elif choice == "2":
            cmd_batch_process()
        elif choice == "3":
            cmd_video_download()
        elif choice == "4":
            cmd_single_transcribe()
        elif choice == "5":
            cmd_video_compress()
        elif choice == "6":
            cmd_data_dashboard()
        elif choice == "7":
            cmd_account_auth()
        elif choice == "8":
            cmd_config_center()
        elif choice == "9":
            cmd_following_management()
        elif choice == "10":
            cmd_data_cleanup()
        else:
            print()
            print(warning("⚠️  无效的选项，请重新选择"))
            print()


def _show_quick_stats():
    """显示快速统计（如果有数据）"""
    from src.media_tools.stats_panel import StatsCollector

    collector = StatsCollector()
    summary = collector.get_summary()

    if summary["total_downloads"] > 0 or summary["total_transcribes"] > 0:
        from scripts.core.ui import dim
        print()
        print(dim("  📊 本月统计:"))
        print(dim(f"     📥 下载 {summary['total_downloads']} 个 | 📝 转写 {summary['total_transcribes']} 篇 | ⏱️  节省约 {summary['estimated_hours_saved']} 小时"))
        print()


def cmd_quick_transcribe():
    """快速转写：输入链接直接下载+转写"""
    from scripts.core.ui import info, error, success, warning

    print()
    print(info("📎 一键转写：输入抖音视频链接，自动下载并转写\n"))

    try:
        url = input("请粘贴抖音链接: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if not url:
        print(warning("未输入链接"))
        _wait_for_key()
        return

    print()
    print(info("开始处理..."))

    try:
        # 步骤1：下载
        from scripts.core.downloader import download_by_url
        print("\n📥 步骤 1/2: 下载视频...")
        result = download_by_url(url, max_counts=1)

        if not result:
            print(error("❌ 下载失败"))
            _wait_for_key()
            return

        # 步骤2：转写
        print("\n🎙️  步骤 2/2: 开始转写...")
        from pathlib import Path
        from scripts.core.config_mgr import get_config
        config = get_config()
        downloads_dir = config.get_download_path()

        video_files = list(downloads_dir.rglob("*.mp4"))
        if not video_files:
            print(error("❌ 未找到下载的视频文件"))
            _wait_for_key()
            return

        latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
        print(f"\n找到视频: {latest_video.name}")

        from src.media_tools.pipeline.orchestrator_v2 import run_enhanced_pipeline
        import asyncio

        async def _run():
            return await run_enhanced_pipeline(
                video_paths=[latest_video],
                on_progress=lambda c, t, p, s: print(f"  [{c}/{t}] {s}"),
            )

        report = asyncio.run(_run())

        if report.success_count > 0:
            print(f"\n{success('✅ 转写成功！')}")
            print(f"文稿: {report.video_details[0].export_path}")

            # 记录统计
            from src.media_tools.stats_panel import StatsCollector
            collector = StatsCollector()
            collector.record_transcribe(word_count=0)
        else:
            print(f"\n{error('❌ 转写失败')}")
            if report.error_summary:
                for err_type, count in report.error_summary.items():
                    print(f"  - {err_type}: {count} 次")

    except Exception as e:
        print(f"\n{error(f'❌ 处理过程出错: {e}')}")

    print()
    _wait_for_key()


def cmd_batch_process():
    """批量处理：从关注列表批量下载转写"""
    from scripts.core.ui import info, error, success, warning
    from src.media_tools.douyin.core.following_mgr import display_users

    print()
    users = display_users()
    if not users:
        print(warning("⚠️  关注列表为空，请先添加博主"))
        _wait_for_key()
        return

    print(info(f"\n发现 {len(users)} 位关注的博主\n"))

    try:
        confirm = input("是否批量处理所有博主？(y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return

    if confirm != 'y':
        return

    # 使用增强版Pipeline处理
    print("\n🔄 开始批量处理...\n")

    try:
        from scripts.core.downloader import download_by_uid
        from pathlib import Path
        from src.media_tools.pipeline.orchestrator_v2 import (
            EnhancedOrchestrator,
            BatchReport,
            print_enhanced_summary,
        )
        import asyncio

        all_videos = []
        total_users = len(users)

        # 遍历所有博主
        for i, user in enumerate(users, 1):
            uid = user["uid"]
            name = user.get("name", uid)

            print(f"\n{'='*60}")
            print(f"[{i}/{total_users}] 📥 {name}")
            print(f"{'='*60}")

            # 下载
            try:
                result = download_by_uid(uid, max_counts=5)
                if not result:
                    print(f"  ⚠️  下载失败，跳过")
                    continue
            except Exception as e:
                print(f"  ❌ 下载出错: {e}")
                continue

            # 查找视频文件
            from scripts.core.config_mgr import get_config
            config = get_config()
            downloads_dir = config.get_download_path()
            user_dir = downloads_dir / name

            if not user_dir.exists():
                user_dir = downloads_dir / uid

            if user_dir.exists():
                videos = list(user_dir.glob("*.mp4"))
                if videos:
                    all_videos.extend(videos)
                    print(f"  ✓ 找到 {len(videos)} 个视频")
                else:
                    print(f"  ⚠️  未找到视频")
            else:
                print(f"  ⚠️  未找到下载目录")

        # 批量转写
        if all_videos:
            print(f"\n🎙️  开始批量转写 {len(all_videos)} 个视频...\n")

            async def _run_batch():
                orchestrator = EnhancedOrchestrator()
                return await orchestrator.transcribe_batch(all_videos)

            report = asyncio.run(_run_batch())
            print_enhanced_summary(report)

            # 记录统计
            from src.media_tools.stats_panel import StatsCollector
            collector = StatsCollector()
            collector.record_transcribe(word_count=0)
        else:
            print(warning("\n⚠️  未找到任何视频文件"))

    except Exception as e:
        print(f"\n{error(f'❌ 批量处理出错: {e}')}")

    print()
    _wait_for_key()


def cmd_video_download():
    """视频下载"""
    from scripts.core.ui import bold, warning

    while True:
        print()
        print("="*60)
        print("📥 视频下载")
        print("="*60)
        print(f"  {bold('1')}. 下载单个博主（输入 URL）")
        print(f"  {bold('2')}. 从关注列表选择下载")
        print(f"  {bold('3')}. 下载所有关注（全量下载）")
        print(f"  {bold('4')}. 采样下载（每个博主1个视频）")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "0":
            return
        elif choice == "1":
            from cli import _cmd_download_by_url
            _cmd_download_by_url()
        elif choice == "2":
            from cli import _cmd_download_select
            _cmd_download_select()
        elif choice == "3":
            from cli import _cmd_download_all
            _cmd_download_all()
        elif choice == "4":
            from cli import _cmd_download_sample
            _cmd_download_sample()
        else:
            print(warning("无效的选项，请重新选择"))


def cmd_single_transcribe():
    """单文件转写"""
    from scripts.core.ui import info, error, success
    from pathlib import Path
    import asyncio

    print()
    print(info("🎙️  单文件转写：选择本地视频/音频文件\n"))

    try:
        file_path = input("请输入文件路径 (支持拖拽): ").strip().strip('"').strip("'")
    except (EOFError, KeyboardInterrupt):
        return

    if not file_path:
        print(error("未输入文件路径"))
        _wait_for_key()
        return

    video_file = Path(file_path)
    if not video_file.exists():
        print(error(f"文件不存在: {video_file}"))
        _wait_for_key()
        return

    print("\n开始转写...")

    try:
        async def _run():
            from src.media_tools.pipeline.orchestrator_v2 import run_enhanced_pipeline
            return await run_enhanced_pipeline(
                video_paths=[video_file],
                on_progress=lambda c, t, p, s: print(f"  [{c}/{t}] {s}"),
            )

        report = asyncio.run(_run())

        if report.success_count > 0:
            print(f"\n{success('✅ 转写成功！')}")
            print(f"文稿: {report.video_details[0].export_path}")
        else:
            print(f"\n{error('❌ 转写失败')}")

    except Exception as e:
        print(f"\n{error(f'❌ 转写出错: {e}')}")

    print()
    _wait_for_key()


def cmd_video_compress():
    """视频压缩"""
    from cli import cmd_compress
    cmd_compress()


def cmd_data_dashboard():
    """数据看板和统计"""
    from scripts.core.ui import bold, warning

    while True:
        print()
        print("="*60)
        print("📊 数据看板 & 统计")
        print("="*60)
        print(f"  {bold('1')}. 📈 查看使用统计")
        print(f"  {bold('2')}. 🌐 生成 Web 数据看板")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-2): ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "0":
            return
        elif choice == "1":
            from src.media_tools.stats_panel import display_stats_panel
            display_stats_panel()
            _wait_for_key()
        elif choice == "2":
            from cli import cmd_generate_data
            cmd_generate_data()
        else:
            print(warning("无效的选项，请重新选择"))


def cmd_account_auth():
    """账号认证"""
    from scripts.core.ui import bold, warning

    while True:
        print()
        print("="*60)
        print("🔑 账号认证")
        print("="*60)
        print(f"  {bold('1')}. 📱 抖音扫码登录")
        print(f"  {bold('2')}. 🤖 Qwen AI 认证")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-2): ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "0":
            return
        elif choice == "1":
            from cli import cmd_login
            cmd_login()
        elif choice == "2":
            from cli import cmd_transcribe_auth
            cmd_transcribe_auth()
        else:
            print(warning("无效的选项，请重新选择"))


def cmd_config_center():
    """配置中心"""
    from scripts.core.ui import bold, info, success, warning

    while True:
        print()
        print("="*60)
        print("⚙️  配置中心")
        print("="*60)
        print(f"  {bold('1')}. 📋 查看当前配置预设")
        print(f"  {bold('2')}. 🔄 切换配置预设")
        print(f"  {bold('3')}. ⚙️  Pipeline 配置")
        print(f"  {bold('4')}. 🔍 环境检测")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "0":
            return
        elif choice == "1":
            from src.media_tools.config_presets import show_current_preset
            show_current_preset()
            _wait_for_key()
        elif choice == "2":
            from src.media_tools.config_presets import interactive_preset_wizard
            interactive_preset_wizard()
            _wait_for_key()
        elif choice == "3":
            from cli import cmd_pipeline_config
            cmd_pipeline_config()
        elif choice == "4":
            from cli import cmd_env_check
            cmd_env_check()
        else:
            print(warning("无效的选项，请重新选择"))


def cmd_following_management():
    """关注列表管理"""
    from cli import cmd_following_menu
    cmd_following_menu()


def cmd_data_cleanup():
    """数据清理"""
    from cli import cmd_clean_data
    cmd_clean_data()


def _wait_for_key():
    """等待用户按键"""
    try:
        input("\n按回车键继续...")
    except (EOFError, KeyboardInterrupt):
        pass


def main():
    """CLI V2 主入口"""
    main_menu_v2()


if __name__ == "__main__":
    main()
