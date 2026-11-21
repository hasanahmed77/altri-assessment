from fastapi import APIRouter, HTTPException, status

from app import repository
from app.api.deps import ReferenceDep, TransactionDep, find_client
from app.api.schemas import FeedbackIn, FeedbackOut

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_feedback(body: FeedbackIn, reference: ReferenceDep, conn: TransactionDep) -> FeedbackOut:
    find_client(reference, body.client_id)
    if body.deal_id not in reference.deals_by_id:
        raise HTTPException(status_code=404, detail=f"Deal {body.deal_id} not found")
    record = repository.insert_feedback(
        conn, body.client_id, body.deal_id, body.reaction, body.comment
    )
    return FeedbackOut.from_record(record)
