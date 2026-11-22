from collections.abc import Mapping
from dataclasses import dataclass

from app.domain.models import Client, Deal, Feedback, Market
from app.domain.rules import max_cash
from app.domain.signals import (
    MARKET_TRAITS,
    TRAIT_LABELS,
    AmountSignal,
    AvoidSignal,
    Evidence,
    FeedbackReading,
    Signals,
    Trait,
    TraitSignal,
    WishSignal,
    has_trait,
)

# Signals nudge the ranking; they never exclude a deal. Hard rules stay with the structured
# profile, and an avoid signal is strong enough to sink a deal without hiding it from the rep.
MUST_HAVE_MET = 0.10
MUST_HAVE_MISSING = -0.15
AVOID_TRAIT = -0.40
AVOIDED_MARKET = -0.40
OVER_SOFT_CAP = -0.30
SENTIMENT_SIGNS = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
# Code, not the model, decides what a reason means for ranking: a pass for timing or while
# unsure says nothing about the house, whatever sentiment the model attached to it.
NOT_ABOUT_THE_HOUSE = frozenset({"timing", "undecided"})
RESTATED_BUDGET_TOLERANCE = 0.01


@dataclass(frozen=True)
class Adjustment:
    code: str
    text: str
    weight: float
    evidence: Evidence


def cash_limit(client: Client, signals: Signals) -> AmountSignal | None:
    """A spoken cash limit that changes something: tighter than the profile allows, and not
    just the profile budget said again (models read "budget around $275K" as a limit)."""
    cap = signals.soft_budget_cap
    if cap is None or cap.amount >= max_cash(client):
        return None
    if abs(cap.amount - client.budget) <= client.budget * RESTATED_BUDGET_TOLERANCE:
        return None
    return cap


SETTING_TRAITS = {
    Trait.LAKE_MOUNTAIN: "lake_mountain",
    Trait.BEACH_COASTAL: "beach_coastal",
    Trait.URBAN: "urban_hybrid",
}
LAST_SETTING_RANK = 3


@dataclass(frozen=True)
class UsableTraits:
    wishes: list[WishSignal]
    avoids: list[AvoidSignal]
    conflicts: list[tuple[TraitSignal, str]]


def usable_traits(client: Client, signals: Signals) -> UsableTraits:
    """The wishes and avoidances that may move the ranking. A reading that contradicts the
    profile the client signed off, or another reading, is held back for the rep to confirm."""
    wishes = _first_per_trait(signals.must_haves)
    avoids = _first_per_trait(signals.avoid_traits)
    conflicts: list[tuple[TraitSignal, str]] = []

    mixed = {w.trait for w in wishes} & {a.trait for a in avoids}
    for signal in [*wishes, *avoids]:
        if signal.trait in mixed:
            conflicts.append((signal, f"Mixed signals on {_label(signal)}"))
        elif (problem := _profile_conflict(signal, client)) is not None:
            conflicts.append((signal, problem))

    held = {id(signal) for signal, _ in conflicts}
    return UsableTraits(
        wishes=[w for w in wishes if id(w) not in held],
        avoids=[a for a in avoids if id(a) not in held],
        conflicts=conflicts,
    )


def _profile_conflict(signal: TraitSignal, client: Client) -> str | None:
    wanted = isinstance(signal, WishSignal)
    if signal.trait == Trait.HEAVY_RENOVATION:
        appetite = client.renovation_appetite
        if (wanted and appetite == "light") or (not wanted and appetite == "heavy"):
            verb = "wanting" if wanted else "avoiding"
            return f"Reads as {verb} a heavy renovation, but the profile says {appetite}"
    setting = SETTING_TRAITS.get(signal.trait)
    if setting is not None:
        rank = client.setting_rank.get(setting)
        if (not wanted and rank == 1) or (wanted and rank == LAST_SETTING_RANK):
            verb = "wanting" if wanted else "avoiding"
            return f"Reads as {verb} {_label(signal)}, which the profile ranks #{rank}"
    return None


def signal_adjustments(
    deal: Deal, market: Market, cash_needed: float, client: Client, signals: Signals
) -> list[Adjustment]:
    found: list[Adjustment] = []
    usable = usable_traits(client, signals)

    for wish in usable.wishes:
        label = _label(wish)
        if has_trait(wish.trait, deal, market):
            text = f"Has {label}, which the client asked for"
            found.append(Adjustment("MUST_HAVE_MET", text, MUST_HAVE_MET, wish))
        elif wish.trait not in MARKET_TRAITS:
            text = f"Lacks {label}, which the client asked for"
            found.append(Adjustment("MUST_HAVE_MISSING", text, MUST_HAVE_MISSING, wish))

    for unwanted in usable.avoids:
        if has_trait(unwanted.trait, deal, market):
            text = f"Has {_label(unwanted)}, which the client wants to avoid"
            found.append(Adjustment("AVOID_TRAIT", text, AVOID_TRAIT, unwanted))

    avoided = next((s for s in signals.avoided_markets if s.market_id == market.id), None)
    if avoided is not None:
        text = f"In {market.name}, which the client spoke against"
        found.append(Adjustment("AVOIDED_MARKET_SIGNAL", text, AVOIDED_MARKET, avoided))

    cap = cash_limit(client, signals)
    if cap is not None and cash_needed > cap.amount:
        text = f"Needs ${cash_needed:,.0f} cash, over the ~${cap.amount:,} the client mentioned"
        found.append(Adjustment("OVER_SOFT_CAP", text, OVER_SOFT_CAP, cap))

    return found


def signal_preferred_markets(signals: Signals) -> dict[str, Evidence]:
    avoided = {s.market_id for s in signals.avoided_markets}
    preferred: dict[str, Evidence] = {}
    for signal in signals.preferred_markets:
        if signal.market_id not in avoided:
            preferred.setdefault(signal.market_id, signal)
    return preferred


def reaction_weights(latest: Mapping[str, Feedback], signals: Signals) -> dict[int, float]:
    """How much each reaction counts. The thumb says up or down and the comment says why, so a
    pass caused only by timing, or an unsure one, stops counting against similar deals."""
    readings = {r.feedback_id: r for r in signals.feedback_readings}
    weights: dict[int, float] = {}
    for item in latest.values():
        reading = readings.get(item.id)
        thumb = 1.0 if item.reaction == "up" else -1.0
        weights[item.id] = reading_weight(reading) if reading else thumb
    return weights


def reading_weight(reading: FeedbackReading) -> float:
    if reading.reason in NOT_ABOUT_THE_HOUSE:
        return 0.0
    return SENTIMENT_SIGNS[reading.sentiment]


def _first_per_trait[S: TraitSignal](signals: list[S]) -> list[S]:
    by_trait: dict[str, S] = {}
    for signal in signals:
        by_trait.setdefault(signal.trait, signal)
    return list(by_trait.values())


def _label(signal: TraitSignal) -> str:
    return TRAIT_LABELS[signal.trait]
