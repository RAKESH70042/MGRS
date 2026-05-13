"""
app/api/transcription.py

Key fix: after every transcribed audio chunk (real or mock), _persist_turns()
writes session["turns"] into ConsultationDB.transcript_json so the polling
endpoint /transcription/{id}/full always returns up-to-date data.

Race-condition fix: on_chunk() no longer bails at entry when active=False.
Audio already captured by AudioCapture is always transcribed to completion
before the active flag is checked — so the last chunk(s) are never silently
dropped when stop_consultation() fires mid-transcription.

Routes:
  POST /transcription/start_pipeline   → no-op (pipeline started by consultation/start)
  GET  /transcription/stream           → SSE stream of live turns
  GET  /transcription/{id}/full        → full transcript polled by Streamlit UI
"""

import json
import asyncio
import os
import threading

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

# Tracks all in-flight on_chunk threads so stop_audio_pipeline()
# can wait for them to finish before returning.
_active_chunk_threads: list[threading.Thread] = []
_chunk_threads_lock = threading.Lock()


# ── DB writer ─────────────────────────────────────────────────────────────────

def _persist_turns(consultation_id: str, turns: list):
    """Write the current turns list to ConsultationDB after every chunk."""
    from app.storage.database import SessionLocal
    from app.storage.consultation_models import ConsultationDB

    db = SessionLocal()
    try:
        db.query(ConsultationDB).filter(
            ConsultationDB.consultation_id == consultation_id
        ).update({"transcript_json": json.dumps(turns)})
        db.commit()
    finally:
        db.close()


# ── audio pipeline ────────────────────────────────────────────────────────────

def start_audio_pipeline(session: dict):
    """
    Starts the audio capture → Whisper → diariser pipeline in a background thread.
    session must contain: active (bool), turns (list), consultation_id (str)
    """
    import time as _time

    consultation_id = session.get("consultation_id", "")

    # Reset thread tracker for this consultation
    with _chunk_threads_lock:
        _active_chunk_threads.clear()

    # ── MOCK MODE ─────────────────────────────────────────────────────────────
    if USE_MOCK:
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
                turn = {
                    "speaker":   spk,
                    "text":      txt,
                    "timestamp": round(_time.time() - start, 1),
                }
                session["turns"].append(turn)
                if consultation_id:
                    _persist_turns(consultation_id, session["turns"])

        threading.Thread(target=_mock_feed, daemon=True).start()
        return

    # ── REAL PIPELINE ─────────────────────────────────────────────────────────
    from app.services.transcriber   import transcribe_chunk
    from app.services.diariser      import label_speaker
    from app.services.audio_capture import AudioCapture
    import time as _t

    start_time = _t.time()

    def on_chunk(audio):
        """
        Called by AudioCapture in its own thread for every captured chunk.

        IMPORTANT — active flag is checked AFTER transcription, not before.
        Audio already handed off to this function has been captured from the
        mic; discarding it before transcription would leave the last 1-2
        utterances out of the transcript, causing an empty-transcript 400
        when /report/generate is called immediately after /consultation/stop.

        Flow:
          1. Transcribe (always — chunk is already in memory)
          2. If no speech detected, discard silently
          3. If session ended between capture and now, still save the turn
             so the stop flush picks it up
          4. Persist to DB
        """
        # Step 1 — transcribe regardless of active flag
        text = transcribe_chunk(audio)

        # Step 2 — skip silent / hallucination chunks
        if not text:
            return

        # Step 3 — get speaker label
        speaker = label_speaker(audio)

        turn = {
            "speaker":   speaker,
            "text":      text,
            "timestamp": round(_t.time() - start_time, 1),
        }

        # Step 4 — append + persist (even if active just flipped False,
        # the turn belongs to this consultation and must be saved)
        session["turns"].append(turn)
        if consultation_id:
            _persist_turns(consultation_id, session["turns"])

    def _tracked_on_chunk(audio):
        """Wraps on_chunk so stop_audio_pipeline() can join() all threads."""
        t = threading.current_thread()
        with _chunk_threads_lock:
            _active_chunk_threads.append(t)
        try:
            on_chunk(audio)
        finally:
            with _chunk_threads_lock:
                try:
                    _active_chunk_threads.remove(t)
                except ValueError:
                    pass

    capture = AudioCapture(on_chunk=_tracked_on_chunk)
    session["_capture"] = capture
    capture.start()


def stop_audio_pipeline(session: dict):
    """
    Stops audio capture and waits for all in-flight on_chunk threads to finish
    before returning, so consultation/stop's final DB flush sees every turn.
    """
    capture = session.pop("_capture", None)
    if capture:
        capture.stop()

    # Drain: wait up to 30 s for any chunk threads still transcribing
    with _chunk_threads_lock:
        threads_to_join = list(_active_chunk_threads)

    for t in threads_to_join:
        t.join(timeout=30)


# ── routes ────────────────────────────────────────────────────────────────────

@router.post("/transcription/start_pipeline")
def start_pipeline_endpoint():
    """
    Called by the Streamlit UI after /consultation/start.
    Pipeline is already running — this is a compatibility no-op.
    """
    return {"message": "Pipeline already started via /consultation/start"}


@router.get("/transcription/stream")
async def stream_transcript():
    """SSE stream — pushes each new turn as a JSON event."""
    from app.api.consultation_api import get_session

    async def event_generator():
        session  = get_session()
        sent_idx = 0
        while True:
            turns = session.get("turns", [])
            while sent_idx < len(turns):
                yield f"data: {json.dumps(turns[sent_idx])}\n\n"
                sent_idx += 1
            if not session.get("active") and sent_idx >= len(turns):
                yield 'data: {"event": "done"}\n\n'
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/transcription/{consultation_id}/full")
def get_full_transcript(consultation_id: str):
    """
    Polled by the Streamlit UI every 0.5 s while recording.
    Reads from DB — always reflects the latest persisted turns.
    """
    from app.storage.database import SessionLocal
    from app.storage.consultation_models import ConsultationDB

    db = SessionLocal()
    record = db.query(ConsultationDB).filter(
        ConsultationDB.consultation_id == consultation_id
    ).first()
    db.close()

    if not record:
        return {"error": "Not found", "turns": []}

    turns = json.loads(record.transcript_json or "[]")
    return {"consultation_id": consultation_id, "turns": turns}