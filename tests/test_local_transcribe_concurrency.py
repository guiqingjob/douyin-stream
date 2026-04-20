from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import asyncio


@dataclass(frozen=True, slots=True)
class _Result:
    success: bool
    transcript_path: str | None = None


class _FakeOrchestrator:
    def __init__(self) -> None:
        self.transcribe_batch_calls: list[list[Path]] = []
        self.transcribe_with_retry_calls: list[Path] = []

    async def transcribe_batch(self, video_paths: list[Path], resume: bool = True) -> Any:
        self.transcribe_batch_calls.append(video_paths)
        return type(
            "BatchReport",
            (),
            {
                "total": len(video_paths),
                "success": len(video_paths),
                "failed": 0,
                "skipped": 0,
                "results": [
                    {"video_path": str(p), "success": True, "transcript_path": None} for p in video_paths
                ],
            },
        )()

    async def transcribe_with_retry(self, video_path: Path) -> _Result:
        self.transcribe_with_retry_calls.append(video_path)
        return _Result(success=True)


def test_pipeline_config_default_concurrency_is_5() -> None:
    from media_tools.pipeline.config import load_pipeline_config

    config = load_pipeline_config()
    assert config.concurrency == 5


def test_local_transcribe_uses_batch_transcribe(monkeypatch) -> None:
    from media_tools.pipeline.worker import run_local_transcribe

    fake = _FakeOrchestrator()

    def _fake_create_orchestrator(*args, **kwargs):  # noqa: ANN001
        return fake

    monkeypatch.setattr("media_tools.pipeline.orchestrator_v2.create_orchestrator", _fake_create_orchestrator)

    mp3_path = Path("/tmp/local_concurrency_test.mp3")
    mp3_path.write_bytes(b"ok")

    result = asyncio.run(run_local_transcribe([str(mp3_path)], update_progress_fn=None, delete_after=False))
    assert result["total"] == 1
    assert len(fake.transcribe_batch_calls) == 1
    assert fake.transcribe_with_retry_calls == []
