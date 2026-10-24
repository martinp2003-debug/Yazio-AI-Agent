import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from agents.mcp import MCPServerStdio
from dotenv import load_dotenv

from agent import create_agent, create_yazio_mcp_server
from data import AgentHistoryStore, ConversationRepository
from services import ChatService, ConversationManager, ObservabilityService


@dataclass(frozen=True)
class ApplicationContainer:
    """Services partagés et cycle de vie des ressources de l'application."""

    chat_service: ChatService
    agent_name: str
    mcp_server: MCPServerStdio
    observability: ObservabilityService

    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator[None, None]:
        try:
            async with self.mcp_server:
                yield
        finally:
            self.observability.flush()


def build_application() -> ApplicationContainer:
    """Assemble le cœur applicatif indépendamment de son interface."""
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY est absente. Copie .env.example vers .env "
            "et ajoute ta clé API."
        )

    db_path = Path(os.getenv("AGENT_DB_PATH", "storage/conversations.db"))
    repository = ConversationRepository(db_path)
    history_store = AgentHistoryStore(db_path)
    conversations = ConversationManager(repository, history_store)
    observability = ObservabilityService.from_env()
    mcp_server = create_yazio_mcp_server()
    agent = create_agent(mcp_server)
    chat_service = ChatService(agent, conversations, observability)

    return ApplicationContainer(
        chat_service=chat_service,
        agent_name=agent.name,
        mcp_server=mcp_server,
        observability=observability,
    )
