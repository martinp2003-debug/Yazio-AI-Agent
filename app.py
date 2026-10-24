from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import gradio as gr
from fastapi import FastAPI

from bootstrap import build_application
from interfaces.web import create_gradio_app, load_app_css


def create_app() -> FastAPI:
    """Crée le point d'entrée web à partir du cœur applicatif."""
    container = build_application()
    demo = create_gradio_app(container.chat_service)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        async with container.lifespan():
            yield

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
        css=load_app_css(),
        show_error=False,
    )


app = create_app()
