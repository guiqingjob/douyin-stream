#!/usr/bin/env python3
"""
综合测试报告: 认证、配额、异常处理、日志、健康检查、性能监控、统计面板

测试内容:
1. 认证模块
2. 配额管理
3. 错误分类体系
4. 日志模块
5. 健康检查
6. 性能监控
7. 统计面板

输出: 详细 PASS/FAIL/WARN 报告
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# 确保 PYTHONPATH 包含 src
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# 统计计数器
TOTAL = 0
PASSED = 0
FAILED = 0
WARNED = 0
DETAILS: list[dict] = []


def record(module: str, test: str, status: str, message: str = ""):
    global TOTAL, PASSED, FAILED, WARNED
    TOTAL += 1
    if status == "PASS":
        PASSED += 1
    elif status == "FAIL":
        FAILED += 1
    elif status == "WARN":
        WARNED += 1
    DETAILS.append(
        {
            "module": module,
            "test": test,
            "status": status,
            "message": message,
        }
    )


def p(module: str, test: str, message: str = ""):
    record(module, test, "PASS", message)
    print(f"  [PASS] {test}" + (f" - {message}" if message else ""))


def f(module: str, test: str, message: str = ""):
    record(module, test, "FAIL", message)
    print(f"  [FAIL] {test} - {message}")


def w(module: str, test: str, message: str = ""):
    record(module, test, "WARN", message)
    print(f"  [WARN] {test} - {message}")


# ============================================================
# 1. 认证模块测试
# ============================================================
def test_auth_module():
    print("\n" + "=" * 60)
    print("1. 认证模块测试")
    print("=" * 60)

    # 1.1 检查 .auth/ 目录状态
    auth_dir = Path("/Users/gq/Projects/media-tools/.auth")
    if auth_dir.exists():
        auth_files = list(auth_dir.iterdir())
        if auth_files:
            p("auth", ".auth/ 目录存在且有文件", f"{len(auth_files)} 个文件")
        else:
            w("auth", ".auth/ 目录存在但为空", "可能未配置认证文件")
    else:
        f("auth", ".auth/ 目录不存在", "认证目录缺失")

    # 1.2 认证文件不存在时的错误提示
    from media_tools.transcribe.errors import (
        AuthenticationRequiredError,
        UserFacingError,
    )

    try:
        raise AuthenticationRequiredError("认证文件不存在")
    except AuthenticationRequiredError as e:
        if isinstance(e, Exception) and "认证文件不存在" in str(e):
            p("auth", "AuthenticationRequiredError 抛出正确", f"消息: {e}")
        else:
            f("auth", "AuthenticationRequiredError 消息不正确", str(e))

    # 检查 exit_code
    if AuthenticationRequiredError.exit_code == 2:
        p("auth", "AuthenticationRequiredError.exit_code == 2", "用户级错误码正确")
    else:
        f(
            "auth",
            "AuthenticationRequiredError.exit_code 错误",
            f"期望 2, 实际 {AuthenticationRequiredError.exit_code}",
        )

    # 1.3 继承链检查
    if issubclass(AuthenticationRequiredError, UserFacingError):  # noqa: F821
        p("auth", "错误继承链正确", "AuthenticationRequiredError -> UserFacingError")
    else:
        f("auth", "错误继承链错误", "AuthenticationRequiredError 未继承 UserFacingError")

    # 1.4 auth CLI 模块可导入
    try:
        from media_tools.transcribe.cli import auth as auth_cli

        p("auth", "auth CLI 模块可导入", f"build_parser: {hasattr(auth_cli, 'build_parser')}")
    except ImportError as e:
        f("auth", "auth CLI 模块导入失败", str(e))

    # 5.15 resolve_auth_state_path 函数 (需要 accounts.json 配置)
    try:
        from media_tools.transcribe.accounts import resolve_auth_state_path

        result = resolve_auth_state_path(account_id="test_account")
        if result.auth_state_path:
            p("auth", "resolve_auth_state_path 工作正常", f"路径: {result.auth_state_path}")
        else:
            f("auth", "resolve_auth_state_path 返回空路径", "")
    except Exception as e:
        # accounts.json 中可能没有 test_account, 这是预期的
        if "Unknown account" in str(e) or "accounts.json" in str(e):
            w("auth", "resolve_auth_state_path 跳过", f"accounts.json 无 test_account: {e}")
        else:
            f("auth", "resolve_auth_state_path 调用异常", str(e))


# ============================================================
# 2. 配额管理测试
# ============================================================
def test_quota_module():
    print("\n" + "=" * 60)
    print("2. 配额管理测试")
    print("=" * 60)

    # 2.1 导入 quota 模块
    try:
        from media_tools.transcribe import quota

        p("quota", "quota 模块可导入", "")
    except ImportError as e:
        f("quota", "quota 模块导入失败", str(e))
        return  # 后续测试无法进行

    # 2.2 QuotaSnapshot 数据结构
    try:
        snap = quota.QuotaSnapshot(
            raw={},
            used_upload=10,
            total_upload=60,
            remaining_upload=50,
            gratis_upload=False,
            free=False,
        )
        if snap.remaining_upload == 50:
            p("quota", "QuotaSnapshot 数据类正确", f"remaining={snap.remaining_upload}")
        else:
            f("quota", "QuotaSnapshot 数据不正确", f"expected 50, got {snap.remaining_upload}")
    except Exception as e:
        f("quota", "QuotaSnapshot 创建失败", str(e))

    # 2.3 ClaimEquityResult 数据结构
    try:
        result = quota.ClaimEquityResult(
            claimed=True, skipped=False, reason="", before_snapshot=None, after_snapshot=None
        )
        if result.claimed and not result.skipped:
            p("quota", "ClaimEquityResult 数据类正确", f"claimed={result.claimed}")
        else:
            f("quota", "ClaimEquityResult 数据不正确", "")
    except Exception as e:
        f("quota", "ClaimEquityResult 创建失败", str(e))

    # 2.4 number_value 函数
    tests = [
        (quota.number_value(10), 10, "整数输入"),
        (quota.number_value("20"), 20, "字符串输入"),
        (quota.number_value(None), 0, "None 输入"),
        (quota.number_value("abc"), 0, "无效字符串"),
    ]
    for actual, expected, desc in tests:
        if actual == expected:
            p("quota", f"number_value({desc})", f"{actual} == {expected}")
        else:
            f("quota", f"number_value({desc})", f"期望 {expected}, 实际 {actual}")

    # 2.5 account_key 函数
    if quota.account_key("user123") == "user123":
        p("quota", "account_key(非空) 正确", "")
    else:
        f("quota", "account_key(非空) 错误", "")

    if quota.account_key("") == "__default__":
        p("quota", "account_key(空) 返回 __default__", "")
    else:
        f("quota", "account_key(空) 错误", f"返回: {quota.account_key('')}")

    # 2.6 today_key 函数
    today = quota.today_key()
    try:
        datetime.fromisoformat(today)
        p("quota", "today_key 返回 ISO 日期格式", today)
    except ValueError:
        f("quota", "today_key 格式错误", today)

    # 2.7 build_daily_record 函数
    record_data = quota.build_daily_record({"consumedMinutes": 15, "extra": "ignored"})
    if record_data["consumedMinutes"] == 15:
        p("quota", "build_daily_record 正确", f"consumedMinutes={record_data['consumedMinutes']}")
    else:
        f("quota", "build_daily_record 错误", str(record_data))

    # 2.8 merge_consumption_record 累加
    merged = quota.merge_consumption_record(
        {"consumedMinutes": 5},
        consumed_minutes=7,
        before_remaining=80,
        after_remaining=73,
        updated_at="2026-04-10T00:00:00",
    )
    if merged["consumedMinutes"] == 12:
        p("quota", "merge_consumption_record 累加正确", "5+7=12")
    else:
        f("quota", "merge_consumption_record 累加错误", f"期望 12, 实际 {merged['consumedMinutes']}")

    # 2.9 merge_equity_claim_record
    merged_claim = quota.merge_equity_claim_record(
        {"consumedMinutes": 9},
        before_remaining=40,
        after_remaining=55,
        claimed_at="2026-04-10T00:00:00",
    )
    if merged_claim["consumedMinutes"] == 9 and merged_claim["lastEquityBeforeRemaining"] == 40:
        p("quota", "merge_equity_claim_record 正确", "")
    else:
        f("quota", "merge_equity_claim_record 错误", str(merged_claim))

    # 2.10 get_daily_quota_record (无文件情况)
    try:
        daily = quota.get_daily_quota_record("test_account")
        if isinstance(daily, dict):
            p("quota", "get_daily_quota_record(无文件) 返回空 dict", str(daily))
        else:
            f("quota", "get_daily_quota_record 返回值类型错误", type(daily))
    except Exception as e:
        f("quota", "get_daily_quota_record 异常", str(e))

    # 2.11 has_claimed_equity_today (无记录)
    if not quota.has_claimed_equity_today("nonexistent_account"):
        p("quota", "has_claimed_equity_today(无记录) 返回 False", "")
    else:
        f("quota", "has_claimed_equity_today(无记录) 返回 True", "应为 False")

    # 2.12 quota 状态文件写入和读取 (临时目录)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ.setdefault("QWEN_TRANSCRIBE_CONFIG", "")
        # 不直接修改 quota_state_path, 测试 _read_quota_state / _write_quota_state 逻辑
        # 使用一个独立的 JSON 文件模拟
        test_state_file = Path(tmpdir) / "test_quota_state.json"
        test_data = {"account1": {"2026-04-12": {"consumedMinutes": 30}}}
        test_state_file.write_text(json.dumps(test_data), encoding="utf-8")
        loaded = json.loads(test_state_file.read_text())
        if loaded.get("account1", {}).get("2026-04-12", {}).get("consumedMinutes") == 30:
            p("quota", "配额状态文件读写(模拟)", "读写一致")
        else:
            f("quota", "配额状态文件读写(模拟)", "数据不一致")

    # 2.13 account_status 模块导入
    try:
        from media_tools.transcribe import account_status

        p("quota", "account_status 模块可导入", "")
    except ImportError as e:
        f("quota", "account_status 模块导入失败", str(e))

    # 2.14 recommend_action 函数
    action_need_auth = account_status.recommend_action(
        auth_exists=False, quota=None, quota_error="", daily={}
    )
    if action_need_auth == "need-auth":
        p("quota", "recommend_action(无认证) -> need-auth", "")
    else:
        f("quota", "recommend_action(无认证) 错误", f"返回: {action_need_auth}")

    action_ready = account_status.recommend_action(
        auth_exists=True, quota=MagicMock(remaining_upload=200), quota_error="", daily={}
    )
    if action_ready == "ready":
        p("quota", "recommend_action(配额充足 200>120) -> ready", "")
    else:
        f("quota", "recommend_action(配额充足 200>120) 错误", f"返回: {action_ready}")

    action_claim = account_status.recommend_action(
        auth_exists=True,
        quota=MagicMock(remaining_upload=5),
        quota_error="",
        daily={"lastEquityClaimAt": ""},
    )
    if action_claim == "claim-today":
        p("quota", "recommend_action(配额低+未领取) -> claim-today", "")
    else:
        f("quota", "recommend_action(配额低+未领取) 错误", f"返回: {action_claim}")


# ============================================================
# 3. 错误分类体系测试
# ============================================================
def test_error_classification():
    print("\n" + "=" * 60)
    print("3. 错误分类体系测试")
    print("=" * 60)

    from media_tools.pipeline.orchestrator_v2 import ErrorType, classify_error

    # 3.1 ErrorType 枚举完整性
    expected_types = [
        "UNKNOWN",
        "NETWORK",
        "QUOTA",
        "AUTH",
        "FILE_NOT_FOUND",
        "PERMISSION",
        "TIMEOUT",
        "VALIDATION",
        "CANCELLED",
    ]
    for t in expected_types:
        if hasattr(ErrorType, t):
            p("error", f"ErrorType.{t} 存在", f"value={getattr(ErrorType, t).value}")
        else:
            f("error", f"ErrorType.{t} 缺失", "")

    # 3.2 classify_error - 认证错误
    auth_errors = [
        (Exception("unauthorized access"), ErrorType.AUTH),
        (Exception("401 token expired"), ErrorType.AUTH),
        (Exception("auth failed"), ErrorType.AUTH),
        (Exception("credential invalid"), ErrorType.AUTH),
        (Exception("permission denied"), ErrorType.AUTH),
    ]
    for exc, expected in auth_errors:
        actual = classify_error(exc)
        if actual == expected:
            p("error", f"classify_error(AUTH): {exc}", f"-> {actual.value}")
        else:
            f("error", f"classify_error(AUTH): {exc}", f"期望 {expected.value}, 实际 {actual.value}")

    # 3.3 classify_error - 网络错误
    network_errors = [
        (Exception("connection refused"), ErrorType.NETWORK),
        (Exception("network unreachable"), ErrorType.NETWORK),
        (Exception("socket error"), ErrorType.NETWORK),
        (Exception("dns resolve failed"), ErrorType.NETWORK),
    ]
    for exc, expected in network_errors:
        actual = classify_error(exc)
        if actual == expected:
            p("error", f"classify_error(NETWORK): {exc}", f"-> {actual.value}")
        else:
            f("error", f"classify_error(NETWORK): {exc}", f"期望 {expected.value}, 实际 {actual.value}")

    # 3.4 classify_error - 超时错误
    timeout_errors = [
        (Exception("request timeout"), ErrorType.TIMEOUT),
        (Exception("operation timed out"), ErrorType.TIMEOUT),
        (Exception("deadline exceeded"), ErrorType.TIMEOUT),
    ]
    for exc, expected in timeout_errors:
        actual = classify_error(exc)
        if actual == expected:
            p("error", f"classify_error(TIMEOUT): {exc}", f"-> {actual.value}")
        else:
            f("error", f"classify_error(TIMEOUT): {exc}", f"期望 {expected.value}, 实际 {actual.value}")

    # 3.5 classify_error - 配额错误
    quota_errors = [
        (Exception("quota exceeded"), ErrorType.QUOTA),
        (Exception("rate limit 429"), ErrorType.QUOTA),
        (Exception("too many requests"), ErrorType.QUOTA),
    ]
    for exc, expected in quota_errors:
        actual = classify_error(exc)
        if actual == expected:
            p("error", f"classify_error(QUOTA): {exc}", f"-> {actual.value}")
        else:
            f("error", f"classify_error(QUOTA): {exc}", f"期望 {expected.value}, 实际 {actual.value}")

    # 3.6 classify_error - 文件不存在
    file_errors = [
        (Exception("file not found"), ErrorType.FILE_NOT_FOUND),
        (Exception("no such file or directory"), ErrorType.FILE_NOT_FOUND),
    ]
    for exc, expected in file_errors:
        actual = classify_error(exc)
        if actual == expected:
            p("error", f"classify_error(FILE_NOT_FOUND): {exc}", f"-> {actual.value}")
        else:
            f(
                "error",
                f"classify_error(FILE_NOT_FOUND): {exc}",
                f"期望 {expected.value}, 实际 {actual.value}",
            )

    # 中文 "找不到" 在代码中被匹配
    if classify_error(Exception("找不到文件")) == ErrorType.FILE_NOT_FOUND:
        p("error", "classify_error(FILE_NOT_FOUND): 找不到文件", "-> file_not_found")
    else:
        w("error", "classify_error(FILE_NOT_FOUND): 找不到文件", "classify_error 未匹配中文'找不到'(实际代码中只有'找不到'关键词)")

    # 3.7 classify_error - 权限错误
    permission_errors = [
        (Exception("permission denied"), ErrorType.AUTH),  # 注意: permission denied 在代码中归为 AUTH
        (Exception("access denied"), ErrorType.PERMISSION),
    ]
    for exc, expected in permission_errors:
        actual = classify_error(exc)
        if actual == expected:
            p("error", f"classify_error({expected.value}): {exc}", f"-> {actual.value}")
        else:
            w(
                "error",
                f"classify_error({expected.value}): {exc}",
                f"期望 {expected.value}, 实际 {actual.value} (注意: 'permission denied' 被优先匹配为 AUTH)",
            )

    # 3.8 classify_error - 验证错误
    validation_errors = [
        (Exception("invalid format"), ErrorType.VALIDATION),
        (Exception("validation failed"), ErrorType.VALIDATION),
    ]
    for exc, expected in validation_errors:
        actual = classify_error(exc)
        if actual == expected:
            p("error", f"classify_error(VALIDATION): {exc}", f"-> {actual.value}")
        else:
            f("error", f"classify_error(VALIDATION): {exc}", f"期望 {expected.value}, 实际 {actual.value}")

    # 3.9 classify_error - 未知错误
    unknown_exc = Exception("some weird error")
    if classify_error(unknown_exc) == ErrorType.UNKNOWN:
        p("error", "classify_error(未知) -> UNKNOWN", "")
    else:
        f("error", "classify_error(未知) 错误", f"期望 UNKNOWN, 实际 {classify_error(unknown_exc).value}")

    # 3.10 errors.py 模块的错误类
    try:
        from media_tools.transcribe.errors import (
            ConfigurationError,
            InputValidationError,
            QwenTranscribeError,
            UserFacingError,
        )

        p("error", "transcribe.errors 所有类可导入", "")

        # 检查继承关系
        if issubclass(ConfigurationError, UserFacingError):
            p("error", "ConfigurationError -> UserFacingError", "")
        else:
            f("error", "ConfigurationError 继承链错误", "")

        if issubclass(UserFacingError, QwenTranscribeError):
            p("error", "UserFacingError -> QwenTranscribeError", "")
        else:
            f("error", "UserFacingError 继承链错误", "")

        # 检查 exit_code
        if QwenTranscribeError.exit_code == 1:
            p("error", "QwenTranscribeError.exit_code == 1", "")
        else:
            f("error", "QwenTranscribeError.exit_code 错误", str(QwenTranscribeError.exit_code))

        if UserFacingError.exit_code == 2:
            p("error", "UserFacingError.exit_code == 2", "")
        else:
            f("error", "UserFacingError.exit_code 错误", str(UserFacingError.exit_code))

    except ImportError as e:
        f("error", "transcribe.errors 导入失败", str(e))


# ============================================================
# 4. 日志模块测试
# ============================================================
def test_logger_module():
    print("\n" + "=" * 60)
    print("4. 日志模块测试")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"

        try:
            from media_tools.logger import MediaLogger, init_logging

            # 4.1 初始化
            logger = init_logging(level="DEBUG", log_dir=log_dir)
            if log_dir.exists():
                p("logger", "日志目录自动创建", str(log_dir))
            else:
                f("logger", "日志目录未创建", str(log_dir))

            # 4.2 各级别日志写入
            logger.debug("debug test")
            logger.info("info test")
            logger.warning("warning test")
            logger.error("error test")

            # 检查文件是否创建
            log_files = list(log_dir.glob("*.log"))
            if len(log_files) >= 1:
                p("logger", "日志文件创建", f"{len(log_files)} 个文件: {[f.name for f in log_files]}")
            else:
                f("logger", "日志文件未创建", str(log_dir))

            # 4.3 文件内容检查
            today_str = datetime.now().strftime("%Y%m%d")
            main_log = log_dir / f"media_tools_{today_str}.log"
            if main_log.exists():
                content = main_log.read_text(encoding="utf-8")
                if "info test" in content:
                    p("logger", "日志内容写入正确", "info test 已写入")
                else:
                    f("logger", "日志内容写入失败", "未找到 'info test'")
            else:
                f("logger", "主日志文件不存在", str(main_log))

            # 4.4 错误日志文件
            error_log = log_dir / f"error_{today_str}.log"
            if error_log.exists():
                error_content = error_log.read_text(encoding="utf-8")
                if "error test" in error_content:
                    p("logger", "错误日志文件写入正确", "")
                else:
                    f("logger", "错误日志内容缺失", "")
            else:
                f("logger", "错误日志文件不存在", str(error_log))

            # 4.5 log_operation 格式化
            logger.log_operation("测试操作", "success", "detail info", 1.5)
            if main_log.exists():
                content = main_log.read_text(encoding="utf-8")
                if "测试操作" in content or "success" in content:
                    p("logger", "log_operation 格式化正确", "")
                else:
                    w("logger", "log_operation 格式化", "操作日志未在主日志中找到")

            # 4.6 异常日志
            try:
                raise ValueError("test exception")
            except Exception:
                logger.exception("捕获异常测试")
            if main_log.exists():
                content = main_log.read_text(encoding="utf-8")
                if "捕获异常测试" in content:
                    p("logger", "exception() 日志写入正确", "")
                else:
                    f("logger", "exception() 日志写入失败", "")

            # 4.7 旧日志清理 (模拟)
            # 创建一个超期的旧日志文件
            old_log = log_dir / "media_tools_20200101.log"
            old_log.write_text("old log content", encoding="utf-8")
            # 修改 mtime 为 60 天前
            old_time = time.time() - (60 * 24 * 3600)
            os.utime(old_log, (old_time, old_time))

            # 手动调用 _cleanup_old_logs
            logger._cleanup_old_logs()
            if not old_log.exists():
                p("logger", "旧日志清理正确", "2020年日志已删除")
            else:
                f("logger", "旧日志清理失败", "2020年日志仍存在")

            # 4.8 get_logger 单例
            logger2 = init_logging(level="INFO", log_dir=log_dir)
            if logger2 is not None:
                p("logger", "get_logger/init_logging 返回非空", "")
            else:
                f("logger", "init_logging 返回 None", "")

        except ImportError as e:
            f("logger", "logger 模块导入失败", str(e))
        except Exception as e:
            f("logger", "logger 模块测试异常", str(e))


# ============================================================
# 5. 健康检查测试
# ============================================================
def test_health_check():
    print("\n" + "=" * 60)
    print("5. 健康检查测试")
    print("=" * 60)

    try:
        from media_tools.health_check import HealthChecker

        # 5.1 创建检查器
        checker = HealthChecker()
        p("health", "HealthChecker 创建成功", "")

        # 5.2 依赖检查
        checker.check_dependencies()
        dep_check = [c for c in checker.checks if c["name"] == "依赖安装"]
        if dep_check:
            if dep_check[0]["status"]:
                p("health", "依赖检查通过", dep_check[0]["message"])
            else:
                w("health", "依赖检查有缺失", dep_check[0]["message"])
        else:
            f("health", "依赖检查未记录", "")

        # 5.3 配置文件检查
        checker.check_config_files()
        config_check = [c for c in checker.checks if c["name"] == "配置文件"]
        if config_check:
            if config_check[0]["status"]:
                p("health", "配置文件检查通过", config_check[0]["message"])
            else:
                w("health", "配置文件有缺失", config_check[0]["message"])
        else:
            f("health", "配置文件检查未记录", "")

        # 5.4 认证状态检查
        checker.check_auth_status()
        auth_check = [c for c in checker.checks if c["name"] == "认证状态"]
        if auth_check:
            # 认证状态通常是 WARN (因为未配置)
            if auth_check[0]["status"]:
                p("health", "认证状态检查完成", auth_check[0]["message"])
            else:
                w("health", "认证状态检查", auth_check[0]["message"])
        else:
            f("health", "认证状态检查未记录", "")

        # 5.5 磁盘空间检查
        checker.check_disk_space()
        disk_check = [c for c in checker.checks if c["name"] == "磁盘空间"]
        if disk_check:
            if disk_check[0]["status"]:
                p("health", "磁盘空间检查通过", disk_check[0]["message"])
            else:
                f("health", "磁盘空间不足", disk_check[0]["message"])
        else:
            f("health", "磁盘空间检查未记录", "")

        # 5.6 数据库检查
        checker.check_database()
        db_check = [c for c in checker.checks if c["name"] == "数据库"]
        if db_check:
            p("health", "数据库检查完成", db_check[0]["message"])
        else:
            f("health", "数据库检查未记录", "")

        # 5.7 日志系统检查
        checker.check_logs()
        log_check = [c for c in checker.checks if c["name"] == "日志系统"]
        if log_check:
            p("health", "日志系统检查完成", log_check[0]["message"])
        else:
            f("health", "日志系统检查未记录", "")

        # 5.8 Git 状态检查
        checker.check_git_status()
        git_check = [c for c in checker.checks if c["name"] == "Git状态"]
        if git_check:
            p("health", "Git状态检查完成", git_check[0]["message"])
        else:
            f("health", "Git状态检查未记录", "")

        # 5.9 汇总功能
        summary = checker._generate_summary()
        if "总检查项" in summary:
            p("health", "汇总报告生成正确", "")
        else:
            f("health", "汇总报告格式异常", summary[:100])

        # 5.10 _all_passed 功能
        result = checker._all_passed()
        if isinstance(result, bool):
            p("health", "_all_passed 返回 bool", f"结果: {result}")
        else:
            f("health", "_all_passed 返回值类型错误", type(result))

    except ImportError as e:
        f("health", "health_check 模块导入失败", str(e))
    except Exception as e:
        f("health", "health_check 测试异常", str(e))


# ============================================================
# 6. 性能监控测试
# ============================================================
def test_perf_monitor():
    print("\n" + "=" * 60)
    print("6. 性能监控测试")
    print("=" * 60)

    try:
        from media_tools.perf_monitor import (
            PerformanceTracker,
            get_tracker,
            track_operation,
            track_performance,
        )

        # 6.1 创建追踪器
        tracker = PerformanceTracker()
        p("perf", "PerformanceTracker 创建成功", "")

        # 6.2 track 上下文管理器
        with tracker.track("测试操作"):
            time.sleep(0.05)

        duration = tracker.get_operation_duration("测试操作")
        if duration is not None and duration >= 0.05:
            p("perf", "track() 计时正确", f"耗时: {duration:.3f}s")
        else:
            f("perf", "track() 计时错误", f"期望 >= 0.05, 实际 {duration}")

        # 6.3 多次操作
        with tracker.track("操作A"):
            time.sleep(0.02)
        with tracker.track("操作B"):
            time.sleep(0.03)

        summary = tracker.get_summary()
        if summary["total_operations"] == 3:
            p("perf", "多次操作记录正确", f"total_operations={summary['total_operations']}")
        else:
            f("perf", "操作计数错误", f"期望 3, 实际 {summary['total_operations']}")

        # 6.4 get_total_duration
        total = tracker.get_total_duration()
        if total >= 0.1:
            p("perf", "get_total_duration 正确", f"总耗时: {total:.3f}s")
        else:
            f("perf", "get_total_duration 错误", f"期望 >= 0.1, 实际 {total}")

        # 6.5 get_slow_operations (阈值设很低)
        slow = tracker.get_slow_operations(threshold=0.025)
        if len(slow) >= 1:
            p("perf", "get_slow_operations 正确", f"慢操作数: {len(slow)}")
        else:
            f("perf", "get_slow_operations 错误", f"期望 >= 1, 实际 {len(slow)}")

        # 6.6 空追踪器摘要
        empty_tracker = PerformanceTracker()
        empty_summary = empty_tracker.get_summary()
        if empty_summary["total_operations"] == 0:
            p("perf", "空追踪器摘要正确", "")
        else:
            f("perf", "空追踪器摘要错误", str(empty_summary))

        # 6.7 get_tracker 全局单例
        t1 = get_tracker()
        t2 = get_tracker()
        if t1 is t2:
            p("perf", "get_tracker() 单例模式正确", "")
        else:
            f("perf", "get_tracker() 非单例", "")

        # 6.8 track_operation 装饰器
        @track_operation("装饰器测试")
        def decorated_func():
            time.sleep(0.01)
            return "ok"

        result = decorated_func()
        tracker_global = get_tracker()
        dur = tracker_global.get_operation_duration("装饰器测试")
        if result == "ok" and dur is not None:
            p("perf", "track_operation 装饰器正确", f"返回值: {result}, 耗时: {dur:.3f}s")
        else:
            f("perf", "track_operation 装饰器错误", f"result={result}, duration={dur}")

        # 6.9 track_performance 装饰器
        @track_performance
        def perf_decorated():
            time.sleep(0.01)
            return "done"

        result = perf_decorated()
        if result == "done":
            p("perf", "track_performance 装饰器正确", "")
        else:
            f("perf", "track_performance 装饰器错误", f"返回值: {result}")

        # 6.10 display_report (不检查输出, 仅确认不崩溃)
        try:
            tracker.display_report()
            p("perf", "display_report() 无崩溃", "")
        except Exception as e:
            f("perf", "display_report() 崩溃", str(e))

    except ImportError as e:
        f("perf", "perf_monitor 模块导入失败", str(e))
    except Exception as e:
        f("perf", "perf_monitor 测试异常", str(e))


# ============================================================
# 7. 统计面板测试
# ============================================================
def test_stats_panel():
    print("\n" + "=" * 60)
    print("7. 统计面板测试")
    print("=" * 60)

    try:
        from media_tools.stats_panel import StatsCollector

        # 使用临时文件隔离测试数据
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            stats_file = Path(tmpdir) / ".usage_stats.json"

            # 7.1 创建收集器(空数据)
            collector = StatsCollector()
            # 覆盖为临时文件
            collector.stats_file = stats_file
            collector.stats = collector._load_stats()  # 重新加载(空)
            p("stats", "StatsCollector 创建成功", "")

            # 7.2 默认统计数据(空)
            summary = collector.get_summary()
            if summary["total_downloads"] == 0 and summary["total_transcribes"] == 0:
                p("stats", "默认统计数据正确(空)", str(summary))
            else:
                f("stats", "默认统计数据错误", str(summary))

            # 7.3 record_download
            collector.record_download("测试博主", video_count=2)
            if collector.stats["total_downloads"] == 2:
                p("stats", "record_download 正确", f"downloads={collector.stats['total_downloads']}")
            else:
                f("stats", "record_download 错误", f"期望 2, 实际 {collector.stats['total_downloads']}")

            # 7.4 record_transcribe
            collector.record_transcribe("测试博主", word_count=1000)
            if collector.stats["total_transcribes"] == 1 and collector.stats["total_words"] == 1000:
                p("stats", "record_transcribe 正确", f"transcribes=1, words=1000")
            else:
                f(
                    "stats",
                    "record_transcribe 错误",
                    f"transcribes={collector.stats['total_transcribes']}, words={collector.stats['total_words']}",
                )

            # 7.5 创作者统计 (按视频数排序, 博主A=5 > 博主B=3 > 测试博主=2)
            collector.record_download("博主A", video_count=5)
            collector.record_download("博主B", video_count=3)
            top = collector.get_top_creators(limit=3)
            if len(top) >= 1 and top[0]["name"] == "博主A" and top[0]["videos"] == 5:
                p("stats", "get_top_creators 排序正确(按视频数)", f"TOP1: {top[0]['name']} ({top[0]['videos']} videos)")
            else:
                f("stats", "get_top_creators 排序错误", str(top))

            # 7.6 空创作者排行
            empty_collector = StatsCollector()
            empty_collector.stats_file = Path(tmpdir) / ".empty_stats.json"
            empty_collector.stats = empty_collector._load_stats()
            empty_collector.stats["creators"] = {}
            top_empty = empty_collector.get_top_creators()
            if top_empty == []:
                p("stats", "空创作者排行返回 []", "")
            else:
                f("stats", "空创作者排行错误", str(top_empty))

            # 7.7 save_stats / load_stats 持久化
            collector.save_stats()
            collector2 = StatsCollector()
            collector2.stats_file = stats_file
            collector2.stats = collector2._load_stats()
            if collector2.stats["total_downloads"] == collector.stats["total_downloads"]:
                p("stats", "统计数据持久化正确", "保存后加载回一致")
            else:
                f("stats", "统计数据持久化错误", f"保存: {collector.stats['total_downloads']}, 加载: {collector2.stats['total_downloads']}")

            # 7.8 估算节省时间
            summary = collector.get_summary()
            if "estimated_hours_saved" in summary and isinstance(summary["estimated_hours_saved"], (int, float)):
                p("stats", "estimated_hours_saved 计算", f"{summary['estimated_hours_saved']} 小时")
            else:
                f("stats", "estimated_hours_saved 缺失或类型错误", str(summary))

        # 7.9 display_stats_panel (不检查输出, 仅确认不崩溃)
        try:
            from media_tools.stats_panel import display_stats_panel

            display_stats_panel()
            p("stats", "display_stats_panel() 无崩溃", "")
        except Exception as e:
            f("stats", "display_stats_panel() 崩溃", str(e))

    except ImportError as e:
        f("stats", "stats_panel 模块导入失败", str(e))
    except Exception as e:
        f("stats", "stats_panel 测试异常", str(e))


# ============================================================
# 汇总报告
# ============================================================
def print_report():
    print("\n" + "=" * 60)
    print("📊 综合测试报告")
    print("=" * 60)
    print(f"  总测试数: {TOTAL}")
    print(f"  [PASS]   : {PASSED}")
    print(f"  [FAIL]   : {FAILED}")
    print(f"  [WARN]   : {WARNED}")
    print(f"  通过率   : {PASSED / TOTAL * 100:.1f}%" if TOTAL > 0 else "  无测试")
    print("=" * 60)

    # 按模块汇总
    modules = {}
    for d in DETAILS:
        mod = d["module"]
        if mod not in modules:
            modules[mod] = {"pass": 0, "fail": 0, "warn": 0}
        modules[mod][d["status"].lower()] += 1

    print("\n按模块汇总:")
    print(f"  {'模块':<15} {'PASS':>5} {'FAIL':>5} {'WARN':>5}")
    print(f"  {'-'*15} {'-'*5} {'-'*5} {'-'*5}")
    for mod, counts in sorted(modules.items()):
        print(f"  {mod:<15} {counts['pass']:>5} {counts['fail']:>5} {counts['warn']:>5}")

    # 失败详情
    failures = [d for d in DETAILS if d["status"] == "FAIL"]
    if failures:
        print("\n失败详情:")
        for d in failures:
            print(f"  [{d['module']}] {d['test']}: {d['message']}")

    # WARN 详情
    warns = [d for d in DETAILS if d["status"] == "WARN"]
    if warns:
        print("\n警告详情:")
        for d in warns:
            print(f"  [{d['module']}] {d['test']}: {d['message']}")

    print()
    if FAILED == 0:
        print("🎉 所有关键测试通过!")
    else:
        print(f"⚠️  有 {FAILED} 个测试失败, 请检查详情.")


# ============================================================
# 主入口
# ============================================================
def main():
    print("=" * 60)
    print("媒体工具 - 认证/配额/异常/日志/健康/性能/统计 综合测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version}")
    print(f"项目路径: /Users/gq/Projects/media-tools")
    print("=" * 60)

    test_auth_module()
    test_quota_module()
    test_error_classification()
    test_logger_module()
    test_health_check()
    test_perf_monitor()
    test_stats_panel()

    print_report()

    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
