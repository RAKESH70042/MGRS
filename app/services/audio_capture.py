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

TARGET_RATE   = 16000   # Whisper expects 16kHz
CHUNK_SECONDS = 5       # seconds per transcription chunk
CHANNELS      = 1


class AudioCapture:
    def __init__(self, on_chunk):
        self.on_chunk   = on_chunk
        self._stream    = None
        self._buffer    = []
        self._lock      = threading.Lock()
        self._running   = False
        self._device_rate = None

    def start(self):
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice not installed. Run: pip install sounddevice")

        # Query actual device sample rate instead of forcing 16kHz
        device_info = sd.query_devices(kind='input')
        self._device_rate = int(device_info['default_samplerate'])
        print(f"[Audio] Device sample rate: {self._device_rate}Hz → resampling to {TARGET_RATE}Hz")

        self._chunk_samples = self._device_rate * CHUNK_SECONDS
        self._running = True
        self._buffer  = []

        self._stream = sd.InputStream(
            samplerate=self._device_rate,
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

    def _resample(self, audio: np.ndarray) -> np.ndarray:
        """Resample from device rate to 16kHz using linear interpolation."""
        if self._device_rate == TARGET_RATE:
            return audio
        target_len = int(len(audio) * TARGET_RATE / self._device_rate)
        resampled = np.interp(
            np.linspace(0, len(audio) - 1, target_len),
            np.arange(len(audio)),
            audio
        )
        return resampled.astype(np.float32)

    def _callback(self, indata, frames, time_info, status):
        with self._lock:
            self._buffer.append(indata.copy().flatten())
            total = sum(len(c) for c in self._buffer)
            if total >= self._chunk_samples:
                chunk = np.concatenate(self._buffer)[:self._chunk_samples]
                self._buffer = [np.concatenate(self._buffer)[self._chunk_samples:]]
                resampled = self._resample(chunk)
                threading.Thread(
                    target=self.on_chunk, args=(resampled,), daemon=True
                ).start()