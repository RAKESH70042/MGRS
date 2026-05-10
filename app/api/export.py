import json
from pathlib import Path

from fastapi import APIRouter

from app.storage.database import SessionLocal
from app.storage.models import PrescriptionRecordDB

router = APIRouter()

EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)


@router.get("/export/json")
def export_json():

    db = SessionLocal()

    records = db.query(
        PrescriptionRecordDB
    ).all()

    export_data = []

    for record in records:

        export_data.append({
            "record_id": record.record_id,
            "source_file": record.source_file,
            "method": record.method,

            "extracted": json.loads(
                record.extracted_json
            ),

            "review": json.loads(
                record.review_json
            ),

            "run_metadata": json.loads(
                record.metadata_json
            )
        })

    export_path = EXPORT_DIR / "reviewed_records.json"

    with open(export_path, "w") as f:
        json.dump(export_data, f, indent=4)

    db.close()

    return {
        "message": "Export completed",
        "export_file": str(export_path),
        "records_exported": len(export_data)
    }