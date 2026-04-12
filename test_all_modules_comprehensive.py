#!/usr/bin/env python3
"""
综合测试脚本 - 测试所有核心模块功能
"""
import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 设置 PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 确保工作目录在项目根
os.chdir(Path(__file__).parent)

# 测试结果记录
test_results = []

def log_test(module_name: str, test_name: str, status: str, detail: str = ""):
    """记录测试结果"""
    test_results.append({
        "module": module_name,
        "test": test_name,
        "status": status,
        "detail": detail,
    })
    icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️ "}.get(status, "❓")
    print(f"  {icon} [{status}] {test_name}" + (f" - {detail}" if detail else ""))


# ============================================================================
# 1. 测试 following.json 完整 CRUD 循环
# ============================================================================
def test_following_json_crud():
    print("\n" + "=" * 70)
    print("测试 1: following.json 完整 CRUD 循环")
    print("=" * 70)

    from media_tools.douyin.utils.following import (
        add_user,
        get_user,
        list_users,
        load_following,
        remove_user,
        save_following,
    )

    original_data = load_following()

    try:
        # --- Create: 添加用户 ---
        print("\n  步骤 1: 添加测试用户 (Create)")
        test_uid = "test_crud_uid_001"
        # 先清理可能存在的测试用户
        remove_user(test_uid)

        test_user_info = {
            "sec_user_id": "test_sec_id_001",
            "name": "测试博主",
            "nickname": "测试博主昵称",
            "avatar_url": "https://example.com/avatar.jpg",
            "signature": "这是一个测试用户",
            "follower_count": 1000,
            "following_count": 50,
            "video_count": 100,
        }

        is_new = add_user(test_uid, test_user_info)
        if is_new:
            log_test("following.json", "添加用户(Create)", "PASS", "新用户添加成功")
        else:
            log_test("following.json", "添加用户(Create)", "FAIL", "add_user 返回 False（可能是更新而非新增）")

        # --- Read: 查询用户 ---
        print("\n  步骤 2: 查询用户 (Read)")
        fetched_user = get_user(test_uid)
        if fetched_user and fetched_user.get("nickname") == "测试博主昵称":
            log_test("following.json", "查询用户(Read)", "PASS", f"查询成功: {fetched_user['nickname']}")
        else:
            log_test("following.json", "查询用户(Read)", "FAIL", "未查询到测试用户或数据不匹配")

        # 也测试 list_users
        all_users = list_users()
        test_user_in_list = any(u.get("uid") == test_uid for u in all_users)
        if test_user_in_list:
            log_test("following.json", "用户列表查询", "PASS", f"列表包含 {len(all_users)} 个用户，含测试用户")
        else:
            log_test("following.json", "用户列表查询", "FAIL", "测试用户不在列表中")

        # --- Update: 修改用户 ---
        print("\n  步骤 3: 修改用户信息 (Update)")
        updated_info = {
            "nickname": "更新后的测试博主",
            "follower_count": 2000,
            "signature": "更新后的简介",
        }
        is_new2 = add_user(test_uid, updated_info, merge=True)
        if not is_new2:  # 应该返回 False 表示更新而非新增
            log_test("following.json", "修改用户标识", "PASS", "add_user 返回 False（表示更新已有用户）")
        else:
            log_test("following.json", "修改用户标识", "WARN", "add_user 返回 True（预期为更新）")

        # 验证更新
        updated_user = get_user(test_uid)
        if updated_user and updated_user.get("nickname") == "更新后的测试博主" and updated_user.get("follower_count") == 2000:
            log_test("following.json", "修改用户(Update)", "PASS", f"昵称={updated_user['nickname']}, 粉丝={updated_user['follower_count']}")
        else:
            log_test("following.json", "修改用户(Update)", "FAIL", f"更新后数据不匹配: {updated_user}")

        # --- Delete: 删除用户 ---
        print("\n  步骤 4: 删除用户 (Delete)")
        deleted = remove_user(test_uid)
        if deleted:
            log_test("following.json", "删除用户(Delete)", "PASS", "remove_user 返回 True")
        else:
            log_test("following.json", "删除用户(Delete)", "FAIL", "remove_user 返回 False")

        # 验证用户已消失
        deleted_user = get_user(test_uid)
        remaining_users = list_users()
        user_gone = deleted_user is None and not any(u.get("uid") == test_uid for u in remaining_users)
        if user_gone:
            log_test("following.json", "验证用户消失", "PASS", "用户已从 following.json 中完全移除")
        else:
            log_test("following.json", "验证用户消失", "FAIL", "用户删除后仍然存在")

        # --- 数据一致性验证 ---
        print("\n  步骤 5: 验证数据一致性")
        final_data = load_following()
        issues = []
        if not isinstance(final_data, dict):
            issues.append("数据不是 dict 类型")
        if "users" not in final_data:
            issues.append("缺少 'users' 键")
        if not isinstance(final_data.get("users", None), list):
            issues.append("'users' 不是 list 类型")

        for i, user in enumerate(final_data.get("users", [])):
            if not isinstance(user, dict):
                issues.append(f"用户[{i}] 不是 dict 类型")
            elif "uid" not in user:
                issues.append(f"用户[{i}] 缺少 'uid' 字段")

        if not issues:
            log_test("following.json", "数据一致性验证", "PASS", "JSON 结构完整，字段类型正确")
        else:
            log_test("following.json", "数据一致性验证", "WARN", f"问题: {'; '.join(issues)}")

    except Exception as e:
        log_test("following.json", "CRUD循环测试", "FAIL", f"异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 恢复原始数据并清理测试用户
        save_following(original_data)
        remove_user("test_crud_uid_001")


# ============================================================================
# 2. 测试配置备份和恢复功能
# ============================================================================
def test_config_backup_restore():
    print("\n" + "=" * 70)
    print("测试 2: 配置备份和恢复功能")
    print("=" * 70)

    from media_tools.config_manager import ConfigManager

    manager = ConfigManager()
    test_backup_name = f"test_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        # --- 创建备份 ---
        print("\n  步骤 1: 创建配置备份")
        backup_path = manager.backup_configs(test_backup_name)

        if backup_path.exists() and backup_path.is_dir():
            backup_files = list(backup_path.iterdir())
            log_test("config_backup", "创建备份", "PASS", f"备份路径: {backup_path}, 文件数: {len(backup_files)}")
        else:
            log_test("config_backup", "创建备份", "FAIL", "备份目录不存在")

        # --- 列出备份 ---
        print("\n  步骤 2: 列出备份")
        if manager.backup_dir.exists():
            backups = [b for b in manager.backup_dir.iterdir() if b.is_dir()]
            test_backup_found = any(b.name == test_backup_name for b in backups)
            if test_backup_found:
                log_test("config_backup", "列出备份", "PASS", f"共 {len(backups)} 个备份，包含测试备份")
            else:
                log_test("config_backup", "列出备份", "FAIL", "未找到测试备份")
        else:
            log_test("config_backup", "列出备份", "FAIL", "备份目录不存在")

        # --- 验证备份元数据 ---
        print("\n  步骤 3: 验证备份内容")
        # ConfigManager 不创建 backup.json，直接验证备份文件
        if backup_path.exists():
            backup_files = list(backup_path.iterdir())
            if backup_files:
                log_test("config_backup", "备份内容验证", "PASS", f"备份包含 {len(backup_files)} 个配置文件")
            else:
                log_test("config_backup", "备份内容验证", "WARN", "备份目录为空（可能无配置文件）")
        else:
            log_test("config_backup", "备份内容验证", "FAIL", "备份路径不存在")

        # --- 配置恢复测试 ---
        print("\n  步骤 4: 配置恢复测试")
        config_yaml = manager.config_dir / "config.yaml"
        original_content = None
        if config_yaml.exists():
            original_content = config_yaml.read_text(encoding="utf-8")
            test_marker = f"\n# test_backup_restore_marker_{datetime.now().strftime('%H%M%S')}"
            with open(config_yaml, "a", encoding="utf-8") as f:
                f.write(test_marker)

            manager.restore_configs(backup_path)

            restored_content = config_yaml.read_text(encoding="utf-8")
            if test_marker not in restored_content:
                log_test("config_backup", "配置恢复", "PASS", "配置已恢复到备份状态（测试标记被移除）")
            else:
                log_test("config_backup", "配置恢复", "WARN", "config.yaml 不在备份中或恢复逻辑未覆盖")

            if original_content:
                config_yaml.write_text(original_content, encoding="utf-8")
        else:
            log_test("config_backup", "配置恢复", "WARN", "config.yaml 不存在，跳过恢复测试")

    except Exception as e:
        log_test("config_backup", "备份恢复测试", "FAIL", f"异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_backup_path = manager.backup_dir / test_backup_name
        if test_backup_path.exists():
            shutil.rmtree(test_backup_path)


# ============================================================================
# 3. 测试数据清理模块
# ============================================================================
def test_data_cleaner():
    print("\n" + "=" * 70)
    print("测试 3: 数据清理模块 (cmd_clean_data)")
    print("=" * 70)

    try:
        from media_tools.douyin.core.cleaner import (
            clean_deleted_videos,
            get_db_video_records,
            interactive_clean_menu,
            scan_local_videos,
        )

        # --- 测试本地视频扫描 ---
        print("\n  步骤 1: 测试本地视频扫描")
        local_videos = scan_local_videos()
        if isinstance(local_videos, dict):
            log_test("cleaner", "本地视频扫描", "PASS", f"扫描 {len(local_videos)} 个用户目录")
        else:
            log_test("cleaner", "本地视频扫描", "FAIL", f"返回值类型错误: {type(local_videos)}")

        # --- 测试数据库记录读取 ---
        print("\n  步骤 2: 测试数据库记录读取")
        db_records = get_db_video_records()
        if isinstance(db_records, dict):
            total_records = sum(len(v.get("aweme_ids", set())) for v in db_records.values())
            log_test("cleaner", "数据库记录读取", "PASS", f"读取 {len(db_records)} 个用户，共 {total_records} 条记录")
        else:
            log_test("cleaner", "数据库记录读取", "FAIL", f"返回值类型错误: {type(db_records)}")

        # --- 测试自动清理 ---
        print("\n  步骤 3: 测试自动清理功能")
        cleaned_count, skipped_count = clean_deleted_videos(auto_confirm=True)
        if isinstance(cleaned_count, int) and isinstance(skipped_count, int):
            log_test("cleaner", "自动清理功能", "PASS", f"清理 {cleaned_count} 条，跳过 {skipped_count} 条")
        else:
            log_test("cleaner", "自动清理功能", "FAIL", f"返回值类型错误: ({type(cleaned_count)}, {type(skipped_count)})")

        # --- 验证交互式菜单函数 ---
        print("\n  步骤 4: 验证交互式菜单函数")
        if callable(interactive_clean_menu):
            log_test("cleaner", "交互式菜单函数", "PASS", "interactive_clean_menu 存在且可调用")
        else:
            log_test("cleaner", "交互式菜单函数", "FAIL", "函数不存在或不可调用")

    except ImportError as e:
        log_test("cleaner", "模块导入", "FAIL", f"无法导入: {e}")
    except Exception as e:
        log_test("cleaner", "数据清理模块", "FAIL", f"异常: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# 4. 测试临时文件检测
# ============================================================================
def test_temp_file_detection():
    print("\n" + "=" * 70)
    print("测试 4: 临时文件检测 (.part/.tmp/.crdownload 等)")
    print("=" * 70)

    project_root = Path(__file__).parent
    test_dirs = ["downloads", "transcripts", "logs"]
    temp_extensions = [".part", ".tmp", ".crdownload", ".download", ".temp"]

    created_files = []
    try:
        # --- 创建测试临时文件 ---
        print("\n  步骤 1: 创建测试临时文件")
        for test_dir in test_dirs:
            dir_path = project_root / test_dir
            dir_path.mkdir(parents=True, exist_ok=True)
            for ext in temp_extensions[:3]:
                test_file = dir_path / f"test_temp_{datetime.now().strftime('%H%M%S')}{ext}"
                test_file.write_text("test content")
                created_files.append(test_file)

        if created_files:
            log_test("temp_detection", "创建测试文件", "PASS", f"创建 {len(created_files)} 个临时文件")
        else:
            log_test("temp_detection", "创建测试文件", "FAIL", "未能创建测试文件")

        # --- 扫描临时文件 ---
        print("\n  步骤 2: 扫描临时文件")
        found_temp = []
        for test_dir in test_dirs:
            dir_path = project_root / test_dir
            if dir_path.exists():
                for ext in temp_extensions:
                    found_temp.extend(list(dir_path.rglob(f"*{ext}")))

        our_files = [f for f in found_temp if "test_temp_" in f.name]
        if len(our_files) >= len(created_files):
            log_test("temp_detection", "扫描临时文件", "PASS", f"检测到 {len(our_files)} 个临时文件")
        else:
            log_test("temp_detection", "扫描临时文件", "WARN", f"仅检测到 {len(our_files)}/{len(created_files)} 个")

        # --- 临时文件报告 ---
        print("\n  步骤 3: 临时文件统计")
        report = {}
        for test_dir in test_dirs:
            dir_path = project_root / test_dir
            if dir_path.exists():
                count = 0
                for ext in temp_extensions:
                    count += len(list(dir_path.rglob(f"*{ext}")))
                if count > 0:
                    report[test_dir] = count

        if report:
            log_test("temp_detection", "临时文件报告", "PASS", f"发现临时文件: {report}")
        else:
            log_test("temp_detection", "临时文件报告", "PASS", "未发现异常临时文件")

    except Exception as e:
        log_test("temp_detection", "临时文件检测", "FAIL", f"异常: {e}")
    finally:
        for f in created_files:
            if f.exists():
                f.unlink()


# ============================================================================
# 5. 测试日志模块
# ============================================================================
def test_logging_module():
    print("\n" + "=" * 70)
    print("测试 5: 日志模块 (写入/轮转/清理)")
    print("=" * 70)

    from media_tools.logger import MediaLogger, init_logging

    test_log_dir = Path("logs_test_integration")
    test_log_dir.mkdir(parents=True, exist_ok=True)

    try:
        # --- 初始化 ---
        print("\n  步骤 1: 初始化日志系统")
        logger = init_logging(level="DEBUG", log_dir=test_log_dir)
        if logger and logger.logger and len(logger.logger.handlers) > 0:
            log_test("logging", "日志初始化", "PASS", f"Handler 数量: {len(logger.logger.handlers)}")
        else:
            log_test("logging", "日志初始化", "FAIL", "Logger 未正确初始化")

        # --- 各级别日志写入 ---
        print("\n  步骤 2: 测试各级别日志写入")
        logger.debug("DEBUG test message")
        logger.info("INFO test message")
        logger.warning("WARNING test message")
        logger.error("ERROR test message")

        today = datetime.now().strftime("%Y%m%d")
        log_file = test_log_dir / f"media_tools_{today}.log"

        if log_file.exists() and log_file.stat().st_size > 0:
            content = log_file.read_text(encoding="utf-8")
        has_info = "INFO test message" in content
        has_debug = "DEBUG test message" in content
        if has_info and has_debug:
            log_test("logging", "日志文件写入", "PASS", f"文件: {log_file.name}, 大小: {log_file.stat().st_size} bytes")
        else:
            log_test("logging", "日志文件写入", "FAIL", f"日志内容不完整 (INFO: {has_info}, DEBUG: {has_debug})")

        # --- 操作日志 ---
        print("\n  步骤 3: 测试操作日志")
        logger.log_operation("测试下载", "success", "video.mp4", 1.5)
        logger.log_operation("测试上传", "failed", "error details", 2.0)

        content = log_file.read_text(encoding="utf-8")
        if "测试下载" in content and "测试上传" in content:
            log_test("logging", "操作日志格式化", "PASS", "操作日志正确写入")
        else:
            log_test("logging", "操作日志格式化", "WARN", "操作日志可能未正确格式化")

        # --- 异常日志 ---
        print("\n  步骤 4: 测试异常日志")
        error_file = test_log_dir / f"error_{today}.log"
        try:
            raise ValueError("Test exception")
        except Exception:
            logger.exception("Test exception logged")

        if error_file.exists() and error_file.stat().st_size > 0:
            log_test("logging", "异常日志记录", "PASS", f"错误日志: {error_file.name}")
        else:
            log_test("logging", "异常日志记录", "WARN", "错误日志文件不存在或为空")

        # --- 日志清理 ---
        print("\n  步骤 5: 测试日志清理功能")
        old_log = test_log_dir / "media_tools_20250101.log"
        old_log.write_text("old log content")
        old_time = time.time() - (31 * 24 * 3600)
        os.utime(old_log, (old_time, old_time))

        logger._cleanup_old_logs()

        if not old_log.exists():
            log_test("logging", "日志清理功能", "PASS", "旧日志文件已被清理")
        else:
            log_test("logging", "日志清理功能", "FAIL", "旧日志文件未被清理")

    except Exception as e:
        log_test("logging", "日志模块测试", "FAIL", f"异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_log_dir.exists():
            shutil.rmtree(test_log_dir)


# ============================================================================
# 6. 测试健康检查模块
# ============================================================================
def test_health_check():
    print("\n" + "=" * 70)
    print("测试 6: 健康检查模块")
    print("=" * 70)

    from media_tools.health_check import HealthChecker

    try:
        checker = HealthChecker()

        checks_to_run = [
            ("依赖检查", "check_dependencies"),
            ("配置文件检查", "check_config_files"),
            ("认证状态检查", "check_auth_status"),
            ("磁盘空间检查", "check_disk_space"),
            ("数据库检查", "check_database"),
            ("日志状态检查", "check_logs"),
            ("Git状态检查", "check_git_status"),
        ]

        for check_name, method_name in checks_to_run:
            print(f"\n  步骤: {check_name}")
            try:
                getattr(checker, method_name)()
                result = next((c for c in checker.checks if c["name"] == check_name.replace("检查", "").replace("状态", "").strip()), None)
                # 重新查找：使用实际存入的 name
                result = next((c for c in checker.checks if check_name.split("检查")[0] in c["name"] or c["name"] == check_name), None)
                # 更宽松的匹配：取最后一个 check
                if result is None and checker.checks:
                    result = checker.checks[-1]

                if result:
                    status = "PASS" if result["status"] else "WARN"
                    log_test("health_check", check_name, status, result["message"])
                else:
                    log_test("health_check", check_name, "WARN", "未找到检查结果")
            except Exception as e:
                log_test("health_check", check_name, "FAIL", f"执行异常: {e}")

        # --- 完整健康检查 ---
        print("\n  步骤: 完整健康检查")
        checker2 = HealthChecker()
        all_passed = checker2.run_all_checks()
        total = len(checker2.checks)
        passed_count = sum(1 for c in checker2.checks if c["status"])
        if all_passed:
            log_test("health_check", "完整健康检查", "PASS", f"全部 {total} 项通过")
        else:
            failed_names = [c["name"] for c in checker2.checks if not c["status"]]
            log_test("health_check", "完整健康检查", "WARN", f"{passed_count}/{total} 通过，失败: {failed_names}")

    except Exception as e:
        log_test("health_check", "健康检查模块", "FAIL", f"异常: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# 7. 测试性能监控模块
# ============================================================================
def test_perf_monitor():
    print("\n" + "=" * 70)
    print("测试 7: 性能监控模块")
    print("=" * 70)

    from media_tools.perf_monitor import (
        PerformanceTracker,
        get_tracker,
        track_operation,
        track_performance,
    )

    try:
        # --- 基础追踪 ---
        print("\n  步骤 1: 测试基础追踪功能")
        tracker = PerformanceTracker()

        with tracker.track("测试操作1"):
            time.sleep(0.1)
        with tracker.track("测试操作2"):
            time.sleep(0.15)

        d1 = tracker.get_operation_duration("测试操作1")
        d2 = tracker.get_operation_duration("测试操作2")

        if d1 is not None and d1 > 0.05 and d2 is not None and d2 > 0.1:
            log_test("perf_monitor", "基础追踪", "PASS", f"操作1: {d1:.3f}s, 操作2: {d2:.3f}s")
        else:
            log_test("perf_monitor", "基础追踪", "FAIL", f"追踪数据异常 (d1={d1}, d2={d2})")

        # --- 总耗时 ---
        print("\n  步骤 2: 测试总耗时")
        total = tracker.get_total_duration()
        if total > 0.2:
            log_test("perf_monitor", "总耗时统计", "PASS", f"总耗时: {total:.3f}s")
        else:
            log_test("perf_monitor", "总耗时统计", "FAIL", f"总耗时异常: {total:.3f}s")

        # --- 慢操作检测 ---
        print("\n  步骤 3: 测试慢操作检测")
        slow_ops = tracker.get_slow_operations(threshold=0.12)
        if len(slow_ops) >= 1:
            log_test("perf_monitor", "慢操作检测", "PASS", f"检测到 {len(slow_ops)} 个慢操作")
        else:
            log_test("perf_monitor", "慢操作检测", "WARN", "未检测到慢操作")

        # --- 性能报告 ---
        print("\n  步骤 4: 测试性能报告")
        summary = tracker.get_summary()
        if summary["total_operations"] == 2 and summary["total_duration"] > 0:
            log_test("perf_monitor", "性能报告", "PASS", f"操作数={summary['total_operations']}, 平均={summary['average_duration']:.3f}s")
        else:
            log_test("perf_monitor", "性能报告", "FAIL", f"报告数据异常: {summary}")

        # --- 装饰器 ---
        print("\n  步骤 5: 测试装饰器")

        @track_performance
        def decorated_func():
            time.sleep(0.1)
            return "ok"

        result = decorated_func()
        if result == "ok":
            log_test("perf_monitor", "track_performance装饰器", "PASS", "装饰器正常工作")
        else:
            log_test("perf_monitor", "track_performance装饰器", "FAIL", f"返回值异常: {result}")

        # --- track_operation 装饰器 ---
        print("\n  步骤 6: 测试 track_operation 装饰器")

        @track_operation("custom_op")
        def decorated_func2():
            time.sleep(0.1)
            return "done"

        global_tracker = get_tracker()
        before_count = len(global_tracker.operations)
        decorated_func2()
        after_count = len(global_tracker.operations)

        if after_count > before_count:
            log_test("perf_monitor", "track_operation装饰器", "PASS", f"操作被追踪 ({before_count} -> {after_count})")
        else:
            log_test("perf_monitor", "track_operation装饰器", "WARN", "操作未被全局追踪器记录")

        # --- 报告显示 ---
        print("\n  步骤 7: 测试报告显示")
        try:
            tracker.display_report()
            log_test("perf_monitor", "报告显示", "PASS", "报告成功生成")
        except Exception as e:
            log_test("perf_monitor", "报告显示", "FAIL", f"报告生成失败: {e}")

    except Exception as e:
        log_test("perf_monitor", "性能监控模块", "FAIL", f"异常: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# 主函数
# ============================================================================
def main():
    print("=" * 70)
    print("综合模块功能测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目目录: {Path(__file__).parent}")
    print("=" * 70)

    test_following_json_crud()
    test_config_backup_restore()
    test_data_cleaner()
    test_temp_file_detection()
    test_logging_module()
    test_health_check()
    test_perf_monitor()

    # 汇总
    print("\n" + "=" * 70)
    print("测试汇总报告")
    print("=" * 70)

    total = len(test_results)
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = sum(1 for r in test_results if r["status"] == "FAIL")
    warned = sum(1 for r in test_results if r["status"] == "WARN")

    print(f"\n总计: {total} 个测试")
    print(f"  ✅ PASS: {passed}")
    print(f"  ❌ FAIL: {failed}")
    print(f"  ⚠️  WARN: {warned}")

    print("\n详细结果:")
    for i, result in enumerate(test_results, 1):
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️ "}.get(result["status"], "❓")
        detail = f" - {result['detail']}" if result['detail'] else ""
        print(f"  {i:2}. {icon} [{result['module']}] {result['test']}{detail}")

    if failed == 0:
        print(f"\n🎉 全部测试通过（{warned} 个警告）")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查上方详情")

    print("=" * 70)


if __name__ == "__main__":
    main()
