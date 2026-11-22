import json
import os
from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import Any

from app.domain.finance import DealNumbers
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
from app.domain.signals import EMPTY_SIGNALS, Signals

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[2] / "data"))

MARKET = Market(
    id="M-01",
    name="Poconos",
    state="PA",
    setting="lake_mountain",
    typical_traveler="Families",
    annual_appreciation=0.0425,
)

DEAL = Deal(
    id="D-900",
    address="1 Test Rd",
    city="Tobyhanna",
    state="PA",
    market_id="M-01",
    property_key="1 test rd|pa",
    purchase_price=400_000,
    bedrooms=4,
    baths=2,
    turnkey=False,
    interest_rate=0.07,
    closing_cost_pct=0.03,
    setup_items=(SetupItem("Furniture and decor", 60_000), SetupItem("Hot tub", 16_250)),
    annual_opex=30_000,
    revenue=LowMidHigh(90_000, 100_000, 110_000),
    est_year1_tax_savings=60_000,
    comps=(Comp(100_000, 4, 10),),
    highlights=("Short walk to lake access",),
    analyst_notes="",
)

CLIENT = Client(
    id="C-900",
    name="Test Client",
    budget=300_000,
    budget_flexibility="strict",
    down_payment_pct=0.2,
    cohost_fee_pct=0.0,
    main_focus=Focus.CASH_FLOW,
    preferred_market_ids=frozenset(),
    avoid_market_ids=frozenset(),
    setting_rank={"lake_mountain": 1, "beach_coastal": 2, "urban_hybrid": 3},
    renovation_appetite="medium",
    wow_factors=(),
    wants_turnkey=False,
    min_bedrooms=3,
)


def make_deal(**changes: Any) -> Deal:
    return replace(DEAL, **changes)


def make_client(**changes: Any) -> Client:
    return replace(CLIENT, **changes)


def make_numbers(
    cash_needed: float = 200_000, coc_low: float = 0.05, cash_flow_low: float = 10_000
) -> DealNumbers:
    return DealNumbers(
        cash_needed=cash_needed,
        annual_debt_service=20_000,
        cash_flow=LowMidHigh(cash_flow_low, cash_flow_low, cash_flow_low),
        coc=LowMidHigh(coc_low, coc_low, coc_low),
    )


def make_feedback(id: int, deal_id: str, reaction: Reaction, comment: str = "") -> Feedback:
    return Feedback(id=id, deal_id=deal_id, reaction=reaction, comment=comment)


@cache
def _raw(name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = json.loads((DATA_DIR / f"{name}.json").read_text())
    return rows


def real_deal(deal_id: str) -> Deal:
    """A deal from the provided data. Market resolution is the database's job, so it is
    left as a placeholder here; integration tests cover it."""
    row = next(r for r in _raw("deals") if r["id"] == deal_id)
    return Deal(
        id=row["id"],
        address=row["address"],
        city=row["city"],
        state=row["state"],
        market_id="unresolved",
        property_key=f"{row['address'].lower()}|{row['state'].lower()}",
        purchase_price=row["purchase_price"],
        bedrooms=row["bedrooms"],
        baths=row["baths"],
        turnkey=row["turnkey"],
        interest_rate=row["interest_rate"],
        closing_cost_pct=row["closing_cost_pct"],
        setup_items=tuple(SetupItem(i["item"], i["cost"]) for i in row["setup_items"]),
        annual_opex=row["annual_opex"],
        revenue=LowMidHigh(**row["revenue"]),
        est_year1_tax_savings=row["est_year1_tax_savings"],
        comps=tuple(Comp(c["revenue"], c["bedrooms"], c["sleeps"]) for c in row["comps"]),
        highlights=tuple(row["highlights"]),
        analyst_notes=row["analyst_notes"],
    )


def real_client(client_id: str) -> Client:
    """A client from the provided data, without market preferences (resolved by the database)."""
    row = next(r for r in _raw("clients") if r["id"] == client_id)
    return Client(
        id=row["id"],
        name=row["name"],
        budget=row["budget"],
        budget_flexibility=row["budget_flexibility"],
        down_payment_pct=row["down_payment_pct"],
        cohost_fee_pct=row["cohost_fee_pct"],
        main_focus=Focus(row["main_focus"]),
        preferred_market_ids=frozenset(),
        avoid_market_ids=frozenset(),
        setting_rank=row["setting_rank"],
        renovation_appetite=row["renovation_appetite"],
        wow_factors=tuple(row["wow_factors"]),
        wants_turnkey=row["wants_turnkey"],
        min_bedrooms=row["min_bedrooms"],
    )


def all_real_highlights_and_notes() -> tuple[set[str], set[str]]:
    deals = _raw("deals")
    return (
        {h for d in deals for h in d["highlights"]},
        {d["analyst_notes"] for d in deals},
    )


def make_signals(**changes: Any) -> Signals:
    return EMPTY_SIGNALS.model_copy(update=changes)
