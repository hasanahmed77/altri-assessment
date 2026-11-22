from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import median

from app.domain.models import Client, Market
from app.domain.scoring import SETTING_LABELS, SETTING_RANK_SCORES, RankedDeal, Reason, normalize
from app.domain.signal_fit import signal_preferred_markets
from app.domain.signals import TRAIT_LABELS, Signals, market_has_trait

# Where to buy is counting and arithmetic, so it is reproducible and cheap. A market is only
# as good as the deals a client can actually buy there, so supply carries real weight.
SETTING_WEIGHT = 0.35
PREFERRED_WEIGHT = 0.25
SUPPLY_WEIGHT = 0.20
RETURNS_WEIGHT = 0.20
FULL_SUPPLY = 5
MARKET_TRAIT_MET = 0.15
MARKET_TRAIT_AVOIDED = -0.40
SPOKEN_AGAINST = -0.40
ORDINALS = {1: "first", 2: "second", 3: "third"}


@dataclass(frozen=True)
class MarketFit:
    market: Market
    eligible: int
    best_deal_id: str | None
    median_coc_low: float | None
    score: float
    avoided: bool
    reasons: tuple[Reason, ...]


def market_fit(
    client: Client,
    markets: Mapping[str, Market],
    ranked: Sequence[RankedDeal],
    signals: Signals,
) -> list[MarketFit]:
    """Every market for this client, best first, each with the reasons behind its place.
    Markets with nothing the client can buy, or that they avoid, go last."""
    by_market: dict[str, list[RankedDeal]] = {m: [] for m in markets}
    for r in ranked:
        by_market[r.candidate.deal.market_id].append(r)

    medians = {
        m: median(r.candidate.numbers.coc.low for r in items) if items else None
        for m, items in by_market.items()
    }
    known = sorted({v for v in medians.values() if v is not None})
    scaled = dict(zip(known, normalize(known), strict=True))

    fits = [
        _fit(client, market, by_market[market.id], medians[market.id], scaled, signals)
        for market in markets.values()
    ]
    return sorted(fits, key=lambda f: (f.avoided, f.eligible == 0, -f.score, f.market.id))


def _fit(
    client: Client,
    market: Market,
    items: list[RankedDeal],
    coc: float | None,
    scaled: Mapping[float, float],
    signals: Signals,
) -> MarketFit:
    reasons: list[Reason] = []
    score = 0.0

    rank = client.setting_rank.get(market.setting, 0)
    score += SETTING_WEIGHT * SETTING_RANK_SCORES.get(rank, 0.0)
    if rank in ORDINALS:
        label = SETTING_LABELS.get(market.setting, market.setting).capitalize()
        reasons.append(Reason("SETTING", f"{label}, the client's {ORDINALS[rank]} choice", 0.0))

    mentioned = signal_preferred_markets(signals)
    if market.id in client.preferred_market_ids:
        score += PREFERRED_WEIGHT
        reasons.append(Reason("PREFERRED_MARKET", "In the client's profile", PREFERRED_WEIGHT))
    elif market.id in mentioned:
        score += PREFERRED_WEIGHT
        evidence = mentioned[market.id]
        reasons.append(
            Reason.quoted("MENTIONED_MARKET", "The client mentioned it", PREFERRED_WEIGHT, evidence)
        )

    score += SUPPLY_WEIGHT * min(len(items), FULL_SUPPLY) / FULL_SUPPLY
    if coc is not None:
        score += RETURNS_WEIGHT * scaled[coc]

    for signal in signals.must_haves:
        if market_has_trait(signal.trait, market):
            score += MARKET_TRAIT_MET
            text = f"Offers {TRAIT_LABELS[signal.trait]}, which the client wants"
            reasons.append(Reason.quoted("MUST_HAVE_MET", text, MARKET_TRAIT_MET, signal))
    for signal in signals.avoid_traits:
        if market_has_trait(signal.trait, market):
            score += MARKET_TRAIT_AVOIDED
            text = f"Has {TRAIT_LABELS[signal.trait]}, which the client avoids"
            reasons.append(Reason.quoted("AVOID_TRAIT", text, MARKET_TRAIT_AVOIDED, signal))

    against = next((s for s in signals.avoided_markets if s.market_id == market.id), None)
    if against is not None:
        score += SPOKEN_AGAINST
        text = "The client spoke against it"
        reasons.append(Reason.quoted("AVOIDED_MARKET_SIGNAL", text, SPOKEN_AGAINST, against))

    avoided = market.id in client.avoid_market_ids
    if avoided:
        reasons.append(Reason("AVOIDED_MARKET", "The client avoids it; never recommended", 0.0))

    to_send = [r for r in items if r.status != "already_shared"]
    best = (to_send or items)[0].candidate.deal.id if items else None
    return MarketFit(market, len(items), best, coc, score, avoided, tuple(reasons))
