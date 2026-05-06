"""Tests for pipeline steps."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from media_tools.pipeline.interface import PipelineContext, Pipeline, PipelineStep
from media_tools.pipeline.steps import (
    F2VideoDownloadStep,
    FFmpegAudioExtractStep,
    QwenTranscribeStep,
    MarkdownExportStep,
    LocalCleanupStep,
    PipelineStepFactory,
)


class PipelineContextTests(unittest.TestCase):
    """Tests for PipelineContext."""

    def test_context_initial_state(self) -> None:
        """Test PipelineContext initial state."""
        context = PipelineContext()
        self.assertIsNone(context.video_path)
        self.assertIsNone(context.audio_path)
        self.assertIsNone(context.transcript_path)
        self.assertEqual(context.metadata, {})
        self.assertEqual(context.status, "pending")
        self.assertEqual(context.errors, [])
        self.assertEqual(context.step_results, {})

    def test_context_set_get_result(self) -> None:
        """Test set_result and get_result."""
        context = PipelineContext()
        context.set_result("step1", "result1")
        self.assertEqual(context.get_result("step1"), "result1")
        self.assertIsNone(context.get_result("nonexistent"))

    def test_context_is_failed(self) -> None:
        """Test is_failed method."""
        context = PipelineContext()
        self.assertFalse(context.is_failed())
        
        context.status = "failed"
        self.assertTrue(context.is_failed())
        
        context.status = "pending"
        context.add_error(Exception("test error"))
        self.assertTrue(context.is_failed())


class PipelineTests(unittest.TestCase):
    """Tests for Pipeline."""

    @patch("media_tools.pipeline.interface.logger")
    def test_pipeline_executes_steps(self, mock_logger: MagicMock) -> None:
        """Test Pipeline executes steps in order."""
        # 创建模拟步骤
        step1 = MagicMock(spec=PipelineStep)
        step1.name = "step1"
        step1.can_execute.return_value = True
        step1.execute = AsyncMock(return_value=PipelineContext())
        
        step2 = MagicMock(spec=PipelineStep)
        step2.name = "step2"
        step2.can_execute.return_value = True
        step2.execute = AsyncMock(return_value=PipelineContext())
        
        pipeline = Pipeline([step1, step2])
        context = PipelineContext()
        
        # 执行管道
        import asyncio
        result = asyncio.run(pipeline.run(context))
        
        # 验证步骤按顺序执行
        step1.execute.assert_called_once()
        step2.execute.assert_called_once()
        self.assertEqual(result.status, "completed")

    @patch("media_tools.pipeline.interface.logger")
    def test_pipeline_stops_on_failure(self, mock_logger: MagicMock) -> None:
        """Test Pipeline stops when a step fails."""
        step1 = MagicMock(spec=PipelineStep)
        step1.name = "step1"
        step1.can_execute.return_value = True
        step1.execute = AsyncMock(side_effect=Exception("step1 failed"))
        
        step2 = MagicMock(spec=PipelineStep)
        step2.name = "step2"
        
        pipeline = Pipeline([step1, step2])
        context = PipelineContext()
        
        import asyncio
        result = asyncio.run(pipeline.run(context))
        
        # 验证 step2 没有执行
        step2.execute.assert_not_called()
        self.assertTrue(result.is_failed())


class PipelineStepFactoryTests(unittest.TestCase):
    """Tests for PipelineStepFactory."""

    def test_create_download_step(self) -> None:
        """Test creating download step."""
        step = PipelineStepFactory.create_download_step("https://example.com/video")
        self.assertIsInstance(step, F2VideoDownloadStep)

    def test_create_audio_extract_step(self) -> None:
        """Test creating audio extract step."""
        step = PipelineStepFactory.create_audio_extract_step()
        self.assertIsInstance(step, FFmpegAudioExtractStep)

    def test_create_transcribe_step(self) -> None:
        """Test creating transcribe step."""
        step = PipelineStepFactory.create_transcribe_step("account1")
        self.assertIsInstance(step, QwenTranscribeStep)

    def test_create_export_step(self) -> None:
        """Test creating export step."""
        step = PipelineStepFactory.create_export_step(Path("/output"))
        self.assertIsInstance(step, MarkdownExportStep)

    def test_create_cleanup_step(self) -> None:
        """Test creating cleanup step."""
        step = PipelineStepFactory.create_cleanup_step(True)
        self.assertIsInstance(step, LocalCleanupStep)


if __name__ == "__main__":
    unittest.main()