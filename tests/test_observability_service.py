import os
import unittest
from unittest.mock import MagicMock, patch

from services.observability_service import ObservabilityService


class ObservabilityServiceTest(unittest.TestCase):
    @patch.dict(os.environ, {"LANGFUSE_ENABLED": "false"}, clear=True)
    @patch("services.observability_service.OpenAIAgentsInstrumentor")
    @patch("services.observability_service.get_client")
    def test_can_be_disabled(self, get_client, instrumentor) -> None:
        observability = ObservabilityService.from_env()

        self.assertFalse(observability.enabled)
        get_client.assert_not_called()
        instrumentor.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    def test_enabled_by_default_requires_credentials(self) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            "LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY",
        ):
            ObservabilityService.from_env()

    @patch.dict(
        os.environ,
        {
            "LANGFUSE_PUBLIC_KEY": "public-key",
            "LANGFUSE_SECRET_KEY": "secret-key",
        },
        clear=True,
    )
    @patch("services.observability_service.OpenAIAgentsInstrumentor")
    @patch("services.observability_service.get_client")
    def test_content_is_captured_by_default(
        self,
        get_client,
        instrumentor_class,
    ) -> None:
        get_client.return_value = MagicMock()

        observability = ObservabilityService.from_env()

        self.assertTrue(observability.enabled)
        trace_config = instrumentor_class.return_value.instrument.call_args.kwargs[
            "config"
        ]
        self.assertFalse(trace_config.hide_inputs)
        self.assertFalse(trace_config.hide_outputs)

    @patch.dict(
        os.environ,
        {
            "LANGFUSE_PUBLIC_KEY": "public-key",
            "LANGFUSE_SECRET_KEY": "secret-key",
            "LANGFUSE_CAPTURE_CONTENT": "false",
        },
        clear=True,
    )
    @patch("services.observability_service.OpenAIAgentsInstrumentor")
    @patch("services.observability_service.get_client")
    def test_content_can_be_hidden(
        self,
        get_client,
        instrumentor_class,
    ) -> None:
        get_client.return_value = MagicMock()

        ObservabilityService.from_env()

        trace_config = instrumentor_class.return_value.instrument.call_args.kwargs[
            "config"
        ]
        self.assertTrue(trace_config.hide_inputs)
        self.assertTrue(trace_config.hide_outputs)

    @patch("services.observability_service.propagate_attributes")
    def test_turn_is_grouped_by_session_id(self, propagate_attributes) -> None:
        client = MagicMock()
        observability = ObservabilityService(client)

        with observability.observe_turn("session-123"):
            pass

        propagate_attributes.assert_called_once_with(
            session_id="session-123",
            tags=["yazio-agent", "cli"],
            trace_name="yazio-agent-turn",
        )
        client.start_as_current_observation.assert_called_once_with(
            as_type="agent",
            name="yazio-agent-turn",
        )

    def test_flushes_pending_traces(self) -> None:
        client = MagicMock()
        observability = ObservabilityService(client)

        observability.flush()

        client.flush.assert_called_once_with()

    @patch.dict(
        os.environ,
        {"LANGFUSE_ENABLED": "sometimes"},
        clear=True,
    )
    def test_rejects_invalid_boolean_configuration(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "LANGFUSE_ENABLED"):
            ObservabilityService.from_env()


if __name__ == "__main__":
    unittest.main()
