import unittest
from contextlib import nullcontext
from unittest.mock import AsyncMock, MagicMock, patch

from services.chat_service import ChatService


class ChatServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.agent = MagicMock()
        self.store = MagicMock()
        self.observability = MagicMock()
        self.observability.observe_turn.return_value = nullcontext()
        self.service = ChatService(
            self.agent,
            self.store,
            self.observability,
        )

    def test_conversation_operations_are_delegated_to_store(self) -> None:
        created = MagicMock()
        conversations = [MagicMock(), MagicMock()]
        self.store.create_session.return_value = created
        self.store.list_sessions.return_value = conversations

        self.assertIs(self.service.create_conversation("Déjeuner"), created)
        self.assertIs(self.service.list_conversations(), conversations)
        self.store.create_session.assert_called_once_with("Déjeuner")

    async def test_load_history_keeps_only_displayable_messages(self) -> None:
        session = MagicMock()
        session.get_items = AsyncMock(
            return_value=[
                {"role": "user", "content": "Bonjour"},
                {
                    "type": "function_call",
                    "name": "search_food",
                    "arguments": "{}",
                },
                {
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "Repas enregistré."}
                    ],
                },
            ]
        )
        self.store.open_session.return_value = session

        history = await self.service.load_history("session-123")

        self.assertEqual(
            history,
            [
                {"role": "user", "content": "Bonjour"},
                {"role": "assistant", "content": "Repas enregistré."},
            ],
        )
        session.close.assert_called_once_with()

    @patch("services.chat_service.Runner.run", new_callable=AsyncMock)
    async def test_send_message_runs_agent_and_updates_session(
        self,
        run_agent: AsyncMock,
    ) -> None:
        session = MagicMock()
        self.store.open_session.return_value = session
        result = MagicMock(final_output="C'est enregistré.")
        run_agent.return_value = result

        response = await self.service.send_message(
            "session-123",
            "  Une pomme  ",
        )

        self.assertEqual(response, "C'est enregistré.")
        run_agent.assert_awaited_once_with(
            self.agent,
            "Une pomme",
            session=session,
        )
        self.observability.observe_turn.assert_called_once_with(
            "session-123",
            channel="web",
        )
        self.store.mark_session_used.assert_called_once_with("session-123")
        session.close.assert_called_once_with()

    @patch("services.chat_service.Runner.run", new_callable=AsyncMock)
    async def test_session_is_closed_when_agent_fails(
        self,
        run_agent: AsyncMock,
    ) -> None:
        session = MagicMock()
        self.store.open_session.return_value = session
        run_agent.side_effect = RuntimeError("Agent indisponible")

        with self.assertRaisesRegex(RuntimeError, "Agent indisponible"):
            await self.service.send_message("session-123", "Une pomme")

        self.store.mark_session_used.assert_not_called()
        session.close.assert_called_once_with()

    @patch("services.chat_service.Runner.run", new_callable=AsyncMock)
    async def test_send_message_accepts_cli_channel(
        self,
        run_agent: AsyncMock,
    ) -> None:
        session = MagicMock()
        self.store.open_session.return_value = session
        run_agent.return_value = MagicMock(final_output="C'est enregistré.")

        await self.service.send_message(
            "session-123",
            "Une pomme",
            channel="cli",
        )

        self.observability.observe_turn.assert_called_once_with(
            "session-123",
            channel="cli",
        )

    async def test_empty_message_is_rejected_before_opening_session(self) -> None:
        with self.assertRaisesRegex(ValueError, "vide"):
            await self.service.send_message("session-123", "   ")

        self.store.open_session.assert_not_called()

    async def test_non_string_message_is_rejected_clearly(self) -> None:
        with self.assertRaisesRegex(TypeError, "chaîne"):
            await self.service.send_message(
                "session-123",
                ["Une pomme"],  # type: ignore[arg-type]
            )

        self.store.open_session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
