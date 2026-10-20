import tempfile
import unittest
from pathlib import Path

from services import SessionStoreService


class SessionStoreServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "conversations.db"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    async def test_session_is_persisted_and_can_be_reopened(self) -> None:
        store = SessionStoreService(self.db_path)
        conversation = store.create_session("Petit-déjeuner")
        session = store.open_session(conversation.session_id)
        await session.add_items([{"role": "user", "content": "Bonjour"}])
        session.close()

        reloaded_store = SessionStoreService(self.db_path)
        reloaded_session = reloaded_store.open_session(conversation.session_id)

        self.assertEqual(len(reloaded_store.list_sessions()), 1)
        self.assertEqual(
            await reloaded_session.get_items(),
            [{"role": "user", "content": "Bonjour"}],
        )
        reloaded_session.close()

    async def test_sessions_have_isolated_histories(self) -> None:
        store = SessionStoreService(self.db_path)
        first = store.create_session("Première")
        second = store.create_session("Deuxième")
        first_session = store.open_session(first.session_id)
        second_session = store.open_session(second.session_id)

        await first_session.add_items([{"role": "user", "content": "Message"}])

        self.assertEqual(len(await first_session.get_items()), 1)
        self.assertEqual(await second_session.get_items(), [])
        first_session.close()
        second_session.close()

    def test_unknown_session_cannot_be_opened(self) -> None:
        store = SessionStoreService(self.db_path)

        with self.assertRaises(LookupError):
            store.open_session("inconnue")


if __name__ == "__main__":
    unittest.main()
