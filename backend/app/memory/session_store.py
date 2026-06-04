import json
import sqlite3
from datetime import datetime
from contextlib import contextmanager

WINDOW = 15  # turns kept per session (1 turn = 1 user + 1 assistant message)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    with _connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                user_id      TEXT NOT NULL,
                role         TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                last_active  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT NOT NULL,
                role         TEXT NOT NULL,
                content      TEXT NOT NULL,
                tool_calls   TEXT,
                timestamp    TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
        """)
        conn.commit()


@contextmanager
def _db(db_path: str):
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_session(db_path: str, session_id: str, user_id: str, role: str) -> None:
    now = datetime.utcnow().isoformat()
    with _db(db_path) as conn:
        existing = conn.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                (now, session_id),
            )
        else:
            conn.execute(
                "INSERT INTO sessions (session_id, user_id, role, created_at, last_active) VALUES (?,?,?,?,?)",
                (session_id, user_id, role, now, now),
            )


def append_message(
    db_path: str,
    session_id: str,
    role: str,
    content: str,
    tool_calls: list | None = None,
) -> None:
    now = datetime.utcnow().isoformat()
    with _db(db_path) as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, tool_calls, timestamp) VALUES (?,?,?,?,?)",
            (session_id, role, content, json.dumps(tool_calls) if tool_calls else None, now),
        )
        # Enforce 15-turn window: keep last 30 messages (15 user + 15 assistant)
        conn.execute(
            """
            DELETE FROM messages WHERE id IN (
                SELECT id FROM messages WHERE session_id = ?
                ORDER BY id DESC LIMIT -1 OFFSET ?
            )
            """,
            (session_id, WINDOW * 2),
        )


def get_history(db_path: str, session_id: str) -> list[dict]:
    with _db(db_path) as conn:
        rows = conn.execute(
            "SELECT role, content, tool_calls FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    history = []
    for row in rows:
        entry = {"role": row["role"], "content": row["content"]}
        if row["tool_calls"]:
            entry["tool_calls"] = json.loads(row["tool_calls"])
        history.append(entry)
    return history


def list_sessions(db_path: str, user_id: str) -> list[dict]:
    with _db(db_path) as conn:
        rows = conn.execute(
            "SELECT session_id, role, created_at, last_active FROM sessions WHERE user_id = ? ORDER BY last_active DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_session(db_path: str, session_id: str) -> None:
    with _db(db_path) as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
