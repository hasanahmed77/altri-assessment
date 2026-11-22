import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, WithJsonSchema

from app.domain.models import Deal, Market
from app.domain.tags import Tag, deal_tags, renovation_level

MarketId = Literal[
    "M-01", "M-02", "M-03", "M-04", "M-05", "M-06", "M-07",
    "M-08", "M-09", "M-10", "M-11", "M-12", "M-13", "M-14",
]  # fmt: skip


class Trait(StrEnum):
    WATER = "water"
    WATERFRONT = "waterfront"
    SKI_ACCESS = "ski_access"
    VIEWS = "views"
    PRIVACY = "privacy"
    NEWER_BUILD = "newer_build"
    CABIN_FEEL = "cabin_feel"
    DATED_INTERIOR = "dated_interior"
    TURNKEY = "turnkey"
    HEAVY_RENOVATION = "heavy_renovation"
    NEAR_ATTRACTIONS = "near_attractions"
    ROOM_TO_ADD = "room_to_add"
    LAKE_MOUNTAIN = "lake_mountain"
    BEACH_COASTAL = "beach_coastal"
    URBAN = "urban"
    PARTY_MARKET = "party_market"
    NEAR_NYC = "near_nyc"


# The model picks traits by these descriptions, and the matchers below decide them on deals,
# so a signal and a deal are compared by code, never by the model.
TRAIT_DESCRIPTIONS: dict[Trait, str] = {
    Trait.WATER: "on or near water of any kind: lakefront, lake access, dock, beach",
    Trait.WATERFRONT: "directly on the water (lakefront, dock)",
    Trait.SKI_ACCESS: "close to ski lifts or a ski mountain",
    Trait.VIEWS: "scenic or mountain views",
    Trait.PRIVACY: "privacy, seclusion, space from neighbors",
    Trait.NEWER_BUILD: "newer construction, low maintenance",
    Trait.CABIN_FEEL: "interior style only: log-cabin or rustic finishes inside the house",
    Trait.DATED_INTERIOR: "dated interior that needs cosmetic work (old kitchen, fixtures)",
    Trait.TURNKEY: "ready to rent with no renovation to manage",
    Trait.HEAVY_RENOVATION: "a big renovation or transformation project",
    Trait.NEAR_ATTRACTIONS: "close to dining, events and things to do",
    Trait.ROOM_TO_ADD: "room on the lot to add amenities (pool, sauna, games)",
    Trait.LAKE_MOUNTAIN: "the kind of place: lakes or mountains (mountain cabins, lake houses)",
    Trait.BEACH_COASTAL: "the kind of place: beach or coast",
    Trait.URBAN: "the kind of place: a city",
    Trait.PARTY_MARKET: "a market known for group, party or event travel",
    Trait.NEAR_NYC: "within a few hours' drive of New York City or northern New Jersey",
}

TRAIT_LABELS: dict[Trait, str] = {
    Trait.WATER: "water access",
    Trait.WATERFRONT: "waterfront",
    Trait.SKI_ACCESS: "ski access",
    Trait.VIEWS: "views",
    Trait.PRIVACY: "privacy",
    Trait.NEWER_BUILD: "a newer build",
    Trait.CABIN_FEEL: "a cabin feel inside",
    Trait.DATED_INTERIOR: "a dated interior",
    Trait.TURNKEY: "a turnkey setup",
    Trait.HEAVY_RENOVATION: "a heavy renovation",
    Trait.NEAR_ATTRACTIONS: "things to do nearby",
    Trait.ROOM_TO_ADD: "room to add amenities",
    Trait.LAKE_MOUNTAIN: "a lake/mountain setting",
    Trait.BEACH_COASTAL: "a beach/coastal setting",
    Trait.URBAN: "a city setting",
    Trait.PARTY_MARKET: "a party crowd",
    Trait.NEAR_NYC: "a short drive from NYC",
}

# From each market's typical traveler: bachelor parties, spring-break and event groups
PARTY_MARKETS = frozenset({"M-10", "M-12", "M-13", "M-14"})
NEAR_NYC_MARKETS = frozenset({"M-01", "M-05"})


def _tagged(*tags: Tag) -> Callable[[Deal, Market], bool]:
    return lambda deal, _: bool(deal_tags(deal) & set(tags))


