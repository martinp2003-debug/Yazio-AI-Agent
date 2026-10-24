from uuid import uuid4

from agents import SQLiteSession

from data import AgentHistoryStore, Conversation, ConversationRepository


class ConversationManager:
    """Coordonne les métadonnées et l'historique des conversations."""

    def __init__(
        self,
        repository: ConversationRepository,
        history_store: AgentHistoryStore,
    ) -> None:
        self._repository = repository
        self._history_store = history_store

    def create_conversation(self, title: str | None = None) -> Conversation:
        conversation_id = str(uuid4())
        normalized_title = title.strip() if title else ""
        if not normalized_title:
            normalized_title = f"Conversation {conversation_id[:8]}"

        return self._repository.create(conversation_id, normalized_title)

    def list_conversations(self) -> list[Conversation]:
        return self._repository.list()

    def open_history(self, conversation_id: str) -> SQLiteSession:
        if self._repository.get(conversation_id) is None:
            raise LookupError(f"Conversation inconnue : {conversation_id}")

        return self._history_store.open(conversation_id)

    def mark_conversation_used(self, conversation_id: str) -> None:
        self._repository.touch(conversation_id)
