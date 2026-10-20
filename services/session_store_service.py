from pathlib import Path
from uuid import uuid4

from agents import SQLiteSession

from data import SessionRecord, SessionRepository


class SessionStoreService:
    """Crée et recharge les conversations persistées localement."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._repository = SessionRepository(self.db_path)

    def create_session(self, title: str | None = None) -> SessionRecord:
        session_id = str(uuid4())
        normalized_title = title.strip() if title else ""
        if not normalized_title:
            normalized_title = f"Conversation {session_id[:8]}"

        return self._repository.create(session_id, normalized_title)

    def list_sessions(self) -> list[SessionRecord]:
        return self._repository.list()

    def open_session(self, session_id: str) -> SQLiteSession:
        if self._repository.get(session_id) is None:
            raise LookupError(f"Session inconnue : {session_id}")

        return SQLiteSession(session_id, db_path=self.db_path)

    def mark_session_used(self, session_id: str) -> None:
        self._repository.touch(session_id)
