"""SQLite-backed audit log for recording user actions in the Streamlit app."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _get_db_path(db_path: Path | None = None) -> Path:
    """Return db_path if provided, otherwise derive the default path from config.

    The deferred import avoids a circular dependency at module load time.
    """
    if db_path is not None:
        return db_path
    from src.config import get_config
    return get_config().project_root / "audit_log.db"


def _init_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp      TEXT NOT NULL,
                role           TEXT NOT NULL,
                action         TEXT NOT NULL,
                transaction_id TEXT,
                details        TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def log_action(
    role: str,
    action: str,
    transaction_id: str | None = None,
    details: dict | None = None,
    *,
    db_path: Path | None = None,
) -> None:
    """Insert one audit row. details is serialised to JSON."""
    path = _get_db_path(db_path)
    _init_db(path)
    timestamp = datetime.now(timezone.utc).isoformat()
    details_json = json.dumps(details) if details is not None else None
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "INSERT INTO audit_log (timestamp, role, action, transaction_id, details) "
            "VALUES (?, ?, ?, ?, ?)",
            (timestamp, role, action, transaction_id, details_json),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_logs(limit: int = 50, *, db_path: Path | None = None) -> list[dict]:
    """Return up to *limit* rows, newest first.

    Each row is a dict with keys: id, timestamp, role, action, transaction_id, details.
    details is parsed back from JSON when present.
    """
    path = _get_db_path(db_path)
    _init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, timestamp, role, action, transaction_id, details "
            "FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    result = []
    for row in rows:
        entry = dict(row)
        if entry["details"] is not None:
            try:
                entry["details"] = json.loads(entry["details"])
            except json.JSONDecodeError:
                pass
        result.append(entry)
    return result
