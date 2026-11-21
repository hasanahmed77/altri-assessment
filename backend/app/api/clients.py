from fastapi import APIRouter

from app import repository
from app.api.deps import ConnectionDep, ReferenceDep, find_client
from app.api.schemas import (
    ClientDetailOut,
    ClientSummaryOut,
    ExcludedDealOut,
    RankedDealOut,
    RecommendationsOut,
)
from app.domain.recommend import recommend

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
        calls=repository.client_calls(conn, client_id),
    )


@router.get("/{client_id}/recommendations")
def get_recommendations(
    client_id: str, reference: ReferenceDep, conn: ConnectionDep
) -> RecommendationsOut:
    profile = find_client(reference, client_id)
    feedback = [r.feedback for r in repository.client_feedback(conn, client_id)]
    result = recommend(profile.client, reference.deals, reference.markets, feedback)
    return RecommendationsOut(
        client_id=client_id,
        ranked=[RankedDealOut.from_domain(i, r) for i, r in enumerate(result.ranked, start=1)],
        excluded=[ExcludedDealOut.from_domain(e) for e in result.excluded],
    )
