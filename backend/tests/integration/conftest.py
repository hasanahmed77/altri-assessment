import os
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from app.config import Settings
from app.main import create_app

ADMIN_URL = os.environ.get("TEST_DATABASE_URL", "")
MIGRATIONS_DIR = Path(
    os.environ.get("MIGRATIONS_DIR", Path(__file__).resolve().parents[3] / "supabase/migrations")
)
LOCAL_HOSTS = {"localhost", "127.0.0.1", "db"}
TEMPLATE_DB = "str_test_template"


def _url_for(database: str) -> str:
    return urlparse(ADMIN_URL)._replace(path=f"/{database}").geturl()


def _admin_execute(statement: sql.Composed) -> None:
    with psycopg.connect(_url_for("postgres").replace("+psycopg", ""), autocommit=True) as conn:
        conn.execute(statement)


@pytest.fixture(scope="session")
def template_db() -> Iterator[str]:
    if not ADMIN_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    host = urlparse(ADMIN_URL).hostname
    if host not in LOCAL_HOSTS:
        raise RuntimeError(f"Refusing to run integration tests against non-local host {host}")

    _admin_execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(TEMPLATE_DB)))
    _admin_execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEMPLATE_DB)))
    with psycopg.connect(_url_for(TEMPLATE_DB).replace("+psycopg", ""), autocommit=True) as conn:
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            conn.execute(migration.read_text())  # type: ignore[call-overload]
    yield TEMPLATE_DB
    _admin_execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(TEMPLATE_DB)))


@pytest.fixture
def database_url(template_db: str) -> Iterator[str]:
    """A fresh copy of the migrated database for each test."""
    name = f"str_test_{uuid4().hex[:8]}"
    _admin_execute(
        sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
            sql.Identifier(name), sql.Identifier(template_db)
        )
    )
    yield _url_for(name)
    _admin_execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def api(database_url: str) -> Iterator[TestClient]:
    app = create_app(Settings(database_url=database_url))
    with TestClient(app) as client:
        yield client
