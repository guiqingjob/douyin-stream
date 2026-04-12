#!/usr/bin/env python3
"""
认证、配额和异常处理 综合测试报告

测试模块:
1. 认证模块 (.auth/ 目录, 认证文件不存在, 认证过期/无效)
2. 配额管理 (账号状态查询, 配额领取, 配额不足错误分类)
3. 错误分类体系 (ErrorType 分类, 错误识别)
4. 日志模块 (logs/ 目录, 日志写入, 日志轮转/清理)
5. 健康检查 (health_check.py, perf_monitor.py, stats_panel.py)
"""

from __future__ import annotations

import json
import logging
import sys
import time
import unittest
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# 确保 src 在路径中
sys.path.insert(0, str(Path(__file__).parent / "src"))

from media_tools.pipeline.orchestrator_v2 import (
    ErrorType,
    classify_error,
    RetryConfig,
    VideoState,
    PipelineStateManager,
    PipelineResultV2,
)
from media_tools.errors import (
    QwenTranscribeError,
    UserFacingError,
    ConfigurationError,
    InputValidationError,
    AuthenticationRequiredError,
)
from media_tools.logger import MediaLogger, init_logging
from media_tools.perf_monitor import PerformanceTracker
from media_tools.stats_panel import StatsCollector
from media_tools.transcribe.quota import (
    QuotaSnapshot,
    ClaimEquityResult,
    build_daily_record,
    merge_consumption_record,
    merge_equity_claim_record,
    account_key,
    today_key,
    number_value,
)
from media_tools.transcribe.account_status import recommend_action
from media_tools.health_check import HealthChecker


class TestResults:
    """测试结果收集器"""

    def __init__(self):
        self.results = []  # [{module, test, status, detail}]

    def record(self, module: str, test: str, status: str, detail: str = ""):
        self.results.append({"module": module, "test": test, "status": status, "detail": detail})

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        warned = sum(1 for r in self.results if r["status"] == "WARN")
        return total, passed, failed, warned


TR = TestResults()


def check(condition: bool, module: str, test: str, detail: str = ""):
    if condition:
        TR.record(module, test, "PASS", detail)
    else:
        TR.record(module, test, "FAIL", detail)


def warn(module: str, test: str, detail: str = ""):
    TR.record(module, test, "WARN", detail)


# ============================================================
# 1. 认证模块测试
# ============================================================
def test_auth_module():
    print("\n" + "=" * 60)
    print("1. 认证模块测试")
    print("=" * 60)

    auth_dir = Path(".auth")

    # 1.1 检查 .auth/ 目录状态
    exists = auth_dir.exists()
    check(exists, "认证模块", ".auth/ 目录存在", f"目录: {auth_dir.absolute()}")
    if exists:
        # 列出文件（包括 gitignore 忽略的）
        import subprocess
        try:
            result = subprocess.run(
                ["ls", "-la", str(auth_dir)], capture_output=True, text=True, timeout=5
            )
            files = [line for line in result.stdout.strip().split("\n") if line and not line.startswith("total")]
            check(len(files) > 0, "认证模块", ".auth/ 目录非空", f"文件数: {len(files)}")
            if len(files) == 0:
                warn("认证模块", ".auth/ 目录为空", "需要运行 qwen-transcribe auth 初始化")
        except Exception as e:
            warn("认证模块", ".auth/ 目录读取失败", str(e))

    # 1.2 认证文件不存在时的错误提示
    nonexistent_auth = Path(".auth/nonexistent_state.json")
    check(
        not nonexistent_auth.exists(),
        "认证模块",
        "不存在的认证文件正确返回 False",
    )

    # 测试 AuthenticationRequiredError
    try:
        raise AuthenticationRequiredError("auth state not found")
    except AuthenticationRequiredError as e:
        check(
            isinstance(e, UserFacingError),
            "认证模块",
            "AuthenticationRequiredError 继承自 UserFacingError",
        )
        check(e.exit_code == 2, "认证模块", "AuthenticationRequiredError exit_code == 2")

    # 1.3 认证过期/无效时的处理 - 模拟加载无效 JSON
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_auth = Path(tmpdir) / "bad_auth.json"
        bad_auth.write_text("{invalid json", encoding="utf-8")
        try:
            json.loads(bad_auth.read_text())
            check(False, "认证模块", "无效 JSON 应抛出异常")
        except json.JSONDecodeError:
            check(True, "认证模块", "无效 JSON 文件正确抛出 JSONDecodeError")

    # 1.4 ConfigurationError 和 InputValidationError
    try:
        raise ConfigurationError("missing API key")
    except ConfigurationError as e:
        check(isinstance(e, UserFacingError), "认证模块", "ConfigurationError 继承链正确")

    try:
        raise InputValidationError("invalid format")
    except InputValidationError as e:
        check(e.exit_code == 2, "认证模块", "InputValidationError exit_code == 2")

    # 1.5 账号状态查询中的认证检查逻辑
    action_no_auth = recommend_action(
        auth_exists=False, quota=None, quota_error="", daily={}
    )
    check(
        action_no_auth == "need-auth",
        "认证模块",
        "无认证时 recommend_action 返回 'need-auth'",
    )


