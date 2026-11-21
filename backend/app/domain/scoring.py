from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from app.domain.feedback import affinity, feedback_by_property, latest_feedback
from app.domain.finance import DealNumbers
from app.domain.models import Client, Deal, Feedback, Focus, Market, Reaction
from app.domain.tags import WOW_FACTOR_TAGS, deal_tags

# (focus weight, preference weight). Lifestyle clients buy for the experience and the hard
# rule already guarantees they break even, so their preferences dominate.
FOCUS_WEIGHTS: dict[Focus, tuple[float, float]] = {
    Focus.CASH_FLOW: (0.7, 0.3),
    Focus.TAX_SAVINGS: (0.7, 0.3),
    Focus.APPRECIATION: (0.7, 0.3),
    Focus.LIFESTYLE: (0.3, 0.7),
}
PASSED_PENALTY = 1.0
ALTERNATIVE_PLAN_PENALTY = 0.5
NOTABLE_AFFINITY = 0.05
# Where the house is matters more to a client than how it is finished
PREFERENCE_WEIGHTS = {
    "market": 0.35,
    "setting": 0.30,
    "wow_factors": 0.15,
    "renovation": 0.10,
    "turnkey": 0.10,
}
SETTING_RANK_SCORES = {1: 1.0, 2: 0.5, 3: 0.0}
SETTING_LABELS = {
    "lake_mountain": "lake/mountain",
    "beach_coastal": "beach/coastal",
    "urban_hybrid": "urban",
}
RENOVATION_LEVELS = ("light", "medium", "heavy")
LIGHT_SETUP_MAX = 125_000
MEDIUM_SETUP_MAX = 160_000

Status = Literal["new", "alternative_plan", "already_shared"]


@dataclass(frozen=True)
class Candidate:
    deal: Deal
    market: Market
    numbers: DealNumbers


@dataclass(frozen=True)
class Reason:
    code: str
    text: str
    weight: float


@dataclass(frozen=True)
class RankedDeal:
    candidate: Candidate
    score: float
    status: Status
    reaction: Reaction | None
    reasons: tuple[Reason, ...]


def _cash_flow_metric(c: Candidate) -> float:
    coc = c.numbers.coc
    return 0.5 * coc.low + 0.3 * coc.mid + 0.2 * coc.high


def _tax_savings_metric(c: Candidate) -> float:
    return c.deal.est_year1_tax_savings / c.numbers.cash_needed


def _appreciation_metric(c: Candidate) -> float:
    equity_growth = c.deal.purchase_price * c.market.annual_appreciation
    return equity_growth / c.numbers.cash_needed + c.numbers.coc.mid


def _lifestyle_metric(c: Candidate) -> float:
    return c.numbers.cash_flow.low / c.numbers.cash_needed


FOCUS_METRICS: dict[Focus, Callable[[Candidate], float]] = {
    Focus.CASH_FLOW: _cash_flow_metric,
    Focus.TAX_SAVINGS: _tax_savings_metric,
    Focus.APPRECIATION: _appreciation_metric,
    Focus.LIFESTYLE: _lifestyle_metric,
}


def rank(
    candidates: Sequence[Candidate],
    client: Client,
    feedback: Iterable[Feedback],
    deals_by_id: Mapping[str, Deal],
) -> list[RankedDeal]:
    latest = latest_feedback(feedback)
    shared = feedback_by_property(latest, deals_by_id)
    focus_weight, preference_weight = FOCUS_WEIGHTS[client.main_focus]
    metric = FOCUS_METRICS[client.main_focus]
    focus_scores = normalize([metric(c) for c in candidates])

    ranked: list[RankedDeal] = []
    for candidate, focus_score in zip(candidates, focus_scores, strict=True):
        preference, preference_reasons = preference_score(candidate, client)
        score = focus_weight * focus_score + preference_weight * preference
        reasons = [
            Reason("FOCUS", focus_reason(candidate, client.main_focus), focus_weight * focus_score),
            *(Reason(r.code, r.text, r.weight * preference_weight) for r in preference_reasons),
        ]

        previous = shared.get(candidate.deal.property_key)
        if previous is None:
            status: Status = "new"
            reaction = None
            fit = affinity(candidate.deal, latest, deals_by_id)
            score += fit
            if abs(fit) >= NOTABLE_AFFINITY:
                text = (
                    "Similar to deals the client liked"
                    if fit > 0
                    else ("Similar to deals the client passed on")
                )
                reasons.append(Reason("FEEDBACK_SIMILARITY", text, fit))
        else:
            status = "already_shared"
            reaction = previous.reaction
            if reaction == "down":
                score -= PASSED_PENALTY
            reasons.append(Reason("ALREADY_SHARED", _shared_text(candidate.deal, previous), 0.0))

        ranked.append(RankedDeal(candidate, score, status, reaction, _ordered(reasons)))

    return _demote_alternative_plans(sorted(ranked, key=_rank_order))


def _rank_order(r: RankedDeal) -> tuple[float, str]:
    return (-r.score, r.candidate.deal.id)


def _demote_alternative_plans(ranked: list[RankedDeal]) -> list[RankedDeal]:
    """Show each house once: its best-scoring plan leads, other plans follow as alternatives."""
    leading_plan: dict[str, str] = {}
    result: list[RankedDeal] = []
    for r in ranked:
        key = r.candidate.deal.property_key
        if r.status != "new" or key not in leading_plan:
            leading_plan.setdefault(key, r.candidate.deal.id)
            result.append(r)
            continue
        note = Reason(
            "ALTERNATIVE_PLAN",
            f"Another plan for the same house as {leading_plan[key]}, which ranks higher",
            0.0,
        )
        result.append(
            replace(
                r,
                score=r.score - ALTERNATIVE_PLAN_PENALTY,
                status="alternative_plan",
                reasons=(*r.reasons, note),
            )
        )
    return sorted(result, key=_rank_order)


