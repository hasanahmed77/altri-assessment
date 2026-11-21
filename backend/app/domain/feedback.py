from collections.abc import Iterable, Mapping

from app.domain.models import Deal, Feedback
from app.domain.tags import deal_tags

SAME_MARKET_WEIGHT = 0.5
SHARED_TAGS_WEIGHT = 0.5
AFFINITY_PER_REACTION = 0.1
MAX_AFFINITY = 0.3


def latest_feedback(feedback: Iterable[Feedback]) -> dict[str, Feedback]:
    """The current reaction per deal. Ordered by id because created_at is only a date."""
    latest: dict[str, Feedback] = {}
    for item in sorted(feedback, key=lambda f: f.id):
        latest[item.deal_id] = item
    return latest


def feedback_by_property(
    latest: Mapping[str, Feedback], deals_by_id: Mapping[str, Deal]
) -> dict[str, Feedback]:
    """The most recent reaction to any underwriting plan of each house."""
    by_property: dict[str, Feedback] = {}
    for item in sorted(latest.values(), key=lambda f: f.id):
        by_property[deals_by_id[item.deal_id].property_key] = item
    return by_property


def similarity(a: Deal, b: Deal) -> float:
    same_market = 1.0 if a.market_id == b.market_id else 0.0
    tags_a, tags_b = deal_tags(a), deal_tags(b)
    union = tags_a | tags_b
    shared_tags = len(tags_a & tags_b) / len(union) if union else 0.0
    return SAME_MARKET_WEIGHT * same_market + SHARED_TAGS_WEIGHT * shared_tags


def affinity(deal: Deal, latest: Mapping[str, Feedback], deals_by_id: Mapping[str, Deal]) -> float:
    """Positive when the deal resembles deals the client liked, negative for ones they passed on."""
    total = 0.0
    for item in latest.values():
        reacted = deals_by_id[item.deal_id]
        if reacted.property_key == deal.property_key:
            continue
        sign = 1.0 if item.reaction == "up" else -1.0
        total += sign * similarity(deal, reacted)
    return max(-MAX_AFFINITY, min(MAX_AFFINITY, total * AFFINITY_PER_REACTION))
