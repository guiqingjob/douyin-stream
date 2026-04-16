from __future__ import annotations

from media_tools.db.core import get_db_connection


def get_bilibili_cookie_string() -> str:
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT cookie_data
            FROM Accounts_Pool
            WHERE platform = 'bilibili' AND status = 'active'
            ORDER BY (last_used IS NULL) ASC, last_used DESC, create_time DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row and row[0]:
            return str(row[0])
    return ""

