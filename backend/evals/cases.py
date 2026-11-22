from collections.abc import Callable
from dataclasses import dataclass

from app.domain.models import Client
from app.domain.signal_fit import cash_limit
from app.domain.signals import Signals, Trait


@dataclass(frozen=True)
class Case:
    client_id: str
    name: str
    expected: str
    check: Callable[[Signals, Client], bool]


def reading(signals: Signals, feedback_id: int) -> tuple[str, str] | None:
    found = next((r for r in signals.feedback_readings if r.feedback_id == feedback_id), None)
    return (found.sentiment, found.reason) if found else None


def wants(signals: Signals, *traits: Trait) -> bool:
    return any(s.trait in traits for s in signals.must_haves)


def avoids(signals: Signals, *traits: Trait) -> bool:
    return any(s.trait in traits for s in signals.avoid_traits)


def markets(signals: Signals) -> set[str]:
    return {s.market_id for s in signals.preferred_markets}


def said_nothing_more(signals: Signals, source: str) -> bool:
    """Only the reading itself may cite this comment."""
    cited = [s.source for group in (signals.must_haves, signals.avoid_traits) for s in group] + [
        s.source for s in signals.preferred_markets + signals.avoided_markets
    ]
    return source not in cited


# Each case comes from the provided data, where the structured fields alone get it wrong.
CASES = [
    Case("C-04", "sarcasm", "'Oh sure, I'd love to fix a 1970s kitchen' reads negative",
         lambda s, _: (reading(s, 38) or ("",))[0] == "negative"),
    Case("C-02", "timing", "'Just bad timing for us this month' is a pass for timing",
         lambda s, _: (reading(s, 31) or ("", ""))[1] == "timing"),
    Case("C-15", "change of mind", "'Actually, looked again ... We like it' reads positive",
         lambda s, _: (reading(s, 28) or ("",))[0] == "positive"),
    Case("C-11", "unsure", "'Hmm. Maybe? Not sure.' reads unsure, not negative",
         lambda s, _: reading(s, 41) in {("neutral", "undecided"), ("neutral", "other")}
         or (reading(s, 41) or ("", ""))[1] == "undecided"),
    Case("C-05", "water must-have", "'Being on the water is a must' becomes a water must-have",
         lambda s, _: wants(s, Trait.WATER, Trait.WATERFRONT)),
    Case("C-09", "party avoidance", "'Avoid markets known for group or party travel'",
         lambda s, _: avoids(s, Trait.PARTY_MARKET)),
    Case("C-01", "soft cap", "'keep total cash under about $320K' is a $320,000 limit",
         lambda s, c: (limit := cash_limit(c, s)) is not None and limit.amount == 320_000),
    Case("C-05", "budget is not a cap", "'Budget around $275K, a little flexible' sets no limit",
         lambda s, c: cash_limit(c, s) is None),
    Case("C-13", "deadline", "'identification window closes Dec 20' is 2026-12-20",
         lambda s, _: s.deadline is not None and s.deadline.date == "2026-12-20"),
    Case("C-08", "ski", "'Really wants a ski destination' becomes ski access",
         lambda s, _: wants(s, Trait.SKI_ACCESS)),
    Case("C-07", "co-host", "'Break-even with a co-host is fine' despite a 0% fee",
         lambda s, _: s.uses_cohost is not None),
    Case("C-03", "not mountains", "'Not interested in mountain cabins' avoids the mountain setting",
         lambda s, _: avoids(s, Trait.LAKE_MOUNTAIN)),
    Case("C-08", "conditional market", "'Poconos only if near a mountain' doesn't rule it out",
         lambda s, _: "M-01" not in {m.market_id for m in s.avoided_markets}),
    Case("C-13", "no invented market", "'Texas Hill Country' is not mapped to San Antonio",
         lambda s, _: "M-13" not in markets(s)),
    Case("C-12", "undecided", "'maybe mountains or a lake' is a setting, not a market",
         lambda s, _: not markets(s) and wants(s, Trait.LAKE_MOUNTAIN)),
    Case("C-09", "polarity: neighbors", "'Too close to the neighbors' never avoids privacy",
         lambda s, _: not avoids(s, Trait.PRIVACY)),
    Case("C-08", "polarity: cabin feel", "'Doesn't have a cabin feel inside' never avoids it",
         lambda s, _: not avoids(s, Trait.CABIN_FEEL)),
    Case("C-14", "innocuous", "'Numbers look solid. What would the hot tub add?' adds no wishes",
         lambda s, _: said_nothing_more(s, "feedback:33")),
]  # fmt: skip
