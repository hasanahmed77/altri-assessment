from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app import repository
from app.api.deps import ConnectionDep, ReferenceDep, SignalServiceDep, find_client
from app.api.schemas import FeedbackIn, FeedbackOut

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_feedback(
    body: FeedbackIn,
    reference: ReferenceDep,
    conn: ConnectionDep,
    service: SignalServiceDep,
    background: BackgroundTasks,
) -> FeedbackOut:
    find_client(reference, body.client_id)
    if body.deal_id not in reference.deals_by_id:
        raise HTTPException(status_code=404, detail=f"Deal {body.deal_id} not found")
    # Committed here, not when the dependency closes, so the background extraction sees it
    with conn.begin():
        record = repository.insert_feedback(
            conn, body.client_id, body.deal_id, body.reaction, body.comment
        )
    if body.comment:
        background.add_task(service.refresh, body.client_id)
    return FeedbackOut.from_record(record)
