from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import Settings
from app.domain.signals import FeedbackReading, Trait, TraitSignal
from app.main import create_app
from tests.factories import make_signals
from tests.fakes import FakeExtractor

WATER = TraitSignal(trait=Trait.WATER, quote="Being on the water is a must", source="feedback:35")


def recommendations(api: TestClient, client_id: str) -> dict[str, Any]:
    response = api.get(f"/clients/{client_id}/recommendations")
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def test_signals_are_extracted_once_and_then_served_from_the_cache(
    api: TestClient, extractor: FakeExtractor
) -> None:
    # TestClient runs background tasks before returning, so the first call also extracts
    assert recommendations(api, "C-05")["signals_status"] == "updating"
    assert len(extractor.calls) == 1

    assert recommendations(api, "C-05")["signals_status"] == "fresh"
    api.get("/clients/C-05/markets")
    assert len(extractor.calls) == 1


def test_only_a_comment_triggers_a_new_extraction(
    api: TestClient, extractor: FakeExtractor
) -> None:
    recommendations(api, "C-05")
    thumb = {"client_id": "C-05", "deal_id": "D-117", "reaction": "up"}

    api.post("/feedback", json=thumb)
    assert recommendations(api, "C-05")["signals_status"] == "fresh"
    assert len(extractor.calls) == 1

    api.post("/feedback", json=thumb | {"comment": "Love the dock"})
    assert len(extractor.calls) == 2
    assert recommendations(api, "C-05")["signals_status"] == "fresh"
    assert extractor.calls[-1][-1].text == "Love the dock"


def test_signals_rerank_deals_and_explain_with_the_clients_words(
    api: TestClient, extractor: FakeExtractor
) -> None:
    extractor.signals = make_signals(must_haves=[WATER])
    recommendations(api, "C-05")
    ranked = recommendations(api, "C-05")["ranked"]

    met = [
        reason
        for item in ranked
        for reason in item["explanation"]
        if reason["code"] == "MUST_HAVE_MET"
    ]
    assert met
    assert met[0]["quote"] == WATER.quote
    assert met[0]["source"].startswith("Thumbs up on D-133")


def test_a_quote_the_client_never_said_is_dropped_before_it_is_stored(
    api: TestClient, extractor: FakeExtractor, database_url: str
) -> None:
    invented = WATER.model_copy(update={"quote": "We only want lakefront"})
    extractor.signals = make_signals(must_haves=[invented])
    recommendations(api, "C-05")

    body = recommendations(api, "C-05")
    assert body["signals"] == []
    with create_engine(database_url).connect() as conn:
        dropped = conn.execute(
            text("SELECT dropped FROM client_signals WHERE client_id = 'C-05'")
        ).scalar_one()
    assert len(dropped) == 1


def test_a_timing_pass_is_not_held_against_similar_deals(
    api: TestClient, extractor: FakeExtractor
) -> None:
    recommendations(api, "C-02")  # the fake replaces the snapshot with no readings
    before = {r["deal"]["id"]: r["score"] for r in recommendations(api, "C-02")["ranked"]}
    timing = FeedbackReading(
        feedback_id=31, sentiment="neutral", reason="timing", quote="Just bad timing"
    )
    extractor.signals = make_signals(feedback_readings=[timing])
    comment = {"client_id": "C-02", "deal_id": "D-117", "reaction": "up", "comment": "Nice"}
    api.post("/feedback", json=comment)

    after = {r["deal"]["id"]: r for r in recommendations(api, "C-02")["ranked"]}
    d145 = after["D-145"]
    assert d145["score"] > before["D-145"]
    assert any(r["code"] == "SOFT_PASS" for r in d145["explanation"])


def test_without_an_api_key_the_committed_snapshot_is_served_until_a_new_comment(
    database_url: str,
) -> None:
    app = create_app(Settings(database_url=database_url, openai_api_key=""))
    with TestClient(app) as api:
        before = recommendations(api, "C-05")
        comment = {"client_id": "C-05", "deal_id": "D-117", "reaction": "up", "comment": "Nice"}
        api.post("/feedback", json=comment)
        after = recommendations(api, "C-05")

    assert before["signals_status"] == "fresh"
    assert any(s["kind"] == "Wants" for s in before["signals"])
    assert after["signals_status"] == "stale"
    assert after["signals"] == before["signals"]


def test_where_to_buy_ranks_every_market_and_puts_avoided_ones_last(api: TestClient) -> None:
    markets = api.get("/clients/C-11/markets").json()

    assert [m["rank"] for m in markets] == list(range(1, 15))
    florida = [m for m in markets if m["market"]["state"] == "FL"]
    assert all(m["avoided"] for m in florida)
    assert markets[-len(florida) :] == florida


def test_a_deal_that_misses_by_a_little_carries_the_price_that_would_pass(
    api: TestClient,
) -> None:
    excluded = {e["deal"]["id"]: e for e in recommendations(api, "C-13")["excluded"]}
    miss = excluded["D-138"]["near_miss"]

    assert miss is not None
    assert miss["max_price"] < excluded["D-138"]["deal"]["purchase_price"]


def test_profile_conflicts_and_unknown_markets_raise_alerts(api: TestClient) -> None:
    c03 = {a["code"] for a in recommendations(api, "C-03")["alerts"]}
    c13 = {a["code"] for a in recommendations(api, "C-13")["alerts"]}

    assert {"BUDGET_RANGE_CONFLICT", "UNRESOLVED_MARKET"} <= c03
    assert "UNRESOLVED_MARKET" in c13
