"""
diariser.py
Assigns speaker labels (Doctor / Patient) to transcript chunks.

Strategy:
- Uses a simple energy + turn-alternation heuristic by default (no GPU needed).
- If pyannote.audio is installed and HF_TOKEN is set, uses the full diarisation
  pipeline for much better accuracy.

Set in .env:
  USE_PYANNOTE=true
  HF_TOKEN=hf_xxxx   (from huggingface.co/settings/tokens)
"""

import os
import numpy as np

USE_PYANNOTE = os.getenv("USE_PYANNOTE", "false").lower() == "true"
HF_TOKEN     = os.getenv("HF_TOKEN", "")

_pipeline = None
_turn_counter = 0   # simple alternating fallback


def _load_pyannote():
    global _pipeline
    if _pipeline is None:
        from pyannote.audio import Pipeline
        _pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=HF_TOKEN
        )
    return _pipeline


def label_speaker(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Returns "Doctor" or "Patient" for this audio chunk.
    Uses pyannote if enabled, otherwise alternates per chunk
    (first chunk = Doctor, second = Patient, etc.).
    """
    global _turn_counter

    if USE_PYANNOTE and HF_TOKEN:
        try:
            pipeline = _load_pyannote()
            import torch, io
            import soundfile as sf

            buf = io.BytesIO()
            sf.write(buf, audio, sample_rate, format="WAV")
            buf.seek(0)

            waveform = torch.tensor(audio).unsqueeze(0)
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})

            # pick the speaker with the most speech in this chunk
            durations: dict[str, float] = {}
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                durations[speaker] = durations.get(speaker, 0) + (turn.end - turn.start)

            if not durations:
                return _alternating()

            dominant = max(durations, key=durations.get)
            # map first-seen speaker → Doctor, second → Patient
            return _map_speaker(dominant)

        except Exception as e:
            print(f"[Diariser] pyannote error: {e} — falling back to alternating")

    return _alternating()


# ── simple fallback helpers ────────────────────────────────────────────────────

_speaker_map: dict[str, str] = {}
_speaker_order: list[str]    = []

def _map_speaker(raw_id: str) -> str:
    global _speaker_map, _speaker_order
    if raw_id not in _speaker_map:
        idx = len(_speaker_order)
        _speaker_map[raw_id] = "Doctor" if idx == 0 else "Patient"
        _speaker_order.append(raw_id)
    return _speaker_map[raw_id]

def _alternating() -> str:
    global _turn_counter
    label = "Doctor" if _turn_counter % 2 == 0 else "Patient"
    _turn_counter += 1
    return label

def reset():
    """Call this when a new consultation starts."""
    global _turn_counter, _speaker_map, _speaker_order
    _turn_counter = 0
    _speaker_map  = {}
    _speaker_order = []