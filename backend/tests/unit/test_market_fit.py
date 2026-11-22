from dataclasses import replace

from app.domain.market_fit import market_fit
from app.domain.models import Client
from app.domain.recommend import recommend
from app.domain.signals import AvoidSignal, Signals, Trait
from tests.factories import MARKET, make_client, make_deal, make_signals

BEACH = replace(MARKET, id="M-08", name="Clearwater Area", setting="beach_coastal")
PARTY = replace(MARKET, id="M-12", name="Scottsdale", setting="urban_hybrid")
MARKETS = {m.id: m for m in (MARKET, BEACH, PARTY)}
DEALS = [
    make_deal(id="D-1", property_key="1"),
    make_deal(id="D-2", property_key="2", market_id="M-08"),
    make_deal(id="D-3", property_key="3", market_id="M-12"),
]


def order(client: Client, signals: Signals | None = None) -> list[str]:
    signals = signals or make_signals()
    result = recommend(client, DEALS, MARKETS, [], signals)
    return [f.market.id for f in market_fit(client, MARKETS, result.ranked, signals)]


def test_the_top_setting_leads_and_avoided_markets_go_last() -> None:
    client = make_client(
        setting_rank={"beach_coastal": 1, "lake_mountain": 2, "urban_hybrid": 3},
        avoid_market_ids=frozenset({"M-08"}),
    )
    assert order(client) == ["M-01", "M-12", "M-08"]


def test_a_party_market_drops_for_a_client_who_avoids_them() -> None:
    client = make_client(setting_rank={"urban_hybrid": 1, "lake_mountain": 2, "beach_coastal": 3})
    avoid = make_signals(
        avoid_traits=[AvoidSignal(trait=Trait.PARTY_MARKET, quote="q", source="notes")]
    )
    assert order(client)[0] == "M-12"
    assert order(client, avoid)[-1] == "M-12"
