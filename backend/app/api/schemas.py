from collections.abc import Mapping
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.domain.alerts import Alert
from app.domain.finance import DealNumbers
from app.domain.market_fit import MarketFit
from app.domain.models import Deal, LowMidHigh, Market
from app.domain.near_miss import NearMiss
from app.domain.recommend import ExcludedDeal
from app.domain.scoring import RankedDeal, Reason
from app.domain.signal_fit import WILLING_NOT_WANTED, reading_weight
from app.domain.signals import TRAIT_LABELS, Signals
from app.repository import CallSummary, ClientProfile, FeedbackRecord
from app.services.signals import SignalsStatus

Labels = Mapping[str, str]

# Rules run on unrounded values; rounding happens only here, at the API boundary.
# Ratios keep enough places that a client rounding them for display gets the same
# figure as the explanation text, which is written from the unrounded value.
MONEY_PLACES = 2
RATIO_PLACES = 6


class LowMidHighOut(BaseModel):
    low: float
    mid: float
    high: float

    @classmethod
    def money(cls, values: LowMidHigh) -> "LowMidHighOut":
        return cls(**{k: round(v, MONEY_PLACES) for k, v in vars(values).items()})

    @classmethod
    def ratio(cls, values: LowMidHigh) -> "LowMidHighOut":
        return cls(**{k: round(v, RATIO_PLACES) for k, v in vars(values).items()})


class NumbersOut(BaseModel):
    cash_needed: float
    annual_debt_service: float
    cash_flow: LowMidHighOut
    coc: LowMidHighOut

    @classmethod
    def from_domain(cls, n: DealNumbers) -> "NumbersOut":
        return cls(
            cash_needed=round(n.cash_needed, MONEY_PLACES),
            annual_debt_service=round(n.annual_debt_service, MONEY_PLACES),
            cash_flow=LowMidHighOut.money(n.cash_flow),
            coc=LowMidHighOut.ratio(n.coc),
        )


class MarketOut(BaseModel):
    id: str
    name: str
    state: str
    setting: str


class DealOut(BaseModel):
    id: str
    address: str
    city: str
    state: str
    market: MarketOut
    purchase_price: float
    bedrooms: int | None
    baths: float
    turnkey: bool
    setup_cost: float
    revenue: LowMidHighOut
    est_year1_tax_savings: float
    highlights: list[str]
    analyst_notes: str

    @classmethod
    def from_domain(cls, deal: Deal, market: Market) -> "DealOut":
        return cls(
            id=deal.id,
            address=deal.address,
            city=deal.city,
            state=deal.state,
            market=MarketOut(
                id=market.id, name=market.name, state=market.state, setting=market.setting
            ),
            purchase_price=deal.purchase_price,
            bedrooms=deal.bedrooms,
            baths=deal.baths,
            turnkey=deal.turnkey,
            setup_cost=deal.setup_cost,
            revenue=LowMidHighOut.money(deal.revenue),
            est_year1_tax_savings=deal.est_year1_tax_savings,
            highlights=list(deal.highlights),
            analyst_notes=deal.analyst_notes,
        )


class ReasonOut(BaseModel):
    code: str
    text: str
    weight: float
    quote: str | None = None
    source: str | None = None

    @classmethod
    def from_domain(cls, r: Reason, labels: Labels) -> "ReasonOut":
        return cls(
            code=r.code,
            text=r.text,
            weight=round(r.weight, RATIO_PLACES),
            quote=r.quote,
            source=labels.get(r.source, r.source) if r.source else None,
        )


class RankedDealOut(BaseModel):
    rank: int
    deal: DealOut
    numbers: NumbersOut
    score: float
    status: Literal["new", "alternative_plan", "already_shared"]
    reaction: Literal["up", "down"] | None
    outside_client_markets: bool
    explanation: list[ReasonOut]

    @classmethod
    def from_domain(cls, rank: int, r: RankedDeal, labels: Labels) -> "RankedDealOut":
        c = r.candidate
        return cls(
            rank=rank,
            deal=DealOut.from_domain(c.deal, c.market),
            numbers=NumbersOut.from_domain(c.numbers),
            score=round(r.score, RATIO_PLACES),
            status=r.status,
            reaction=r.reaction,
            outside_client_markets=r.outside_client_markets,
            explanation=[ReasonOut.from_domain(x, labels) for x in r.reasons],
        )


