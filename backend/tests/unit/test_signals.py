import pytest
from pydantic import ValidationError

from app.domain.signals import (
    MARKET_TRAIT_MATCHERS,
    TRAIT_DESCRIPTIONS,
    TRAIT_LABELS,
    TRAIT_MATCHERS,
    AvoidSignal,
    DateSignal,
    FeedbackReading,
    MarketSignal,
    ReactedDeal,
    Trait,
    WishSignal,
    check_against_deals,
    ground,
    has_trait,
)
from tests.factories import MARKET, make_deal, make_signals

SOURCES = {
    "call:2026-10-28": "Has been drawn to lake houses lately.",
    "feedback:35": "Being on the water is a must for us now.",
    "notes": "Doing a 1031 exchange; identification window closes Dec 20.",
}


def test_a_verbatim_quote_is_kept_even_with_different_case_and_spacing() -> None:
    signals = make_signals(
        must_haves=[
            WishSignal(trait=Trait.WATER, quote="being on  the WATER", source="feedback:35")
        ]
    )
    kept, dropped = ground(signals, SOURCES)
    assert kept.must_haves == signals.must_haves
    assert dropped == []


def test_a_paraphrased_quote_is_dropped() -> None:
    signals = make_signals(
        must_haves=[WishSignal(trait=Trait.WATER, quote="wants waterfront", source="feedback:35")]
    )
    kept, dropped = ground(signals, SOURCES)
    assert kept.must_haves == []
    assert len(dropped) == 1


def test_a_real_quote_cited_to_the_wrong_source_is_recited_to_where_it_appears() -> None:
    signals = make_signals(
        preferred_markets=[
            MarketSignal(market_id="M-02", quote="drawn to lake houses", source="notes")
        ]
    )
    assert ground(signals, SOURCES)[0].preferred_markets[0].source == "call:2026-10-28"


def test_a_copied_source_header_still_resolves_to_its_id() -> None:
    signals = make_signals(
        must_haves=[
            WishSignal(trait=Trait.WATER, quote="on the water", source="[feedback:35] Thumbs up")
        ]
    )
    assert ground(signals, SOURCES)[0].must_haves[0].source == "feedback:35"


def test_feedback_readings_are_checked_against_their_own_comment() -> None:
    good = FeedbackReading(feedback_id=35, sentiment="positive", reason="other", quote="a must")
    bad = FeedbackReading(feedback_id=36, sentiment="positive", reason="other", quote="a must")
    assert ground(make_signals(feedback_readings=[good, bad]), SOURCES)[0].feedback_readings == [
        good
    ]


def test_a_deadline_that_is_not_a_date_is_dropped() -> None:
    bad = DateSignal(date="Dec 20", quote="closes Dec 20", source="notes")
    good = DateSignal(date="2026-12-20", quote="closes Dec 20", source="notes")
    assert ground(make_signals(deadline=bad), SOURCES)[0].deadline is None
    assert ground(make_signals(deadline=good), SOURCES)[0].deadline == good


def test_traits_are_decided_from_deal_tags_and_market_data() -> None:
    lake = make_deal(highlights=("Short walk to lake access",))
    assert has_trait(Trait.WATER, lake, MARKET)
    assert not has_trait(Trait.WATERFRONT, lake, MARKET)
    assert has_trait(Trait.LAKE_MOUNTAIN, lake, MARKET)
    assert has_trait(Trait.NEAR_NYC, lake, MARKET)
    assert not has_trait(Trait.PARTY_MARKET, lake, MARKET)


def test_every_trait_has_a_label_a_description_and_a_matcher() -> None:
    matched = set(TRAIT_MATCHERS) | set(MARKET_TRAIT_MATCHERS)
    assert set(TRAIT_LABELS) == set(TRAIT_DESCRIPTIONS) == matched == set(Trait)


def test_a_thumbs_down_cannot_avoid_a_feature_the_house_lacks() -> None:
    plain = make_deal(highlights=())
    wants_cabin = WishSignal(trait=Trait.CABIN_FEEL, quote="no cabin feel", source="feedback:1")
    lacks_cabin = AvoidSignal(trait=Trait.CABIN_FEEL, quote="no cabin feel", source="feedback:1")
    too_much_work = AvoidSignal(
        trait=Trait.HEAVY_RENOVATION, quote="Too much renovation", source="feedback:1"
    )
    signals = make_signals(must_haves=[wants_cabin], avoid_traits=[lacks_cabin, too_much_work])

    kept, dropped = check_against_deals(signals, {"feedback:1": ReactedDeal(plain, MARKET, False)})

    assert kept.must_haves == [wants_cabin]
    assert kept.avoid_traits == [too_much_work]
    assert len(dropped) == 1


def test_the_schema_decides_which_way_a_trait_can_point() -> None:
    with pytest.raises(ValidationError):
        AvoidSignal(trait=Trait.PRIVACY, quote="Too close to the neighbors", source="notes")
    with pytest.raises(ValidationError):
        WishSignal(trait=Trait.PARTY_MARKET, quote="worried about parties", source="notes")