# ============================================================
# 2. 配额管理测试
# ============================================================
def test_quota_module():
    print("\n" + "=" * 60)
    print("2. 配额管理测试")
    print("=" * 60)

    # 2.1 账号状态查询 - QuotaSnapshot 构建
    snapshot = QuotaSnapshot(
        raw={"data": {"usedQuota": {"upload": 30}, "totalQuota": {"upload": 100}}},
        used_upload=30,
        total_upload=100,
        remaining_upload=70,
        gratis_upload=False,
        free=False,
    )
    check(snapshot.remaining_upload == 70, "配额管理", "QuotaSnapshot 剩余配额计算正确")
    check(snapshot.total_upload == 100, "配额管理", "QuotaSnapshot 总配额正确")

    # 2.2 配额领取结果
    claim_result = ClaimEquityResult(
        claimed=True, skipped=False, reason="", before_snapshot=snapshot, after_snapshot=snapshot
    )
    check(claim_result.claimed is True, "配额管理", "ClaimEquityResult.claimed 正确")
    check(claim_result.skipped is False, "配额管理", "ClaimEquityResult.skipped 正确")

    # 2.3 配额领取跳过
    skip_result = ClaimEquityResult(
        claimed=False, skipped=True, reason="already-claimed-today",
        before_snapshot=None, after_snapshot=None,
    )
    check(skip_result.skipped is True, "配额管理", "跳过领取 skipped=True")
    check(skip_result.reason == "already-claimed-today", "配额管理", "跳过原因正确")

    # 2.4 number_value 转换
    check(number_value(42) == 42, "配额管理", "number_value(int) 正确")
    check(number_value("100") == 100, "配额管理", "number_value(str) 正确")
    check(number_value("abc") == 0, "配额管理", "number_value(无效字符串) 返回 0")
    check(number_value(None) == 0, "配额管理", "number_value(None) 返回 0")

    # 2.5 account_key 和 today_key
    check(account_key("user123") == "user123", "配额管理", "account_key 正确")
    check(account_key("") == "__default__", "配额管理", "account_key(空) 返回 __default__")
    check(today_key() == datetime.now().strftime("%Y-%m-%d"), "配额管理", "today_key 格式正确 (ISO date)")

    # 2.6 build_daily_record
    record = build_daily_record({"consumedMinutes": 15, "lastBeforeRemaining": 80})
    check(record["consumedMinutes"] == 15, "配额管理", "build_daily_record consumedMinutes 正确")
    check("lastBeforeRemaining" in record, "配额管理", "build_daily_record 包含 lastBeforeRemaining")

    # 2.7 merge_consumption_record 累加
    merged = merge_consumption_record(
        {"consumedMinutes": 10},
        consumed_minutes=5,
        before_remaining=90,
        after_remaining=85,
        updated_at="2026-04-12T00:00:00",
    )
    check(merged["consumedMinutes"] == 15, "配额管理", "merge_consumption_record 累加正确 (10+5=15)")

    # 2.8 配额不足时的错误分类 - recommend_action
    action_ready = recommend_action(
        auth_exists=True, quota=snapshot, quota_error="", daily={"lastEquityClaimAt": ""}
    )
    check(action_ready == "ready", "配额管理", "配额充足时 recommend_action 返回 'ready'")

    action_quota_low = recommend_action(
        auth_exists=True, quota=QuotaSnapshot(
            raw={}, used_upload=95, total_upload=100, remaining_upload=5,
            gratis_upload=False, free=False,
        ),
        quota_error="",
        daily={"lastEquityClaimAt": ""}
    )
    check(
        action_quota_low == "claim-today",
        "配额管理",
        "配额低且未领取时 recommend_action 返回 'claim-today'",
    )

    action_quota_check_fail = recommend_action(
        auth_exists=True, quota=None, quota_error="quota check failed", daily={}
    )
    check(
        action_quota_check_fail == "quota-check-failed",
        "配额管理",
        "配额检查失败时 recommend_action 返回 'quota-check-failed'",
    )


