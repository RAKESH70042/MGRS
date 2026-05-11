"""
transcription.py — API router
GET  /transcription/stream          → SSE stream of live transcript turns
POST /transcription/add_turn        → called internally by audio pipeline
GET  /transcription/{id}/full       → full transcript for a completed consultation
"""

import json
import asyncio
import os

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"


# ── live audio pipeline (runs in background thread when recording) ─────────────

_audio_thread = None


def start_audio_pipeline(session: dict):
    """
    Starts the audio capture → Whisper → diariser pipeline in a background thread.
    Each transcribed chunk is appended to session["turns"].
    """
    import threading
    import time as _time

    if USE_MOCK:
        # In mock mode, inject fake turns every few seconds
        def _mock_feed():
            mock_turns = [
                ("Doctor",  "Good morning, what brings you in today?"),
                ("Patient", "I have had a fever and sore throat for about three days."),
                ("Doctor",  "Any difficulty swallowing or ear pain?"),
                ("Patient", "Yes, swallowing is quite painful."),
                ("Doctor",  "Let me take a look at your throat."),
                ("Doctor",  "I can see some redness. No sign of bacterial infection though."),
                ("Doctor",  "I will prescribe paracetamol for the fever and pain."),
                ("Patient", "Should I rest at home?"),
                ("Doctor",  "Yes, rest and plenty of fluids. Come back in a week."),
            ]
            start = _time.time()
            for spk, txt in mock_turns:
                if not session.get("active"):
                    break
                _time.sleep(2)
                session["turns"].append({
                    "speaker":   spk,
                    "text":      txt,
                    "timestamp": round(_time.time() - start, 1),
                })
        threading.Thread(target=_mock_feed, daemon=True).start()
        return

    # Real pipeline
    from app.services.transcriber  import transcribe_chunk
    from app.services.diariser     import label_speaker
    from app.services.audio_capture import AudioCapture
    import time as _t

    start_time = _t.time()

    def on_chunk(audio):
        if not session.get("active"):
            return
        text = transcribe_chunk(audio)
        if not text:
            return
        speaker = label_speaker(audio)
        session["turns"].append({
            "speaker":   speaker,
            "text":      text,
            "timestamp": round(_t.time() - start_time, 1),
        })

    capture = AudioCapture(on_chunk=on_chunk)
    session["_capture"] = capture
    capture.start()


def stop_audio_pipeline(session: dict):
    capture = session.pop("_capture", None)
    if capture:
        capture.stop()


# ── SSE stream endpoint ────────────────────────────────────────────────────────

@router.get("/transcription/stream")
async def stream_transcript():
    """
    Server-Sent Events stream.
    The Streamlit UI polls this; each new turn is pushed as a JSON event.
    """
    from app.api.consultation import get_session

    async def event_generator():
        session   = get_session()
        sent_idx  = 0
        while True:
            turns = session.get("turns", [])
            while sent_idx < len(turns):
                turn = turns[sent_idx]
                yield f"data: {json.dumps(turn)}\n\n"
                sent_idx += 1
            if not session.get("active") and sent_idx >= len(turns):
                yield "data: {\"event\": \"done\"}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── full transcript endpoint ───────────────────────────────────────────────────

@router.get("/transcription/{consultation_id}/full")
def get_full_transcript(consultation_id: str):
    from app.storage.database import SessionLocal
    from app.storage.consultation_models import ConsultationDB

    db = SessionLocal()
    record = db.query(ConsultationDB).filter(
        ConsultationDB.consultation_id == consultation_id
    ).first()
    db.close()

    if not record:
        return {"error": "Not found"}

    turns = json.loads(record.transcript_json or "[]")
    return {"consultation_id": consultation_id, "turns": turns}