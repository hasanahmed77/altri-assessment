from dataclasses import dataclass
from datetime import date

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import Connection

from app import repository
from app.api.deps import ConnectionDep, ReferenceDep, SignalServiceDep, find_client
from app.api.schemas import (
    AlertOut,
    ClientDetailOut,
    ClientSummaryOut,
    ExcludedDealOut,
    MarketFitOut,
    RankedDealOut,
    RecommendationsOut,
    signal_items,
)
from app.domain.alerts import Alert, alerts
from app.domain.market_fit import MarketFit, market_fit
from app.domain.recommend import Recommendations, recommend
from app.repository import Reference
from app.services.signals import CurrentSignals, SignalService

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("")
def list_clients(reference: ReferenceDep, conn: ConnectionDep) -> list[ClientSummaryOut]:
    counts = repository.feedback_counts(conn)
    return [
        ClientSummaryOut.from_profile(profile, counts.get(client_id, 0))
        for client_id, profile in reference.clients.items()
    ]


@router.get("/{client_id}")
def get_client(client_id: str, reference: ReferenceDep, conn: ConnectionDep) -> ClientDetailOut:
    profile = find_client(reference, client_id)
    return ClientDetailOut.from_profile(
        profile,
        feedback=repository.client_feedback(conn, client_id),
        calls=list(reference.calls.get(client_id, ())),
    )


@router.get("/{client_id}/recommendations")
def get_recommendations(
    client_id: str,
    reference: ReferenceDep,
    conn: ConnectionDep,
    service: SignalServiceDep,
    background: BackgroundTasks,
) -> RecommendationsOut:
    view = _evaluate(client_id, reference, conn, service, background)
    labels = view.current.labels
    return RecommendationsOut(
        client_id=client_id,
        signals_status=view.current.status,
        signals=signal_items(view.current.signals, labels, reference.markets, view.thumbs),
        alerts=[AlertOut.from_domain(a, labels) for a in view.alerts],
        ranked=[
            RankedDealOut.from_domain(i, r, labels)
            for i, r in enumerate(view.recommendations.ranked, start=1)
        ],
        excluded=[ExcludedDealOut.from_domain(e) for e in view.recommendations.excluded],
    )


@router.get("/{client_id}/markets")
def get_markets(
    client_id: str,
    reference: ReferenceDep,
    conn: ConnectionDep,
    service: SignalServiceDep,
    background: BackgroundTasks,
) -> list[MarketFitOut]:
    view = _evaluate(client_id, reference, conn, service, background)
    return [
        MarketFitOut.from_domain(i, f, view.current.labels)
        for i, f in enumerate(view.fits, start=1)
    ]


@dataclass(frozen=True)
class _ClientView:
    current: CurrentSignals
    recommendations: Recommendations
    fits: list[MarketFit]
    alerts: list[Alert]
    thumbs: dict[int, float]


def _evaluate(
    client_id: str,
    reference: Reference,
    conn: Connection,
    service: SignalService,
    background: BackgroundTasks,
) -> _ClientView:
    profile = find_client(reference, client_id)
    records = repository.client_feedback(conn, client_id)
    current = service.current(conn, client_id, records)
    if current.needs_refresh:
        background.add_task(service.refresh, client_id)

    client = profile.client
    feedback = [r.feedback for r in records]
    result = recommend(client, reference.deals, reference.markets, feedback, current.signals)
    fits = market_fit(client, reference.markets, result.ranked, current.signals)
    found = alerts(
        client,
        profile.budget_range,
        profile.unresolved_terms,
        reference.markets,
        result,
        fits,
        current.signals,
        today=date.today(),
    )
    thumbs = {r.feedback.id: 1.0 if r.feedback.reaction == "up" else -1.0 for r in records}
    return _ClientView(current, result, fits, found, thumbs)
