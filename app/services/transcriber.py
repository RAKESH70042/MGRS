"""
transcriber.py
Converts audio chunks (np.ndarray, 16kHz float32) to text using
OpenAI Whisper running fully locally.
"""

import os
import numpy as np

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")  # tiny.en / base.en / small.en / medium.en

_model = None


def _load_model():
    global _model
    if _model is None:
        try:
            import whisper
            _model = whisper.load_model(WHISPER_MODEL)
        except ImportError:
            raise RuntimeError(
                "openai-whisper not installed. Run: pip install openai-whisper"
            )
    return _model


def transcribe_chunk(audio: np.ndarray) -> str:
    """
    Transcribe a float32 16kHz numpy array.
    Returns the transcript string (empty string on failure).
    """
    model = _load_model()
    try:
        result = model.transcribe(
            audio,
            language="en",
            fp16=False,          # CPU-safe
            condition_on_previous_text=True,
        )
        return result.get("text", "").strip()
    except Exception as e:
        print(f"[Whisper] transcription error: {e}")
        return ""