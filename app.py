import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from fastapi import FastAPI

from agent import create_agent, create_yazio_mcp_server
from gradio_app import APP_CSS, create_gradio_app
from services import ChatService, ObservabilityService, SessionStoreService


load_dotenv()


def create_app() -> FastAPI:
    """Assemble l'application et possède le cycle de vie de ses ressources."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY est absente. Copie .env.example vers .env "
            "et ajoute ta clé API."
        )

    db_path = Path(os.getenv("AGENT_DB_PATH", "storage/conversations.db"))
    store = SessionStoreService(db_path)
    observability = ObservabilityService.from_env()
    yazio_mcp = create_yazio_mcp_server()
    agent = create_agent(yazio_mcp)
    chat_service = ChatService(agent, store, observability)
    demo = create_gradio_app(chat_service)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        try:
            async with yazio_mcp:
                yield
        finally:
            observability.flush()

    fastapi_app = FastAPI(
        title="Assistant YAZIO",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    return gr.mount_gradio_app(
        fastapi_app,
        demo,
        path="/",
        footer_links=[],
        css=APP_CSS,
        show_error=False,
    )


app = create_app()
