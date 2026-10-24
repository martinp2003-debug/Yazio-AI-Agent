import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast


@dataclass(frozen=True)
class Conversation:
    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationRepository:
    """Gère uniquement les métadonnées des conversations dans SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path: Path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def create(self, conversation_id: str, title: str) -> Conversation:
        now: datetime = datetime.now(timezone.utc)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (session_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, title, now.isoformat(), now.isoformat()),
            )

        return Conversation(conversation_id, title, now, now)

    def get(self, conversation_id: str) -> Conversation | None:
        with self._connect() as connection:
            row: sqlite3.Row | None = connection.execute(
                """
                SELECT session_id, title, created_at, updated_at
                FROM conversations
                WHERE session_id = ?
                """,
                (conversation_id,),
            ).fetchone()

        return self._to_record(row) if row else None

    def list(self) -> list[Conversation]:
        with self._connect() as connection:
            rows: list[sqlite3.Row] = connection.execute(
                """
                SELECT session_id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                """
            ).fetchall()

        return [self._to_record(row) for row in rows]

    def touch(self, conversation_id: str) -> None:
        now: str = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor: sqlite3.Cursor = connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE session_id = ?
                """,
                (now, conversation_id),
            )

        if cursor.rowcount == 0:
            raise LookupError(f"Conversation inconnue : {conversation_id}")

    def _connect(self) -> sqlite3.Connection:
        connection: sqlite3.Connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _to_record(row: sqlite3.Row) -> Conversation:
        return Conversation(
            conversation_id=cast(str, row["session_id"]),
            title=cast(str, row["title"]),
            created_at=datetime.fromisoformat(cast(str, row["created_at"])),
            updated_at=datetime.fromisoformat(cast(str, row["updated_at"])),
        )
