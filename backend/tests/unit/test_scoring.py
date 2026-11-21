from app.domain.finance import deal_numbers
from app.domain.models import Client, Deal, Feedback, Focus, LowMidHigh
from app.domain.scoring import Candidate, RankedDeal, normalize, rank
from tests.factories import MARKET, make_client, make_deal, make_feedback


def ranking(
    deals: list[Deal], client: Client | None = None, feedback: list[Feedback] | None = None
) -> list[RankedDeal]:
    client = client or make_client()
    candidates = [Candidate(d, MARKET, deal_numbers(d, client)) for d in deals]
    return rank(candidates, client, feedback or [], {d.id: d for d in deals})


def ids(ranked: list[RankedDeal]) -> list[str]:
    return [r.candidate.deal.id for r in ranked]


def test_normalize_scales_to_zero_and_one() -> None:
    assert normalize([2.0, 4.0, 3.0]) == [0.0, 1.0, 0.5]


def test_normalize_handles_zero_one_and_equal_values() -> None:
    assert normalize([]) == []
    assert normalize([5.0]) == [1.0]
    assert normalize([3.0, 3.0]) == [1.0, 1.0]


def test_cash_flow_clients_get_the_best_downside_return_first() -> None:
    strong = make_deal(id="D-1", property_key="1", revenue=LowMidHigh(110_000, 120_000, 130_000))
    weak = make_deal(id="D-2", property_key="2", revenue=LowMidHigh(80_000, 90_000, 100_000))
    assert ids(ranking([weak, strong])) == ["D-1", "D-2"]


def test_tax_clients_get_the_most_tax_savings_per_dollar_first() -> None:
    client = make_client(main_focus=Focus.TAX_SAVINGS)
    big_saving = make_deal(id="D-1", property_key="1", est_year1_tax_savings=90_000)
    small_saving = make_deal(id="D-2", property_key="2", est_year1_tax_savings=40_000)
    assert ids(ranking([small_saving, big_saving], client)) == ["D-1", "D-2"]


def test_ties_are_broken_by_deal_id() -> None:
    a = make_deal(id="D-2", property_key="2")
    b = make_deal(id="D-1", property_key="1")
    assert ids(ranking([a, b])) == ["D-1", "D-2"]


def test_the_explanation_leads_with_the_clients_main_focus() -> None:
    [only] = ranking([make_deal()])
    assert only.reasons[0].code == "FOCUS"
    assert "cash-on-cash" in only.reasons[0].text


def test_a_passed_deal_stays_listed_but_sinks_to_the_bottom() -> None:
    best = make_deal(id="D-1", property_key="1", revenue=LowMidHigh(120_000, 130_000, 140_000))
    other = make_deal(id="D-2", property_key="2")
    ranked = ranking([best, other], feedback=[make_feedback(1, "D-1", "down")])

    assert ids(ranked) == ["D-2", "D-1"]
    assert (ranked[1].status, ranked[1].reaction) == ("already_shared", "down")


def test_another_plan_of_a_shared_house_is_marked_already_shared() -> None:
    light = make_deal(id="D-126", property_key="3094 willow trl|pa")
    full = make_deal(id="D-116", property_key="3094 willow trl|pa")
    ranked = ranking([light, full], feedback=[make_feedback(1, "D-126", "up")])

    by_id = {r.candidate.deal.id: r for r in ranked}
    assert by_id["D-116"].status == "already_shared"
    assert "same house" in by_id["D-116"].reasons[-1].text


def test_feedback_moves_similar_deals() -> None:
    passed = make_deal(id="D-1", property_key="1", market_id="M-01")
    similar = make_deal(id="D-2", property_key="2", market_id="M-01")
    different = make_deal(id="D-3", property_key="3", market_id="M-09", highlights=())

    before = {r.candidate.deal.id: r.score for r in ranking([passed, similar, different])}
    after = {
        r.candidate.deal.id: r.score
        for r in ranking([passed, similar, different], feedback=[make_feedback(1, "D-1", "down")])
    }
    assert after["D-2"] < before["D-2"]


def test_lifestyle_clients_weigh_preferences_over_returns() -> None:
    client = make_client(main_focus=Focus.LIFESTYLE, preferred_market_ids=frozenset({"M-01"}))
    preferred = make_deal(id="D-1", property_key="1", revenue=LowMidHigh(90_000, 95_000, 100_000))
    elsewhere = make_deal(
        id="D-2",
        property_key="2",
        market_id="M-99",
        revenue=LowMidHigh(120_000, 130_000, 140_000),
    )
    assert ids(ranking([elsewhere, preferred], client))[0] == "D-1"


def test_each_house_leads_with_one_plan_and_other_plans_follow() -> None:
    full = make_deal(id="D-116", property_key="same", revenue=LowMidHigh(130_000, 140_000, 150_000))
    light = make_deal(id="D-126", property_key="same")
    other = make_deal(id="D-2", property_key="other", revenue=LowMidHigh(95_000, 105_000, 115_000))
    ranked = ranking([light, other, full])

    by_id = {r.candidate.deal.id: r for r in ranked}
    assert by_id["D-116"].status == "new"
    assert by_id["D-126"].status == "alternative_plan"
    assert "same house as D-116" in by_id["D-126"].reasons[-1].text
    assert ids(ranked).index("D-2") < ids(ranked).index("D-126")