TRAIT_MATCHERS: dict[Trait, Callable[[Deal, Market], bool]] = {
    Trait.WATER: _tagged(Tag.WATERFRONT, Tag.LAKE_ACCESS, Tag.BEACH_ACCESS),
    Trait.WATERFRONT: _tagged(Tag.WATERFRONT),
    Trait.SKI_ACCESS: _tagged(Tag.SKI_ACCESS),
    Trait.VIEWS: _tagged(Tag.VIEWS),
    Trait.PRIVACY: _tagged(Tag.PRIVACY),
    Trait.NEWER_BUILD: _tagged(Tag.NEWER_BUILD),
    Trait.CABIN_FEEL: _tagged(Tag.CABIN_FEEL),
    Trait.DATED_INTERIOR: _tagged(Tag.DATED_INTERIOR),
    Trait.TURNKEY: lambda deal, _: deal.turnkey,
    Trait.HEAVY_RENOVATION: lambda deal, _: renovation_level(deal) == "heavy",
    Trait.NEAR_ATTRACTIONS: _tagged(Tag.NEAR_ATTRACTIONS),
    Trait.ROOM_TO_ADD: _tagged(Tag.ROOM_TO_ADD),
}
# Yes-or-no features read from a deal's highlights and notes, as opposed to judgments
# (how much renovation is too much) or facts about the market
FEATURE_TRAITS = frozenset(
    {
        Trait.WATER,
        Trait.WATERFRONT,
        Trait.SKI_ACCESS,
        Trait.VIEWS,
        Trait.PRIVACY,
        Trait.NEWER_BUILD,
        Trait.CABIN_FEEL,
        Trait.DATED_INTERIOR,
        Trait.NEAR_ATTRACTIONS,
        Trait.ROOM_TO_ADD,
    }
)
MARKET_TRAIT_MATCHERS: dict[Trait, Callable[[Market], bool]] = {
    Trait.LAKE_MOUNTAIN: lambda market: market.setting == "lake_mountain",
    Trait.BEACH_COASTAL: lambda market: market.setting == "beach_coastal",
    Trait.URBAN: lambda market: market.setting == "urban_hybrid",
    Trait.PARTY_MARKET: lambda market: market.id in PARTY_MARKETS,
    Trait.NEAR_NYC: lambda market: market.id in NEAR_NYC_MARKETS,
}
MARKET_TRAITS = frozenset(MARKET_TRAIT_MATCHERS)


def market_has_trait(trait: Trait, market: Market) -> bool:
    matcher = MARKET_TRAIT_MATCHERS.get(trait)
    return matcher is not None and matcher(market)


def has_trait(trait: Trait, deal: Deal, market: Market) -> bool:
    if trait in MARKET_TRAIT_MATCHERS:
        return market_has_trait(trait, market)
    return TRAIT_MATCHERS[trait](deal, market)


Sentiment = Literal["positive", "neutral", "negative"]
FeedbackReason = Literal[
    "price", "location", "returns", "renovation", "privacy",
    "remoteness", "style", "timing", "undecided", "other",
]  # fmt: skip


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    quote: str
    source: str


class TraitSignal(Evidence):
    trait: Trait


# Which way a trait can point is decided here, not by the model. Nobody avoids privacy or
# views and nobody wants a party crowd, yet models invert complaints into exactly that
# ("Too close to the neighbors" read as avoiding privacy). The schema sent to the model offers
# only the allowed traits for each list, and validation rejects the rest.
WANTABLE = frozenset(Trait) - {Trait.PARTY_MARKET, Trait.DATED_INTERIOR}
AVOIDABLE = frozenset(
    {
        Trait.DATED_INTERIOR,
        Trait.HEAVY_RENOVATION,
        Trait.CABIN_FEEL,
        Trait.NEAR_ATTRACTIONS,
        Trait.ROOM_TO_ADD,
        Trait.LAKE_MOUNTAIN,
        Trait.BEACH_COASTAL,
        Trait.URBAN,
        Trait.PARTY_MARKET,
    }
)


def _only(allowed: frozenset[Trait]) -> Callable[[Trait], Trait]:
    def check(trait: Trait) -> Trait:
        if trait not in allowed:
            raise ValueError(f"{trait.value} is not allowed here")
        return trait

    return check


def _enum_of(allowed: frozenset[Trait]) -> WithJsonSchema:
    return WithJsonSchema({"type": "string", "enum": sorted(t.value for t in allowed)})


class WishSignal(TraitSignal):
    trait: Annotated[Trait, AfterValidator(_only(WANTABLE)), _enum_of(WANTABLE)]


class AvoidSignal(TraitSignal):
    trait: Annotated[Trait, AfterValidator(_only(AVOIDABLE)), _enum_of(AVOIDABLE)]


class MarketSignal(Evidence):
    market_id: MarketId


class AmountSignal(Evidence):
    amount: int


class DateSignal(Evidence):
    date: str


class FeedbackReading(BaseModel):
    model_config = ConfigDict(frozen=True)

    feedback_id: int
    sentiment: Sentiment
    reason: FeedbackReason
    quote: str

    @property
    def source(self) -> str:
        return f"feedback:{self.feedback_id}"


