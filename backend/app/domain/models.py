from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

Reaction = Literal["up", "down"]


class Focus(StrEnum):
    CASH_FLOW = "cash_flow"
    TAX_SAVINGS = "tax_savings"
    APPRECIATION = "appreciation"
    LIFESTYLE = "lifestyle"


@dataclass(frozen=True)
class LowMidHigh:
    low: float
    mid: float
    high: float


@dataclass(frozen=True)
class Market:
    id: str
    name: str
    state: str
    setting: str
    typical_traveler: str
    annual_appreciation: float


@dataclass(frozen=True)
class SetupItem:
    item: str
    cost: float


@dataclass(frozen=True)
class Comp:
    revenue: float
    bedrooms: int
    sleeps: int


@dataclass(frozen=True)
class Deal:
    id: str
    address: str
    city: str
    state: str
    market_id: str
    property_key: str
    purchase_price: float
    bedrooms: int | None
    baths: float
    turnkey: bool
    interest_rate: float
    closing_cost_pct: float
    setup_items: tuple[SetupItem, ...]
    annual_opex: float
    revenue: LowMidHigh
    est_year1_tax_savings: float
    comps: tuple[Comp, ...]
    highlights: tuple[str, ...]
    analyst_notes: str

    @property
    def setup_cost(self) -> float:
        return sum(item.cost for item in self.setup_items)


@dataclass(frozen=True)
class Client:
    id: str
    name: str
    budget: float
    budget_flexibility: Literal["flexible", "strict"]
    down_payment_pct: float
    cohost_fee_pct: float
    main_focus: Focus
    preferred_market_ids: frozenset[str]
    avoid_market_ids: frozenset[str]
    setting_rank: Mapping[str, int]
    renovation_appetite: Literal["light", "medium", "heavy"]
    wow_factors: tuple[str, ...]
    wants_turnkey: bool
    min_bedrooms: int


@dataclass(frozen=True)
class Feedback:
    id: int
    deal_id: str
    reaction: Reaction
    comment: str
