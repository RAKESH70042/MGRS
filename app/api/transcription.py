"""
transcriber.py
Converts audio chunks (np.ndarray, 16kHz float32) to text using
OpenAI Whisper running locally.

.env settings:
  WHISPER_MODEL=small       # tiny / base / small / medium / large-v3
  WHISPER_LANGUAGE=         # empty = auto-detect (best for Hinglish)
  WHISPER_TASK=transcribe
"""

import os
import numpy as np

WHISPER_MODEL    = os.getenv("WHISPER_MODEL",    "small")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "")
WHISPER_TASK     = os.getenv("WHISPER_TASK",     "transcribe")

_model    = None
_device   = None
_last_text = ""   # rolling context for cross-chunk accuracy


def _load_model():
    global _model, _device
    if _model is None:
        try:
            import whisper
            import torch

            if torch.cuda.is_available():
                _device = "cuda"
                print(f"[Whisper] GPU: {torch.cuda.get_device_name(0)}")
            else:
                _device = "cpu"
                print("[Whisper] No GPU — using CPU")

            print(f"[Whisper] Loading '{WHISPER_MODEL}' on {_device}...")
            _model = whisper.load_model(WHISPER_MODEL, device=_device)
            print(f"[Whisper] ✅ Ready — language={'auto-detect' if not WHISPER_LANGUAGE else WHISPER_LANGUAGE}")

        except ImportError:
            raise RuntimeError("openai-whisper not installed. Run: pip install openai-whisper")
    return _model


def transcribe_chunk(audio: np.ndarray) -> str:
    """
    Transcribe a float32 16kHz numpy array.
    Returns transcript string, empty string on silence/failure.
    """
    global _last_text

    model = _load_model()

    if _is_silent(audio):
        return ""

    try:
        options = {
            "task":                        WHISPER_TASK,
            "fp16":                        (_device == "cuda"),
            "condition_on_previous_text":  True,
            "no_speech_threshold":         0.5,
            "compression_ratio_threshold": 2.4,
        }

        if WHISPER_LANGUAGE:
            options["language"] = WHISPER_LANGUAGE

        # Feed last transcript as context for better cross-chunk accuracy
        if _last_text:
            options["initial_prompt"] = _last_text

        result = model.transcribe(audio, **options)
        text   = result.get("text", "").strip()

        HALLUCINATIONS = {
            "thank you", "thanks", "thank you.", "thanks.",
            "you", ".", "..", "...", "bye", "bye.",
            "subtitles by", "www.", "subscribe",
            "okay", "ok", "um", "uh", "hmm",
        }
        if text.lower() in HALLUCINATIONS:
            return ""

        _last_text = text
        return text

    except Exception as e:
        print(f"[Whisper] transcription error: {e}")
        return ""


def _is_silent(audio: np.ndarray, threshold: float = 0.01) -> bool:
    if len(audio) == 0:
        return True
    rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
    return rms < threshold


def reset_context():
    """Call at the start of each consultation to clear rolling context."""
    global _last_text
    _last_text = ""


def get_model_info() -> dict:
    return {
        "model":    WHISPER_MODEL,
        "device":   _device or "not loaded yet",
        "language": WHISPER_LANGUAGE or "auto-detect",
        "task":     WHISPER_TASK,
        "loaded":   _model is not None,
    }