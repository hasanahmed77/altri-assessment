from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api import clients, feedback
from app.api.deps import ConnectionDep
from app.config import Settings, get_settings
from app.db import make_engine
from app.repository import load_reference


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings.database_url)
        with engine.connect() as conn:
            app.state.reference = load_reference(conn)
        app.state.engine = engine
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
