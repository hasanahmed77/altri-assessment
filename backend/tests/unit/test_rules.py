import pytest

from app.domain.finance import DealNumbers, deal_numbers
from app.domain.models import Client, Deal, Focus
from app.domain.rules import RuleCode, violations
from tests.factories import MARKET, make_client, make_deal, make_numbers, real_client, real_deal


def codes(
    deal: Deal | None = None, client: Client | None = None, numbers: DealNumbers | None = None
) -> set[RuleCode]:
    deal = deal or make_deal()
    client = client or make_client()
    numbers = numbers or make_numbers()
    return {v.code for v in violations(deal, client, MARKET, numbers)}


def test_a_deal_that_fits_breaks_no_rule() -> None:
    assert codes() == set()


def test_strict_budget_allows_exactly_the_budget() -> None:
    client = make_client(budget=200_000, budget_flexibility="strict")
    assert codes(client=client, numbers=make_numbers(cash_needed=200_000)) == set()
    assert codes(client=client, numbers=make_numbers(cash_needed=200_001)) == {RuleCode.OVER_BUDGET}


def test_flexible_budget_allows_up_to_ten_percent_over() -> None:
    client = make_client(budget=200_000, budget_flexibility="flexible")
    assert codes(client=client, numbers=make_numbers(cash_needed=220_000)) == set()
    assert codes(client=client, numbers=make_numbers(cash_needed=220_001)) == {RuleCode.OVER_BUDGET}


def test_avoided_market_is_excluded() -> None:
    client = make_client(avoid_market_ids=frozenset({"M-01"}))
    assert codes(client=client) == {RuleCode.AVOIDED_MARKET}


def test_too_few_bedrooms_is_excluded() -> None:
    assert codes(deal=make_deal(bedrooms=3), client=make_client(min_bedrooms=4)) == {
        RuleCode.TOO_FEW_BEDROOMS
    }


def test_unknown_bedrooms_is_excluded_with_its_own_reason() -> None:
    assert codes(deal=make_deal(bedrooms=None)) == {RuleCode.BEDROOMS_UNKNOWN}


def test_exactly_three_percent_pencils() -> None:
    assert codes(numbers=make_numbers(coc_low=0.03)) == set()
    assert codes(numbers=make_numbers(coc_low=0.0299)) == {RuleCode.DOES_NOT_PENCIL}


def test_lifestyle_only_needs_to_break_even() -> None:
    client = make_client(main_focus=Focus.LIFESTYLE)
    assert codes(client=client, numbers=make_numbers(coc_low=0.001, cash_flow_low=0)) == set()
    assert codes(client=client, numbers=make_numbers(coc_low=0.001, cash_flow_low=-1)) == {
        RuleCode.DOES_NOT_PENCIL
    }


def test_every_broken_rule_is_reported() -> None:
    client = make_client(min_bedrooms=5, avoid_market_ids=frozenset({"M-01"}), budget=100_000)
    numbers = make_numbers(cash_needed=150_000, coc_low=0.01)
    assert codes(deal=make_deal(bedrooms=4), client=client, numbers=numbers) == {
        RuleCode.OVER_BUDGET,
        RuleCode.AVOIDED_MARKET,
        RuleCode.TOO_FEW_BEDROOMS,
        RuleCode.DOES_NOT_PENCIL,
    }


def test_messages_carry_the_numbers() -> None:
    client = make_client(budget=200_000)
    [violation] = violations(make_deal(), client, MARKET, make_numbers(cash_needed=210_000))
    assert violation.message == "Needs $210,000 cash; the client's cap is $200,000"


@pytest.mark.parametrize(
    ("client_id", "deal_id", "expected"),
    [
        # CoC on low revenue is 2.993%: rounding before the check would wrongly pass it
        ("C-03", "D-132", RuleCode.DOES_NOT_PENCIL),
        # Needs $200,600 against a strict $200,000 budget
        ("C-04", "D-136", RuleCode.OVER_BUDGET),
    ],
)
def test_real_deals_just_outside_a_boundary_are_excluded(
    client_id: str, deal_id: str, expected: RuleCode
) -> None:
    deal, client = real_deal(deal_id), real_client(client_id)
    found = {v.code for v in violations(deal, client, MARKET, deal_numbers(deal, client))}
    assert expected in found


@pytest.mark.parametrize(
    ("client_id", "deal_id"),
    [
        # $348,395 against a strict $350,000, and 3.064% CoC on low revenue
        ("C-02", "D-127"),
        # $249,665 against a strict $250,000
        ("C-07", "D-140"),
    ],
)
def test_real_deals_just_inside_every_boundary_pass(client_id: str, deal_id: str) -> None:
    deal, client = real_deal(deal_id), real_client(client_id)
    assert violations(deal, client, MARKET, deal_numbers(deal, client)) == []
