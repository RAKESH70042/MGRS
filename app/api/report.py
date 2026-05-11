"""
report.py — API router
POST /report/generate/{consultation_id}  → generate structured report via MedGemma
GET  /report/{consultation_id}           → fetch saved report
PUT  /report/{consultation_id}           → save edited report
"""

import json
import os

from fastapi import APIRouter, HTTPException, Body
from typing import Optional, Dict, Any

router = APIRouter()

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"


@router.post("/report/generate/{consultation_id}")
def generate_report(consultation_id: str):
    from app.storage.database import SessionLocal
    from app.storage.consultation_models import ConsultationDB

    db = SessionLocal()
    record = db.query(ConsultationDB).filter(
        ConsultationDB.consultation_id == consultation_id
    ).first()

    if not record:
        db.close()
        raise HTTPException(status_code=404, detail="Consultation not found.")

    turns = json.loads(record.transcript_json or "[]")

    if not turns:
        db.close()
        raise HTTPException(status_code=400, detail="No transcript to generate report from.")

    if USE_MOCK:
        from app.services.report_generator import generate_report_mock
        report_data = generate_report_mock(turns)
    else:
        from app.services.report_generator import generate_report
        try:
            report_data = generate_report(turns)
        except RuntimeError as e:
            db.close()
            raise HTTPException(status_code=503, detail=str(e))

    # Build plain-language summary
    summary_parts = []
    if report_data.get("diagnosis"):
        summary_parts.append(f"Diagnosis: {report_data['diagnosis']}.")
    meds = report_data.get("prescribed_medicines", [])
    if meds:
        med_names = ", ".join(m.get("medication_name", "") for m in meds if m.get("medication_name"))
        summary_parts.append(f"Prescribed: {med_names}.")
    if report_data.get("follow_up_instructions"):
        summary_parts.append(f"Follow-up: {report_data['follow_up_instructions']}.")
    summary = " ".join(summary_parts) or "No summary available."

    record.report_json = json.dumps(report_data)
    record.summary     = summary
    record.status      = "reviewed"
    db.commit()
    db.close()

    return {
        "message":         "Report generated",
        "consultation_id": consultation_id,
        "report":          report_data,
        "summary":         summary,
    }


@router.get("/report/{consultation_id}")
def get_report(consultation_id: str):
    from app.storage.database import SessionLocal
    from app.storage.consultation_models import ConsultationDB

    db = SessionLocal()
    record = db.query(ConsultationDB).filter(
        ConsultationDB.consultation_id == consultation_id
    ).first()
    db.close()

    if not record:
        raise HTTPException(status_code=404, detail="Not found.")

    return {
        "consultation_id": consultation_id,
        "report":          json.loads(record.report_json or "{}"),
        "summary":         record.summary,
        "status":          record.status,
    }


@router.put("/report/{consultation_id}")
def update_report(
    consultation_id: str,
    payload: Optional[Dict[str, Any]] = Body(None)
):
    from app.storage.database import SessionLocal
    from app.storage.consultation_models import ConsultationDB

    db = SessionLocal()
    record = db.query(ConsultationDB).filter(
        ConsultationDB.consultation_id == consultation_id
    ).first()

    if not record:
        db.close()
        raise HTTPException(status_code=404, detail="Not found.")

    if payload and "report" in payload:
        record.report_json = json.dumps(payload["report"])
    if payload and "summary" in payload:
        record.summary = payload["summary"]

    record.status = "reviewed"
    db.commit()
    db.close()

    return {"message": "Report updated", "consultation_id": consultation_id}