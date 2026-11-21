from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from app.domain.finance import DealNumbers, deal_numbers
from app.domain.models import Client, Deal, Feedback, Market
from app.domain.rules import Violation, violations
from app.domain.scoring import Candidate, RankedDeal, rank


@dataclass(frozen=True)
class ExcludedDeal:
    deal: Deal
    market: Market
    numbers: DealNumbers
    violations: tuple[Violation, ...]


@dataclass(frozen=True)
class Recommendations:
    ranked: tuple[RankedDeal, ...]
    excluded: tuple[ExcludedDeal, ...]


def recommend(
    client: Client,
    deals: Sequence[Deal],
    markets: Mapping[str, Market],
    feedback: Iterable[Feedback],
) -> Recommendations:
    candidates: list[Candidate] = []
    excluded: list[ExcludedDeal] = []

    for deal in deals:
        market = markets[deal.market_id]
        numbers = deal_numbers(deal, client)
        broken = violations(deal, client, market, numbers)
        if broken:
            excluded.append(ExcludedDeal(deal, market, numbers, tuple(broken)))
        else:
            candidates.append(Candidate(deal, market, numbers))

    ranked = rank(candidates, client, feedback, {d.id: d for d in deals})
    return Recommendations(
        ranked=tuple(ranked),
        excluded=tuple(sorted(excluded, key=lambda e: e.deal.id)),
    )
