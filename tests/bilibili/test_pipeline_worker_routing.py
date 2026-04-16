from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from media_tools.pipeline.worker import run_pipeline_for_user


class PipelineWorkerRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_download_uses_router(self) -> None:
        update_progress = AsyncMock()
        download_mock = AsyncMock()
        orchestrator = SimpleNamespace(transcribe_with_retry=AsyncMock())
        fake_config = SimpleNamespace()

        with patch("media_tools.pipeline.download_router.download_by_url", download_mock), patch(
            "media_tools.pipeline.worker.asyncio.to_thread",
            new=AsyncMock(return_value={"success": True, "new_files": ["/tmp/video.mp4"]}),
        ) as mocked_to_thread, patch(
            "media_tools.pipeline.config.load_pipeline_config",
            return_value=fake_config,
        ), patch(
            "media_tools.pipeline.orchestrator_v2.create_orchestrator",
            return_value=orchestrator,
        ):
            result = await run_pipeline_for_user(
                url="https://space.bilibili.com/123",
                max_counts=1,
                update_progress_fn=update_progress,
                delete_after=False,
            )

        self.assertEqual(result, {"success_count": 1, "failed_count": 0})
        mocked_to_thread.assert_awaited_once()
        self.assertIs(mocked_to_thread.await_args.args[0], download_mock)
        self.assertEqual(
            mocked_to_thread.await_args.args[1:],
            ("https://space.bilibili.com/123", 1, True, True),
        )


if __name__ == "__main__":
    unittest.main()

