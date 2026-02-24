"""
SQLite storage for conversation history and metadata.
"""

import sqlite3
import json
import time
from pathlib import Path
from core.config import config


class Database:
    """SQLite database for persistent storage."""

    def __init__(self):
        db_path = config.get("storage.db_path", "./data/agent.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """Create tables if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                tool_calls TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_conv_session 
                ON conversations(session_id);
        """)
        self.conn.commit()

    def create_session(self, session_id: str, title: str = "New Chat") -> str:
        """Create a new chat session."""
        self.conn.execute(
            "INSERT OR REPLACE INTO sessions (id, title) VALUES (?, ?)",
            (session_id, title),
        )
        self.conn.commit()
        return session_id

    def save_message(self, session_id: str, role: str, content: str, tool_calls: list = None):
        """Save a message to conversation history."""
        self.conn.execute(
            "INSERT INTO conversations (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
            (session_id, role, content, json.dumps(tool_calls) if tool_calls else None),
        )
        self.conn.execute(
            "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,),
        )
        self.conn.commit()

    def get_session_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        """Get messages for a session."""
        rows = self.conn.execute(
            "SELECT role, content, tool_calls, created_at FROM conversations "
            "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()

        messages = []
        for row in reversed(rows):
            msg = {
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"],
            }
            if row["tool_calls"]:
                msg["tool_calls"] = json.loads(row["tool_calls"])
            messages.append(msg)
        return messages

    def list_sessions(self, limit: int = 20) -> list[dict]:
        """List recent sessions."""
        rows = self.conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions "
            "ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_session(self, session_id: str):
        """Delete a session and all its messages."""
        self.conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()

    def close(self):
        """Close database connection."""
        self.conn.close()