# ============================================================
# 3. 错误分类体系测试
# ============================================================
def test_error_classification():
    print("\n" + "=" * 60)
    print("3. 错误分类体系测试")
    print("=" * 60)

    # 3.1 ErrorType 枚举完整性
    expected_types = [
        ErrorType.UNKNOWN, ErrorType.NETWORK, ErrorType.QUOTA,
        ErrorType.AUTH, ErrorType.FILE_NOT_FOUND, ErrorType.PERMISSION,
        ErrorType.TIMEOUT, ErrorType.VALIDATION, ErrorType.CANCELLED,
    ]
    for et in expected_types:
        check(et in ErrorType, "错误分类", f"ErrorType.{et.name} 存在")

    # 3.2 网络错误识别
    check(
        classify_error(ConnectionError("connection refused")) == ErrorType.NETWORK,
        "错误分类",
        "ConnectionError 识别为 NETWORK",
    )
    check(
        classify_error(Exception("socket error")) == ErrorType.NETWORK,
        "错误分类",
        "socket 关键词识别为 NETWORK",
    )
    check(
        classify_error(Exception("DNS resolve failed")) == ErrorType.NETWORK,
        "错误分类",
        "DNS 关键词识别为 NETWORK",
    )

    # 3.3 认证错误识别
    check(
        classify_error(Exception("unauthorized access")) == ErrorType.AUTH,
        "错误分类",
        "unauthorized 关键词识别为 AUTH",
    )
    check(
        classify_error(Exception("401 error")) == ErrorType.AUTH,
        "错误分类",
        "401 状态码识别为 AUTH",
    )
    check(
        classify_error(Exception("token expired")) == ErrorType.AUTH,
        "错误分类",
        "token 关键词识别为 AUTH",
    )
    check(
        classify_error(Exception("credential invalid")) == ErrorType.AUTH,
        "错误分类",
        "credential 关键词识别为 AUTH",
    )
    check(
        classify_error(Exception("403 forbidden")) == ErrorType.AUTH,
        "错误分类",
        "403 状态码识别为 AUTH",
    )

    # 3.4 配额错误识别
    check(
        classify_error(Exception("quota exceeded")) == ErrorType.QUOTA,
        "错误分类",
        "quota exceeded 识别为 QUOTA",
    )
    check(
        classify_error(Exception("rate limit 429")) == ErrorType.QUOTA,
        "错误分类",
        "rate limit 429 识别为 QUOTA",
    )
    check(
        classify_error(Exception("too many requests")) == ErrorType.QUOTA,
        "错误分类",
        "too many requests 识别为 QUOTA",
    )

    # 3.5 超时错误识别
    check(
        classify_error(Exception("request timed out")) == ErrorType.TIMEOUT,
        "错误分类",
        "timed out 识别为 TIMEOUT",
    )
    check(
        classify_error(Exception("deadline exceeded")) == ErrorType.TIMEOUT,
        "错误分类",
        "deadline 识别为 TIMEOUT",
    )

    # 3.6 文件不存在错误识别
    check(
        classify_error(FileNotFoundError("no such file")) == ErrorType.FILE_NOT_FOUND,
        "错误分类",
        "no such file 识别为 FILE_NOT_FOUND",
    )
    check(
        classify_error(Exception("file not found")) == ErrorType.FILE_NOT_FOUND,
        "错误分类",
        "file not found 识别为 FILE_NOT_FOUND",
    )

    # 3.7 权限错误识别
    check(
        classify_error(Exception("permission denied")) == ErrorType.PERMISSION,
        "错误分类",
        "permission denied 识别为 PERMISSION",
        # Note: "permission denied" matches AUTH first in classify_error
        # This is a known behavior - AUTH check comes before PERMISSION
    )

    # 3.8 验证错误识别
    check(
        classify_error(Exception("invalid format")) == ErrorType.VALIDATION,
        "错误分类",
        "invalid 识别为 VALIDATION",
    )

    # 3.9 未知错误
    check(
        classify_error(Exception("some random error")) == ErrorType.UNKNOWN,
        "错误分类",
        "无匹配关键词返回 UNKNOWN",
    )

    # 3.10 TimeoutError 类型匹配
    check(
        classify_error(TimeoutError("operation timed out")) == ErrorType.TIMEOUT,
        "错误分类",
        "TimeoutError 类型识别 (通过 error_type)",
    )


