"""Lightweight SQLite rolling conversation memory and tool execution audit log."""
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryStore:
    """Zero-dependency SQLite store for rolling multi-turn conversation & tool audit logs."""

    def __init__(self, db_path: Optional[str] = None, max_turns: int = 10) -> None:
        default_path = Path.home() / ".local" / "share" / "javis" / "javis.db"
        self.db_path = Path(db_path) if db_path else default_path
        self.max_turns = max_turns
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tier TEXT DEFAULT 'tier2'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    tool_name TEXT NOT NULL,
                    args_json TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    confirmed INTEGER NOT NULL,
                    success INTEGER NOT NULL,
                    result_summary TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def add_turn(self, role: str, content: str, tier: str = "tier2") -> None:
        if not content.strip():
            return
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversation_turns (ts, role, content, tier) VALUES (?, ?, ?, ?)",
                (time.time(), role, content.strip(), tier),
            )
            conn.commit()

    def get_recent_turns(self, limit_turns: Optional[int] = None) -> List[Dict[str, str]]:
        limit_rows = (limit_turns or self.max_turns) * 2
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM conversation_turns ORDER BY id DESC LIMIT ?",
                (limit_rows,),
            ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def log_tool_execution(
        self,
        tool_name: str,
        args: Dict[str, Any],
        risk_level: str,
        confirmed: bool,
        success: bool,
        result_summary: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tool_audit_log
                (ts, tool_name, args_json, risk_level, confirmed, success, result_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    tool_name,
                    json.dumps(args, ensure_ascii=False),
                    risk_level,
                    1 if confirmed else 0,
                    1 if success else 0,
                    result_summary,
                ),
            )
            conn.commit()

    def get_recent_audit_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ts, tool_name, args_json, risk_level, confirmed, success, result_summary
                FROM tool_audit_log ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "ts": r[0],
                "tool_name": r[1],
                "args": json.loads(r[2]),
                "risk_level": r[3],
                "confirmed": bool(r[4]),
                "success": bool(r[5]),
                "result_summary": r[6],
            }
            for r in rows
        ]
