import tempfile
import unittest
from pathlib import Path

from data import AgentHistoryStore, ConversationRepository
from services import ConversationManager


class ConversationManagerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "conversations.db"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_manager(self) -> ConversationManager:
        return ConversationManager(
            ConversationRepository(self.db_path),
            AgentHistoryStore(self.db_path),
        )

    async def test_conversation_is_persisted_and_can_be_reopened(self) -> None:
        manager = self.create_manager()
        conversation = manager.create_conversation("Petit-déjeuner")
        session = manager.open_history(conversation.conversation_id)
        await session.add_items([{"role": "user", "content": "Bonjour"}])
        session.close()

        reloaded_manager = self.create_manager()
        reloaded_session = reloaded_manager.open_history(
            conversation.conversation_id
        )

        self.assertEqual(len(reloaded_manager.list_conversations()), 1)
        self.assertEqual(
            await reloaded_session.get_items(),
            [{"role": "user", "content": "Bonjour"}],
        )
        reloaded_session.close()

    async def test_sessions_have_isolated_histories(self) -> None:
        manager = self.create_manager()
        first = manager.create_conversation("Première")
        second = manager.create_conversation("Deuxième")
        first_session = manager.open_history(first.conversation_id)
        second_session = manager.open_history(second.conversation_id)

        await first_session.add_items([{"role": "user", "content": "Message"}])

        self.assertEqual(len(await first_session.get_items()), 1)
        self.assertEqual(await second_session.get_items(), [])
        first_session.close()
        second_session.close()

    def test_history_without_conversation_cannot_be_opened(self) -> None:
        manager = self.create_manager()

        with self.assertRaises(LookupError):
            manager.open_history("inconnue")


if __name__ == "__main__":
    unittest.main()
