import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.finance import annual_debt_service, cash_needed, deal_numbers
from tests.factories import make_client, make_deal, real_client, real_deal


def test_debt_service_matches_a_known_mortgage_payment() -> None:
    # $100,000 at 6% over 30 years is $599.55 a month in any standard mortgage table
    assert annual_debt_service(100_000, 0.06) == pytest.approx(599.55 * 12, abs=0.1)


def test_debt_service_at_zero_interest_is_straight_repayment() -> None:
    assert annual_debt_service(360_000, 0.0) == pytest.approx(12_000)


def test_cash_needed_adds_down_payment_closing_and_buffered_setup() -> None:
    deal = make_deal(purchase_price=400_000, closing_cost_pct=0.03)
    client = make_client(down_payment_pct=0.2)
    # 80,000 down + 12,000 closing + 76,250 setup * 1.10
    assert cash_needed(deal, client) == pytest.approx(80_000 + 12_000 + 83_875)


def test_golden_values_for_c01_and_d126() -> None:
    # Worked by hand from the brief: 479,000 * 0.20 + 479,000 * 0.03 + 113,750 * 1.10
    numbers = deal_numbers(real_deal("D-126"), real_client("C-01"))

    assert numbers.cash_needed == pytest.approx(235_295)
    assert numbers.coc.low == pytest.approx(0.113, abs=5e-4)
    assert numbers.coc.mid == pytest.approx(0.169, abs=5e-4)
    assert numbers.coc.high == pytest.approx(0.225, abs=5e-4)


def test_cash_flow_subtracts_opex_cohost_fee_and_debt() -> None:
    deal = make_deal()
    client = make_client(cohost_fee_pct=0.12)
    numbers = deal_numbers(deal, client)

    expected_low = 90_000 - 30_000 - 90_000 * 0.12 - numbers.annual_debt_service
    assert numbers.cash_flow.low == pytest.approx(expected_low)
    assert numbers.coc.low == pytest.approx(expected_low / numbers.cash_needed)


@given(st.floats(min_value=100_000, max_value=2_000_000))
def test_cash_needed_rises_with_price(price: float) -> None:
    client = make_client()
    cheaper = cash_needed(make_deal(purchase_price=price), client)
    pricier = cash_needed(make_deal(purchase_price=price + 1_000), client)
    assert pricier > cheaper


@given(st.floats(min_value=0, max_value=0.25), st.floats(min_value=0.001, max_value=0.1))
def test_coc_never_rises_with_a_higher_cohost_fee(fee: float, increase: float) -> None:
    deal = make_deal()
    lower = deal_numbers(deal, make_client(cohost_fee_pct=fee)).coc.low
    higher = deal_numbers(deal, make_client(cohost_fee_pct=fee + increase)).coc.low
    assert higher < lower