def normalize(values: Sequence[float]) -> list[float]:
    """Min-max scale to 0..1. With fewer than two distinct values every deal scores 1."""
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [1.0] * len(values)
    return [(v - low) / (high - low) for v in values]


def preference_score(c: Candidate, client: Client) -> tuple[float, list[Reason]]:
    """Weighted fit with the client's structured preferences, with the reasons behind it.
    Preferences the client didn't state are left out rather than scored as neutral."""
    parts: list[_Part] = []
    tags = deal_tags(c.deal)

    if client.preferred_market_ids:
        preferred = c.deal.market_id in client.preferred_market_ids
        reason = Reason("PREFERRED_MARKET", f"In {c.market.name}, a preferred market", 1.0)
        parts.append(_Part("market", 1.0 if preferred else 0.0, reason if preferred else None))

    setting_rank = client.setting_rank.get(c.market.setting, 0)
    label = SETTING_LABELS.get(c.market.setting, c.market.setting).capitalize()
    reason = Reason("TOP_SETTING", f"{label} setting, the client's first choice", 1.0)
    parts.append(
        _Part(
            "setting",
            SETTING_RANK_SCORES.get(setting_rank, 0.0),
            reason if setting_rank == 1 else None,
        )
    )

    wanted = [w for w in client.wow_factors if WOW_FACTOR_TAGS.get(w)]
    if wanted:
        matched = [w for w in wanted if WOW_FACTOR_TAGS[w] & tags]
        reason = Reason("WOW_FACTORS", f"Has the {' and '.join(matched)} the client wants", 1.0)
        parts.append(_Part("wow_factors", len(matched) / len(wanted), reason if matched else None))

    level = renovation_level(c.deal)
    distance = abs(
        RENOVATION_LEVELS.index(level) - RENOVATION_LEVELS.index(client.renovation_appetite)
    )
    parts.append(
        _Part("renovation", 1 - distance / 2, _renovation_reason(level, client, c.deal, distance))
    )

    if client.wants_turnkey:
        reason = (
            Reason("TURNKEY", "Turnkey, as the client wants", 1.0)
            if c.deal.turnkey
            else Reason("NOT_TURNKEY", "Not turnkey; the client wants turnkey", -1.0)
        )
        parts.append(_Part("turnkey", 1.0 if c.deal.turnkey else 0.0, reason))

    total_weight = sum(PREFERENCE_WEIGHTS[p.name] for p in parts)
    score = sum(PREFERENCE_WEIGHTS[p.name] * p.value for p in parts) / total_weight
    reasons = [p.weighted_reason(total_weight) for p in parts if p.reason is not None]
    return score, reasons


@dataclass(frozen=True)
class _Part:
    name: str
    value: float
    reason: Reason | None

    def weighted_reason(self, total_weight: float) -> Reason:
        """A positive reason weighs what it added to the score; a caveat weighs what it cost."""
        assert self.reason is not None
        share = self.value if self.reason.weight > 0 else self.value - 1
        weight = PREFERENCE_WEIGHTS[self.name] * share / total_weight
        return Reason(self.reason.code, self.reason.text, weight)


def renovation_level(deal: Deal) -> str:
    if deal.setup_cost <= LIGHT_SETUP_MAX:
        return "light"
    if deal.setup_cost <= MEDIUM_SETUP_MAX:
        return "medium"
    return "heavy"


def focus_reason(c: Candidate, focus: Focus) -> str:
    n = c.numbers
    match focus:
        case Focus.CASH_FLOW:
            return f"{n.coc.low:.1%} cash-on-cash even on low revenue ({n.coc.mid:.1%} expected)"
        case Focus.TAX_SAVINGS:
            return (
                f"About {_usd(c.deal.est_year1_tax_savings)} estimated first-year tax savings "
                f"on {_usd(n.cash_needed)} invested"
            )
        case Focus.APPRECIATION:
            growth = c.market.annual_appreciation
            return (
                f"{c.market.name} values grow about {growth:.1%} a year "
                f"(~{_usd(c.deal.purchase_price * growth)} of equity a year), "
                f"plus {n.coc.mid:.1%} cash-on-cash"
            )
        case Focus.LIFESTYLE:
            return f"Breaks even with {_usd(n.cash_flow.low)} a year to spare on low revenue"


def _renovation_reason(level: str, client: Client, deal: Deal, distance: int) -> Reason | None:
    plan = f"{level.capitalize()} setup plan ({_usd(deal.setup_cost)})"
    if distance == 0:
        return Reason("RENOVATION_FIT", f"{plan} matches the client's renovation appetite", 1.0)
    if distance == 2:
        return Reason(
            "RENOVATION_MISMATCH",
            f"{plan}; the client wants {client.renovation_appetite} work",
            -1.0,
        )
    return None


def _shared_text(deal: Deal, previous: Feedback) -> str:
    verdict = "liked" if previous.reaction == "up" else "passed on"
    if previous.deal_id == deal.id:
        return f"Already shared; the client {verdict} it"
    return (
        f"Already shared as {previous.deal_id} (same house, different plan); "
        f"the client {verdict} it"
    )


def _ordered(reasons: list[Reason]) -> tuple[Reason, ...]:
    focus = [r for r in reasons if r.code == "FOCUS"]
    rest = sorted((r for r in reasons if r.code != "FOCUS"), key=lambda r: -r.weight)
    return (*focus, *rest)


def _usd(amount: float) -> str:
    return f"${amount:,.0f}"
