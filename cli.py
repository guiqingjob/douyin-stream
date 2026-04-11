#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音下载管家 CLI - 统一交互式入口

用法:
    python cli.py

功能:
    交互式菜单，用户只需选择序号即可执行对应功能
"""

import os
import sys
from pathlib import Path

# 切换到脚本所在目录
SKILL_DIR = Path(__file__).parent.resolve()
os.chdir(SKILL_DIR)

# 添加 scripts 目录到路径
sys.path.insert(0, str(SKILL_DIR / "scripts"))


def main_menu():
    """主菜单"""
    from scripts.core.ui import (
        bold,
        header,
        info,
        print_header,
        separator,
        success,
        warning,
    )

    while True:
        print_header("🎬 Media Tools 媒体工具")
        print("  ━━ 抖音功能 ━━")
        print(f"  {bold('1')}. 🔍 检查博主更新")
        print(f"  {bold('2')}. 📥 下载所有更新")
        print(f"  {bold('3')}. 👤 关注列表管理")
        print(f"  {bold('4')}. 📺 视频下载")
        print(f"  {bold('5')}. 🔄 下载并自动转写（Pipeline）")
        print(f"  {bold('6')}. 🗜️  视频压缩")
        print(f"  {bold('7')}. 📊 生成数据看板")
        print()
        print("  ━━ 转写功能 ━━")
        print(f"  {bold('8')}. 🎙️  视频/音频转写")
        print(f"  {bold('9')}. 📂 批量转写")
        print(f"  {bold('10')}. 🔑 转写认证管理")
        print(f"  {bold('11')}. 📊 账号状态/配额")
        print()
        print("  ━━ 系统设置 ━━")
        print(f"  {bold('12')}. ⚙️  系统设置")
        print(f"  {bold('13')}. 🗑️  数据清理")
        print()
        print(f"  {bold('0')}. 退出程序")
        print()

        try:
            choice = input("请输入选项 (0-13): ").strip()
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
            cmd_check_updates()
        elif choice == "2":
            cmd_download_updates()
        elif choice == "3":
            cmd_following_menu()
        elif choice == "4":
            cmd_download_menu()
        elif choice == "5":
            cmd_pipeline_menu()
        elif choice == "6":
            cmd_compress()
        elif choice == "7":
            cmd_generate_data()
        elif choice == "8":
            cmd_transcribe_run()
        elif choice == "9":
            cmd_transcribe_batch()
        elif choice == "10":
            cmd_transcribe_auth()
        elif choice == "11":
            cmd_transcribe_accounts()
        elif choice == "12":
            cmd_system_settings()
        elif choice == "13":
            cmd_clean_data()
        else:
            print()
            print(warning("无效的选项，请重新选择"))
            print()


def _check_updates_on_startup():
    """启动时自动检查更新"""
    from scripts.core.update_checker import check_all_updates
    from scripts.core.ui import separator, dim

    try:
        result = check_all_updates()

        if result["has_updates_count"] > 0:
            print()
            print(dim(separator("─", 60)))
            print(f"  💡 提示: 有 {result['has_updates_count']} 位博主更新了内容")
            print(f"     选择 '2' 可快速下载所有更新")
            print(dim(separator("─", 60)))
            print()
        else:
            print()
            print("  ✓ 所有博主均为最新状态")
            print()

    except Exception as e:
        print()
        print(f"  ⚠️  检查更新时出错: {e}")
        print()


def cmd_check_updates():
    """检查更新"""
    from scripts.core.update_checker import check_all_updates

    print()
    check_all_updates()
    print()
    _wait_for_key()


def cmd_download_updates():
    """下载所有更新"""
    from scripts.core.update_checker import check_all_updates
    from scripts.core.downloader import download_by_uid
    from scripts.core.ui import info, success, error

    print()
    result = check_all_updates()

    if result["total_new"] == 0:
        print(info("✓ 所有博主均为最新，无需下载更新"))
        print()
        _wait_for_key()
        return

    print()
    confirm = input(f"确认下载 {result['total_new']} 个新视频？(y/N): ").strip().lower()
    if confirm != "y":
        print(info("已取消"))
        print()
        _wait_for_key()
        return

    success_count = 0
    failed_count = 0

    for user in result["users"]:
        if user["has_update"]:
            uid = user["uid"]
            name = user["name"]
            new_count = user["new_count"]

            print()
            print(info(f"下载: {name} ({new_count} 个新视频)"))
            ok = download_by_uid(uid)
            if ok:
                success_count += 1
            else:
                failed_count += 1

    print()
    print_header("更新下载完成")
    print(success(f"成功: {success_count} 位博主"))
    print(error(f"失败: {failed_count} 位博主"))
    print()
    _wait_for_key()


def cmd_system_settings():
    """系统设置子菜单"""
    from scripts.core.ui import bold, info, print_header, warning

    while True:
        print_header("⚙️  系统设置")
        print(f"  {bold('1')}. 🔍 环境检测与初始化")
        print(f"  {bold('2')}. 🔑 扫码登录获取 Cookie")
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
            cmd_env_check()
        elif choice == "2":
            cmd_login()
        else:
            print()
            print(warning("无效的选项，请重新选择"))


def cmd_env_check():
    """环境检测"""
    from scripts.core.env_check import check_all

    print()
    all_passed, _ = check_all()
    _wait_for_key()


def cmd_login():
    """登录认证"""
    from scripts.core.auth import login_sync

    print()
    try:
        persist_input = input("是否启用持久化模式？(y/N): ").strip().lower()
        persist = persist_input == "y"
    except (EOFError, KeyboardInterrupt):
        persist = False
    success_flag, _ = login_sync(persist=persist)

    if success_flag:
        _wait_for_key()


def cmd_following_menu():
    """关注列表管理子菜单"""
    from scripts.core.ui import bold, info, print_header, warning

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
            _cmd_list_users()
        elif choice == "2":
            _cmd_add_user()
        elif choice == "3":
            _cmd_remove_user()
        elif choice == "4":
            _cmd_batch_add()
        else:
            print()
            print(warning("无效的选项，请重新选择"))


def _cmd_list_users():
    """查看关注列表"""
    from scripts.core.following_mgr import display_users

    print()
    display_users()
    print()
    _wait_for_key()


def _cmd_add_user():
    """添加博主"""
    from scripts.core.following_mgr import add_user

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


def _cmd_remove_user():
    """移除博主"""
    from scripts.core.following_mgr import display_users, remove_user

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


def _cmd_batch_add():
    """批量导入"""
    from scripts.core.following_mgr import batch_add_urls

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


def cmd_download_menu():
    """视频下载子菜单"""
    from scripts.core.ui import bold, info, print_header, warning

    while True:
        print_header("视频下载")
        print(f"  {bold('1')}. 下载单个博主（输入 URL）")
        print(f"  {bold('2')}. 从关注列表选择下载")
        print(f"  {bold('3')}. 下载所有关注（全量下载）")
        print(f"  {bold('4')}. 采样下载（每个博主1个视频）")
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
            _cmd_download_by_url()
        elif choice == "2":
            _cmd_download_select()
        elif choice == "3":
            _cmd_download_all()
        elif choice == "4":
            _cmd_download_sample()
        else:
            print()
            print(warning("无效的选项，请重新选择"))


def _cmd_download_by_url():
    """通过 URL 下载"""
    from scripts.core.downloader import download_by_url
    from scripts.core.ui import info
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
            from scripts.core.downloader import _trigger_auto_transcribe
            from scripts.core.config_mgr import get_config
            config = get_config()
            if config.is_auto_transcribe():
                _trigger_auto_transcribe(result['uid'], result['nickname'])
        except Exception as e:
            print(f"⚠️  自动转写触发失败: {e}")
            
    print()
    _wait_for_key()


def _cmd_download_select():
    """交互式选择下载"""
    from scripts.core.downloader import interactive_select

    print()
    interactive_select()
    print()
    _wait_for_key()


def _cmd_download_all():
    """全量下载"""
    from scripts.core.downloader import download_all

    print()
    download_all()
    print()
    _wait_for_key()


def _cmd_download_sample():
    """采样下载"""
    from scripts.core.downloader import download_sample

    print()
    download_sample()
    print()
    _wait_for_key()


def cmd_compress():
    """视频压缩"""
    from scripts.core.compressor import compress_all

    print()
    try:
        crf_input = input("压缩质量 CRF (0-51，默认32，越小质量越好): ").strip()
        crf = int(crf_input) if crf_input.isdigit() else 32
        # CRF 范围校验
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
    from scripts.core.data_generator import generate_data

    print()
    generate_data()
    print()
    _wait_for_key()


def cmd_clean_data():
    """数据清理"""
    from scripts.core.cleaner import interactive_clean_menu

    print()
    interactive_clean_menu()
    print()


def cmd_pipeline_menu():
    """Pipeline 功能菜单"""
    from scripts.core.ui import bold, info, print_header, warning, error

    while True:
        print_header("🔄 下载并自动转写（Pipeline）")
        print("  自动流程：下载视频 → 上传转写 → 输出文稿")
        print()
        print(f"  {bold('1')}. 📎 输入抖音链接，下载并转写")
        print(f"  {bold('2')}. 👥 从关注列表批量下载并转写")
        print(f"  {bold('3')}. 🔄 同步模式（只处理新视频）")
        print(f"  {bold('4')}. 📂 指定本地视频文件转写")
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
            _cmd_pipeline_from_url()
        elif choice == "2":
            _cmd_pipeline_from_following()
        elif choice == "3":
            _cmd_pipeline_sync()
        elif choice == "4":
            _cmd_pipeline_from_file()
        else:
            print()
            print(warning("无效的选项，请重新选择"))


def _cmd_pipeline_from_url():
    """从 URL 下载并转写"""
    from scripts.core.downloader import download_by_url
    from pathlib import Path
    import glob as glob_module

    print()
    try:
        url = input("请粘贴抖音主页链接: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not url:
        return

    print()
    print("开始下载视频...")
    
    # 下载视频
    download_by_url(url, max_counts=1)
    
    # 查找最新下载的视频
    downloads_dir = Path("downloads")
    if not downloads_dir.exists():
        print(error("下载目录不存在"))
        _wait_for_key()
        return
    
    # 查找最新的 MP4 文件
    video_files = list(downloads_dir.rglob("*.mp4"))
    if not video_files:
        print(error("未找到下载的视频文件"))
        _wait_for_key()
        return
    
    # 按修改时间排序，取最新
    latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
    
    print(f"\n找到视频: {latest_video}")
    print("开始转写...")
    
    # 执行转写
    try:
        from src.media_tools.pipeline.orchestrator import run_pipeline_single
        result = run_pipeline_single(latest_video)
        
        if result.success:
            print(f"\n✅ 转写成功!")
            print(f"文稿: {result.transcript_path}")
        else:
            print(f"\n❌ 转写失败: {result.error}")
    except Exception as e:
        print(f"\n❌ 转写过程出错: {e}")
    
    print()
    _wait_for_key()


def _cmd_pipeline_from_following():
    """从关注列表批量下载并转写"""
    from scripts.core.following_mgr import display_users
    from scripts.core.downloader import download_by_uid
    from pathlib import Path
    import questionary

    print()
    users = display_users()
    if not users:
        print("关注列表为空，请先添加博主")
        _wait_for_key()
        return

    # 让用户选择处理方式
    choice = questionary.select(
        "选择处理方式:",
        choices=[
            f"全部关注 ({len(users)} 位博主)",
            *[f"{u['name']} ({u['uid']})" for u in users],
            "返回",
        ]
    ).ask()

    if choice == "返回":
        return
    
    print()
    
    # 询问每个博主下载数量
    try:
        count_input = input("每个博主最多下载几个视频？(直接回车=3个): ").strip()
        max_counts = int(count_input) if count_input.isdigit() else 3
    except (EOFError, KeyboardInterrupt):
        max_counts = 3
    
    print(f"\n开始批量下载并转写（每个博主最多 {max_counts} 个）...")
    print("=" * 60)
    
    # 确定要处理的博主
    if choice == f"全部关注 ({len(users)} 位博主)":
        target_users = users
    else:
        # 提取 UID
        uid = choice.split("(")[-1].rstrip(")")
        target_users = [u for u in users if u["uid"] == uid]
    
    total_downloaded = 0
    total_transcribed = 0
    total_errors = 0
    
    for i, user in enumerate(target_users, 1):
        uid = user["uid"]
        name = user.get("name", uid)
        
        print(f"\n{'='*60}")
        print(f"[{i}/{len(target_users)}] 处理: {name}")
        print(f"{'='*60}")
        
        # 步骤1：下载
        try:
            print(f"\n📥 下载视频（最多 {max_counts} 个）...")
            result = download_by_uid(uid, max_counts=max_counts)
            
            if not result:
                print(f"⚠️  {name} 下载失败，跳过")
                total_errors += 1
                continue
            
            total_downloaded += max_counts  # 约略计数
            
        except Exception as e:
            print(f"❌ {name} 下载出错: {e}")
            total_errors += 1
            continue
        
        # 步骤2：找到下载的视频并转写
        try:
            user_dir = Path("downloads") / name
            if not user_dir.exists():
                # 尝试用 UID 查找
                user_dir = Path("downloads") / uid
            
            if not user_dir.exists():
                print(f"⚠️  未找到 {name} 的下载目录")
                continue
            
            video_files = list(user_dir.glob("*.mp4"))
            if not video_files:
                print(f"⚠️  {name} 没有下载到视频")
                continue
            
            print(f"\n🎙️  转写 {len(video_files)} 个视频...")
            
            from src.media_tools.pipeline.orchestrator import run_pipeline_single
            
            for j, video in enumerate(video_files, 1):
                print(f"  [{j}/{len(video_files)}] {video.name[:50]}...")
                result = run_pipeline_single(video)
                
                if result.success:
                    total_transcribed += 1
                    print(f"  ✅ 成功: {result.transcript_path.name}")
                else:
                    total_errors += 1
                    print(f"  ❌ 失败: {result.error}")
        
        except Exception as e:
            print(f"❌ {name} 转写出错: {e}")
            total_errors += 1
    
    # 打印汇总
    print(f"\n{'='*60}")
    print(f"📊 批量 Pipeline 完成")
    print(f"{'='*60}")
    print(f"  处理博主: {len(target_users)} 位")
    print(f"  下载视频: ~{total_downloaded} 个")
    print(f"  转写成功: {total_transcribed} 个")
    print(f"  失败/跳过: {total_errors} 个")
    print(f"{'='*60}")
    
    print()
    _wait_for_key()


def _cmd_pipeline_sync():
    """同步模式：只处理新视频"""
    from scripts.core.update_checker import check_all_updates
    from scripts.core.downloader import download_by_uid
    from pathlib import Path
    from src.media_tools.pipeline.orchestrator import run_pipeline_single

    print()
    print("🔍 检查更新...")
    result = check_all_updates()

    if result["total_new"] == 0:
        print("✅ 所有博主均为最新，无需处理")
        _wait_for_key()
        return

    print(f"\n📊 发现 {result['total_new']} 个新视频")
    print(f"   涉及 {result['has_updates_count']} 位博主")
    print()
    
    # 确认是否处理
    try:
        confirm = input("是否下载并转写这些新视频？(y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    
    if confirm != 'y':
        print("已取消")
        _wait_for_key()
        return
    
    print("\n开始同步 Pipeline...")
    print("=" * 60)
    
    total_transcribed = 0
    total_errors = 0
    
    # 遍历有新视频的博主
    for user in result["users"]:
        if not user["has_update"]:
            continue
        
        uid = user["uid"]
        name = user["name"]
        new_count = user["new_count"]
        
        print(f"\n📥 {name}: {new_count} 个新视频")
        
        # 下载新视频（只下载新视频数量）
        try:
            download_by_uid(uid, max_counts=new_count)
            
            # 找到并转写新视频
            user_dir = Path("downloads") / name
            if user_dir.exists():
                # 按修改时间排序，取最新的 new_count 个
                video_files = sorted(user_dir.glob("*.mp4"), 
                                    key=lambda p: p.stat().st_mtime, 
                                    reverse=True)[:new_count]
                
                for video in video_files:
                    print(f"  🎙️  转写: {video.name[:50]}...")
                    result = run_pipeline_single(video)
                    
                    if result.success:
                        total_transcribed += 1
                        print(f"  ✅ {result.transcript_path.name}")
                    else:
                        total_errors += 1
                        print(f"  ❌ {result.error}")
        
        except Exception as e:
            print(f"  ❌ {name} 处理失败: {e}")
            total_errors += 1
    
    # 打印汇总
    print(f"\n{'='*60}")
    print(f"📊 同步完成")
    print(f"{'='*60}")
    print(f"  转写成功: {total_transcribed} 个")
    print(f"  失败: {total_errors} 个")
    print(f"{'='*60}")
    
    print()
    _wait_for_key()


def _cmd_pipeline_from_file():
    """转写本地视频文件"""
    from pathlib import Path
    import questionary

    print()
    try:
        file_path = input("请输入视频文件路径: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    
    if not file_path:
        return
    
    video = Path(file_path)
    if not video.exists():
        print(error(f"文件不存在: {video}"))
        _wait_for_key()
        return
    
    if not video.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv']:
        print(error("不支持的视频格式"))
        _wait_for_key()
        return
    
    print(f"\n开始转写: {video}")
    
    try:
        from src.media_tools.pipeline.orchestrator import run_pipeline_single
        result = run_pipeline_single(video)
        
        if result.success:
            print(f"\n✅ 转写成功!")
            print(f"文稿: {result.transcript_path}")
        else:
            print(f"\n❌ 转写失败: {result.error}")
    except Exception as e:
        print(f"\n❌ 转写过程出错: {e}")
        import traceback
        print(traceback.format_exc())
    
    print()
    _wait_for_key()


# ============================================================
# 转写功能命令
# ============================================================

def cmd_transcribe_run():
    """单文件转写"""
    import questionary
    from pathlib import Path

    print()
    try:
        file_path = questionary.path("请选择视频/音频文件: ").ask()
    except (EOFError, KeyboardInterrupt):
        return
    
    if not file_path:
        return
    
    video = Path(file_path)
    if not video.exists():
        print("❌ 文件不存在")
        _wait_for_key()
        return
    
    print(f"\n开始转写: {video.name}")
    print("=" * 50)
    
    try:
        import asyncio
        from src.media_tools.transcribe.cli.run_api import run
        asyncio.run(run(argv=[str(video)]))
    except Exception as e:
        print(f"\n❌ 转写过程出错: {e}")
        import traceback
        print(traceback.format_exc())
    
    print()
    _wait_for_key()


def cmd_transcribe_batch():
    """批量转写"""
    import questionary
    from pathlib import Path

    print()
    try:
        dir_path = questionary.path("请选择包含视频/音频的目录: ").ask()
    except (EOFError, KeyboardInterrupt):
        return
    
    if not dir_path:
        return
    
    target = Path(dir_path)
    if not target.is_dir():
        print("❌ 目录不存在")
        _wait_for_key()
        return
    
    print(f"\n开始批量转写: {target}")
    print("=" * 50)
    
    try:
        import asyncio
        from src.media_tools.transcribe.cli.run_batch import run
        asyncio.run(run(argv=[str(target)]))
    except Exception as e:
        print(f"\n❌ 批量转写过程出错: {e}")
        import traceback
        print(traceback.format_exc())
    
    print()
    _wait_for_key()


def cmd_transcribe_auth():
    """转写认证管理"""
    from scripts.core.ui import bold, print_header, warning

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
            _cmd_transcribe_auth_login()
        elif choice == "2":
            _cmd_transcribe_auth_check()
        else:
            print()
            print(warning("无效的选项，请重新选择"))


def _cmd_transcribe_auth_login():
    """浏览器扫码登录"""
    print()
    print("正在启动浏览器进行认证...")
    try:
        import asyncio
        from src.media_tools.transcribe.cli.auth import run
        asyncio.run(run(argv=[]))
    except Exception as e:
        print(f"\n❌ 认证失败: {e}")
    _wait_for_key()


def _cmd_transcribe_auth_check():
    """检查认证状态"""
    print()
    try:
        from pathlib import Path
        auth_path = Path(".auth/qwen-storage-state.json")
        if auth_path.exists():
            print("✅ 认证文件存在")
            print(f"路径: {auth_path.resolve()}")
        else:
            print("❌ 认证文件不存在")
            print("请先进行扫码登录")
    except Exception as e:
        print(f"❌ 检查状态失败: {e}")
    _wait_for_key()


def cmd_transcribe_accounts():
    """账号状态和配额管理"""
    from scripts.core.ui import bold, print_header, warning

    while True:
        print_header("📊 账号状态/配额")
        print(f"  {bold('1')}. 查看账号状态")
        print(f"  {bold('2')}. 查看配额")
        print(f"  {bold('3')}. 领取配额")
        print(f"  {bold('0')}. 返回主菜单")
        print()

        try:
            choice = input("请输入选项 (0-3): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "0":
            return
        elif choice == "1":
            _cmd_transcribe_accounts_status()
        elif choice == "2":
            _cmd_transcribe_quota_status()
        elif choice == "3":
            _cmd_transcribe_quota_claim()
        else:
            print()
            print(warning("无效的选项，请重新选择"))


def _cmd_transcribe_accounts_status():
    """查看账号状态"""
    print()
    try:
        import asyncio
        from src.media_tools.transcribe.cli.accounts_status import run
        asyncio.run(run(argv=[]))
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    _wait_for_key()


def _cmd_transcribe_quota_status():
    """查看配额"""
    print()
    try:
        from src.media_tools.transcribe.quota import get_quota_snapshot
        from pathlib import Path
        import asyncio
        
        auth_path = Path(".auth/qwen-storage-state.json")
        if not auth_path.exists():
            print("❌ 未认证，请先进行登录")
            _wait_for_key()
            return
        
        snapshot = asyncio.run(get_quota_snapshot(auth_state_path=auth_path))
        print(f"总配额: {snapshot.total_upload}")
        print(f"已使用: {snapshot.used_upload}")
        print(f"剩余: {snapshot.remaining_upload}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    _wait_for_key()


def _cmd_transcribe_quota_claim():
    """领取配额"""
    print()
    print("正在领取配额...")
    try:
        import asyncio
        from src.media_tools.transcribe.cli.claim_needed import run
        asyncio.run(run(argv=[]))
    except Exception as e:
        print(f"❌ 领取失败: {e}")
    _wait_for_key()


def _wait_for_key():
    """等待用户按键返回"""
    try:
        input("按回车键返回...")
    except (EOFError, KeyboardInterrupt):
        print()
        pass


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print()
        print("\n已取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)