# ============================================================
# 4. 日志模块测试
# ============================================================
def test_logger_module():
    print("\n" + "=" * 60)
    print("4. 日志模块测试")
    print("=" * 60)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "test_logs"

        # 4.1 日志初始化
        logger = MediaLogger(name="test_logger", log_dir=log_dir, level=logging.DEBUG)
        check(log_dir.exists(), "日志模块", "日志目录自动创建")

        # 4.2 各级别日志写入
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        check(True, "日志模块", "各级别日志调用无异常")

        # 4.3 操作日志
        logger.log_operation("测试操作", "success", "detail info", 1.5)
        logger.log_operation("失败操作", "failed", "error detail", 2.0)
        logger.log_operation("警告操作", "warning", "warning detail", 0.5)
        check(True, "日志模块", "log_operation 格式化调用无异常")

        # 4.4 日志文件创建
        today_str = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"media_tools_{today_str}.log"
        check(log_file.exists(), "日志模块", f"日志文件创建: {log_file.name}")

        if log_file.exists():
            content = log_file.read_text(encoding="utf-8")
            check("info message" in content, "日志模块", "INFO 日志写入文件")
            check("error message" in content, "日志模块", "ERROR 日志写入文件")
            check("debug message" in content, "日志模块", "DEBUG 日志写入文件")

        # 4.5 错误日志文件
        error_file = log_dir / f"error_{today_str}.log"
        check(error_file.exists(), "日志模块", f"错误日志文件创建: {error_file.name}")

        # 4.6 日志轮转/清理测试
        # 创建旧日志文件
        old_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
        old_log = log_dir / f"media_tools_{old_date}.log"
        old_log.write_text("old log content", encoding="utf-8")

        # 修改文件时间为 60 天前
        old_time = (datetime.now() - timedelta(days=60)).timestamp()
        import os
        os.utime(old_log, (old_time, old_time))

        check(old_log.exists(), "日志模块", "旧日志文件创建成功 (60天前)")

        # 测试清理
        logger2 = MediaLogger(name="test_logger2", log_dir=log_dir, max_age_days=30)
        logger2._cleanup_old_logs()
        check(
            not old_log.exists(),
            "日志模块",
            "超过 30 天的旧日志被清理",
        )

        # 今天的日志不应被清理
        check(
            log_file.exists(),
            "日志模块",
            "当天日志未被清理",
        )

        # 4.7 get_logger 单例
        from media_tools.logger import get_logger
        g1 = get_logger("singleton_test")
        g2 = get_logger("singleton_test")
        check(g1 is g2, "日志模块", "get_logger 返回单例")


