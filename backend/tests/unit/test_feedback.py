from app.domain.feedback import MAX_AFFINITY, affinity, feedback_by_property, latest_feedback
from tests.factories import make_deal, make_feedback


def test_latest_reaction_wins_by_id() -> None:
    # C-15 passed on D-101, then liked it after a second look
    feedback = [make_feedback(28, "D-101", "up"), make_feedback(16, "D-101", "down")]
    assert latest_feedback(feedback)["D-101"].reaction == "up"


def test_a_reaction_covers_every_plan_of_the_same_house() -> None:
    light = make_deal(id="D-126", property_key="3094 willow trl|pa")
    full = make_deal(id="D-116", property_key="3094 willow trl|pa")
    deals = {d.id: d for d in (light, full)}

    shared = feedback_by_property(latest_feedback([make_feedback(1, "D-126", "up")]), deals)

    assert shared[full.property_key].deal_id == "D-126"


def test_affinity_is_positive_for_deals_like_liked_ones_and_negative_for_passed_ones() -> None:
    liked = make_deal(id="D-1", property_key="a", market_id="M-01")
    candidate = make_deal(id="D-2", property_key="b", market_id="M-01")
    deals = {d.id: d for d in (liked, candidate)}

    assert affinity(candidate, latest_feedback([make_feedback(1, "D-1", "up")]), deals) > 0
    assert affinity(candidate, latest_feedback([make_feedback(1, "D-1", "down")]), deals) < 0


def test_affinity_is_capped() -> None:
    candidate = make_deal(id="D-0", property_key="candidate")
    liked = [make_deal(id=f"D-{i}", property_key=f"house-{i}") for i in range(1, 30)]
    deals = {d.id: d for d in (candidate, *liked)}
    feedback = [make_feedback(i, d.id, "up") for i, d in enumerate(liked, start=1)]

    assert affinity(candidate, latest_feedback(feedback), deals) == MAX_AFFINITY


def test_affinity_ignores_reactions_to_the_same_house() -> None:
    other_plan = make_deal(id="D-1", property_key="same")
    candidate = make_deal(id="D-2", property_key="same")
    deals = {d.id: d for d in (other_plan, candidate)}

    assert affinity(candidate, latest_feedback([make_feedback(1, "D-1", "up")]), deals) == 0
