from dataclasses import dataclass
from enum import StrEnum

from app.domain.finance import DealNumbers
from app.domain.models import Client, Deal, Focus, Market

FLEXIBLE_BUDGET_MARGIN = 0.10
MIN_COC_ON_LOW_REVENUE = 0.03


class RuleCode(StrEnum):
    OVER_BUDGET = "OVER_BUDGET"
    AVOIDED_MARKET = "AVOIDED_MARKET"
    TOO_FEW_BEDROOMS = "TOO_FEW_BEDROOMS"
    BEDROOMS_UNKNOWN = "BEDROOMS_UNKNOWN"
    DOES_NOT_PENCIL = "DOES_NOT_PENCIL"


@dataclass(frozen=True)
class Violation:
    code: RuleCode
    message: str


def max_cash(client: Client) -> float:
    if client.budget_flexibility == "flexible":
        return client.budget * (1 + FLEXIBLE_BUDGET_MARGIN)
    return client.budget


def violations(deal: Deal, client: Client, market: Market, numbers: DealNumbers) -> list[Violation]:
    found: list[Violation] = []

    cap = max_cash(client)
    if numbers.cash_needed > cap:
        found.append(
            Violation(
                RuleCode.OVER_BUDGET,
                f"Needs {_usd(numbers.cash_needed)} cash; the client's cap is {_usd(cap)}",
            )
        )

    if deal.market_id in client.avoid_market_ids:
        found.append(
            Violation(RuleCode.AVOIDED_MARKET, f"{market.name} is a market the client avoids")
        )

    if deal.bedrooms is None:
        # Brief: never recommend a deal that breaks a hard rule; a missing count can't be checked
        found.append(
            Violation(
                RuleCode.BEDROOMS_UNKNOWN,
                f"Bedroom count is missing; the client needs at least {client.min_bedrooms}",
            )
        )
    elif deal.bedrooms < client.min_bedrooms:
        found.append(
            Violation(
                RuleCode.TOO_FEW_BEDROOMS,
                f"{deal.bedrooms} bedrooms; the client needs at least {client.min_bedrooms}",
            )
        )

    pencil = _pencil_violation(client, numbers)
    if pencil:
        found.append(pencil)

    return found


def _pencil_violation(client: Client, numbers: DealNumbers) -> Violation | None:
    if client.main_focus == Focus.LIFESTYLE:
        if numbers.cash_flow.low < 0:
            return Violation(
                RuleCode.DOES_NOT_PENCIL,
                f"Loses {_usd(-numbers.cash_flow.low)} a year on low revenue; "
                "lifestyle clients need to at least break even",
            )
        return None
    if numbers.coc.low < MIN_COC_ON_LOW_REVENUE:
        return Violation(
            RuleCode.DOES_NOT_PENCIL,
            f"Cash-on-cash on low revenue is {numbers.coc.low:.2%}; "
            f"the minimum is {MIN_COC_ON_LOW_REVENUE:.2%}",
        )
    return None


def _usd(amount: float) -> str:
    return f"${amount:,.0f}"