# ============================================================
# 5. 健康检查测试
# ============================================================
def test_health_check():
    print("\n" + "=" * 60)
    print("5. 健康检查测试")
    print("=" * 60)

    # 5.1 HealthChecker 初始化
    checker = HealthChecker()
    check(checker.checks == [], "健康检查", "HealthChecker 初始化为空")
    check(hasattr(checker, "run_all_checks"), "健康检查", "run_all_checks 方法存在")

    # 5.2 add_check 方法
    checker.add_check("测试检查", True, "测试通过")
    check(len(checker.checks) == 1, "健康检查", "add_check 添加检查项")
    check(checker.checks[0]["name"] == "测试检查", "健康检查", "检查项名称正确")
    check(checker.checks[0]["status"] is True, "健康检查", "检查项状态正确")

    # 5.3 _all_passed
    checker2 = HealthChecker()
    checker2.add_check("pass", True, "ok")
    check(checker2._all_passed(), "健康检查", "全部通过时 _all_passed 返回 True")

    checker3 = HealthChecker()
    checker3.add_check("pass", True, "ok")
    checker3.add_check("fail", False, "error")
    check(not checker3._all_passed(), "健康检查", "有失败时 _all_passed 返回 False")

    # 5.4 磁盘空间检查 (实际执行)
    checker4 = HealthChecker()
    checker4.check_disk_space()
    disk_check = [c for c in checker4.checks if c["name"] == "磁盘空间"]
    check(len(disk_check) == 1, "健康检查", "磁盘空间检查已执行")

    # 5.5 Git 状态检查 (实际执行)
    checker5 = HealthChecker()
    checker5.check_git_status()
    git_check = [c for c in checker5.checks if c["name"] == "Git状态"]
    check(len(git_check) == 1, "健康检查", "Git状态检查已执行")


# ============================================================
# 6. 性能监控测试
# ============================================================
def test_perf_monitor():
    print("\n" + "=" * 60)
    print("6. 性能监控测试")
    print("=" * 60)

    tracker = PerformanceTracker()

    # 6.1 track 上下文管理器
    with tracker.track("测试操作"):
        time.sleep(0.01)
    check(len(tracker.operations) == 1, "性能监控", "track 上下文记录操作")
    check(tracker.operations[0]["name"] == "测试操作", "性能监控", "操作名称正确")
    check(tracker.operations[0]["duration"] > 0, "性能监控", "操作时长 > 0")

    # 6.2 多个操作
    with tracker.track("操作A"):
        time.sleep(0.01)
    with tracker.track("操作B"):
        time.sleep(0.02)
    check(len(tracker.operations) == 3, "性能监控", "多个操作正确记录")

    # 6.3 get_operation_duration
    duration = tracker.get_operation_duration("操作A")
    check(duration is not None and duration > 0, "性能监控", "get_operation_duration 返回有效值")
    check(tracker.get_operation_duration("不存在") is None, "性能监控", "不存在的操作返回 None")

    # 6.4 get_total_duration
    total = tracker.get_total_duration()
    check(total > 0, "性能监控", f"get_total_duration 返回有效值 ({total:.3f}s)")

    # 6.5 get_slow_operations
    tracker2 = PerformanceTracker()
    with tracker2.track("快操作"):
        time.sleep(0.01)
    with tracker2.track("慢操作"):
        time.sleep(0.1)
    slow = tracker2.get_slow_operations(threshold=0.05)
    check(len(slow) == 1, "性能监控", "慢操作检测正确")
    check(slow[0]["name"] == "慢操作", "性能监控", "慢操作名称正确")

    # 6.6 get_summary
    summary = tracker2.get_summary()
    check(summary["total_operations"] == 2, "性能监控", "summary total_operations 正确")
    check(summary["total_duration"] > 0, "性能监控", "summary total_duration > 0")
    check(summary["slowest_operation"] is not None, "性能监控", "summary slowest_operation 存在")
    check(summary["fastest_operation"] is not None, "性能监控", "summary fastest_operation 存在")

    # 6.7 display_report (不操作时)
    tracker3 = PerformanceTracker()
    buf = StringIO()
    from rich.console import Console
    console = Console(file=buf, force_terminal=True)
    # 用 patch 替换全局 console
    import media_tools.perf_monitor as pm
    old_console = pm.console
    pm.console = console
    tracker3.display_report()
    pm.console = old_console
    output = buf.getvalue()
    check("暂无性能数据" in output, "性能监控", "空数据时显示 '暂无性能数据'")


