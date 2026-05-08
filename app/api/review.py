import json
from datetime import datetime

from fastapi import APIRouter

from app.storage.database import SessionLocal
from app.storage.models import PrescriptionRecordDB

router = APIRouter()


@router.put("/review/{record_id}")
def review_record(
    record_id: str,
    status: str,
    reviewer_notes: str = ""
):

    db = SessionLocal()

    record = db.query(
        PrescriptionRecordDB
    ).filter(
        PrescriptionRecordDB.record_id == record_id
    ).first()

    if not record:
        db.close()

        return {
            "error": "Record not found"
        }

    review_data = json.loads(
        record.review_json
    )

    review_data["status"] = status
    review_data["reviewer_notes"] = reviewer_notes
    review_data["reviewed_at"] = datetime.utcnow().isoformat()

    record.review_json = json.dumps(
        review_data
    )

    db.commit()

    updated_review = review_data

    db.close()

    return {
        "message": "Review updated",
        "record_id": record_id,
        "review": updated_review
    }