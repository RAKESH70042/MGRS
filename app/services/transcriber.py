"""
transcriber.py
Converts audio chunks (np.ndarray, 16kHz float32) to text using
OpenAI Whisper running locally.

For Hinglish (Hindi + English):
- Use WHISPER_MODEL=small or medium (NOT base.en / small.en — .en models ignore Hindi)
- Set WHISPER_LANGUAGE=hi for Hindi-dominant, or leave empty for auto-detect
- GPU is used automatically if available (fp16=True)

.env settings:
  WHISPER_MODEL=small          # tiny / base / small / medium / large-v3
  WHISPER_LANGUAGE=            # leave empty = auto-detect (best for Hinglish)
  WHISPER_TASK=transcribe      # transcribe = keep original language, translate = force English
"""

import os
import numpy as np

WHISPER_MODEL    = os.getenv("WHISPER_MODEL",    "small")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "")        # empty = auto-detect
WHISPER_TASK     = os.getenv("WHISPER_TASK",     "transcribe")

_model  = None
_device = None


def _load_model():
    global _model, _device
    if _model is None:
        try:
            import whisper
            import torch

            # Auto-select GPU if available
            if torch.cuda.is_available():
                _device = "cuda"
                print(f"[Whisper] GPU detected: {torch.cuda.get_device_name(0)}")
            else:
                _device = "cpu"
                print("[Whisper] No GPU found, using CPU")

            print(f"[Whisper] Loading model '{WHISPER_MODEL}' on {_device}…")
            _model = whisper.load_model(WHISPER_MODEL, device=_device)
            print(f"[Whisper] ✅ Model loaded — language={'auto-detect' if not WHISPER_LANGUAGE else WHISPER_LANGUAGE}")

        except ImportError:
            raise RuntimeError(
                "openai-whisper not installed. Run: pip install openai-whisper"
            )
    return _model


def transcribe_chunk(audio: np.ndarray) -> str:
    """
    Transcribe a float32 16kHz numpy array.
    Returns transcript string (empty string on silence/failure).
    """
    model = _load_model()

    # Skip very silent chunks to avoid hallucinations
    if _is_silent(audio):
        return ""

    try:
        # Build options
        options = {
            "task":   WHISPER_TASK,
            "fp16":   (_device == "cuda"),   # fp16 only on GPU
            "condition_on_previous_text": True,
            "no_speech_threshold": 0.5,      # skip chunks that are mostly silence
            "compression_ratio_threshold": 2.4,
        }

        # Only pass language if explicitly set — empty = auto-detect (best for Hinglish)
        if WHISPER_LANGUAGE:
            options["language"] = WHISPER_LANGUAGE

        result = model.transcribe(audio, **options)
        text   = result.get("text", "").strip()

        # Filter out Whisper hallucinations on silence
        HALLUCINATIONS = {
            "thank you", "thanks", "thank you.", "thanks.",
            "you", ".", "..", "...", "bye", "bye.",
            "subtitles by", "www.", "subscribe",
        }
        if text.lower() in HALLUCINATIONS:
            return ""

        return text

    except Exception as e:
        print(f"[Whisper] transcription error: {e}")
        return ""


def _is_silent(audio: np.ndarray, threshold: float = 0.01) -> bool:
    """Return True if audio chunk is below silence threshold (RMS energy)."""
    if len(audio) == 0:
        return True
    rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
    return rms < threshold


def get_model_info() -> dict:
    """Return info about the loaded model."""
    return {
        "model":    WHISPER_MODEL,
        "device":   _device or "not loaded yet",
        "language": WHISPER_LANGUAGE or "auto-detect",
        "task":     WHISPER_TASK,
        "loaded":   _model is not None,
    }