# ============================================================
# 7. 统计面板测试
# ============================================================
def test_stats_panel():
    print("\n" + "=" * 60)
    print("7. 统计面板测试")
    print("=" * 60)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        stats_file = Path(tmpdir) / ".usage_stats.json"

        # 7.1 初始化
        collector = StatsCollector()
        collector.stats_file = stats_file
        check(collector.stats["total_downloads"] == 0, "统计面板", "初始下载数 = 0")
        check(collector.stats["total_transcribes"] == 0, "统计面板", "初始转写数 = 0")
        check(collector.stats["total_words"] == 0, "统计面板", "初始字数 = 0")

        # 7.2 记录下载
        collector.record_download("创作者A", video_count=3)
        check(collector.stats["total_downloads"] == 3, "统计面板", "记录下载数正确")
        check(collector.stats["creators"]["创作者A"]["videos"] == 3, "统计面板", "创作者视频数正确")

        # 7.3 记录转写
        collector.record_transcribe("创作者A", word_count=5000)
        check(collector.stats["total_transcribes"] == 1, "统计面板", "记录转写数正确")
        check(collector.stats["total_words"] == 5000, "统计面板", "记录字数正确")
        check(collector.stats["creators"]["创作者A"]["words"] == 5000, "统计面板", "创作者字数正确")

        # 7.4 保存和加载
        collector.save_stats()
        check(stats_file.exists(), "统计面板", "统计文件已保存")

        collector2 = StatsCollector()
        collector2.stats_file = stats_file
        collector2.stats = collector2._load_stats()
        check(collector2.stats["total_downloads"] == 3, "统计面板", "从文件加载统计数据正确")

        # 7.5 get_summary
        summary = collector.get_summary()
        check("days_active" in summary, "统计面板", "summary 包含 days_active")
        check("estimated_hours_saved" in summary, "统计面板", "summary 包含 estimated_hours_saved")
        check(summary["total_downloads"] == 3, "统计面板", "summary downloads 正确")

        # 7.6 get_top_creators
        collector.record_download("创作者B", video_count=5)
        collector.record_download("创作者C", video_count=2)
        top = collector.get_top_creators(limit=3)
        check(len(top) == 3, "统计面板", "get_top_creators 返回正确数量")
        check(top[0]["name"] == "创作者B", "统计面板", "排行第一名正确 (5 videos)")
        check(top[1]["name"] == "创作者A", "统计面板", "排行第二名正确 (3 videos)")


