import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import Connection, RowMapping, text

from app.domain.models import (
    Client,
    Comp,
    Deal,
    Feedback,
    Focus,
    LowMidHigh,
    Market,
    Reaction,
    SetupItem,
)
from app.domain.signals import Signals


@dataclass(frozen=True)
class ClientProfile:
    client: Client
    budget_range: str
    notes: str
    onboarded_at: date
    preferred_terms: tuple[str, ...]
    avoided_terms: tuple[str, ...]
    unresolved_terms: tuple[str, ...]


@dataclass(frozen=True)
class FeedbackRecord:
    feedback: Feedback
    client_id: str
    created_at: date


@dataclass(frozen=True)
class CallSummary:
    call_date: date
    summary: str


@dataclass(frozen=True)
class Reference:
    """Markets, deals and clients never change at runtime, so they are loaded once."""

    markets: Mapping[str, Market]
    deals: tuple[Deal, ...]
    deals_by_id: Mapping[str, Deal]
    clients: Mapping[str, ClientProfile]
    calls: Mapping[str, tuple[CallSummary, ...]]


@dataclass(frozen=True)
class StoredSignals:
    signals: Signals
    dropped: tuple[str, ...]
    source_hash: str
    model: str
    input_tokens: int
    output_tokens: int
    extracted_at: datetime


def load_reference(conn: Connection) -> Reference:
    deals = _load_deals(conn)
    return Reference(
        markets=_load_markets(conn),
        deals=deals,
        deals_by_id={d.id: d for d in deals},
        clients=_load_clients(conn),
        calls=_load_calls(conn),
    )


def client_feedback(conn: Connection, client_id: str) -> list[FeedbackRecord]:
    rows = conn.execute(
        text(
            "SELECT id, client_id, deal_id, reaction, comment, created_at "
            "FROM feedback WHERE client_id = :client_id ORDER BY id DESC"
        ),
        {"client_id": client_id},
    ).mappings()
    return [_feedback_record(row) for row in rows]


def feedback_counts(conn: Connection) -> dict[str, int]:
    rows = conn.execute(text("SELECT client_id, count(*) AS n FROM feedback GROUP BY client_id"))
    return {client_id: n for client_id, n in rows}


