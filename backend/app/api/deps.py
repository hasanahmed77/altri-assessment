from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import Connection, Engine

from app.repository import ClientProfile, Reference


def get_reference(request: Request) -> Reference:
    reference: Reference = request.app.state.reference
    return reference


def get_connection(request: Request) -> Iterator[Connection]:
    engine: Engine = request.app.state.engine
    with engine.connect() as conn:
        yield conn


def get_transaction(request: Request) -> Iterator[Connection]:
    engine: Engine = request.app.state.engine
    with engine.begin() as conn:
        yield conn


ReferenceDep = Annotated[Reference, Depends(get_reference)]
ConnectionDep = Annotated[Connection, Depends(get_connection)]
TransactionDep = Annotated[Connection, Depends(get_transaction)]


def find_client(reference: Reference, client_id: str) -> ClientProfile:
    profile = reference.clients.get(client_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return profile
