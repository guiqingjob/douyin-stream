#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量下载脚本 - 使用 F2 Python API 下载视频并自动保存统计数据

用法：
    # 交互式选择博主下载
    python scripts/batch-download.py

    # 一键全量下载
    python scripts/batch-download.py --all

    # 下载指定博主
    python scripts/batch-download.py --uid 7483912725043774523

    # 采样下载（每个博主1个视频，用于快速更新统计数据）
    python scripts/batch-download.py --sample

特性：
    - 自动保存视频统计数据（点赞、评论、收藏、分享）
    - 零额外 API 请求（数据在下载时获取）
    - 使用博主昵称作为文件夹名
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# 强制使用脚本所在目录作为工作目录
SKILL_DIR = Path(__file__).parent.parent.resolve()
# 切换到脚本目录（确保相对路径正确）
os.chdir(SKILL_DIR)

# 导入统一配置模块
from utils.logger import logger
from utils.config import get_download_path, get_user_folder_name
from utils.following import get_user, list_users, update_fetch_time

DOWNLOAD_SCRIPT = SKILL_DIR / "scripts" / "download.py"
DOWNLOADS_PATH = get_download_path()


def get_local_video_count(folder: str) -> int:
    """获取本地视频数量"""
    user_dir = DOWNLOADS_PATH / folder
    if user_dir.exists():
        return len(list(user_dir.glob("*.mp4")))
    return 0


