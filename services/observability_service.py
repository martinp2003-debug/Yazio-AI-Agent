import os
from contextlib import contextmanager
from typing import Iterator

from langfuse import Langfuse, get_client, propagate_attributes
from openinference.instrumentation import TraceConfig
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor


class ObservabilityService:
    """Configure et expose l'observabilité Langfuse de l'agent."""

    def __init__(self, client: Langfuse | None = None) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @classmethod
    def from_env(cls) -> "ObservabilityService":
        enabled = _read_bool_env("LANGFUSE_ENABLED", default=True)
        if not enabled:
            return cls()

        missing_variables = [
            name
            for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
            if not os.getenv(name)
        ]
        if missing_variables:
            raise RuntimeError(
                "Configuration Langfuse incomplète : "
                + ", ".join(missing_variables)
                + ". Configure ces variables ou définis LANGFUSE_ENABLED=false."
            )

        capture_content = _read_bool_env(
            "LANGFUSE_CAPTURE_CONTENT",
            default=True,
        )
        client = get_client()
        trace_config = TraceConfig(
            hide_inputs=not capture_content,
            hide_outputs=not capture_content,
        )
        OpenAIAgentsInstrumentor().instrument(config=trace_config)

        return cls(client)

    @contextmanager
    def observe_turn(self, session_id: str) -> Iterator[None]:
        """Crée une trace par tour et la rattache à la conversation."""
        if self._client is None:
            yield
            return

        with propagate_attributes(
            session_id=session_id,
            tags=["yazio-agent", "cli"],
            trace_name="yazio-agent-turn",
        ):
            with self._client.start_as_current_observation(
                as_type="agent",
                name="yazio-agent-turn",
            ):
                yield

    def flush(self) -> None:
        """Envoie les traces encore en attente avant l'arrêt du programme."""
        if self._client is not None:
            self._client.flush()


def _read_bool_env(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False

    raise RuntimeError(
        f"{name} doit être un booléen "
        "(true/false, yes/no, on/off ou 1/0)."
    )
