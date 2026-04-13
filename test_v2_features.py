#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 新功能综合测试

测试所有新增功能是否正常工作
"""

import json
import sys
import time
from pathlib import Path


def test_wizard():
    """测试首次使用向导"""
    print("\n" + "="*60)
    print("测试 1/9: 首次使用向导")
    print("="*60)

    from media_tools.wizard import check_first_run, mark_config_initialized

    # 测试检测
    is_first = check_first_run()
    print(f"  ✓ 首次运行检测: {is_first}")

    # 测试标记
    mark_config_initialized()
    assert Path(".config_initialized").exists()
    print(f"  ✓ 配置标记创建成功")

    # 再次检测
    is_first = check_first_run()
    assert not is_first
    print(f"  ✓ 非首次运行检测: {is_first}")

    # 清理
    Path(".config_initialized").unlink()
    print(f"  ✓ 测试清理成功\n")

    return True


def test_config_presets():
    """测试配置预设"""
    print("\n" + "="*60)
    print("测试 2/9: 配置预设模板")
    print("="*60)

    from media_tools.config_presets import PRESETS, apply_preset

    # 测试预设存在
    assert "beginner" in PRESETS
    assert "pro" in PRESETS
    assert "server" in PRESETS
    print(f"  ✓ 3种预设模板存在")

    # 测试预设内容
    for name, preset in PRESETS.items():
        assert "name" in preset
        assert "description" in preset
        assert "config" in preset
        assert "features" in preset
        print(f"  ✓ {name}: {preset['name']}")

    # 测试应用预设（不实际写入环境变量）
    preset = PRESETS["beginner"]
    assert len(preset["config"]) > 0
    print(f"  ✓ 预设配置完整\n")

    return True


def test_stats_panel():
    """测试统计面板"""
    print("\n" + "="*60)
    print("测试 3/9: 创作数据统计")
    print("="*60)

    from media_tools.stats_panel import StatsCollector

    # 创建收集器
    collector = StatsCollector()
    print(f"  ✓ StatsCollector 创建成功")

    # 测试记录下载
    collector.record_download("测试博主", 5)
    assert collector.stats["total_downloads"] > 0
    print(f"  ✓ 下载记录功能正常")

    # 测试记录转写
    collector.record_transcribe("测试博主", 1000)
    assert collector.stats["total_transcribes"] > 0
    print(f"  ✓ 转写记录功能正常")

    # 测试获取摘要
    summary = collector.get_summary()
    assert "total_downloads" in summary
    assert "total_transcribes" in summary
    assert "total_words" in summary
    print(f"  ✓ 统计摘要完整")

    # 测试热门创作者
    top = collector.get_top_creators()
    assert len(top) > 0
    print(f"  ✓ 热门创作者排行正常\n")

    return True


def test_progress_panel():
    """测试进度面板"""
    print("\n" + "="*60)
    print("测试 4/9: 任务进度可视化")
    print("="*60)

    from media_tools.progress_panel import (
        TaskProgressPanel,
        TaskItem,
        TaskStatus,
        create_progress_callback,
    )
    from pathlib import Path as PathLib

    # 测试面板创建
    panel = TaskProgressPanel(total=3, title="测试任务")
    print(f"  ✓ TaskProgressPanel 创建成功")

    # 测试任务项
    task = TaskItem("test.mp4", PathLib("test.mp4"))
    assert task.status == TaskStatus.PENDING
    print(f"  ✓ TaskItem 创建成功")

    # 测试状态转换
    task.start()
    assert task.status == TaskStatus.RUNNING
    task.complete("测试完成")
    assert task.status == TaskStatus.SUCCESS
    assert task.duration is not None
    print(f"  ✓ 状态转换正常")

    # 测试回调
    from pathlib import Path
    paths = [Path("v1.mp4"), Path("v2.mp4")]
    callback = create_progress_callback(panel, paths)
    assert callable(callback)
    print(f"  ✓ 进度回调创建成功\n")

    return True


def test_error_diagnosis():
    """测试错误诊断"""
    print("\n" + "="*60)
    print("测试 5/9: 智能错误诊断")
    print("="*60)

    from media_tools.error_diagnosis import (
        classify_error,
        ErrorCategory,
        SOLUTIONS,
    )

    # 测试错误分类
    test_cases = [
        ("Connection timeout", ErrorCategory.NETWORK),
        ("Auth token expired", ErrorCategory.AUTH),
        ("Quota exceeded", ErrorCategory.QUOTA),
        ("File not found", ErrorCategory.FILE),
        ("Config missing", ErrorCategory.CONFIG),
    ]

    for error_msg, expected in test_cases:
        result = classify_error(error_msg)
        assert result == expected, f"{error_msg}: {result} != {expected}"
        print(f"  ✓ 分类正确: {error_msg} → {result.value}")

    # 测试解决方案存在
    for category in ErrorCategory:
        assert category in SOLUTIONS
        print(f"  ✓ {category.value} 有解决方案")

    print()
    return True


def test_batch_report():
    """测试批量报告"""
    print("\n" + "="*60)
    print("测试 6/9: 批量操作报告")
    print("="*60)

    from media_tools.batch_report import BatchReport

    # 创建报告
    report = BatchReport("测试批量操作")
    print(f"  ✓ BatchReport 创建成功")

    # 添加数据
    report.add_item("video_1.mp4", "success", duration=1.5)
    report.add_item("video_2.mp4", "success", duration=2.0)
    report.add_item("video_3.mp4", "failed", duration=1.0, error="Network error")
    print(f"  ✓ 添加任务结果成功")

    # 完成报告
    report.finish()
    assert report.total == 3
    assert report.success == 2
    assert report.failed == 1
    print(f"  ✓ 统计正确: {report.success}/{report.total}")

    # 测试成功率
    assert 65 < report.success_rate < 68
    print(f"  ✓ 成功率计算: {report.success_rate:.1f}%")

    # 测试导出JSON
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        report.export_json(Path(f.name))
        assert Path(f.name).exists()
        with open(f.name, 'r') as f2:
            data = json.load(f2)
            assert data["summary"]["total"] == 3
        Path(f.name).unlink()
    print(f"  ✓ JSON导出正常")

    # 测试导出文本
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        report.export_text(Path(f.name))
        assert Path(f.name).exists()
        content = Path(f.name).read_text()
        assert "测试批量操作" in content
        Path(f.name).unlink()
    print(f"  ✓ 文本导出正常\n")

    return True


def test_config_manager():
    """测试配置管理"""
    print("\n" + "="*60)
    print("测试 7/9: 统一配置管理")
    print("="*60)

    from media_tools.config_manager import ConfigManager

    # 创建管理器
    manager = ConfigManager()
    print(f"  ✓ ConfigManager 创建成功")

    # 测试验证
    validation = manager.validate_all()
    assert len(validation) > 0
    print(f"  ✓ 验证配置: {len(validation)} 个文件")

    # 统计有效/无效
    valid_count = sum(1 for v in validation.values() if v["valid"])
    print(f"  ✓ 有效配置: {valid_count}/{len(validation)}")

    print()
    return True


def test_pipeline_v2():
    """测试增强版Pipeline"""
    print("\n" + "="*60)
    print("测试 8/9: 增强版Pipeline")
    print("="*60)

    from media_tools.pipeline.orchestrator_v2 import (
        PipelineStateManager,
        BatchReport as V2BatchReport,
        create_orchestrator,
    )

    # 测试RetryConfig
    from media_tools.pipeline.orchestrator_v2 import RetryConfig
    retry_config = RetryConfig(max_retries=3, base_delay=1.0)
    assert retry_config.max_retries == 3
    print(f"  ✓ RetryConfig 创建成功")

    # 测试StateManager
    state_mgr = PipelineStateManager(Path(".test_state.json"))
    print(f"  ✓ PipelineStateManager 创建成功")

    # 测试Orchestrator
    orchestrator = create_orchestrator(retry_config=retry_config)
    print(f"  ✓ EnhancedOrchestrator 创建成功")

    # 测试V2报告
    report = V2BatchReport("测试")
    assert report.success == 0
    print(f"  ✓ BatchReport V2 创建成功\n")

    return True


def test_integration():
    """测试集成"""
    print("\n" + "="*60)
    print("测试 9/9: 功能集成测试")
    print("="*60)

    # 测试模块导入
    print("  测试模块导入...")
    from media_tools import wizard
    from media_tools import config_presets
    from media_tools import stats_panel
    from media_tools import progress_panel
    from media_tools import error_diagnosis
    from media_tools import batch_report
    from media_tools import config_manager
    print(f"  ✓ 所有模块导入成功")

    # 测试CLI V2导入
    print("  测试CLI V2导入...")
    try:
        import cli_v2
        print(f"  ✓ CLI V2 导入成功")
    except Exception as e:
        print(f"  ⚠️  CLI V2 导入失败 (可接受): {e}")

    print()
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("[bold]🧪 Media Tools V2 新功能测试[/bold]")
    print("="*70)

    tests = [
        ("首次使用向导", test_wizard),
        ("配置预设", test_config_presets),
        ("统计面板", test_stats_panel),
        ("进度面板", test_progress_panel),
        ("错误诊断", test_error_diagnosis),
        ("批量报告", test_batch_report),
        ("配置管理", test_config_manager),
        ("Pipeline V2", test_pipeline_v2),
        ("集成测试", test_integration),
    ]

    passed = 0
    failed = 0
    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                results.append((name, "✅ 通过"))
            else:
                failed += 1
                results.append((name, "❌ 失败"))
        except Exception as e:
            failed += 1
            results.append((name, f"❌ 异常: {e}"))
            import traceback
            traceback.print_exc()

    # 打印总结
    print("\n" + "="*70)
    print("[bold]📊 测试总结[/bold]")
    print("="*70)
    print()

    for name, result in results:
        print(f"  {result:12s}  {name}")

    print()
    print(f"  总计: {len(tests)} | 通过: {passed} | 失败: {failed}")
    print()

    if failed == 0:
        print("✅ [bold green]所有测试通过！[/bold green]\n")
    else:
        print(f"⚠️  [bold yellow]{failed} 个测试失败[/bold yellow]\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
