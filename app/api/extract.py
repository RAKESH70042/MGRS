import os

from fastapi import APIRouter, Query, HTTPException

from app.services.save_record import save_prescription_record
from app.storage.database import SessionLocal
from app.storage.models import PrescriptionRecordDB
from app.utils import generate_record_id

router = APIRouter()

# -------------------------------------------------------------------
# Provider toggle (check .env):
#   USE_MOCK=true      → fake data, no model needed
#   USE_OLLAMA=true    → Ollama API (llama3, llava, medgemma via Ollama)
#   default            → local llama.cpp MedGemma server
# -------------------------------------------------------------------

USE_MOCK   = os.getenv("USE_MOCK",   "false").lower() == "true"
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"

if USE_MOCK:
    from app.providers.mock_provider   import mock_extract      as _extract
elif USE_OLLAMA:
    from app.providers.ollama_provider import ollama_extract    as _extract
else:
    from app.providers.medgemma_provider import medgemma_extract as _extract


@router.get("/extract")
def extract_demo(file_name: str = Query(...)):

    db = SessionLocal()
    records = db.query(PrescriptionRecordDB).all()
    db.close()

    new_record_id = generate_record_id(records)

    try:
        result = _extract(file_name, new_record_id)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    save_prescription_record(result)
    return result


@router.delete("/records/all")
def delete_all_records():
    db = SessionLocal()
    try:
        db.query(PrescriptionRecordDB).delete()
        db.commit()
        return {"message": "All records deleted successfully"}
    finally:
        db.close()