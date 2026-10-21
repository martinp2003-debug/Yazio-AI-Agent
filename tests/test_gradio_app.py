import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

import gradio as gr

from data import SessionRecord
from gradio_app import (
    _conversation_choices,
    _normalize_gradio_history,
    create_gradio_app,
)


class GradioAppTest(unittest.TestCase):
    def test_builds_blocks_application(self) -> None:
        demo = create_gradio_app(MagicMock())

        self.assertIsInstance(demo, gr.Blocks)
        config = demo.get_config_file()
        component_types = {
            component["type"] for component in config["components"]
        }
        self.assertIn("chatbot", component_types)
        self.assertIn("dropdown", component_types)
        self.assertIn("textbox", component_types)

    def test_conversation_choices_use_id_as_value(self) -> None:
        conversation = SessionRecord(
            session_id="session-123",
            title="Petit-déjeuner",
            created_at=datetime(2026, 10, 21, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 21, 8, 30, tzinfo=timezone.utc),
        )

        choices = _conversation_choices([conversation])

        self.assertEqual(choices[0][1], "session-123")
        self.assertIn("Petit-déjeuner", choices[0][0])

    def test_normalizes_text_blocks_returned_by_gradio(self) -> None:
        history = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Une pomme"},
                ],
            }
        ]

        normalized = _normalize_gradio_history(history)

        self.assertEqual(
            normalized,
            [{"role": "user", "content": "Une pomme"}],
        )


if __name__ == "__main__":
    unittest.main()
