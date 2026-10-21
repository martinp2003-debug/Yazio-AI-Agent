import logging
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Literal, TypeAlias, cast

import gradio as gr

from data import SessionRecord
from services import ChatService, DisplayMessage


logger = logging.getLogger(__name__)

ComponentUpdate: TypeAlias = dict[str, object]
GradioHistory: TypeAlias = Sequence[Mapping[str, object]]


APP_CSS = """
:root {
    --yazio-bg: #fff8fa;
    --yazio-surface: #ffffff;
    --yazio-ink: #301b2b;
    --yazio-muted: #796b75;
    --yazio-berry: #e94f6d;
    --yazio-berry-dark: #bf334f;
    --yazio-sage: #ddebd9;
    --yazio-line: #eadde2;
}

.gradio-container {
    background: var(--yazio-bg) !important;
    color: var(--yazio-ink) !important;
    font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif !important;
    max-width: none !important;
}

#app-header {
    align-items: center;
    border-bottom: 1px solid var(--yazio-line);
    margin-bottom: 1rem;
    padding: 0.35rem 0 1rem;
}

#brand-lockup h1 {
    color: var(--yazio-ink);
    font-size: clamp(1.55rem, 3vw, 2.35rem);
    font-weight: 650;
    letter-spacing: -0.045em;
    line-height: 1;
    margin: 0;
}

#brand-lockup p {
    color: var(--yazio-muted);
    margin: 0.45rem 0 0;
}

#status-pill {
    align-items: center;
    background: var(--yazio-sage);
    border-radius: 999px;
    color: #35523b;
    display: inline-flex;
    font-size: 0.78rem;
    font-weight: 650;
    gap: 0.45rem;
    padding: 0.45rem 0.75rem;
    width: fit-content;
}

#status-pill::before {
    background: #5d9967;
    border-radius: 999px;
    content: "";
    height: 0.5rem;
    width: 0.5rem;
}

#conversation-panel,
#chat-panel {
    background: var(--yazio-surface);
    border: 1px solid var(--yazio-line);
    border-radius: 22px;
    box-shadow: 0 16px 45px rgba(75, 34, 57, 0.07);
    padding: 1rem;
}

#conversation-panel {
    height: fit-content;
}

#new-conversation button,
#send-message button {
    background: var(--yazio-berry) !important;
    border: 0 !important;
    color: white !important;
    font-weight: 650 !important;
}

#new-conversation button:hover,
#send-message button:hover {
    background: var(--yazio-berry-dark) !important;
}

#conversation-list label,
#message-input label {
    color: var(--yazio-ink) !important;
    font-weight: 600 !important;
}

#chatbot {
    border: 0 !important;
    min-height: 56vh;
}

.meal-strip {
    align-items: center;
    gap: 0.5rem;
    margin: 0.4rem 0 0.25rem;
}

.meal-button button {
    background: #fff !important;
    border: 1px solid var(--yazio-line) !important;
    border-radius: 999px !important;
    color: var(--yazio-ink) !important;
    font-size: 0.82rem !important;
    min-width: 0 !important;
}

.meal-button button:hover {
    background: var(--yazio-sage) !important;
    border-color: #bfd5ba !important;
}

#privacy-note {
    color: var(--yazio-muted);
    font-size: 0.76rem;
    line-height: 1.45;
    margin-top: 1rem;
}

@media (max-width: 760px) {
    #conversation-panel,
    #chat-panel {
        border-radius: 16px;
    }

    #chatbot {
        min-height: 48vh;
    }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
    }
}
"""