class Signals(BaseModel):
    """What a client said, as checkable claims. Every field carries the words it came from."""

    model_config = ConfigDict(frozen=True)

    must_haves: list[WishSignal]
    avoid_traits: list[AvoidSignal]
    preferred_markets: list[MarketSignal]
    avoided_markets: list[MarketSignal]
    soft_budget_cap: AmountSignal | None
    deadline: DateSignal | None
    uses_cohost: Evidence | None
    feedback_readings: list[FeedbackReading]


EMPTY_SIGNALS = Signals(
    must_haves=[],
    avoid_traits=[],
    preferred_markets=[],
    avoided_markets=[],
    soft_budget_cap=None,
    deadline=None,
    uses_cohost=None,
    feedback_readings=[],
)


_CURLY_QUOTES = str.maketrans({0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"'})


def _normalized(text: str) -> str:
    text = text.translate(_CURLY_QUOTES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def source_id(cited: str) -> str:
    """The id a model meant to cite. Models sometimes copy the whole source header
    ("[call:2026-09-10] Call on ..."); the quote is still checked against that one source."""
    match = re.match(r"\[?([\w:-]+)\]?", cited.strip())
    return match.group(1) if match else cited


def is_grounded(quote: str, source: str, sources: Mapping[str, str]) -> bool:
    """A quote counts only if it appears word for word in the source it cites."""
    text = sources.get(source_id(source))
    needle = _normalized(quote)
    return text is not None and bool(needle) and needle in _normalized(text)


def locate(quote: str, cited: str, sources: Mapping[str, str]) -> str | None:
    """The source a quote really comes from. The model's citation wins when it is right; a real
    quote cited to the wrong source is re-cited when exactly one source contains it."""
    if is_grounded(quote, cited, sources):
        return source_id(cited)
    containing = [sid for sid in sources if is_grounded(quote, sid, sources)]
    return containing[0] if len(containing) == 1 else None


def ground(signals: Signals, sources: Mapping[str, str]) -> tuple[Signals, list[str]]:
    """Drop every claim whose quote the client never said, and say what was dropped."""
    dropped: list[str] = []

    def keep[S: Evidence](items: list[S], label: str) -> list[S]:
        kept = []
        for item in items:
            found = locate(item.quote, item.source, sources)
            if found is not None:
                kept.append(item.model_copy(update={"source": found}))
            else:
                dropped.append(f"{label}: {item.quote!r} not found in {item.source}")
        return kept

    def keep_readings(items: list[FeedbackReading]) -> list[FeedbackReading]:
        kept = []
        for item in items:
            if is_grounded(item.quote, item.source, sources):
                kept.append(item)
            else:
                dropped.append(f"feedback_reading: {item.quote!r} not found in {item.source}")
        return kept

    def keep_one[S: Evidence](item: S | None, label: str) -> S | None:
        if item is None:
            return None
        kept = keep([item], label)
        return kept[0] if kept else None

    deadline = keep_one(signals.deadline, "deadline")
    if deadline is not None and _parse_date(deadline.date) is None:
        dropped.append(f"deadline: {deadline.date!r} is not a date")
        deadline = None

    return (
        Signals(
            must_haves=keep(signals.must_haves, "must_have"),
            avoid_traits=keep(signals.avoid_traits, "avoid_trait"),
            preferred_markets=keep(signals.preferred_markets, "preferred_market"),
            avoided_markets=keep(signals.avoided_markets, "avoided_market"),
            soft_budget_cap=keep_one(signals.soft_budget_cap, "soft_budget_cap"),
            deadline=deadline,
            uses_cohost=keep_one(signals.uses_cohost, "uses_cohost"),
            feedback_readings=keep_readings(signals.feedback_readings),
        ),
        dropped,
    )


@dataclass(frozen=True)
class ReactedDeal:
    deal: Deal
    market: Market
    liked: bool


def check_against_deals(
    signals: Signals, reacted: Mapping[str, ReactedDeal]
) -> tuple[Signals, list[str]]:
    """Models invert complaints: "Doesn't have a cabin feel inside" comes back as avoiding cabin
    feel. A thumbs down can only avoid a feature the house has, so an avoided feature the house
    lacks is dropped. Wishes are left alone: tags miss things a client noticed ("Great views")."""
    dropped: list[str] = []

    def fits(signal: TraitSignal) -> bool:
        about = reacted.get(signal.source)
        if about is None or about.liked or signal.trait not in FEATURE_TRAITS:
            return True
        if has_trait(signal.trait, about.deal, about.market):
            return True
        dropped.append(
            f"avoid_trait: {about.deal.id} has no {signal.trait.value} to avoid ({signal.quote!r})"
        )
        return False

    kept = [s for s in signals.avoid_traits if fits(s)]
    return signals.model_copy(update={"avoid_traits": kept}), dropped


def deadline_date(signals: Signals) -> date | None:
    return _parse_date(signals.deadline.date) if signals.deadline else None


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
