"""orchestrator._transcribe_single_video 与 transcribe_runs 的集成测试。

覆盖 Step 11 + Step 12 的端到端契约：
- 没有 resumable run 时 -> create 新 run，最终 mark_saved
- 已有 stage='uploaded' 的 run（同 asset+account） -> 复用 run_id（不新建）
- flow 抛错 -> mark_failed 写入正确的 stage / error_type
- asset_id 解析三段式 fallback 走 DB by video_path
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from media_tools.db.core import init_db
from media_tools.pipeline.config import PipelineConfig
from media_tools.pipeline.error_types import ErrorType
from media_tools.pipeline.models import AccountPool
from media_tools.pipeline.orchestrator_v2 import OrchestratorV2
from media_tools.repositories.transcribe_run_repository import TranscribeRunRepository
from media_tools.transcribe.flow import FlowResult


@pytest.fixture
def db(tmp_path: Path):
    db_file = tmp_path / "orch.db"
    init_db(str(db_file))
    conn = sqlite3.connect(db_file, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    with patch(
        "media_tools.repositories.transcribe_run_repository.get_db_connection",
        return_value=conn,
    ), patch(
        "media_tools.services.media_asset_service.get_db_connection",
        return_value=conn,
    ):
        yield conn
    conn.close()


def _build_orchestrator(tmp_path: Path) -> OrchestratorV2:
    cfg = PipelineConfig(
        export_format="md",
        output_dir=str(tmp_path / "out"),
        delete_after_export=False,
        remove_video=False,
        keep_original=True,
        concurrency=1,
    )
    orch = OrchestratorV2(config=cfg, state_file=tmp_path / ".state.json")
    # 注入一个 1 个账号的 pool，跳过 _resolve_qwen_execution_accounts 的真实查询
    orch._account_pool = AccountPool(
        [{"account_id": "acc-1", "auth_state_path": tmp_path / "auth.json"}],
        [10],
    )
    return orch


def _seed_asset(db: sqlite3.Connection, *, asset_id: str, video_path: Path) -> None:
    db.execute(
        """
        INSERT INTO media_assets
            (asset_id, creator_uid, title, video_path, video_status, transcript_status,
             create_time, update_time)
        VALUES (?, ?, ?, ?, 'downloaded', 'pending', '2025', '2025')
        """,
        (asset_id, "u1", asset_id, str(video_path)),
    )


@pytest.mark.asyncio
async def test_first_attempt_creates_run_and_marks_saved(
    db: sqlite3.Connection, tmp_path: Path
) -> None:
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"x")
    _seed_asset(db, asset_id="asset-OK", video_path=video)

    transcript = tmp_path / "out" / "demo.md"
    transcript.parent.mkdir(parents=True)
    transcript.write_text("ok")

    orch = _build_orchestrator(tmp_path)
    fake_flow = AsyncMock(return_value=FlowResult(
        record_id="rec", gen_record_id="gen",
        export_path=transcript, remote_deleted=False,
    ))

    # 让 asset_id 解析命中 DB（aweme 正则不会命中 'asset-OK'）
    with patch(
        "media_tools.services.media_asset_service.MediaAssetService.find_asset_id_for_video_path",
        return_value="asset-OK",
    ), patch("media_tools.pipeline.orchestrator_v2.run_real_flow", fake_flow):
        result = await orch._transcribe_single_video(video)

    assert result.success
    fake_flow.assert_called_once()
    # flow 被传入了 run_id
    kwargs = fake_flow.call_args.kwargs
    assert kwargs["run_id"]

    # transcribe_runs 应有 1 行 saved
    rows = db.execute("SELECT stage, transcript_path FROM transcribe_runs").fetchall()
    assert len(rows) == 1
    assert rows[0]["stage"] == "saved"
    assert rows[0]["transcript_path"] == str(transcript)


@pytest.mark.asyncio
async def test_existing_resumable_run_is_reused_not_recreated(
    db: sqlite3.Connection, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"x")
    _seed_asset(db, asset_id="asset-RESUME", video_path=video)

    # 预置一个 uploaded 的 run（带 gen_record_id 才会被 find_resumable 命中）
    existing = TranscribeRunRepository.create(
        asset_id="asset-RESUME", video_path=str(video), account_id="acc-1",
    )
    TranscribeRunRepository.update_stage(
        existing, "uploaded",
        {"gen_record_id": "gen-X", "record_id": "rec-X"},
    )

    transcript = tmp_path / "out" / "demo.md"
    transcript.parent.mkdir(parents=True)
    transcript.write_text("ok")

    orch = _build_orchestrator(tmp_path)
    fake_flow = AsyncMock(return_value=FlowResult(
        record_id="rec-X", gen_record_id="gen-X",
        export_path=transcript, remote_deleted=False,
    ))

    caplog.set_level("INFO")
    with patch(
        "media_tools.services.media_asset_service.MediaAssetService.find_asset_id_for_video_path",
        return_value="asset-RESUME",
    ), patch("media_tools.pipeline.orchestrator_v2.run_real_flow", fake_flow):
        result = await orch._transcribe_single_video(video)

    assert result.success

    # 关键：仍只有 1 行 run（复用，不是新建）
    runs = db.execute("SELECT run_id, stage FROM transcribe_runs").fetchall()
    assert len(runs) == 1
    assert runs[0]["run_id"] == existing
    assert runs[0]["stage"] == "saved"

    # flow 收到的 run_id 是已有那条
    assert fake_flow.call_args.kwargs["run_id"] == existing

    # INFO 日志里能看到"发现可续传 run"
    assert any("发现可续传 run" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_failure_marks_run_failed_with_current_stage(
    db: sqlite3.Connection, tmp_path: Path
) -> None:
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"x")
    _seed_asset(db, asset_id="asset-FAIL", video_path=video)

    orch = _build_orchestrator(tmp_path)

    # flow 在 stage 已被推进到 'transcribing' 时抛错；orchestrator 应把 mark_failed
    # 的 error_stage 写成查表所得的当前阶段
    async def flow_that_advances_then_fails(*args, **kwargs):
        run_id = kwargs.get("run_id")
        assert run_id, "expected run_id propagated"
        TranscribeRunRepository.update_stage(run_id, "transcribing", {"batch_id": "b1"})
        raise RuntimeError("network reset")

    with patch(
        "media_tools.services.media_asset_service.MediaAssetService.find_asset_id_for_video_path",
        return_value="asset-FAIL",
    ), patch("media_tools.pipeline.orchestrator_v2.run_real_flow", side_effect=flow_that_advances_then_fails):
        result = await orch._transcribe_single_video(video)

    assert not result.success
    assert result.error_type == ErrorType.NETWORK or "reset" in (result.error or "")

    row = db.execute(
        "SELECT stage, error_stage, error_type, last_error FROM transcribe_runs"
    ).fetchone()
    assert row["stage"] == "failed"
    assert row["error_stage"] == "transcribing"
    assert row["error_type"]  # ErrorType.value 写入
    assert "reset" in (row["last_error"] or "")


@pytest.mark.asyncio
async def test_no_asset_id_skips_run_creation_and_still_runs_flow(
    db: sqlite3.Connection, tmp_path: Path
) -> None:
    """孤儿文件（无法解析 asset_id）也能跑，只是不写 transcribe_runs。"""
    video = tmp_path / "orphan.mp4"
    video.write_bytes(b"x")

    orch = _build_orchestrator(tmp_path)
    transcript = tmp_path / "out" / "orphan.md"
    transcript.parent.mkdir(parents=True)
    transcript.write_text("ok")

    fake_flow = AsyncMock(return_value=FlowResult(
        record_id="r", gen_record_id="g",
        export_path=transcript, remote_deleted=False,
    ))

    with patch(
        "media_tools.services.media_asset_service.MediaAssetService.find_asset_id_for_video_path",
        return_value=None,
    ), patch("media_tools.pipeline.orchestrator_v2.run_real_flow", fake_flow):
        result = await orch._transcribe_single_video(video)

    assert result.success
    # 没 asset_id -> 不传 run_id -> 不写表
    assert fake_flow.call_args.kwargs.get("run_id") is None
    assert db.execute("SELECT COUNT(*) FROM transcribe_runs").fetchone()[0] == 0
