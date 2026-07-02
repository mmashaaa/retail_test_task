"""Per-user preferences — the User-Level half of the Learning Loop (req #4).

The agent remembers each manager's preferred report format (e.g. Manager A
likes tables, Manager B likes bullet points). Stored in the same SQLite file
as saved reports. Preferences are read on every report and can be changed by
the user in natural language ("from now on use bullet points").
"""
import sqlite3

from . import config

# Recognised formats -> the instruction injected into the report prompt.
FORMATS = {
    "table": "Format the report as Markdown tables wherever data is tabular.",
    "bullets": "Format the report as concise bullet points.",
    "prose": "Format the report as short narrative paragraphs.",
}
DEFAULT_FORMAT = "prose"

# Seeded so the demo shows the difference immediately (assignment example).
_SEED = {"manager_a": "table", "manager_b": "bullets"}


def _conn():
    c = sqlite3.connect(config.REPORTS_DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_prefs (
                user_id TEXT PRIMARY KEY,
                report_format TEXT NOT NULL
            )
        """)
        for uid, fmt in _SEED.items():
            c.execute(
                "INSERT OR IGNORE INTO user_prefs (user_id, report_format) "
                "VALUES (?, ?)", (uid, fmt))


def get_format(user_id: str) -> str:
    with _conn() as c:
        row = c.execute(
            "SELECT report_format FROM user_prefs WHERE user_id = ?",
            (user_id,)).fetchone()
    return row["report_format"] if row else DEFAULT_FORMAT


def set_format(user_id: str, report_format: str) -> None:
    if report_format not in FORMATS:
        raise ValueError(f"Unknown format: {report_format}")
    with _conn() as c:
        c.execute(
            "INSERT INTO user_prefs (user_id, report_format) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET report_format = excluded.report_format",
            (user_id, report_format))


def format_directive(user_id: str) -> str:
    return FORMATS[get_format(user_id)]
