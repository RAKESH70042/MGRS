import json

from app.storage.database import SessionLocal
from app.storage.models import PrescriptionRecordDB


def save_prescription_record(record):

    db = SessionLocal()

    db_record = PrescriptionRecordDB(
        record_id=record.record_id,
        source_file=record.source_file,
        method=record.method,

        extracted_json=json.dumps(
            record.extracted.model_dump()
        ),

        review_json=json.dumps(
            record.review.model_dump()
        ),

        metadata_json=json.dumps(
            record.run_metadata.model_dump()
        )
    )

    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    db.close()

    return db_record