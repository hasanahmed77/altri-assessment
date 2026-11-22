from dataclasses import dataclass, replace
from math import floor

from app.domain.finance import deal_numbers
from app.domain.models import Client, Deal, Market
from app.domain.rules import RuleCode, Violation, violations
from app.domain.tags import Tag, deal_tags

# A price cut is the one lever a rep has on a deal, and it moves both money rules at once:
# a lower price needs less cash and carries less debt.
MONEY_RULES = frozenset({RuleCode.OVER_BUDGET, RuleCode.DOES_NOT_PENCIL})
MAX_DISCOUNT = 0.05
PRICE_STEP = 1_000
ITERATIONS = 40


@dataclass(frozen=True)
class NearMiss:
    max_price: float
    discount: float
    text: str


def near_miss(
    deal: Deal, client: Client, market: Market, broken: list[Violation]
) -> NearMiss | None:
    """The highest price at which a deal excluded only for money would pass every rule, if it is
    within MAX_DISCOUNT of the asking price. The rules themselves are unchanged."""
    if not broken or any(v.code not in MONEY_RULES for v in broken):
        return None

    def passes(price: float) -> bool:
        repriced = replace(deal, purchase_price=price)
        return not violations(repriced, client, market, deal_numbers(repriced, client))

    failing, passing = deal.purchase_price, deal.purchase_price * (1 - MAX_DISCOUNT)
    if not passes(passing):
        return None
    for _ in range(ITERATIONS):
        middle = (failing + passing) / 2
        if passes(middle):
            passing = middle
        else:
            failing = middle

    offer = floor(passing / PRICE_STEP) * PRICE_STEP
    discount = 1 - offer / deal.purchase_price
    if discount > MAX_DISCOUNT or not passes(offer):
        return None
    text = f"Would pass every rule at ${offer:,.0f} or less ({discount:.1%} under asking)"
    if Tag.NEGOTIABLE in deal_tags(deal):
        text += f"; analyst notes: {deal.analyst_notes.rstrip('.')}"
    return NearMiss(max_price=offer, discount=discount, text=text)
