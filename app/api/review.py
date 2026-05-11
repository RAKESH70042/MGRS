import json
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Body

from app.storage.database import SessionLocal
from app.storage.models import PrescriptionRecordDB

router = APIRouter()

@router.put("/review/{record_id}")
def review_record(
    record_id: str,
    status: str,
    reviewer_notes: str = "",
    payload: Optional[Dict[str, Any]] = Body(None)
):
    db = SessionLocal()

    # 1. Find the existing record
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

    # 2. Update the review status & notes
    review_data = json.loads(record.review_json)
    review_data["status"] = status
    review_data["reviewer_notes"] = reviewer_notes
    review_data["reviewed_at"] = datetime.utcnow().isoformat()
    record.review_json = json.dumps(review_data)

    # 3. If the UI sent corrected extraction data, update it!
    if payload and "extracted" in payload:
        record.extracted_json = json.dumps(payload["extracted"])

    # 4. Save to database
    db.commit()
    updated_review = review_data
    db.close()

    return {
        "message": "Review updated successfully",
        "record_id": record_id,
        "review": updated_review,
        "edited": payload is not None and "extracted" in payload
    }