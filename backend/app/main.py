from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api import clients, feedback
from app.api.deps import ConnectionDep
from app.config import Settings, get_settings
from app.db import make_engine
from app.llm.extractor import OpenAIExtractor, SignalExtractor
from app.repository import load_reference
from app.services.signals import SignalService


def create_app(
    settings: Settings | None = None, extractor: SignalExtractor | None = None
) -> FastAPI:
    """`extractor` replaces the OpenAI one (tests pass a fake). Without either, stored signals
    are still served and new comments simply leave them stale."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings.database_url)
        with engine.connect() as conn:
            reference = load_reference(conn)
        chosen = extractor
        if chosen is None and settings.openai_api_key:
            chosen = OpenAIExtractor(
                settings.openai_api_key, settings.openai_model, reference.markets
            )
        app.state.reference = reference
        app.state.engine = engine
        app.state.signals = SignalService(
            engine, reference, chosen, chosen.model if chosen else settings.openai_model
        )
        yield
        engine.dispose()

    app = FastAPI(title="STR Search deal recommendations", lifespan=lifespan)
    app.include_router(clients.router)
    app.include_router(feedback.router)

    @app.get("/health", tags=["health"])
    def health(conn: ConnectionDep) -> dict[str, str]:
        conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