def client_signals(conn: Connection, client_id: str) -> StoredSignals | None:
    row = (
        conn.execute(
            text(
                "SELECT signals, dropped, source_hash, model, input_tokens, output_tokens, "
                "extracted_at FROM client_signals WHERE client_id = :client_id"
            ),
            {"client_id": client_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    try:
        signals = Signals.model_validate(row["signals"])
    except ValidationError:
        # Stored by an older, looser schema: treat as missing so it is extracted again
        return None
    return StoredSignals(
        signals=signals,
        dropped=tuple(row["dropped"]),
        source_hash=row["source_hash"],
        model=row["model"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        extracted_at=row["extracted_at"],
    )


def save_signals(
    conn: Connection,
    client_id: str,
    stored: StoredSignals,
    prompt_version: str,
) -> None:
    conn.execute(
        text(
            "INSERT INTO client_signals (client_id, signals, dropped, source_hash, model, "
            "prompt_version, input_tokens, output_tokens) "
            "VALUES (:client_id, CAST(:signals AS jsonb), CAST(:dropped AS jsonb), :source_hash, "
            ":model, :prompt_version, :input_tokens, :output_tokens) "
            "ON CONFLICT (client_id) DO UPDATE SET signals = EXCLUDED.signals, "
            "dropped = EXCLUDED.dropped, source_hash = EXCLUDED.source_hash, "
            "model = EXCLUDED.model, prompt_version = EXCLUDED.prompt_version, "
            "input_tokens = EXCLUDED.input_tokens, output_tokens = EXCLUDED.output_tokens, "
            "extracted_at = now()"
        ),
        {
            "client_id": client_id,
            "signals": stored.signals.model_dump_json(),
            "dropped": json.dumps(stored.dropped),
            "source_hash": stored.source_hash,
            "model": stored.model,
            "prompt_version": prompt_version,
            "input_tokens": stored.input_tokens,
            "output_tokens": stored.output_tokens,
        },
    )


def insert_feedback(
    conn: Connection, client_id: str, deal_id: str, reaction: Reaction, comment: str
) -> FeedbackRecord:
    row = (
        conn.execute(
            text(
                "INSERT INTO feedback (client_id, deal_id, reaction, comment) "
                "VALUES (:client_id, :deal_id, :reaction, :comment) "
                "RETURNING id, client_id, deal_id, reaction, comment, created_at"
            ),
            {"client_id": client_id, "deal_id": deal_id, "reaction": reaction, "comment": comment},
        )
        .mappings()
        .one()
    )
    return _feedback_record(row)


def _load_calls(conn: Connection) -> dict[str, tuple[CallSummary, ...]]:
    rows = conn.execute(
        text(
            "SELECT client_id, call_date, summary FROM call_summaries "
            "ORDER BY call_date DESC, id DESC"
        )
    )
    calls: dict[str, list[CallSummary]] = {}
    for client_id, call_date, summary in rows:
        calls.setdefault(client_id, []).append(CallSummary(call_date, summary))
    return {client_id: tuple(items) for client_id, items in calls.items()}


def _load_markets(conn: Connection) -> dict[str, Market]:
    rows = conn.execute(
        text("SELECT id, name, state, setting, typical_traveler, annual_appreciation FROM markets")
    ).mappings()
    return {
        r["id"]: Market(
            id=r["id"],
            name=r["name"],
            state=r["state"],
            setting=r["setting"],
            typical_traveler=r["typical_traveler"],
            annual_appreciation=float(r["annual_appreciation"]),
        )
        for r in rows
    }


def _load_deals(conn: Connection) -> tuple[Deal, ...]:
    rows = conn.execute(text("SELECT * FROM deals ORDER BY id")).mappings()
    return tuple(_deal(r) for r in rows)


def _deal(r: RowMapping) -> Deal:
    return Deal(
        id=r["id"],
        address=r["address"],
        city=r["city"],
        state=r["state"],
        market_id=r["market_id"],
        property_key=r["property_key"],
        purchase_price=float(r["purchase_price"]),
        bedrooms=r["bedrooms"],
        baths=float(r["baths"]),
        turnkey=r["turnkey"],
        interest_rate=float(r["interest_rate"]),
        closing_cost_pct=float(r["closing_cost_pct"]),
        setup_items=tuple(SetupItem(i["item"], float(i["cost"])) for i in r["setup_items"]),
        annual_opex=float(r["annual_opex"]),
        revenue=LowMidHigh(
            low=float(r["revenue"]["low"]),
            mid=float(r["revenue"]["mid"]),
            high=float(r["revenue"]["high"]),
        ),
        est_year1_tax_savings=float(r["est_year1_tax_savings"]),
        comps=tuple(Comp(float(c["revenue"]), c["bedrooms"], c["sleeps"]) for c in r["comps"]),
        highlights=tuple(r["highlights"]),
        analyst_notes=r["analyst_notes"] or "",
    )


def _load_clients(conn: Connection) -> dict[str, ClientProfile]:
    refs = conn.execute(
        text("SELECT client_id, kind, raw_term, market_id FROM client_market_refs")
    ).all()
    rows = conn.execute(text("SELECT * FROM clients ORDER BY id")).mappings()
    return {r["id"]: _client_profile(r, [ref for ref in refs if ref[0] == r["id"]]) for r in rows}


def _client_profile(r: RowMapping, refs: list[Any]) -> ClientProfile:
    def market_ids(kind: str) -> frozenset[str]:
        return frozenset(m for _, k, _, m in refs if k == kind and m is not None)

    client = Client(
        id=r["id"],
        name=r["name"],
        budget=float(r["budget"]),
        budget_flexibility=r["budget_flexibility"],
        down_payment_pct=float(r["down_payment_pct"]),
        cohost_fee_pct=float(r["cohost_fee_pct"]),
        main_focus=Focus(r["main_focus"]),
        preferred_market_ids=market_ids("prefer"),
        avoid_market_ids=market_ids("avoid"),
        setting_rank=r["setting_rank"],
        renovation_appetite=r["renovation_appetite"],
        wow_factors=tuple(r["wow_factors"]),
        wants_turnkey=r["wants_turnkey"],
        min_bedrooms=r["min_bedrooms"],
    )
    return ClientProfile(
        client=client,
        budget_range=r["budget_range"],
        notes=r["notes"] or "",
        onboarded_at=r["onboarded_at"],
        preferred_terms=tuple(r["market_preferences"]),
        avoided_terms=tuple(r["avoid_markets"]),
        unresolved_terms=tuple(sorted({term for _, _, term, m in refs if m is None})),
    )


def _feedback_record(row: RowMapping) -> FeedbackRecord:
    return FeedbackRecord(
        feedback=Feedback(
            id=row["id"],
            deal_id=row["deal_id"],
            reaction=row["reaction"],
            comment=row["comment"] or "",
        ),
        client_id=row["client_id"],
        created_at=row["created_at"],
    )
