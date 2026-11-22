from dataclasses import replace

from app.domain.finance import deal_numbers
from app.domain.models import Client, Deal, LowMidHigh
from app.domain.near_miss import MAX_DISCOUNT, PRICE_STEP, near_miss
from app.domain.rules import Violation, violations
from tests.factories import MARKET, make_client, make_deal


def broken(deal: Deal, client: Client) -> list[Violation]:
    return violations(deal, client, MARKET, deal_numbers(deal, client))


def passes_at(price: float, deal: Deal, client: Client) -> bool:
    return not broken(replace(deal, purchase_price=price), client)


def test_the_solver_finds_the_highest_round_price_that_passes() -> None:
    client = make_client(budget=500_000)
    deal = make_deal(revenue=LowMidHigh(60_000, 80_000, 90_000))
    found = near_miss(deal, client, MARKET, broken(deal, client))

    assert found is not None
    assert passes_at(found.max_price, deal, client)
    assert not passes_at(found.max_price + PRICE_STEP, deal, client)
    assert 0 < found.discount <= MAX_DISCOUNT


def test_a_deal_that_needs_a_big_cut_is_not_a_near_miss() -> None:
    client = make_client(budget=500_000)
    deal = make_deal(revenue=LowMidHigh(40_000, 50_000, 60_000))
    assert near_miss(deal, client, MARKET, broken(deal, client)) is None


def test_a_deal_broken_for_bedrooms_is_never_a_near_miss() -> None:
    client = make_client(budget=500_000, min_bedrooms=6)
    deal = make_deal(revenue=LowMidHigh(60_000, 80_000, 90_000))
    assert near_miss(deal, client, MARKET, broken(deal, client)) is None


def test_negotiable_deals_say_so() -> None:
    client = make_client(budget=500_000)
    deal = make_deal(
        revenue=LowMidHigh(60_000, 80_000, 90_000), analyst_notes="Seller open to offers."
    )
    found = near_miss(deal, client, MARKET, broken(deal, client))
    assert found is not None and "Seller open to offers" in found.text
