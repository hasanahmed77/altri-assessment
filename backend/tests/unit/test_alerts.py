from datetime import date

from app.domain.alerts import alerts, parse_budget_range
from app.domain.market_fit import market_fit
from app.domain.models import Client
from app.domain.recommend import recommend
from app.domain.signals import AmountSignal, DateSignal, Evidence, Signals, Trait, WishSignal
from tests.factories import MARKET, make_client, make_deal, make_signals

TODAY = date(2026, 11, 22)


def codes(
    client: Client, signals: Signals, budget_range: str = "", terms: tuple[str, ...] = ()
) -> dict[str, str]:
    markets = {MARKET.id: MARKET}
    result = recommend(client, [make_deal()], markets, [], signals)
    fits = market_fit(client, markets, result.ranked, signals)
    found = alerts(client, budget_range, terms, markets, result, fits, signals, TODAY)
    return {a.code: a.text for a in found}


def test_budget_ranges_parse_to_inclusive_bounds() -> None:
    assert parse_budget_range("$300K-$400K") == (300_000, 400_000)
    assert parse_budget_range("< $200K") == (0, 200_000)
    assert parse_budget_range("> $500K") == (500_000, float("inf"))
    assert parse_budget_range("ask me later") is None


def test_a_deadline_inside_a_month_is_urgent_and_counts_days() -> None:
    signals = make_signals(deadline=DateSignal(date="2026-12-20", quote="Dec 20", source="notes"))
    assert "28 days left" in codes(make_client(), signals)["DEADLINE"]


def test_conflicts_between_what_was_said_and_the_profile_are_raised() -> None:
    client = make_client(budget=500_000, budget_flexibility="flexible", cohost_fee_pct=0.0)
    signals = make_signals(
        soft_budget_cap=AmountSignal(amount=320_000, quote="q", source="notes"),
        uses_cohost=Evidence(quote="q", source="notes"),
    )
    found = codes(client, signals, budget_range="$300K-$400K")
    assert {"SOFT_BUDGET_CAP", "BUDGET_RANGE_CONFLICT", "COHOST_FEE_MISSING"} <= found.keys()


def test_unresolved_terms_and_undecided_clients_are_flagged() -> None:
    found = codes(make_client(), make_signals(), terms=("Charlotte",))
    assert "Charlotte" in found["UNRESOLVED_MARKET"]
    assert "UNDECIDED_MARKET" in found


def test_no_eligible_deal_in_a_preferred_market_is_flagged() -> None:
    client = make_client(budget=10_000, preferred_market_ids=frozenset({"M-01"}))
    assert "Nothing eligible in Poconos" in codes(client, make_signals())["NO_DEALS_IN_PREFERRED"]


def test_a_must_have_no_eligible_deal_offers_is_flagged() -> None:
    ski = WishSignal(trait=Trait.SKI_ACCESS, quote="Really wants a ski destination", source="notes")
    assert "ski access" in codes(make_client(), make_signals(must_haves=[ski]))["MUST_HAVE_UNMET"]


def test_a_budget_said_again_is_not_a_cash_limit() -> None:
    client = make_client(budget=275_000, budget_flexibility="flexible")
    restated = make_signals(soft_budget_cap=AmountSignal(amount=275_000, quote="q", source="notes"))
    assert "SOFT_BUDGET_CAP" not in codes(client, restated)
