import sqlite3
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from media_tools.db.core import get_db_connection

logger = logging.getLogger(__name__)


def reconcile_transcripts():
    project_root = Path(__file__).parent.parent.parent.parent
    transcripts_dir = project_root / "transcripts"

    if not transcripts_dir.exists():
        raise RuntimeError(f"transcripts 目录不存在: {transcripts_dir}")

    results = {
        "creators_found": 0,
        "assets_created": 0,
        "assets_updated": 0,
        "creators_removed": 0,
        "assets_removed": 0,
    }
    now = datetime.now().isoformat()

    actual_folders = set()
    try:
        for folder in list(transcripts_dir.iterdir()):
            if folder.is_dir() and not folder.name.startswith('.'):
                md_files = list(folder.glob("*.md"))
                if md_files:
                    actual_folders.add(folder.name)
    except FileNotFoundError:
        logger.warning(f"transcripts 目录在遍历时被删除: {transcripts_dir}")
        raise RuntimeError("transcripts 目录不存在")

    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row

        local_creators = conn.execute(
            "SELECT uid, nickname FROM creators WHERE platform='local' AND uid LIKE 'local:%'"
        ).fetchall()
        for creator in local_creators:
            nickname = creator['nickname']
            uid = creator['uid']
            if nickname not in actual_folders and nickname != "本地上传":
                deleted = conn.execute("DELETE FROM media_assets WHERE creator_uid = ?", (uid,))
                conn.execute("DELETE FROM creators WHERE uid = ?", (uid,))
                results['creators_removed'] += 1
                results['assets_removed'] += deleted.rowcount
                logger.info(f"Removed local creator '{nickname}' and {deleted.rowcount} assets")

        legacy_uid = "local:upload"
        legacy_assets = conn.execute(
            "SELECT asset_id, title, transcript_path, folder_path FROM media_assets WHERE creator_uid = ?",
            (legacy_uid,)
        ).fetchall()

        creators = conn.execute("SELECT uid, nickname FROM creators").fetchall()
        # 使用 uid 优先，nickname 碰撞时保留最早插入的
        creator_map: dict[str, str] = {}
        for row in creators:
            nickname = row['nickname']
            if nickname not in creator_map:
                creator_map[nickname] = row['uid']

        for asset in legacy_assets:
            folder_name = asset['folder_path'] or ''
            if not folder_name and asset['transcript_path']:
                if '/' in asset['transcript_path']:
                    folder_name = asset['transcript_path'].split('/')[0]

            if not folder_name:
                continue

            target_uid = creator_map.get(folder_name)
            if not target_uid:
                target_uid = f"local:{hashlib.sha1(folder_name.encode()).hexdigest()[:16]}"
                conn.execute(
                    "INSERT OR IGNORE INTO creators (uid, nickname, platform, sync_status, last_fetch_time) VALUES (?, ?, 'local', 'active', ?)",
                    (target_uid, folder_name, now)
                )
                creator_map[folder_name] = target_uid
                results['creators_found'] += 1

            conn.execute(
                "UPDATE media_assets SET creator_uid = ?, folder_path = ? WHERE asset_id = ?",
                (target_uid, folder_name, asset['asset_id'])
            )
            results['assets_updated'] += 1

        conn.execute("DELETE FROM creators WHERE uid = ?", (legacy_uid,))

        for folder_name in actual_folders:
            folder_path = transcripts_dir / folder_name
            creator_uid = creator_map.get(folder_name)

            if not creator_uid:
                creator_uid = f"local:{hashlib.sha1(folder_name.encode()).hexdigest()[:16]}"
                conn.execute(
                    "INSERT OR IGNORE INTO creators (uid, nickname, platform, sync_status, last_fetch_time) VALUES (?, ?, 'local', 'active', ?)",
                    (creator_uid, folder_name, now)
                )
                creator_map[folder_name] = creator_uid
                results['creators_found'] += 1

            batch_count = 0
            for md_file in folder_path.glob("*.md"):
                title = md_file.stem
                asset_id = f"local:{hashlib.sha1(str(md_file.resolve()).encode()).hexdigest()[:24]}"
                relative_path = f"{folder_name}/{md_file.name}"

                existing = conn.execute(
                    "SELECT asset_id FROM media_assets WHERE asset_id = ?",
                    (asset_id,)
                ).fetchone()

                if existing:
                    conn.execute(
                        "UPDATE media_assets SET transcript_status='completed', transcript_path=?, folder_path=?, update_time=? WHERE asset_id=?",
                        (relative_path, folder_name, now, asset_id)
                    )
                    results['assets_updated'] += 1
                else:
                    conn.execute(
                        "INSERT INTO media_assets (asset_id, creator_uid, title, video_status, transcript_status, transcript_path, folder_path, create_time, update_time) VALUES (?, ?, ?, 'downloaded', 'completed', ?, ?, ?, ?)",
                        (asset_id, creator_uid, title, relative_path, folder_name, now, now)
                    )
                    results['assets_created'] += 1

                batch_count += 1
                if batch_count >= 100:
                    conn.commit()
                    batch_count = 0

        empty = conn.execute(
            "SELECT c.uid FROM creators c LEFT JOIN media_assets m ON c.uid=m.creator_uid WHERE c.platform='local' AND m.asset_id IS NULL"
        ).fetchall()
        for row in empty:
            conn.execute("DELETE FROM creators WHERE uid = ?", (row['uid'],))
            results['creators_removed'] += 1

        conn.commit()

    return {"status": "success", **results}