class ViolationOut(BaseModel):
    code: str
    message: str


class NearMissOut(BaseModel):
    max_price: float
    discount: float
    text: str

    @classmethod
    def from_domain(cls, n: NearMiss) -> "NearMissOut":
        return cls(max_price=n.max_price, discount=round(n.discount, RATIO_PLACES), text=n.text)


class ExcludedDealOut(BaseModel):
    deal: DealOut
    numbers: NumbersOut
    violations: list[ViolationOut]
    near_miss: NearMissOut | None

    @classmethod
    def from_domain(cls, e: ExcludedDeal) -> "ExcludedDealOut":
        return cls(
            deal=DealOut.from_domain(e.deal, e.market),
            numbers=NumbersOut.from_domain(e.numbers),
            violations=[ViolationOut(code=v.code, message=v.message) for v in e.violations],
            near_miss=NearMissOut.from_domain(e.near_miss) if e.near_miss else None,
        )


class AlertOut(BaseModel):
    code: str
    severity: Literal["urgent", "warning", "info"]
    text: str
    quote: str | None
    source: str | None

    @classmethod
    def from_domain(cls, a: Alert, labels: Labels) -> "AlertOut":
        source = labels.get(a.source, a.source) if a.source else None
        return cls(code=a.code, severity=a.severity, text=a.text, quote=a.quote, source=source)


class QuoteOut(BaseModel):
    quote: str
    source: str


class SignalOut(BaseModel):
    kind: str
    text: str
    quotes: list[QuoteOut]


def signal_items(
    signals: Signals,
    labels: Labels,
    markets: Mapping[str, Market],
    thumbs: Mapping[int, float],
) -> list[SignalOut]:
    """The signals the rep should read, each once, with every quote behind it. A comment
    reading is listed only when it changes how its thumb counts (`thumbs`: id to ±1)."""
    grouped: dict[tuple[str, str], list[QuoteOut]] = {}

    def add(kind: str, text: str, quote: str, source: str) -> None:
        quotes = grouped.setdefault((kind, text), [])
        quotes.append(QuoteOut(quote=quote, source=labels.get(source, source)))

    if signals.deadline:
        d = signals.deadline
        add("Deadline", d.date, d.quote, d.source)
    if signals.soft_budget_cap:
        c = signals.soft_budget_cap
        add("Cash limit", f"${c.amount:,}", c.quote, c.source)
    for t in signals.must_haves:
        kind = "Open to" if t.trait in WILLING_NOT_WANTED else "Wants"
        add(kind, TRAIT_LABELS[t.trait], t.quote, t.source)
    for a in signals.avoid_traits:
        add("Avoids", TRAIT_LABELS[a.trait], a.quote, a.source)
    for m in signals.preferred_markets:
        add("Market", markets[m.market_id].name, m.quote, m.source)
    for m in signals.avoided_markets:
        add("Against market", markets[m.market_id].name, m.quote, m.source)
    if signals.uses_cohost:
        u = signals.uses_cohost
        add("Co-host", "Plans to use one", u.quote, u.source)
    for q in signals.client_questions:
        add("Asked", "A question to answer", q.quote, q.source)
    for r in signals.feedback_readings:
        if reading_weight(r) != thumbs.get(r.feedback_id):
            add("Comment read as", f"{r.sentiment} ({r.reason})", r.quote, r.source)
    return [SignalOut(kind=k, text=t, quotes=q) for (k, t), q in grouped.items()]


class RecommendationsOut(BaseModel):
    client_id: str
    signals_status: SignalsStatus
    signals: list[SignalOut]
    alerts: list[AlertOut]
    ranked: list[RankedDealOut]
    excluded: list[ExcludedDealOut]


