"""Smoke tests for src/audit_log.py — uses a temp SQLite path, no real config needed."""

import tempfile
from pathlib import Path

from src.audit_log import get_recent_logs, log_action


def test_write_and_read():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test_audit.db"
        log_action(
            "Reviewer",
            "test_action",
            transaction_id="TX123",
            details={"k": "v"},
            db_path=db,
        )
        logs = get_recent_logs(limit=10, db_path=db)
        assert len(logs) == 1
        row = logs[0]
        assert row["role"] == "Reviewer"
        assert row["action"] == "test_action"
        assert row["transaction_id"] == "TX123"
        assert isinstance(row["details"], dict)
        assert row["details"]["k"] == "v"


def test_multiple_logs_newest_first():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test_audit.db"
        log_action("Reviewer", "first", db_path=db)
        log_action("Senior Auditor", "second", db_path=db)
        logs = get_recent_logs(limit=10, db_path=db)
        assert logs[0]["action"] == "second"
        assert logs[1]["action"] == "first"


def test_null_transaction_id_and_details():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test_audit.db"
        log_action("Reviewer", "role_switch", db_path=db)
        logs = get_recent_logs(limit=10, db_path=db)
        assert logs[0]["transaction_id"] is None
        assert logs[0]["details"] is None


def test_limit_respected():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test_audit.db"
        for i in range(10):
            log_action("Reviewer", f"action_{i}", db_path=db)
        logs = get_recent_logs(limit=5, db_path=db)
        assert len(logs) == 5
        assert logs[0]["action"] == "action_9"
