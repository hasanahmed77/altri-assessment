import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.domain.market_fit import MarketFit
from app.domain.models import Client, Market
from app.domain.near_miss import MONEY_RULES
from app.domain.recommend import ExcludedDeal, Recommendations
from app.domain.rules import RuleCode, max_cash
from app.domain.signal_fit import cash_limit, signal_preferred_markets, usable_traits
from app.domain.signals import (
    MARKET_TRAITS,
    TRAIT_LABELS,
    Evidence,
    Signals,
    deadline_date,
    has_trait,
)

Severity = Literal["urgent", "warning", "info"]
URGENT_DAYS = 30
_AMOUNT = r"\$\s*(\d+(?:\.\d+)?)\s*([KkMm]?)"


@dataclass(frozen=True)
class Alert:
    code: str
    severity: Severity
    text: str
    quote: str | None = None
    source: str | None = None

    @classmethod
    def quoted(cls, code: str, severity: Severity, text: str, evidence: Evidence) -> "Alert":
        return cls(code, severity, text, evidence.quote, evidence.source)


def alerts(
    client: Client,
    budget_range: str,
    unresolved_terms: Sequence[str],
    markets: Mapping[str, Market],
    recommendations: Recommendations,
    fits: Sequence[MarketFit],
    signals: Signals,
    today: date,
) -> list[Alert]:
    """What a rep should know before sending anything, most pressing first."""
    found: list[Alert] = []

    deadline = deadline_date(signals)
    if deadline is not None and signals.deadline is not None and deadline >= today:
        days = (deadline - today).days
        severity: Severity = "urgent" if days <= URGENT_DAYS else "info"
        text = f"Must act by {deadline:%b %-d, %Y}: {days} days left"
        found.append(Alert.quoted("DEADLINE", severity, text, signals.deadline))

    cap = cash_limit(client, signals)
    if cap is not None:
        text = (
            f"Wants to stay under ~${cap.amount:,} cash; the profile allows up to "
            f"${max_cash(client):,.0f}. Deals in between are marked down"
        )
        found.append(Alert.quoted("SOFT_BUDGET_CAP", "warning", text, cap))

    stated = parse_budget_range(budget_range)
    if stated is not None and not stated[0] <= client.budget <= stated[1]:
        text = (
            f"Profile budget ${client.budget:,.0f} is outside the stated range "
            f"{budget_range}; confirm which one is real"
        )
        found.append(Alert("BUDGET_RANGE_CONFLICT", "warning", text))

    if signals.uses_cohost is not None and client.cohost_fee_pct == 0:
        text = "Mentions a co-host, but the profile has no co-host fee, so returns look too high"
        found.append(Alert.quoted("COHOST_FEE_MISSING", "warning", text, signals.uses_cohost))

    to_send = [r.candidate for r in recommendations.ranked if r.status != "already_shared"]
    usable = usable_traits(client, signals)
    for signal, problem in usable.conflicts:
        text = f"{problem}; confirm with the client before relying on it"
        found.append(Alert.quoted("SIGNAL_CONFLICT", "warning", text, signal))

    for wish in usable.wishes:
        if wish.trait in MARKET_TRAITS:
            continue
        if not any(has_trait(wish.trait, c.deal, c.market) for c in to_send):
            text = f"No eligible deal has {TRAIT_LABELS[wish.trait]}, which the client asked for"
            found.append(Alert.quoted("MUST_HAVE_UNMET", "warning", text, wish))

    for question in signals.client_questions:
        text = "The client asked something; reply before sending more deals"
        found.append(Alert.quoted("CLIENT_QUESTION", "warning", text, question))

    for term in unresolved_terms:
        text = f"'{term}' doesn't match a market we cover; ask what they meant"
        found.append(Alert("UNRESOLVED_MARKET", "info", text))

    wanted = client.preferred_market_ids | signal_preferred_markets(signals).keys()
    if wanted:
        names = ", ".join(sorted(markets[m].name for m in wanted))
        in_wanted = [r for r in recommendations.ranked if r.candidate.deal.market_id in wanted]
        if not any(r.status != "already_shared" for r in in_wanted):
            text = (
                f"Every eligible deal in {names} has been shared; nothing new to send there"
                if in_wanted
                else f"Nothing eligible in {names}"
            )
            nearby = [e for e in recommendations.excluded if e.deal.market_id in wanted]
            text += _closest(nearby, client)
            found.append(Alert("NO_DEALS_IN_PREFERRED", "warning", text))
    else:
        text = "Hasn't picked a market yet; see Where to buy"
        found.append(Alert("UNDECIDED_MARKET", "info", text))

    order = {"urgent": 0, "warning": 1, "info": 2}
    return sorted(found, key=lambda a: order[a.severity])


def _closest(excluded: Sequence[ExcludedDeal], client: Client) -> str:
    """How near the nearest money-only miss is, so the rep can talk about price or budget."""
    money_only = [e for e in excluded if all(v.code in MONEY_RULES for v in e.violations)]
    priced = [(e.deal.id, e.near_miss) for e in money_only if e.near_miss is not None]
    if priced:
        deal_id, miss = min(priced, key=lambda pair: pair[1].discount)
        return f"; closest is {deal_id}: {miss.text[0].lower()}{miss.text[1:]}"
    over = [e for e in money_only if {v.code for v in e.violations} == {RuleCode.OVER_BUDGET}]
    if over:
        cheapest = min(over, key=lambda e: e.numbers.cash_needed)
        gap = cheapest.numbers.cash_needed - max_cash(client)
        return f"; cheapest there is {cheapest.deal.id}, ${gap:,.0f} over the client's cash cap"
    return "; see Where to buy for alternatives"


def parse_budget_range(text: str) -> tuple[float, float] | None:
    """'$300K-$400K', '< $200K' and '> $500K' as inclusive bounds; anything else is None."""
    amounts = [_dollars(n, unit) for n, unit in re.findall(_AMOUNT, text)]
    if len(amounts) == 2:
        return (min(amounts), max(amounts))
    if len(amounts) == 1 and text.strip().startswith("<"):
        return (0.0, amounts[0])
    if len(amounts) == 1 and text.strip().startswith(">"):
        return (amounts[0], float("inf"))
    return None


def _dollars(number: str, unit: str) -> float:
    scale = {"k": 1_000, "m": 1_000_000}.get(unit.lower(), 1)
    return float(number) * scale