def download_user(
    uid: str,
    sec_user_id: str = None,
    nickname: str = "",
    max_counts: int = None,
    daemon: bool = False,
):
    """下载单个用户的视频

    Args:
        uid: 用户 ID
        sec_user_id: 用户 sec_user_id
        nickname: 用户昵称（用于文件夹命名）
        max_counts: 最大下载数量，None 表示不限制
        daemon: 是否后台运行
    """
    # 构建用户主页 URL
    if sec_user_id and sec_user_id.startswith("MS4w"):
        url = f"https://www.douyin.com/user/{sec_user_id}"
    else:
        url = f"https://www.douyin.com/user/{uid}"

    # 生成任务 ID
    task_id = f"douyin-{uid}-{int(time.time())}"

    if daemon:
        # 后台运行模式
        log_dir = DOWNLOADS_PATH / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{task_id}.log"

        cmd = [
            sys.executable,
            str(DOWNLOAD_SCRIPT),
            url,
            "--daemon",
            f"--task-id={task_id}",
        ]
        if max_counts is not None:
            cmd.append(f"--max-counts={max_counts}")

        # 使用 nohup 后台运行
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"[任务创建] {task_id}\n")
            f.write(f"[UID] {uid}\n")
            f.write(f"[昵称] {nickname}\n")
            f.write(f"[URL] {url}\n")
            f.write(f"[时间] {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n")

        # 后台启动进程
        subprocess.Popen(
            cmd,
            cwd=str(SKILL_DIR),
            stdout=open(log_file, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            start_new_session=True,  # 脱离父进程
        )

        logger.info(f"✅ 已启动后台任务: {task_id}")
        logger.info(f"   📋 任务ID: {task_id}")
        logger.info(f"   📁 日志: {log_file}")
        logger.info(f"   🔍 查看进度: tail -f {log_file}")
        return task_id
    else:
        # 同步运行模式
        logger.info(f"\n{'='*60}")
        print(
            f"📥 开始下载: {nickname or uid}"
            + (f" (最多 {max_counts} 个)" if max_counts else "")
        )
        logger.info(f"{'='*60}")

        cmd = [sys.executable, str(DOWNLOAD_SCRIPT), url]
        if max_counts is not None:
            cmd.append(f"--max-counts={max_counts}")

        result = subprocess.run(cmd, cwd=str(SKILL_DIR))

        if result.returncode == 0:
            # 更新 last_fetch_time
            update_fetch_time(uid, nickname)
            logger.info(f"✅ 下载完成: {nickname or uid}")
            return True
        else:
            logger.error(f"❌ 下载失败: {nickname or uid}")
            return False


def interactive_select():
    """交互式选择博主下载"""
    users = list_users()

    if not users:
        logger.info("📋 关注列表为空，请先添加用户")
        logger.info("   用法: python scripts/manage-following.py --batch")
        return

    logger.info("\n📋 选择要下载的博主")
    logger.info("=" * 60)

    for i, user in enumerate(users, 1):
        uid = user.get("uid", "未知")
        name = user.get("nickname", user.get("name", "未知"))
        folder = user.get("folder", name or uid)
        local_count = get_local_video_count(folder)
        last_fetch = user.get("last_fetch_time", "未获取")

        # 显示状态标记
        if local_count > 0:
            status = f"📦 已下载 {local_count} 个"
        else:
            status = "🆕 未下载"

        logger.info(f"  {i:2}. {name}")
        logger.info(f"      UID: {uid}")
        logger.info(f"      文件夹: {folder}")
        logger.info(f"      状态: {status} | 最后获取: {last_fetch or '未获取'}")
        logger.info("")

    logger.info("=" * 60)
    logger.info("输入数字选择博主（支持多选，用逗号分隔）")
    logger.info("输入 'all' 下载全部，'q' 退出")
    logger.info("-" * 60)

    choice = input("请选择: ").strip().lower()

    if choice == "q" or choice == "":
        logger.error("❌ 已取消")
        return

    if choice == "all":
        download_all_users(users)
        return

    # 解析选择的数字
    try:
        indices = [int(x.strip()) for x in choice.split(",")]
        selected = []
        for idx in indices:
            if 1 <= idx <= len(users):
                selected.append(users[idx - 1])
            else:
                logger.warning(f"⚠️ 无效的序号: {idx}")

        if not selected:
            logger.error("❌ 没有有效的选择")
            return

        logger.info(f"\n📝 已选择 {len(selected)} 个博主")
        download_selected_users(selected)

    except ValueError:
        logger.error("❌ 无效的输入，请输入数字")


def download_selected_users(users: list):
    """下载选定的用户"""
    total = len(users)
    success = 0
    failed = 0

    for i, user in enumerate(users, 1):
        uid = user.get("uid")
        sec_user_id = user.get("sec_user_id", "")
        name = user.get("nickname", user.get("name", "未知"))

        logger.info(f"\n[{i}/{total}] 处理: {name}")

        if download_user(uid, sec_user_id, name):
            success += 1
        else:
            failed += 1

    logger.info("\n" + "=" * 60)
    logger.info(f"✨ 批量下载完成: 成功 {success}，失败 {failed}")
    logger.info(f"📁 下载目录: {DOWNLOADS_PATH}")
    logger.info("=" * 60)


def download_all_users(
    users: list = None, auto_confirm: bool = False, daemon: bool = False
):
    """下载全部用户

    Args:
        users: 用户列表，None 表示从 following.json 加载
        auto_confirm: 是否跳过确认
        daemon: 是否后台运行
    """
    if users is None:
        users = list_users()

    if not users:
        logger.info("📋 关注列表为空，请先添加用户")
        return

    total = len(users)

    if daemon:
        # 后台模式：直接启动所有任务
        logger.info(f"\n🚀 后台模式：准备启动全部 {total} 个下载任务")
        logger.info(f"📁 下载目录: {DOWNLOADS_PATH}")
        logger.info("-" * 60)

        task_ids = []
        for user in users:
            uid = user.get("uid")
            sec_user_id = user.get("sec_user_id", "")
            name = user.get("nickname", user.get("name", "未知"))
            task_id = download_user(uid, sec_user_id, name, daemon=True)
            if task_id:
                task_ids.append((name, task_id))

        logger.info("\n" + "=" * 60)
        logger.info(f"✅ 已启动 {len(task_ids)} 个后台任务")
        logger.info("-" * 60)
        for name, task_id in task_ids:
            logger.info(f"   📺 {name}: {task_id}")
        logger.info("-" * 60)
        logger.info("🔍 查看所有日志: ls {}/logs/")
        logger.info("=" * 60)
    else:
        # 同步模式
        logger.info(f"\n📥 准备下载全部 {total} 个博主")
        logger.info(f"📁 下载目录: {DOWNLOADS_PATH}")
        logger.info("-" * 60)

        if not auto_confirm:
            confirm = input("确认开始？(y/N): ").strip().lower()
            if confirm != "y":
                logger.error("❌ 已取消")
                return

        download_selected_users(users)


def download_by_uid(uid: str, max_counts: int = None, daemon: bool = False):
    """下载指定 UID 的用户

    Args:
        uid: 用户 ID
        max_counts: 最大下载数量
        daemon: 是否后台运行
    """
    user = get_user(uid)

    if not user:
        logger.error(f"❌ 用户 {uid} 不在关注列表中")
        logger.info("   请先添加: python scripts/manage-following.py --add <URL>")
        return

    name = user.get("nickname", user.get("name", "未知"))
    sec_user_id = user.get("sec_user_id", "")

    if daemon:
        logger.info("\n🚀 后台模式：准备启动下载任务")
        logger.info(f"   📺 博主: {name} (UID: {uid})")
        logger.info(f"   📁 下载目录: {DOWNLOADS_PATH}")
        logger.info("-" * 60)
        task_id = download_user(uid, sec_user_id, name, max_counts, daemon=True)
        logger.info("\n" + "=" * 60)
        if task_id:
            logger.info("✅ 后台任务已启动")
            logger.info(f"   📋 任务ID: {task_id}")
        logger.info("=" * 60)
    else:
        logger.info(f"\n📥 下载博主: {name} (UID: {uid})")
        logger.info(f"📁 下载目录: {DOWNLOADS_PATH}")
        download_user(uid, sec_user_id, name, max_counts)


def download_sample(auto_confirm: bool = False, daemon: bool = False):
    """每个用户只下载1个视频，用于快速更新数据

    Args:
        auto_confirm: 是否跳过确认
        daemon: 是否后台运行
    """
    users = list_users()

    if not users:
        logger.info("📋 关注列表为空，请先添加用户")
        return

    total = len(users)

    if daemon:
        # 后台模式：直接启动所有任务
        logger.info(f"\n🚀 后台模式：准备启动 {total} 个采样下载任务")
        logger.info(f"📁 下载目录: {DOWNLOADS_PATH}")
        logger.info("-" * 60)

        task_ids = []
        for user in users:
            uid = user.get("uid")
            sec_user_id = user.get("sec_user_id", "")
            name = user.get("nickname", user.get("name", "未知"))
            task_id = download_user(uid, sec_user_id, name, max_counts=1, daemon=True)
            if task_id:
                task_ids.append((name, task_id))

        logger.info("\n" + "=" * 60)
        logger.info(f"✅ 已启动 {len(task_ids)} 个后台任务")
        logger.info("-" * 60)
        for name, task_id in task_ids:
            logger.info(f"   📺 {name}: {task_id}")
        logger.info("-" * 60)
        logger.info("🔍 查看所有日志: ls {}/logs/")
        logger.info("=" * 60)
    else:
        # 同步模式
        logger.info("\n📥 采样下载：每个博主只下载 1 个视频")
        logger.info(f"   共 {total} 个博主")
        logger.info(f"📁 下载目录: {DOWNLOADS_PATH}")
        logger.info("-" * 60)

        if not auto_confirm:
            confirm = input("确认开始？(y/N): ").strip().lower()
            if confirm != "y":
                logger.error("❌ 已取消")
                return

        success = 0
        failed = 0

        for i, user in enumerate(users, 1):
            uid = user.get("uid")
            sec_user_id = user.get("sec_user_id", "")
            name = user.get("nickname", user.get("name", "未知"))

            logger.info(f"\n[{i}/{total}] 采样下载: {name}")

            if download_user(uid, sec_user_id, name, max_counts=1):
                success += 1
            else:
                failed += 1

        logger.info("\n" + "=" * 60)
    logger.info(f"✨ 采样下载完成: 成功 {success}，失败 {failed}")
    logger.info("=" * 60)


def main():
    # 检查是否有 --yes 参数（跳过确认）
    auto_confirm = "--yes" in sys.argv
    if auto_confirm:
        sys.argv.remove("--yes")

    # 检查是否有 --daemon 参数（后台运行）
    daemon_mode = "--daemon" in sys.argv
    if daemon_mode:
        sys.argv.remove("--daemon")

    if len(sys.argv) < 2:
        interactive_select()
        return

    action = sys.argv[1]

    if action == "--all":
        download_all_users(auto_confirm=auto_confirm, daemon=daemon_mode)
    elif action == "--sample":
        # 每个用户只下载1个视频，用于更新数据
        download_sample(auto_confirm=auto_confirm, daemon=daemon_mode)
    elif action == "--uid":
        if len(sys.argv) < 3:
            logger.info("用法: python scripts/batch-download.py --uid <UID>")
            return
        download_by_uid(sys.argv[2], daemon=daemon_mode)
    else:
        logger.error(f"❌ 未知参数: {action}")
        logger.info("用法:")
        logger.info("  python scripts/batch-download.py           # 交互选择")
        logger.info("  python scripts/batch-download.py --all      # 全量下载")
        logger.info("  python scripts/batch-download.py --sample   # 采样下载（每个1个视频）")
        logger.info("  python scripts/batch-download.py --uid <UID> # 指定博主")
        logger.info("  --daemon                                # 后台运行模式")
        logger.info("  --yes                                   # 跳过确认直接执行")


if __name__ == "__main__":
    main()