class MarketFitOut(BaseModel):
    rank: int
    market: MarketOut
    typical_traveler: str
    annual_appreciation: float
    eligible_deals: int
    best_deal_id: str | None
    median_coc_low: float | None
    score: float
    avoided: bool
    reasons: list[ReasonOut]

    @classmethod
    def from_domain(cls, rank: int, f: MarketFit, labels: Labels) -> "MarketFitOut":
        m = f.market
        return cls(
            rank=rank,
            market=MarketOut(id=m.id, name=m.name, state=m.state, setting=m.setting),
            typical_traveler=m.typical_traveler,
            annual_appreciation=m.annual_appreciation,
            eligible_deals=f.eligible,
            best_deal_id=f.best_deal_id,
            median_coc_low=(
                round(f.median_coc_low, RATIO_PLACES) if f.median_coc_low is not None else None
            ),
            score=round(f.score, RATIO_PLACES),
            avoided=f.avoided,
            reasons=[ReasonOut.from_domain(r, labels) for r in f.reasons],
        )


class ClientSummaryOut(BaseModel):
    id: str
    name: str
    budget: float
    budget_flexibility: str
    main_focus: str
    preferred_markets: list[str]
    min_bedrooms: int
    feedback_count: int
    summary: str

    @classmethod
    def from_profile(cls, p: ClientProfile, feedback_count: int) -> "ClientSummaryOut":
        c = p.client
        terms = [t for t in p.preferred_terms if t.strip().lower() != "all"]
        if terms:
            markets = ", ".join(terms)
        else:
            markets = "open to any market" if p.preferred_terms else "no market preference"
        return cls(
            id=c.id,
            name=c.name,
            budget=c.budget,
            budget_flexibility=c.budget_flexibility,
            main_focus=c.main_focus.value,
            preferred_markets=list(p.preferred_terms),
            min_bedrooms=c.min_bedrooms,
            feedback_count=feedback_count,
            summary=(
                f"${c.budget:,.0f} ({c.budget_flexibility}), "
                f"{c.main_focus.value.replace('_', ' ')} focus, {markets}, "
                f"{c.min_bedrooms}+ bedrooms"
            ),
        )


class FeedbackOut(BaseModel):
    id: int
    client_id: str
    deal_id: str
    reaction: Literal["up", "down"]
    comment: str
    created_at: date

    @classmethod
    def from_record(cls, r: FeedbackRecord) -> "FeedbackOut":
        f = r.feedback
        return cls(
            id=f.id,
            client_id=r.client_id,
            deal_id=f.deal_id,
            reaction=f.reaction,
            comment=f.comment,
            created_at=r.created_at,
        )


class CallSummaryOut(BaseModel):
    call_date: date
    summary: str

    @classmethod
    def from_record(cls, c: CallSummary) -> "CallSummaryOut":
        return cls(call_date=c.call_date, summary=c.summary)


class ClientDetailOut(BaseModel):
    id: str
    name: str
    budget_range: str
    budget: float
    budget_flexibility: str
    down_payment_pct: float
    cohost_fee_pct: float
    main_focus: str
    preferred_markets: list[str]
    avoid_markets: list[str]
    unresolved_markets: list[str]
    setting_rank: dict[str, int]
    renovation_appetite: str
    wow_factors: list[str]
    wants_turnkey: bool
    min_bedrooms: int
    notes: str
    onboarded_at: date
    feedback: list[FeedbackOut]
    calls: list[CallSummaryOut]

    @classmethod
    def from_profile(
        cls, p: ClientProfile, feedback: list[FeedbackRecord], calls: list[CallSummary]
    ) -> "ClientDetailOut":
        c = p.client
        return cls(
            id=c.id,
            name=c.name,
            budget_range=p.budget_range,
            budget=c.budget,
            budget_flexibility=c.budget_flexibility,
            down_payment_pct=c.down_payment_pct,
            cohost_fee_pct=c.cohost_fee_pct,
            main_focus=c.main_focus.value,
            preferred_markets=list(p.preferred_terms),
            avoid_markets=list(p.avoided_terms),
            unresolved_markets=list(p.unresolved_terms),
            setting_rank=dict(c.setting_rank),
            renovation_appetite=c.renovation_appetite,
            wow_factors=list(c.wow_factors),
            wants_turnkey=c.wants_turnkey,
            min_bedrooms=c.min_bedrooms,
            notes=p.notes,
            onboarded_at=p.onboarded_at,
            feedback=[FeedbackOut.from_record(f) for f in feedback],
            calls=[CallSummaryOut.from_record(x) for x in calls],
        )


class FeedbackIn(BaseModel):
    client_id: str
    deal_id: str
    reaction: Literal["up", "down"]
    comment: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
