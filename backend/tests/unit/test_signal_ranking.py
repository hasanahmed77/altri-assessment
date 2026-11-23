from app.domain.finance import deal_numbers
from app.domain.models import Client, Deal, Feedback, LowMidHigh
from app.domain.scoring import Candidate, RankedDeal, rank
from app.domain.signal_fit import usable_traits
from app.domain.signals import (
    AmountSignal,
    AvoidSignal,
    FeedbackReading,
    MarketSignal,
    Signals,
    Trait,
    WishSignal,
)
from tests.factories import MARKET, make_client, make_deal, make_feedback, make_signals

STRONG = LowMidHigh(110_000, 120_000, 130_000)


def ranking(
    deals: list[Deal],
    signals: Signals,
    feedback: list[Feedback] | None = None,
    client: Client | None = None,
) -> dict[str, RankedDeal]:
    client = client or make_client()
    candidates = [Candidate(d, MARKET, deal_numbers(d, client)) for d in deals]
    ranked = rank(candidates, client, feedback or [], {d.id: d for d in deals}, signals)
    return {r.candidate.deal.id: r for r in ranked}


def wish(t: Trait) -> WishSignal:
    return WishSignal(trait=t, quote="q", source="notes")


def avoid(t: Trait) -> AvoidSignal:
    return AvoidSignal(trait=t, quote="q", source="notes")


def test_a_must_have_lifts_deals_that_have_it_and_explains_with_the_quote() -> None:
    # A weak third deal keeps the other two close once returns are scaled to 0..1
    weak = make_deal(
        id="D-0", property_key="0", highlights=(), revenue=LowMidHigh(60_000, 70_000, 80_000)
    )
    plain = make_deal(
        id="D-1", property_key="1", highlights=(), revenue=LowMidHigh(101_000, 101_000, 101_000)
    )
    on_water = make_deal(
        id="D-2",
        property_key="2",
        highlights=("Lakefront with private dock",),
        revenue=LowMidHigh(100_000, 100_000, 100_000),
    )
    deals = [weak, plain, on_water]

    without = ranking(deals, make_signals())
    with_signal = ranking(deals, make_signals(must_haves=[wish(Trait.WATER)]))

    assert without["D-1"].score > without["D-2"].score
    assert with_signal["D-2"].score > with_signal["D-1"].score
    reason = next(r for r in with_signal["D-2"].reasons if r.code == "MUST_HAVE_MET")
    assert (reason.quote, reason.source) == ("q", "notes")


def test_an_avoided_trait_sinks_a_deal_without_excluding_it() -> None:
    deals = [
        make_deal(id="D-1", property_key="1", revenue=STRONG),
        make_deal(id="D-2", property_key="2"),
    ]
    beach_first = make_client(
        setting_rank={"beach_coastal": 1, "urban_hybrid": 2, "lake_mountain": 3}
    )
    ranked = ranking(
        deals, make_signals(avoid_traits=[avoid(Trait.LAKE_MOUNTAIN)]), client=beach_first
    )
    assert set(ranked) == {"D-1", "D-2"}
    assert all(any(r.code == "AVOID_TRAIT" for r in d.reasons) for d in ranked.values())


def test_a_market_the_client_mentioned_counts_as_preferred() -> None:
    mentioned = make_signals(
        preferred_markets=[MarketSignal(market_id="M-01", quote="q", source="notes")]
    )
    ranked = ranking(
        [make_deal()], mentioned, client=make_client(preferred_market_ids=frozenset({"M-05"}))
    )
    assert any(r.code == "MENTIONED_MARKET" for r in ranked["D-900"].reasons)


def test_cash_over_the_spoken_limit_is_marked_down() -> None:
    deal = make_deal()
    cash = deal_numbers(deal, make_client()).cash_needed
    under = ranking(
        [deal],
        make_signals(soft_budget_cap=AmountSignal(amount=int(cash) + 1, quote="q", source="notes")),
    )
    over = ranking(
        [deal],
        make_signals(soft_budget_cap=AmountSignal(amount=int(cash) - 1, quote="q", source="notes")),
    )
    assert over["D-900"].score < under["D-900"].score
    assert any(r.code == "OVER_SOFT_CAP" for r in over["D-900"].reasons)


def test_a_pass_only_for_timing_is_not_held_against_the_house_or_its_neighbours() -> None:
    passed = make_deal(id="D-1", property_key="1")
    neighbour = make_deal(id="D-2", property_key="2")
    feedback = [make_feedback(31, "D-1", "down", "Just bad timing for us this month.")]
    timing = FeedbackReading(
        feedback_id=31, sentiment="neutral", reason="timing", quote="bad timing"
    )

    plain = ranking([passed, neighbour], make_signals(), feedback)
    read = ranking([passed, neighbour], make_signals(feedback_readings=[timing]), feedback)

    assert read["D-1"].score > plain["D-1"].score
    assert read["D-2"].score > plain["D-2"].score
    assert any(r.code == "SOFT_PASS" for r in read["D-1"].reasons)


def test_readings_that_contradict_the_profile_or_each_other_are_held_back() -> None:
    client = make_client(renovation_appetite="heavy")
    signals = make_signals(
        must_haves=[wish(Trait.VIEWS), wish(Trait.ROOM_TO_ADD)],
        avoid_traits=[avoid(Trait.HEAVY_RENOVATION), avoid(Trait.ROOM_TO_ADD)],
    )

    usable = usable_traits(client, signals)

    assert [w.trait for w in usable.wishes] == [Trait.VIEWS]
    assert usable.avoids == []
    assert len(usable.conflicts) == 3


def test_being_fine_with_a_heavy_renovation_is_not_a_wish() -> None:
    client = make_client(renovation_appetite="heavy")
    signals = make_signals(must_haves=[wish(Trait.HEAVY_RENOVATION)])

    usable = usable_traits(client, signals)
    reasons = ranking([make_deal()], signals, client=client)["D-900"].reasons

    assert usable.wishes == []
    assert usable.conflicts == []
    assert not any(r.code.startswith("MUST_HAVE") for r in reasons)