def create_gradio_app(chat_service: ChatService) -> gr.Blocks:
    """Construit l'interface web et lui injecte le service de conversation."""

    async def initialize() -> tuple[
        str,
        ComponentUpdate,
        list[DisplayMessage],
    ]:
        conversations = chat_service.list_conversations()
        if not conversations:
            conversations = [chat_service.create_conversation()]

        selected = conversations[0]
        history = await chat_service.load_history(selected.session_id)
        return (
            selected.session_id,
            gr.update(
                choices=_conversation_choices(conversations),
                value=selected.session_id,
            ),
            history,
        )

    async def select_conversation(
        session_id: str | None,
    ) -> tuple[str | None, list[DisplayMessage]]:
        if not session_id:
            return None, []
        return session_id, await chat_service.load_history(session_id)

    def create_conversation() -> tuple[
        str,
        ComponentUpdate,
        list[DisplayMessage],
    ]:
        conversation = chat_service.create_conversation()
        conversations = chat_service.list_conversations()
        return (
            conversation.session_id,
            gr.update(
                choices=_conversation_choices(conversations),
                value=conversation.session_id,
            ),
            [],
        )

    def add_user_message(
        message: str,
        history: GradioHistory | None,
    ) -> tuple[str, list[DisplayMessage]]:
        normalized_message = message.strip()
        current_history = _normalize_gradio_history(history)
        if not normalized_message:
            return "", current_history

        current_history.append(
            {"role": "user", "content": normalized_message}
        )
        return "", current_history

    async def answer(
        session_id: str | None,
        history: GradioHistory,
    ) -> tuple[list[DisplayMessage], ComponentUpdate]:
        if not session_id:
            raise gr.Error("Crée ou sélectionne une conversation.")

        normalized_history = _normalize_gradio_history(history)
        if not normalized_history or normalized_history[-1]["role"] != "user":
            return normalized_history, gr.update()

        message = normalized_history[-1]["content"]
        try:
            response = await chat_service.send_message(session_id, message)
        except Exception as error:
            logger.exception("Échec du tour de conversation")
            raise gr.Error(
                "La réponse n'a pas pu être générée. Réessaie dans un instant."
            ) from error

        updated_history = [
            *normalized_history,
            {"role": "assistant", "content": response},
        ]
        return (
            updated_history,
            gr.update(
                choices=_conversation_choices(chat_service.list_conversations()),
                value=session_id,
            ),
        )

    with gr.Blocks(
        title="Journal alimentaire",
        fill_height=True,
        fill_width=True,
    ) as demo:
        session_id = gr.State(value=None)

        with gr.Row(elem_id="app-header"):
            gr.HTML(
                """
                <div id="brand-lockup">
                    <h1>Journal alimentaire</h1>
                    <p>Dis simplement ce que tu as consommé.</p>
                </div>
                """,
                scale=4,
            )
            gr.HTML('<div id="status-pill">Agent prêt</div>', scale=1)

        with gr.Row(equal_height=False):
            with gr.Column(
                scale=1,
                min_width=250,
                elem_id="conversation-panel",
            ):
                new_conversation = gr.Button(
                    "+ Nouvelle conversation",
                    elem_id="new-conversation",
                )
                conversation_list = gr.Dropdown(
                    label="Conversations",
                    choices=[],
                    interactive=True,
                    filterable=True,
                    elem_id="conversation-list",
                )
                gr.HTML(
                    "Les conversations sont enregistrées localement. ",
                    elem_id="privacy-note",
                )

            with gr.Column(scale=3, elem_id="chat-panel"):
                chatbot = gr.Chatbot(
                    label="Conversation",
                    show_label=False,
                    height="62vh",
                    layout="bubble",
                    buttons=["copy"],
                    placeholder=(
                        "Commence par exemple avec :<br>"
                        "<strong>J'ai mangé deux œufs et une tranche de pain."
                        "</strong>"
                    ),
                    elem_id="chatbot",
                )

                with gr.Row(elem_classes="meal-strip"):
                    meal_buttons = [
                        gr.Button(
                            label,
                            size="sm",
                            elem_classes="meal-button",
                        )
                        for label in (
                            "Petit-déjeuner",
                            "Déjeuner",
                            "Dîner",
                            "Collation",
                        )
                    ]

                with gr.Row():
                    message_input = gr.Textbox(
                        label="Message",
                        placeholder="Ex. J'ai bu un café au lait ce matin…",
                        lines=1,
                        max_lines=4,
                        autofocus=True,
                        container=False,
                        scale=8,
                        elem_id="message-input",
                    )
                    send_message = gr.Button(
                        "Envoyer",
                        variant="primary",
                        scale=1,
                        elem_id="send-message",
                    )

        demo.load(
            initialize,
            outputs=[session_id, conversation_list, chatbot],
            queue=False,
        )
        conversation_list.input(
            select_conversation,
            inputs=[conversation_list],
            outputs=[session_id, chatbot],
            queue=False,
        )
        new_conversation.click(
            create_conversation,
            outputs=[session_id, conversation_list, chatbot],
            queue=False,
        )

        for meal_button, meal_name in zip(
            meal_buttons,
            ("petit-déjeuner", "déjeuner", "dîner", "collation"),
            strict=True,
        ):
            meal_button.click(
                partial(_meal_prompt, meal_name),
                outputs=[message_input],
                queue=False,
            )

        for trigger in (message_input.submit, send_message.click):
            trigger(
                add_user_message,
                inputs=[message_input, chatbot],
                outputs=[message_input, chatbot],
                queue=False,
            ).then(
                answer,
                inputs=[session_id, chatbot],
                outputs=[chatbot, conversation_list],
                concurrency_limit=1,
                concurrency_id="yazio-agent",
            )

    return demo.queue(default_concurrency_limit=1)


def _conversation_choices(
    conversations: Sequence[SessionRecord],
) -> list[tuple[str, str]]:
    return [
        (
            f"{conversation.title} · "
            f"{conversation.updated_at.astimezone():%d/%m %H:%M}",
            conversation.session_id,
        )
        for conversation in conversations
    ]


def _normalize_gradio_history(
    history: GradioHistory | None,
) -> list[DisplayMessage]:
    """Convertit les blocs de contenu Gradio en messages textuels simples."""
    normalized_history: list[DisplayMessage] = []
    for message in history or []:
        role = message.get("role")
        if role not in {"user", "assistant"}:
            continue

        content = _extract_gradio_text(message.get("content"))
        if content:
            display_role = cast(Literal["user", "assistant"], role)
            normalized_history.append(
                {"role": display_role, "content": content}
            )

    return normalized_history


def _extract_gradio_text(content: object) -> str:
    """Extrait le texte d'une chaîne ou d'une liste de blocs Gradio."""
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


def _meal_prompt(meal_name: str) -> str:
    """Construit l'amorce de message associée à un repas."""
    return f"Pour mon {meal_name}, j'ai consommé "
