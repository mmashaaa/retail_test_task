"""Saved Reports library. The DB itself is read-only re: BigQuery, but this
local library supports create/list/delete. Deletes are destructive and must
pass a confirmation gate (handled in the graph). Users may only delete their
own reports.
"""
import sqlite3
from datetime import datetime, timezone

from . import config


def _conn():
    c = sqlite3.connect(config.REPORTS_DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS saved_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def save_report(user_id: str, title: str, content: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO saved_reports (user_id, title, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, title, content, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def list_reports(user_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM saved_reports WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_by_id(user_id: str, rid: int) -> dict | None:
    """Fetch a single report by id, scoped to its owner."""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM saved_reports WHERE user_id = ? AND id = ?",
            (user_id, rid)).fetchone()
    return dict(row) if row else None


def find_reports(user_id: str, keyword: str = None,
                 on_date: str = None) -> list[dict]:
    """Find a user's reports matching a keyword (in title/content) and/or a
    specific UTC date (YYYY-MM-DD). Scoped to the requesting user only."""
    query = "SELECT * FROM saved_reports WHERE user_id = ?"
    params: list = [user_id]
    if keyword:
        query += " AND (title LIKE ? OR content LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    if on_date:
        query += " AND substr(created_at, 1, 10) = ?"
        params.append(on_date)
    query += " ORDER BY created_at DESC"
    with _conn() as c:
        rows = c.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def delete_reports(user_id: str, ids: list[int]) -> int:
    """Delete reports by id, scoped to the owner. Returns rows deleted."""
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    with _conn() as c:
        cur = c.execute(
            f"DELETE FROM saved_reports WHERE user_id = ? AND id IN ({placeholders})",
            [user_id, *ids],
        )
        return cur.rowcount
