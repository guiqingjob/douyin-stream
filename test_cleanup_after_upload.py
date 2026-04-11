#!/usr/bin/env python3
"""测试上传后自动删除功能

验证两个删除功能：
1. delete_after_export=True → 删除云端转写记录
2. remove_video=True + keep_original=False → 删除本地原视频
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from src.media_tools.pipeline.config import PipelineConfig, load_pipeline_config
from src.media_tools.pipeline.orchestrator import transcribe_video, PipelineResult
from src.media_tools.transcribe.flow import FlowResult
from src.media_tools.transcribe.runtime import ExportConfig


def test_config_defaults():
    """测试配置默认值"""
    print("=" * 60)
    print("  测试 1: 配置默认值")
    print("=" * 60)
    
    config = PipelineConfig()
    print(f"  delete_after_export: {config.delete_after_export}")
    print(f"  remove_video: {config.remove_video}")
    print(f"  keep_original: {config.keep_original}")
    
    # 验证默认值
    assert config.delete_after_export == True, "默认应该开启云端删除"
    assert config.remove_video == False, "默认不应该删除本地视频"
    assert config.keep_original == True, "默认应该保留原文件"
    
    print("  ✅ 配置默认值正确\n")


def test_config_from_env():
    """测试环境变量配置"""
    print("=" * 60)
    print("  测试 2: 环境变量配置")
    print("=" * 60)
    
    import os
    
    # 模拟环境变量
    os.environ["PIPELINE_DELETE_AFTER_EXPORT"] = "true"
    os.environ["PIPELINE_REMOVE_VIDEO"] = "true"
    os.environ["PIPELINE_KEEP_ORIGINAL"] = "false"
    
    config = load_pipeline_config()
    print(f"  delete_after_export: {config.delete_after_export}")
    print(f"  remove_video: {config.remove_video}")
    print(f"  keep_original: {config.keep_original}")
    
    assert config.delete_after_export == True
    assert config.remove_video == True
    assert config.keep_original == False
    
    # 清理环境变量
    del os.environ["PIPELINE_DELETE_AFTER_EXPORT"]
    del os.environ["PIPELINE_REMOVE_VIDEO"]
    del os.environ["PIPELINE_KEEP_ORIGINAL"]
    
    print("  ✅ 环境变量配置正确\n")


async def test_local_video_deletion():
    """测试本地视频删除功能"""
    print("=" * 60)
    print("  测试 3: 本地视频删除")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # 创建模拟视频文件
        video_file = tmp_path / "test_video.mp4"
        video_file.write_text("fake video content")
        assert video_file.exists(), "测试文件应该存在"
        print(f"  📹 创建测试视频: {video_file}")
        
        # 配置：删除本地视频
        config = PipelineConfig(
            remove_video=True,
            keep_original=False,
            delete_after_export=True,
            output_dir=str(tmp_path / "output"),
        )
        
        # Mock 转写流程
        flow_result = FlowResult(
            record_id="test-record",
            gen_record_id="test-gen-record",
            export_path=tmp_path / "output" / "test_video.md",
            remote_deleted=True,
        )
        
        # 创建输出目录
        (tmp_path / "output").mkdir(exist_ok=True)
        
        with patch("src.media_tools.pipeline.orchestrator.run_real_flow", 
                   new=AsyncMock(return_value=flow_result)):
            result = await transcribe_video(
                video_path=video_file,
                config=config,
                auth_state_path=tmp_path / "auth.json",
            )
        
        print(f"  ✅ 转写完成")
        print(f"  📁 检查本地文件: {video_file}")
        
        # 验证文件被删除
        if not video_file.exists():
            print(f"  🗑️  本地视频已删除 ✅")
        else:
            print(f"  ❌ 本地视频未被删除")
            raise AssertionError("本地视频应该被删除！")
    
    print()


async def test_local_video_kept():
    """测试保留本地视频功能"""
    print("=" * 60)
    print("  测试 4: 保留本地视频")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # 创建模拟视频文件
        video_file = tmp_path / "test_video.mp4"
        video_file.write_text("fake video content")
        print(f"  📹 创建测试视频: {video_file}")
        
        # 配置：保留本地视频
        config = PipelineConfig(
            remove_video=False,  # 不删除
            keep_original=True,
            delete_after_export=True,
            output_dir=str(tmp_path / "output"),
        )
        
        # Mock 转写流程
        flow_result = FlowResult(
            record_id="test-record",
            gen_record_id="test-gen-record",
            export_path=tmp_path / "output" / "test_video.md",
            remote_deleted=True,
        )
        
        (tmp_path / "output").mkdir(exist_ok=True)
        
        with patch("src.media_tools.pipeline.orchestrator.run_real_flow", 
                   new=AsyncMock(return_value=flow_result)):
            result = await transcribe_video(
                video_path=video_file,
                config=config,
                auth_state_path=tmp_path / "auth.json",
            )
        
        print(f"  ✅ 转写完成")
        print(f"  📁 检查本地文件: {video_file}")
        
        # 验证文件保留
        if video_file.exists():
            print(f"  ✅ 本地视频已保留")
        else:
            print(f"  ❌ 本地视频被意外删除")
            raise AssertionError("本地视频应该被保留！")
    
    print()


async def test_cloud_deletion_flag():
    """测试云端删除标志传递"""
    print("=" * 60)
    print("  测试 5: 云端删除标志传递")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        video_file = tmp_path / "test_video.mp4"
        video_file.write_text("fake video content")
        
        # 配置：开启云端删除
        config = PipelineConfig(
            delete_after_export=True,
            output_dir=str(tmp_path / "output"),
        )
        
        (tmp_path / "output").mkdir(exist_ok=True)
        
        # Mock 并检查 should_delete 参数
        mock_run = AsyncMock(return_value=FlowResult(
            record_id="test",
            gen_record_id="test-gen",
            export_path=tmp_path / "output" / "test.md",
            remote_deleted=True,
        ))
        
        with patch("src.media_tools.pipeline.orchestrator.run_real_flow", new=mock_run):
            await transcribe_video(
                video_path=video_file,
                config=config,
                auth_state_path=tmp_path / "auth.json",
            )
        
        # 验证 should_delete=True 被传递
        call_kwargs = mock_run.call_args.kwargs
        print(f"  should_delete 参数: {call_kwargs.get('should_delete')}")
        
        if call_kwargs.get('should_delete') == True:
            print(f"  ✅ 云端删除标志正确传递")
        else:
            raise AssertionError("should_delete 应该为 True！")
    
    print()


async def main():
    """运行所有测试"""
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "上传后自动删除功能测试" + " " * 24 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 测试 1: 配置默认值
    test_config_defaults()
    
    # 测试 2: 环境变量配置
    test_config_from_env()
    
    # 测试 3: 本地视频删除
    await test_local_video_deletion()
    
    # 测试 4: 保留本地视频
    await test_local_video_kept()
    
    # 测试 5: 云端删除标志
    await test_cloud_deletion_flag()
    
    print("=" * 60)
    print("  ✅ 所有测试通过！")
    print("=" * 60)
    print()
    print("功能总结：")
    print("  1. delete_after_export=True → 删除云端转写记录 ✅")
    print("  2. remove_video=True + keep_original=False → 删除本地视频 ✅")
    print("  3. remove_video=False → 保留本地视频 ✅")
    print()


if __name__ == "__main__":
    asyncio.run(main())
