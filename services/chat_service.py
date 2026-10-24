from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict, cast

from agents import Agent, Runner

from data import Conversation

from .conversation_manager import ConversationManager
from .observability_service import ObservabilityService


class DisplayMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


ChatChannel = Literal["web", "cli"]


class ChatService:
    """Orchestre les conversations sans dépendre de l'interface utilisateur."""

    def __init__(
        self,
        agent: Agent[None],
        conversations: ConversationManager,
        observability: ObservabilityService,
    ) -> None:
        self._agent = agent
        self._conversations = conversations
        self._observability = observability

    def create_conversation(self, title: str | None = None) -> Conversation:
        return self._conversations.create_conversation(title)

    def list_conversations(self) -> list[Conversation]:
        return self._conversations.list_conversations()

    async def load_history(self, conversation_id: str) -> list[DisplayMessage]:
        session = self._conversations.open_history(conversation_id)
        try:
            items = await session.get_items()
            return _to_display_messages(items)
        finally:
            session.close()

    async def send_message(
        self,
        conversation_id: str,
        message: str,
        *,
        channel: ChatChannel = "web",
    ) -> str:
        if not isinstance(message, str):
            raise TypeError("Le message doit être une chaîne de caractères.")

        normalized_message = message.strip()
        if not normalized_message:
            raise ValueError("Le message ne peut pas être vide.")

        session = self._conversations.open_history(conversation_id)
        try:
            with self._observability.observe_turn(
                conversation_id,
                channel=channel,
            ):
                result = await Runner.run(
                    self._agent,
                    normalized_message,
                    session=session,
                )
            self._conversations.mark_conversation_used(conversation_id)
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
