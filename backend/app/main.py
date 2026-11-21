from fastapi import FastAPI
from sqlalchemy import text

from app.db import get_engine

app = FastAPI(title="STR Search deal recommendations")


@app.get("/health")
def health() -> dict[str, str]:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
