"""
audio_capture.py
Captures microphone audio in chunks using sounddevice.
Each chunk is a raw PCM bytes object passed to a callback.
"""

import threading
import numpy as np

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

SAMPLE_RATE   = 16000   # Whisper expects 16kHz
CHUNK_SECONDS = 5       # seconds per transcription chunk
CHANNELS      = 1


class AudioCapture:
    def __init__(self, on_chunk):
        """
        on_chunk: callable(np.ndarray) — called with each audio chunk
        """
        self.on_chunk   = on_chunk
        self._stream    = None
        self._buffer    = []
        self._lock      = threading.Lock()
        self._running   = False
        self._chunk_samples = SAMPLE_RATE * CHUNK_SECONDS

    def start(self):
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError(
                "sounddevice not installed. Run: pip install sounddevice"
            )
        self._running = True
        self._buffer  = []
        self._stream  = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=self._callback
        )
        self._stream.start()

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback(self, indata, frames, time_info, status):
        with self._lock:
            self._buffer.append(indata.copy().flatten())
            total = sum(len(c) for c in self._buffer)
            if total >= self._chunk_samples:
                chunk = np.concatenate(self._buffer)[:self._chunk_samples]
                self._buffer = [np.concatenate(self._buffer)[self._chunk_samples:]]
                # fire callback in a separate thread so audio never drops
                threading.Thread(
                    target=self.on_chunk, args=(chunk,), daemon=True
                ).start()