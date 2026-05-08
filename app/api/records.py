from fastapi import APIRouter

from app.storage.database import SessionLocal
from app.storage.models import PrescriptionRecordDB

router = APIRouter()


@router.get("/records")
def get_records():

    db = SessionLocal()

    records = db.query(
        PrescriptionRecordDB
    ).all()

    db.close()

    return records