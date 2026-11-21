from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.domain.finance import DealNumbers
from app.domain.models import Deal, LowMidHigh, Market
from app.domain.recommend import ExcludedDeal
from app.domain.scoring import RankedDeal
from app.repository import CallSummary, ClientProfile, FeedbackRecord

# Rules run on unrounded values; rounding happens only here, at the API boundary
MONEY_PLACES = 2
RATIO_PLACES = 4


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


class RankedDealOut(BaseModel):
    rank: int
    deal: DealOut
    numbers: NumbersOut
    score: float
    status: Literal["new", "alternative_plan", "already_shared"]
    reaction: Literal["up", "down"] | None
    explanation: list[ReasonOut]

    @classmethod
    def from_domain(cls, rank: int, r: RankedDeal) -> "RankedDealOut":
        c = r.candidate
        return cls(
            rank=rank,
            deal=DealOut.from_domain(c.deal, c.market),
            numbers=NumbersOut.from_domain(c.numbers),
            score=round(r.score, RATIO_PLACES),
            status=r.status,
            reaction=r.reaction,
            explanation=[
                ReasonOut(code=x.code, text=x.text, weight=round(x.weight, RATIO_PLACES))
                for x in r.reasons
            ],
        )


class ViolationOut(BaseModel):
    code: str
    message: str


class ExcludedDealOut(BaseModel):
    deal: DealOut
    numbers: NumbersOut
    violations: list[ViolationOut]

    @classmethod
    def from_domain(cls, e: ExcludedDeal) -> "ExcludedDealOut":
        return cls(
            deal=DealOut.from_domain(e.deal, e.market),
            numbers=NumbersOut.from_domain(e.numbers),
            violations=[ViolationOut(code=v.code, message=v.message) for v in e.violations],
        )


class RecommendationsOut(BaseModel):
    client_id: str
    ranked: list[RankedDealOut]
    excluded: list[ExcludedDealOut]


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
        markets = ", ".join(p.preferred_terms) or "no market preference"
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
