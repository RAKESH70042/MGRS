"""
app/api/consultation_api.py

FastAPI router handling consultation lifecycle.
Routes:
  POST /consultation/start   → create DB row, reset diariser, start audio pipeline
  POST /consultation/stop    → stop pipeline, flush transcript to DB
  GET  /consultations        → list all consultations (for history table)
"""

import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter
from app.storage.database import SessionLocal
from app.storage.consultation_models import ConsultationDB

router = APIRouter()

# Single in-memory session — one consultation at a time
_session: dict = {}


def get_session() -> dict:
    """Shared accessor used by transcription.py for the SSE stream."""
    return _session


def _generate_consultation_id(db) -> str:
    """
    Finds the highest existing CONS number and increments it.
    Using max() instead of count() means IDs stay unique even if
    old records are deleted (e.g. CONS0011 exists → next is CONS0012,
    not CONS0012 colliding with a deleted slot).
    """
    records = db.query(ConsultationDB).all()
    if not records:
        return "CONS0001"
    max_num = 0
    for r in records:
        match = re.search(r"(\d+)$", r.consultation_id or "")
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"CONS{(max_num + 1):04d}"


# ── /consultation/start ───────────────────────────────────────────────────────

@router.post("/consultation/start")
def start_consultation(patient_id: str = "", doctor_id: str = ""):
    from app.api.transcription import start_audio_pipeline
    from app.services.diariser import reset as reset_diariser

    db = SessionLocal()
    consultation_id = _generate_consultation_id(db)

    record = ConsultationDB(
        consultation_id=consultation_id,
        patient_id=patient_id or None,
        doctor_id=doctor_id or None,
        started_at=datetime.now(timezone.utc).isoformat(),
        status="recording",
        transcript_json="[]",
        report_json="{}",
        summary=None,
    )
    db.add(record)
    db.commit()
    db.close()

    # Reset diariser so Doctor/Patient labels start fresh each consultation
    reset_diariser()

    # Reset Whisper rolling context — safe import in case old transcriber.py
    # is still in place (reset_context added in updated transcriber.py)
    try:
        from app.services.transcriber import reset_context
        reset_context()
    except ImportError:
        pass

    # Build session — consultation_id is required so the audio pipeline
    # can write turns back to the correct DB row after every chunk
    _session.clear()
    _session.update({
        "active":          True,
        "turns":           [],
        "consultation_id": consultation_id,
    })

    start_audio_pipeline(_session)

    return {
        "consultation_id": consultation_id,
        "patient_id":      patient_id,
        "doctor_id":       doctor_id,
        "status":          "recording",
    }


# ── /consultation/stop ────────────────────────────────────────────────────────

@router.post("/consultation/stop")
def stop_consultation():
    from app.api.transcription import stop_audio_pipeline

    _session["active"] = False
    stop_audio_pipeline(_session)

    consultation_id = _session.get("consultation_id")
    if not consultation_id:
        return {"message": "No active consultation"}

    db = SessionLocal()
    record = db.query(ConsultationDB).filter(
        ConsultationDB.consultation_id == consultation_id
    ).first()

    if record:
        record.ended_at        = datetime.now(timezone.utc).isoformat()
        record.status          = "completed"
        # Final flush — makes sure every turn captured before stop is saved
        record.transcript_json = json.dumps(_session.get("turns", []))
        db.commit()

    db.close()

    return {
        "message":         "Consultation stopped",
        "consultation_id": consultation_id,
        "turns_recorded":  len(_session.get("turns", [])),
    }


# ── /consultations ────────────────────────────────────────────────────────────

@router.get("/consultations")
def list_consultations():
    db = SessionLocal()
    records = db.query(ConsultationDB).order_by(ConsultationDB.id.desc()).all()
    db.close()

    return [
        {
            "consultation_id": r.consultation_id,
            "patient_id":      r.patient_id,
            "doctor_id":       r.doctor_id,
            "started_at":      r.started_at,
            "ended_at":        r.ended_at,
            "status":          r.status,
            "summary":         r.summary,
        }
        for r in records
    ]