from pathlib import Path

from agents import SQLiteSession


class AgentHistoryStore:
    """Ouvre la mémoire technique de l'agent pour une conversation."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def open(self, conversation_id: str) -> SQLiteSession:
        return SQLiteSession(conversation_id, db_path=self.db_path)
