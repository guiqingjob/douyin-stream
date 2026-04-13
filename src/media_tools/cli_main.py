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




def check_and_run_wizard():
    """智能检测并自动配置"""
    from media_tools.wizard import check_first_run, mark_config_initialized
    from media_tools.config_presets import apply_preset

    if check_first_run():
        print("\n" + "="*60)
        print("🎉 欢迎使用 Media Tools！首次启动自动配置中...")
        print("="*60)

        # 1. 自动运行环境检测
        print("\n🔍 自动检测环境...")
        try:
            from media_tools.douyin.core.env_check import check_all
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
    from media_tools.douyin.core.ui import (
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
    from media_tools.stats_panel import StatsCollector

    collector = StatsCollector()
    summary = collector.get_summary()

    if summary["total_downloads"] > 0 or summary["total_transcribes"] > 0:
        from media_tools.douyin.core.ui import dim
        print()
        print(dim("  📊 本月统计:"))
        print(dim(f"     📥 下载 {summary['total_downloads']} 个 | 📝 转写 {summary['total_transcribes']} 篇 | ⏱️  节省约 {summary['estimated_hours_saved']} 小时"))
        print()


def cmd_quick_transcribe():
    """快速转写：输入链接直接下载+转写"""
    from media_tools.douyin.core.ui import info, error, success, warning

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
        from media_tools.douyin.core.downloader import download_by_url
        print("\n📥 步骤 1/2: 下载视频...")
        result = download_by_url(url, max_counts=1)

        if not result:
            print(error("❌ 下载失败"))
            _wait_for_key()
            return

        # 步骤2：转写
        print("\n🎙️  步骤 2/2: 开始转写...")
        from pathlib import Path
        from media_tools.douyin.core.config_mgr import get_config
        config = get_config()
        downloads_dir = config.get_download_path()

        video_files = list(downloads_dir.rglob("*.mp4"))
        if not video_files:
            print(error("❌ 未找到下载的视频文件"))
            _wait_for_key()
            return

        latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
        print(f"\n找到视频: {latest_video.name}")

        from media_tools.pipeline.orchestrator_v2 import run_enhanced_pipeline
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
            from media_tools.stats_panel import StatsCollector
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
    from media_tools.douyin.core.ui import info, error, success, warning
    from media_tools.douyin.core.following_mgr import display_users

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
        from media_tools.douyin.core.downloader import download_by_uid
        from pathlib import Path
        from media_tools.pipeline.orchestrator_v2 import (
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
            from media_tools.douyin.core.config_mgr import get_config
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
            from media_tools.stats_panel import StatsCollector
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
    from media_tools.douyin.core.ui import bold, warning

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
            _cmd_download_by_url()
        elif choice == "2":
            _cmd_download_select()
        elif choice == "3":
            _cmd_download_all()
        elif choice == "4":
            _cmd_download_sample()
        else:
            print(warning("无效的选项，请重新选择"))


def cmd_single_transcribe():
    """单文件转写"""
    from media_tools.douyin.core.ui import info, error, success
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
            from media_tools.pipeline.orchestrator_v2 import run_enhanced_pipeline
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
    cmd_compress()


def cmd_data_dashboard():
    """数据看板和统计"""
    from media_tools.douyin.core.ui import bold, warning

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
            from media_tools.stats_panel import display_stats_panel
            display_stats_panel()
            _wait_for_key()
        elif choice == "2":
            cmd_generate_data()
        else:
            print(warning("无效的选项，请重新选择"))


def cmd_account_auth():
    """账号认证"""
    from media_tools.douyin.core.ui import bold, warning

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
            cmd_login()
        elif choice == "2":
            cmd_transcribe_auth()
        else:
            print(warning("无效的选项，请重新选择"))


def cmd_config_center():
    """配置中心"""
    from media_tools.douyin.core.ui import bold, info, success, warning

    while True:
        print()
        print("="*60)
        print("⚙️  配置中心")
        print("="*60)
        print(f"  {bold('1')}. 📋 交互式配置管理")
        print(f"  {bold('2')}. 👁️  查看当前配置预设")
        print(f"  {bold('3')}. 🔄 切换配置预设")
        print(f"  {bold('4')}. ⚙️  Pipeline 配置")
        print(f"  {bold('5')}. 🔍 环境检测")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-5): ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice == "0":
            return
        elif choice == "1":
            from media_tools.config_manager import ConfigManager
            manager = ConfigManager()
            manager.interactive_menu()
        elif choice == "2":
            from media_tools.config_presets import show_current_preset
            show_current_preset()
            _wait_for_key()
        elif choice == "3":
            from media_tools.config_presets import interactive_preset_wizard
            interactive_preset_wizard()
            _wait_for_key()
        elif choice == "4":
            cmd_pipeline_config()
        elif choice == "5":
            cmd_env_check()
        else:
            print(warning("无效的选项，请重新选择"))


def cmd_following_management():
    """关注列表管理"""
    cmd_following_menu()


def cmd_data_cleanup():
    """数据清理"""
    cmd_clean_data()


def _cmd_download_by_url():
    """通过 URL 下载"""
    from media_tools.douyin.core.downloader import download_by_url
    from media_tools.douyin.core.ui import info
    from urllib.parse import urlparse, parse_qs

    print()
    try:
        url_input = input("请粘贴抖音链接: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not url_input:
        return

    # 自动转换 URL 格式
    if '/jingxuan' in url_input:
        # 解析 modal_id 并转换成标准视频 URL
        parsed = urlparse(url_input)
        params = parse_qs(parsed.query)
        modal_id = params.get('modal_id', [None])[0]
        if modal_id:
            url = f"https://www.douyin.com/video/{modal_id}"
            print(info(f"自动转换: {url}"))
        else:
            print(info("输入不是完整 URL，尝试作为 sec_user_id 处理..."))
            url = f"https://www.douyin.com/user/{url_input}"
    elif not url_input.startswith("http"):
        print(info("检测到输入不是完整 URL，自动补全..."))
        url = f"https://www.douyin.com/user/{url_input}"
    else:
        url = url_input

    try:
        max_counts_input = input("最大下载数量（直接回车表示不限制）: ").strip()
        max_counts = int(max_counts_input) if max_counts_input.isdigit() else None
    except (EOFError, KeyboardInterrupt):
        max_counts = None

    result = download_by_url(url, max_counts)
    
    # 检查是否开启全自动模式
    if isinstance(result, dict) and result.get('success'):
        try:
            from media_tools.douyin.core.downloader import _trigger_auto_transcribe
            from media_tools.douyin.core.config_mgr import get_config
            config = get_config()
            if config.is_auto_transcribe():
                _trigger_auto_transcribe(result['uid'], result['nickname'])
        except Exception as e:
            print(f"⚠️  自动转写触发失败: {e}")
            
    print()
    _wait_for_key()


def _cmd_download_select():
    """交互式选择下载"""
    from media_tools.douyin.core.downloader import interactive_select

    print()
    interactive_select()
    print()
    _wait_for_key()


def _cmd_download_all():
    """全量下载"""
    from media_tools.douyin.core.downloader import download_all

    print()
    download_all()
    print()
    _wait_for_key()


def _cmd_download_sample():
    """采样下载"""
    from media_tools.douyin.core.downloader import download_sample

    print()
    download_sample()
    print()
    _wait_for_key()

def cmd_compress():
    """视频压缩"""
    from media_tools.douyin.core.compressor import compress_all

    print()
    try:
        crf_input = input("压缩质量 CRF (0-51，默认32，越小质量越好): ").strip()
        crf = int(crf_input) if crf_input.isdigit() else 32
        if crf < 0:
            crf = 0
            print("CRF 值过小，已调整为 0")
        elif crf > 51:
            crf = 51
            print("CRF 值过大，已调整为 51")
    except (EOFError, KeyboardInterrupt):
        crf = 32

    try:
        preset_input = input(
            "压缩速度 (ultrafast/fast/medium/slow，默认fast): "
        ).strip().lower()
        preset = preset_input if preset_input in ["ultrafast", "fast", "medium", "slow"] else "fast"
    except (EOFError, KeyboardInterrupt):
        preset = "fast"

    try:
        replace_input = input("是否直接替换原文件？(Y/n): ").strip().lower()
        replace = replace_input != "n"
    except (EOFError, KeyboardInterrupt):
        replace = True

    compress_all(crf=crf, preset=preset, replace=replace)
    print()
    _wait_for_key()

def cmd_generate_data():
    """生成数据看板"""
    from media_tools.douyin.core.data_generator import generate_data

    print()
    generate_data()
    print()
    _wait_for_key()

def cmd_login():
    """登录认证"""
    from media_tools.douyin.core.auth import login_sync
    from media_tools.douyin.core.ui import error, success

    print()
    try:
        persist_input = input("是否启用持久化模式？(y/N): ").strip().lower()
        persist = persist_input == "y"
    except (EOFError, KeyboardInterrupt):
        persist = False
    
    success_flag, msg = login_sync(persist=persist)

    if success_flag:
        print(success("登录认证成功！"))
    else:
        print(error(f"登录失败: {msg or '未知错误'}"))
    
    _wait_for_key()

def cmd_transcribe_auth():
    """转写认证管理"""
    from media_tools.douyin.core.ui import bold, print_header, warning

    while True:
        print_header("🔑 转写认证管理")
        print(f"  {bold('1')}. 浏览器扫码登录")
        print(f"  {bold('2')}. 检查认证状态")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-2): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "0":
            return
        elif choice == "1":
            print()
            print("正在启动浏览器进行认证...")
            try:
                import asyncio
                from media_tools.transcribe.cli.auth import run
                asyncio.run(run(argv=[]))
            except Exception as e:
                print(f"\n❌ 认证失败: {e}")
            _wait_for_key()
        elif choice == "2":
            print()
            try:
                from media_tools.transcribe.auth_state import has_qwen_auth_state
                if has_qwen_auth_state():
                    print("✅ Qwen 认证已就绪（已检测到有效认证状态）")
                else:
                    print("❌ 未检测到有效的 Qwen 认证，请重新扫码登录或重新粘贴 Cookie")
            except Exception as e:
                print(f"❌ 检查状态失败: {e}")
            _wait_for_key()
        else:
            print()
            print(warning("无效的选项，请重新选择"))

def cmd_pipeline_config():
    """Pipeline 配置"""
    from media_tools.douyin.core.ui import bold, info, print_header, warning, success, error
    from media_tools.pipeline.config import load_pipeline_config
    import os

    while True:
        config = load_pipeline_config()
        
        print_header("🔄 Pipeline 配置")
        print()
        print(f"  当前配置:")
        print(f"  {bold('1')}. 导出后删除云端记录: {'是' if config.delete_after_export else '否'}")
        print(f"  {bold('2')}. 转写后删除本地视频: {'是' if config.remove_video and not config.keep_original else '否'}")
        print(f"  {bold('3')}. 保留原始文件: {'是' if config.keep_original else '否'}")
        print(f"  {bold('4')}. 并发数: {config.concurrency}")
        print()
        print(f"  {bold('0')}. 返回上级菜单")
        print()

        try:
            choice = input("请选择要修改的配置 (0-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "0":
            return
        elif choice == "1":
            current = config.delete_after_export
            new_val = input(f"  导出后删除云端记录 (当前: {'是' if current else '否'}), 输入 是/否: ").strip()
            if new_val in ['是', 'yes', 'y', 'true', '1']:
                os.environ["PIPELINE_DELETE_AFTER_EXPORT"] = "true"
                print(success("✅ 已设置: 导出后删除云端记录"))
            elif new_val in ['否', 'no', 'n', 'false', '0']:
                os.environ["PIPELINE_DELETE_AFTER_EXPORT"] = "false"
                print(success("✅ 已设置: 导出后保留云端记录"))
            else:
                print(warning("输入无效，请重新选择"))
        elif choice == "2":
            current = config.remove_video and not config.keep_original
            new_val = input(f"  转写后删除本地视频 (当前: {'是' if current else '否'}), 输入 是/否: ").strip()
            if new_val in ['是', 'yes', 'y', 'true', '1']:
                os.environ["PIPELINE_REMOVE_VIDEO"] = "true"
                os.environ["PIPELINE_KEEP_ORIGINAL"] = "false"
                print(success("✅ 已设置: 转写后删除本地视频"))
            elif new_val in ['否', 'no', 'n', 'false', '0']:
                os.environ["PIPELINE_REMOVE_VIDEO"] = "false"
                os.environ["PIPELINE_KEEP_ORIGINAL"] = "true"
                print(success("✅ 已设置: 转写后保留本地视频"))
            else:
                print(warning("输入无效，请重新选择"))
        elif choice == "3":
            current = config.keep_original
            new_val = input(f"  保留原始文件 (当前: {'是' if current else '否'}), 输入 是/否: ").strip()
            if new_val in ['是', 'yes', 'y', 'true', '1']:
                os.environ["PIPELINE_KEEP_ORIGINAL"] = "true"
                print(success("✅ 已设置: 保留原始文件"))
            elif new_val in ['否', 'no', 'n', 'false', '0']:
                os.environ["PIPELINE_KEEP_ORIGINAL"] = "false"
                print(success("✅ 已设置: 不保留原始文件"))
            else:
                print(warning("输入无效，请重新选择"))
        elif choice == "4":
            new_val = input(f"  并发数 (当前: {config.concurrency}), 输入数字: ").strip()
            if new_val.isdigit() and int(new_val) > 0:
                os.environ["PIPELINE_CONCURRENCY"] = new_val
                print(success(f"✅ 已设置: 并发数 = {new_val}"))
            else:
                print(warning("请输入有效的数字"))
        else:
            print(warning("无效的选项，请重新选择"))
        
        print()
        _wait_for_key()

def cmd_env_check():
    """环境检测"""
    from media_tools.douyin.core.env_check import check_all

    print()
    all_passed, _ = check_all()
    _wait_for_key()

def cmd_following_menu():
    """关注列表管理子菜单"""
    from media_tools.douyin.core.ui import bold, info, print_header, warning

    while True:
        print_header("关注列表管理")
        print(f"  {bold('1')}. 查看关注列表")
        print(f"  {bold('2')}. 添加博主链接")
        print(f"  {bold('3')}. 移除博主")
        print(f"  {bold('4')}. 批量导入")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "0":
            return
        elif choice == "1":
            from media_tools.douyin.core.following_mgr import display_users
            print()
            display_users()
            print()
            _wait_for_key()
        elif choice == "2":
            from media_tools.douyin.core.following_mgr import add_user
            print()
            try:
                url = input("请粘贴抖音主页链接: ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if not url:
                return
            add_user(url)
            print()
            _wait_for_key()
        elif choice == "3":
            from media_tools.douyin.core.following_mgr import display_users, remove_user
            print()
            users = display_users()
            if not users:
                _wait_for_key()
                return
            print()
            try:
                uid = input("请输入要移除的博主 UID: ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if not uid:
                return
            try:
                delete_local = (
                    input("是否同时删除本地视频文件？(y/N): ").strip().lower() == "y"
                )
            except (EOFError, KeyboardInterrupt):
                delete_local = False
            remove_user(uid, delete_local=delete_local)
            print()
            _wait_for_key()
        elif choice == "4":
            from media_tools.douyin.core.following_mgr import batch_add_urls
            print()
            print("请粘贴多个抖音主页 URL（逗号、空格或换行分隔，输入空行结束）")
            print()
            lines = []
            while True:
                try:
                    line = input()
                    if not line.strip():
                        break
                    lines.append(line)
                except EOFError:
                    break
            all_text = " ".join(lines)
            urls = [u.strip() for u in all_text.replace(",", " ").split() if u.strip()]
            if not urls:
                print("未检测到有效的 URL")
                _wait_for_key()
                return
            batch_add_urls(urls)
            print()
            _wait_for_key()
        else:
            print()
            print(warning("无效的选项，请重新选择"))

def cmd_clean_data():
    """数据清理"""
    from media_tools.douyin.core.cleaner import interactive_clean_menu

    print()
    interactive_clean_menu()
    print()

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
