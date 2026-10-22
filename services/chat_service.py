from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict, cast

from agents import Agent, Runner

from data import SessionRecord

from .observability_service import ObservabilityService
from .session_store_service import SessionStoreService


class DisplayMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


ChatChannel = Literal["web", "cli"]


class ChatService:
    """Orchestre les conversations sans dépendre de l'interface utilisateur."""

    def __init__(
        self,
        agent: Agent[None],
        store: SessionStoreService,
        observability: ObservabilityService,
    ) -> None:
        self._agent = agent
        self._store = store
        self._observability = observability

    def create_conversation(self, title: str | None = None) -> SessionRecord:
        return self._store.create_session(title)

    def list_conversations(self) -> list[SessionRecord]:
        return self._store.list_sessions()

    async def load_history(self, session_id: str) -> list[DisplayMessage]:
        session = self._store.open_session(session_id)
        try:
            items = await session.get_items()
            return _to_display_messages(items)
        finally:
            session.close()

    async def send_message(
        self,
        session_id: str,
        message: str,
        *,
        channel: ChatChannel = "web",
    ) -> str:
        if not isinstance(message, str):
            raise TypeError("Le message doit être une chaîne de caractères.")

        normalized_message = message.strip()
        if not normalized_message:
            raise ValueError("Le message ne peut pas être vide.")

        session = self._store.open_session(session_id)
        try:
            with self._observability.observe_turn(session_id, channel=channel):
                result = await Runner.run(
                    self._agent,
                    normalized_message,
                    session=session,
                )
            self._store.mark_session_used(session_id)
            return str(result.final_output)
        finally:
            session.close()


def _to_display_messages(items: Sequence[object]) -> list[DisplayMessage]:
    messages: list[DisplayMessage] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue

        role = item.get("role")
        if role not in {"user", "assistant"}:
            continue

        content = _extract_text(item.get("content"))
        if content:
            display_role = cast(Literal["user", "assistant"], role)
            messages.append({"role": display_role, "content": content})

    return messages


def _extract_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    text_parts: list[str] = []
    for part in content:
        if isinstance(part, str):
            text_parts.append(part)
            continue
        if not isinstance(part, Mapping):
            continue

        text = part.get("text")
        if isinstance(text, str):
            text_parts.append(text)

    return "\n".join(text_parts)