# ============================================================
# 8. PipelineStateManager 断点续传测试
# ============================================================
def test_pipeline_state():
    print("\n" + "=" * 60)
    print("8. Pipeline 状态管理测试")
    print("=" * 60)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "test_state.json"

        # 8.1 初始化
        mgr = PipelineStateManager(state_file)
        check(state_file.parent.exists(), "状态管理", "状态文件父目录存在")

        # 8.2 获取新状态
        video_path = Path("/tmp/test_video.mp4")
        state = mgr.get_state(video_path)
        check(state.video_path == str(video_path), "状态管理", "get_state 创建新状态")
        check(state.status == "pending", "状态管理", "初始状态为 pending")

        # 8.3 更新状态
        mgr.update_state(video_path, status="running", attempt=1, max_attempts=3)
        state = mgr.get_state(video_path)
        check(state.status == "running", "状态管理", "状态更新为 running")
        check(state.attempt == 1, "状态管理", "尝试次数正确")
        check(state.started_at > 0, "状态管理", "started_at 已设置")

        # 8.4 状态持久化
        check(state_file.exists(), "状态管理", "状态文件已创建")
        loaded_data = json.loads(state_file.read_text())
        check(str(video_path) in loaded_data, "状态管理", "状态数据已写入 JSON")

        # 8.5 成功状态
        mgr.update_state(
            video_path, status="success", attempt=1, max_attempts=3,
            transcript_path="/tmp/output.md"
        )
        state = mgr.get_state(video_path)
        check(state.status == "success", "状态管理", "状态更新为 success")
        check(state.transcript_path == "/tmp/output.md", "状态管理", "transcript_path 正确")
        check(state.completed_at > 0, "状态管理", "completed_at 已设置")

        # 8.6 can_retry 属性
        video2 = Path("/tmp/test_video2.mp4")
        mgr.update_state(video2, status="failed", attempt=1, max_attempts=3,
                         error_type="network", error_message="timeout")
        state2 = mgr.get_state(video2)
        check(state2.can_retry is True, "状态管理", "失败且 attempt < max 时可重试")

        # 8.7 不可重试 (已达最大次数)
        video3 = Path("/tmp/test_video3.mp4")
        mgr.update_state(video3, status="failed", attempt=3, max_attempts=3,
                         error_type="auth", error_message="token expired")
        state3 = mgr.get_state(video3)
        check(state3.can_retry is False, "状态管理", "已达最大尝试次数时不可重试")

        # 8.8 get_pending_videos
        pending = mgr.get_pending_videos([video_path, video2, video3])
        check(len(pending) == 2, "状态管理", f"待处理视频数量正确 (跳过1个success, 得到{len(pending)}个)")
        check(video_path not in pending, "状态管理", "已成功的视频不在待处理列表")

        # 8.9 clear_completed
        cleared = mgr.clear_completed()
        check(cleared == 1, "状态管理", "clear_completed 返回清除数量")

        # 8.10 reset_all
        mgr.reset_all()
        check(len(mgr.states) == 0, "状态管理", "reset_all 清空所有状态")


# ============================================================
# 9. RetryConfig 和 VideoState 测试
# ============================================================
def test_retry_config():
    print("\n" + "=" * 60)
    print("9. RetryConfig 和 VideoState 测试")
    print("=" * 60)

    # 9.1 默认配置
    rc = RetryConfig()
    check(rc.max_retries == 3, "重试配置", "默认 max_retries = 3")
    check(rc.base_delay == 1.0, "重试配置", "默认 base_delay = 1.0")
    check(rc.max_delay == 60.0, "重试配置", "默认 max_delay = 60.0")
    check(ErrorType.NETWORK in rc.retryable_errors, "重试配置", "NETWORK 在可重试列表中")
    check(ErrorType.TIMEOUT in rc.retryable_errors, "重试配置", "TIMEOUT 在可重试列表中")
    check(ErrorType.QUOTA in rc.retryable_errors, "重试配置", "QUOTA 在可重试列表中")
    check(ErrorType.AUTH not in rc.retryable_errors, "重试配置", "AUTH 不在可重试列表中 (正确)")

    # 9.2 VideoState 属性
    vs = VideoState(video_path="/tmp/test.mp4", status="pending", attempt=0, max_attempts=3)
    check(vs.can_retry is False, "VideoState", "pending 状态 can_retry = False")

    vs2 = VideoState(video_path="/tmp/test.mp4", status="failed", attempt=1, max_attempts=3)
    check(vs2.can_retry is True, "VideoState", "failed 且 attempt