"""Local feedback storage (SQLite). Nothing here ever leaves the machine."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import History

_FMT = "%Y-%m-%d %H:%M:%S"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    place_id TEXT NOT NULL,
    place_name TEXT NOT NULL,
    category TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('accepted', 'skipped', 'done')),
    effort TEXT,
    duration_minutes INTEGER
)
"""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Store:
    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def record(
        self,
        *,
        place_id: str,
        place_name: str,
        category: str,
        action: str,
        effort: str | None = None,
        duration_minutes: int | None = None,
        now: datetime | None = None,
    ) -> None:
        stamp = (now or _utc_now()).strftime(_FMT)
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO events (ts, place_id, place_name, category, action, effort, "
                "duration_minutes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (stamp, place_id, place_name, category, action, effort, duration_minutes),
            )

    def history(self, now: datetime | None = None) -> History:
        """Summarise recent behaviour for the prompt and the fallback ranking."""
        now = now or _utc_now()
        three_days = (now - timedelta(days=3)).strftime(_FMT)
        one_day = (now - timedelta(days=1)).strftime(_FMT)
        seven_days = (now - timedelta(days=7)).strftime(_FMT)
        with closing(self._connect()) as conn:
            recent_ids = [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT place_id FROM events "
                    "WHERE action IN ('accepted', 'done') AND ts >= ?",
                    (three_days,),
                )
            ]
            load = conn.execute(
                "SELECT COALESCE(SUM(duration_minutes), 0) FROM events "
                "WHERE action = 'done' AND ts >= ?",
                (one_day,),
            ).fetchone()[0]
            done_7d = conn.execute(
                "SELECT COUNT(*) FROM events WHERE action = 'done' AND ts >= ?",
                (seven_days,),
            ).fetchone()[0]
        return History(
            recent_place_ids=recent_ids, recent_load_minutes=int(load), done_last_7d=int(done_7d)
        )

    def list_recent(self, limit: int = 10) -> list[dict]:
        """Return the most recent events."""
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, ts, place_id, place_name, category, action, effort, duration_minutes "
                "FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def clear(self) -> None:
        """Clear all stored events."""
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM events")
