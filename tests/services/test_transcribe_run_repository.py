"""TranscribeRunRepository 的 round-trip 测试。

覆盖：create / update_stage（含 extra 字段）/ mark_saved（清错语义）/
mark_failed（按阶段记录错误）/ find_resumable（仅返回上传后 + 同账号）/
find_saved_for_asset（跨账号去重），以及 init_db 建出来的表/索引齐全。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from media_tools.db.core import init_db
from media_tools.repositories.transcribe_run_repository import (
    RESUMABLE_STAGES,
    TERMINAL_STAGES,
    TranscribeRunRepository,
)


@pytest.fixture
def db(tmp_path: Path):
    db_file = tmp_path / "transcribe_runs.db"
    init_db(str(db_file))
    conn = sqlite3.connect(db_file, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    with patch(
        "media_tools.repositories.transcribe_run_repository.get_db_connection",
        return_value=conn,
    ):
        yield conn
    conn.close()


def test_table_and_indexes_exist(tmp_path: Path) -> None:
    db_file = tmp_path / "schema.db"
    init_db(str(db_file))
    with sqlite3.connect(db_file) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(transcribe_runs)").fetchall()}
        idx_names = {r[1] for r in conn.execute("PRAGMA index_list(transcribe_runs)").fetchall()}

    expected_cols = {
        "run_id", "asset_id", "video_path", "account_id", "task_id", "stage",
        "record_id", "gen_record_id", "batch_id", "export_task_id", "export_url",
        "transcript_path", "last_error", "error_stage", "error_type",
        "created_at", "updated_at",
    }
    assert expected_cols.issubset(cols), f"missing: {expected_cols - cols}"
    assert "idx_transcribe_runs_asset_account" in idx_names
    assert "idx_transcribe_runs_asset_stage" in idx_names
    assert "idx_transcribe_runs_stage_updated" in idx_names


def test_create_then_update_stage_then_mark_saved(db: sqlite3.Connection) -> None:
    run_id = TranscribeRunRepository.create(
        asset_id="asset-1",
        video_path="/tmp/x.mp4",
        account_id="acc-1",
        task_id="task-1",
    )
    assert run_id

    row = TranscribeRunRepository.get(run_id)
    assert row["stage"] == "queued"
    assert row["asset_id"] == "asset-1"
    assert row["created_at"] == row["updated_at"]

    TranscribeRunRepository.update_stage(
        run_id, "uploaded",
        {"record_id": "rec-1", "gen_record_id": "gen-1"},
    )
    row = TranscribeRunRepository.get(run_id)
    assert row["stage"] == "uploaded"
    assert row["record_id"] == "rec-1"
    assert row["gen_record_id"] == "gen-1"
    assert row["updated_at"] >= row["created_at"]

    TranscribeRunRepository.update_stage(run_id, "exporting", {"export_url": "https://x"})
    row = TranscribeRunRepository.get(run_id)
    assert row["stage"] == "exporting"
    assert row["export_url"] == "https://x"
    # 之前写过的字段不会被清掉
    assert row["gen_record_id"] == "gen-1"

    TranscribeRunRepository.mark_saved(run_id, "/output/x.docx")
    row = TranscribeRunRepository.get(run_id)
    assert row["stage"] == "saved"
    assert row["transcript_path"] == "/output/x.docx"
    assert row["last_error"] is None
    assert row["error_stage"] is None
    assert row["error_type"] is None


def test_mark_failed_records_stage_and_truncates_long_error(db: sqlite3.Connection) -> None:
    run_id = TranscribeRunRepository.create(
        asset_id="asset-2", video_path="/tmp/y.mp4", account_id="acc-1",
    )
    TranscribeRunRepository.update_stage(run_id, "exporting", {"gen_record_id": "gen-2"})

    long_err = "E" * 5000
    TranscribeRunRepository.mark_failed(
        run_id,
        error_stage="exporting",
        error_type="quota",
        last_error=long_err,
    )
    row = TranscribeRunRepository.get(run_id)
    assert row["stage"] == "failed"
    assert row["error_stage"] == "exporting"
    assert row["error_type"] == "quota"
    assert len(row["last_error"]) == 2000  # repo 截到 2000


def test_find_resumable_filters_by_stage_and_account(db: sqlite3.Connection) -> None:
    # acc-1 上一条 uploaded 但没 gen_record_id（不应被返回，因为 SQL 强制 gen_record_id NOT NULL/!=''）
    no_gen = TranscribeRunRepository.create(
        asset_id="asset-X", video_path="/tmp/x.mp4", account_id="acc-1",
    )
    TranscribeRunRepository.update_stage(no_gen, "uploaded", {"record_id": "r-X"})

    # acc-1 上一条 transcribing 且 gen_record_id 已写 -> 应当被返回
    resumable = TranscribeRunRepository.create(
        asset_id="asset-X", video_path="/tmp/x.mp4", account_id="acc-1",
    )
    TranscribeRunRepository.update_stage(
        resumable, "transcribing",
        {"gen_record_id": "gen-resume", "record_id": "r-resume"},
    )

    # acc-2 的 run（不同账号）—— 不应命中 acc-1 的查询
    other_acc = TranscribeRunRepository.create(
        asset_id="asset-X", video_path="/tmp/x.mp4", account_id="acc-2",
    )
    TranscribeRunRepository.update_stage(
        other_acc, "uploaded",
        {"gen_record_id": "gen-other", "record_id": "r-other"},
    )

    # 已 saved 的 run（终态）—— 不应命中
    saved = TranscribeRunRepository.create(
        asset_id="asset-X", video_path="/tmp/x.mp4", account_id="acc-1",
    )
    TranscribeRunRepository.update_stage(
        saved, "uploaded", {"gen_record_id": "gen-saved"}
    )
    TranscribeRunRepository.mark_saved(saved, "/out.docx")

    found = TranscribeRunRepository.find_resumable("asset-X", "acc-1")
    assert found is not None
    assert found["run_id"] == resumable
    assert found["gen_record_id"] == "gen-resume"

    # 不同 account 隔离
    found_other = TranscribeRunRepository.find_resumable("asset-X", "acc-2")
    assert found_other is not None
    assert found_other["run_id"] == other_acc

    # 不存在的组合
    assert TranscribeRunRepository.find_resumable("asset-X", "no-such-acc") is None
    assert TranscribeRunRepository.find_resumable("no-such-asset", "acc-1") is None


def test_find_saved_for_asset_returns_latest_saved_run(db: sqlite3.Connection) -> None:
    # 没 saved 时应返回 None
    assert TranscribeRunRepository.find_saved_for_asset("asset-S") is None

    # 一个失败的 run 不算
    failed = TranscribeRunRepository.create(
        asset_id="asset-S", video_path="/tmp/s.mp4", account_id="acc-1",
    )
    TranscribeRunRepository.mark_failed(failed, "uploading", "network", "boom")
    assert TranscribeRunRepository.find_saved_for_asset("asset-S") is None

    # acc-1 上 save 一次 —— 跨账号也能查到
    saved_a = TranscribeRunRepository.create(
        asset_id="asset-S", video_path="/tmp/s.mp4", account_id="acc-1",
    )
    TranscribeRunRepository.mark_saved(saved_a, "/out/v1.docx")
    found = TranscribeRunRepository.find_saved_for_asset("asset-S")
    assert found is not None
    assert found["transcript_path"] == "/out/v1.docx"
    assert found["account_id"] == "acc-1"


def test_resumable_constants_match_doc() -> None:
    """文档承诺的阶段集合不能被随手改掉。"""
    assert RESUMABLE_STAGES == ("uploaded", "transcribing", "exporting", "downloading")
    assert TERMINAL_STAGES == ("saved", "failed")
