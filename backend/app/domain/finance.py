from dataclasses import dataclass

from app.domain.models import Client, Deal, LowMidHigh

SETUP_COST_BUFFER = 1.10
LOAN_TERM_MONTHS = 360


@dataclass(frozen=True)
class DealNumbers:
    cash_needed: float
    annual_debt_service: float
    cash_flow: LowMidHigh
    coc: LowMidHigh


def cash_needed(deal: Deal, client: Client) -> float:
    price = deal.purchase_price
    return (
        price * client.down_payment_pct
        + price * deal.closing_cost_pct
        + deal.setup_cost * SETUP_COST_BUFFER
    )


def annual_debt_service(principal: float, annual_rate: float) -> float:
    """Twelve monthly payments of a fixed-rate loan amortized over LOAN_TERM_MONTHS."""
    if annual_rate == 0:
        return principal / LOAN_TERM_MONTHS * 12
    monthly_rate = annual_rate / 12
    monthly_payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -LOAN_TERM_MONTHS)
    return monthly_payment * 12


def deal_numbers(deal: Deal, client: Client) -> DealNumbers:
    cash = cash_needed(deal, client)
    loan = deal.purchase_price * (1 - client.down_payment_pct)
    debt_service = annual_debt_service(loan, deal.interest_rate)

    def cash_flow(revenue: float) -> float:
        return revenue - deal.annual_opex - revenue * client.cohost_fee_pct - debt_service

    flows = LowMidHigh(
        low=cash_flow(deal.revenue.low),
        mid=cash_flow(deal.revenue.mid),
        high=cash_flow(deal.revenue.high),
    )
    return DealNumbers(
        cash_needed=cash,
        annual_debt_service=debt_service,
        cash_flow=flows,
        coc=LowMidHigh(low=flows.low / cash, mid=flows.mid / cash, high=flows.high / cash),
    )
