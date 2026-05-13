"""
app/services/diariser.py

Assigns speaker labels (Doctor / Patient) to transcript chunks.

Default: simple alternating heuristic — no GPU, no extra packages needed.
Optional: set USE_PYANNOTE=true and HF_TOKEN=hf_xxx in .env for full
          speaker diarisation via pyannote.audio.

Pylance note: pyannote.audio and soundfile are optional dependencies used
only when USE_PYANNOTE=true. The type:ignore comments suppress the
"import could not be resolved" warnings — the code is guarded by a
runtime check so these imports never execute in the default configuration.
"""

import os
import numpy as np

USE_PYANNOTE = os.getenv("USE_PYANNOTE", "false").lower() == "true"
HF_TOKEN     = os.getenv("HF_TOKEN", "")

_pipeline:      object          = None
_turn_counter:  int             = 0
_speaker_map:   dict[str, str]  = {}
_speaker_order: list[str]       = []


def reset():
    """
    Call at the start of every new consultation.
    Clears the alternating counter and pyannote speaker map so
    Doctor/Patient labels always start fresh.
    """
    global _turn_counter, _speaker_map, _speaker_order
    _turn_counter  = 0
    _speaker_map   = {}
    _speaker_order = []


def _load_pyannote():
    global _pipeline
    if _pipeline is None:
        from pyannote.audio import Pipeline  # type: ignore[import]
        
        _pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    token=HF_TOKEN   # ✅ pyannote 3.x)
    )
    return _pipeline


def label_speaker(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Returns "Doctor" or "Patient" for this audio chunk.
    Uses pyannote if USE_PYANNOTE=true, otherwise alternates per chunk.
    """
    if USE_PYANNOTE and HF_TOKEN:
        try:
            pipeline = _load_pyannote()
            import torch                      # type: ignore[import]
            import soundfile as sf            # type: ignore[import]
            import io

            buf = io.BytesIO()
            sf.write(buf, audio, sample_rate, format="WAV")
            buf.seek(0)

            waveform    = torch.tensor(audio).unsqueeze(0)
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})

            durations: dict[str, float] = {}
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                durations[speaker] = durations.get(speaker, 0) + (turn.end - turn.start)

            if not durations:
                return _alternating()

            dominant = max(durations, key=durations.get)
            return _map_speaker(dominant)

        except Exception as e:
            print(f"[Diariser] pyannote error: {e} — falling back to alternating")

    return _alternating()


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