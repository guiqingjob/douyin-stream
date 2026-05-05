from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from media_tools.services.log_rotation import archive_old_logs


def _create_log_with_mtime(path: Path, days_ago: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"log {days_ago} days ago")
    target = (datetime.now() - timedelta(days=days_ago)).timestamp()
    os.utime(path, (target, target))


def test_archives_old_log_and_jsonl(tmp_path: Path) -> None:
    old_log = tmp_path / "media_tools_20251001.log"
    new_log = tmp_path / "media_tools_today.log"
    old_jsonl = tmp_path / "structured_old.jsonl"

    _create_log_with_mtime(old_log, days_ago=45)
    _create_log_with_mtime(new_log, days_ago=2)
    _create_log_with_mtime(old_jsonl, days_ago=60)

    outcome = archive_old_logs(tmp_path, days=30)

    assert outcome.archived_count == 2
    assert outcome.failed_count == 0
    assert not old_log.exists()
    assert not old_jsonl.exists()
    assert new_log.exists()  # 仍在 30 天内，不动
    # 归档子目录按 yyyy-mm 分组
    archive_root = tmp_path / "archive"
    assert archive_root.exists()
    archived_files = list(archive_root.rglob("*"))
    assert any(f.name == "media_tools_20251001.log" for f in archived_files)
    assert any(f.name == "structured_old.jsonl" for f in archived_files)


def test_skips_archive_subdir_to_avoid_recursion(tmp_path: Path) -> None:
    archived = tmp_path / "archive" / "2025-08" / "old.log"
    _create_log_with_mtime(archived, days_ago=300)

    outcome = archive_old_logs(tmp_path, days=30)

    assert outcome.archived_count == 0
    assert archived.exists()  # 归档子目录里的文件不会被再归档


def test_skips_non_log_extensions(tmp_path: Path) -> None:
    txt = tmp_path / "old.txt"
    md = tmp_path / "old.md"
    ds_store = tmp_path / ".DS_Store"
    _create_log_with_mtime(txt, days_ago=60)
    _create_log_with_mtime(md, days_ago=60)
    _create_log_with_mtime(ds_store, days_ago=60)

    outcome = archive_old_logs(tmp_path, days=30)

    assert outcome.archived_count == 0
    assert txt.exists()
    assert md.exists()
    assert ds_store.exists()


def test_handles_missing_dir_gracefully(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist"
    outcome = archive_old_logs(nonexistent, days=30)
    assert outcome.archived_count == 0
    assert outcome.failed_count == 0


def test_collision_appends_epoch_suffix(tmp_path: Path) -> None:
    # 让两个不同 mtime 的同名 log 都进入同一个 yyyy-mm 归档目录
    log_a = tmp_path / "duplicate.log"
    _create_log_with_mtime(log_a, days_ago=45)

    # 第一次归档
    archive_old_logs(tmp_path, days=30)

    # 再造一个同名文件，更早一些（不同月）
    log_b = tmp_path / "duplicate.log"
    _create_log_with_mtime(log_b, days_ago=46)
    # 把 log_b 的 mtime 改到与 a 相同的月份制造冲突
    target_dir = tmp_path / "archive"
    same_month_dir = next(target_dir.iterdir())  # 上一次归档创建的 yyyy-mm
    # 复制 log_b 的 mtime 让它落到同一个月
    target_ts = datetime.strptime(same_month_dir.name, "%Y-%m").timestamp() + 86400
    os.utime(log_b, (target_ts, target_ts))

    outcome = archive_old_logs(tmp_path, days=30)
    assert outcome.archived_count == 1
    archived = list(same_month_dir.iterdir())
    assert len(archived) == 2  # 原来 1 个 + 新归档 1 个（带 epoch 后缀）
