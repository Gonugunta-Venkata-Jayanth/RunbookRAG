"""SQLite query log and feedback store used by the container deployment."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    question TEXT NOT NULL,
    mode TEXT NOT NULL,
    top_chunk TEXT,
    answered INTEGER NOT NULL,
    latency_ms REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
    query_id TEXT PRIMARY KEY REFERENCES queries(id),
    helpful INTEGER NOT NULL,
    ts TEXT NOT NULL
);
"""


class SQLiteStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    def log_query(self, question: str, mode: str, top_chunk: str | None, answered: bool,
                  latency_ms: float) -> str:
        qid = uuid.uuid4().hex
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO queries VALUES (?, ?, ?, ?, ?, ?, ?)",
                (qid, datetime.now(UTC).isoformat(), question, mode, top_chunk, int(answered), latency_ms),
            )
        return qid

    def add_feedback(self, query_id: str, helpful: bool) -> bool:
        with self._lock, self._conn:
            exists = self._conn.execute("SELECT 1 FROM queries WHERE id = ?", (query_id,)).fetchone()
            if not exists:
                return False
            self._conn.execute(
                "INSERT OR REPLACE INTO feedback VALUES (?, ?, ?)",
                (query_id, int(helpful), datetime.now(UTC).isoformat()),
            )
        return True

    def stats(self) -> dict:
        with self._lock:
            total, answered, latency = self._conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(answered), 0), AVG(latency_ms) FROM queries"
            ).fetchone()
            votes, helpful = self._conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(helpful), 0) FROM feedback"
            ).fetchone()
            top = self._conn.execute(
                "SELECT top_chunk, COUNT(*) n FROM queries WHERE top_chunk IS NOT NULL "
                "GROUP BY top_chunk ORDER BY n DESC, top_chunk LIMIT 5"
            ).fetchall()
        return {
            "queries": total,
            "answered_rate": round(answered / total, 4) if total else None,
            "avg_latency_ms": round(latency, 3) if latency is not None else None,
            "feedback": votes,
            "helpful_rate": round(helpful / votes, 4) if votes else None,
            "top_sections": [{"id": c, "count": n} for c, n in top],
        }
