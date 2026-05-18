import sounddevice as sd
import numpy as np

devices = sd.query_devices()

print("Testing all input devices for 1 second each...\n")
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        for rate in [16000, 44100, 48000]:
            try:
                audio = sd.rec(int(1 * rate), samplerate=rate,
                               channels=1, dtype='float32', device=i)
                sd.wait()
                rms = float(np.sqrt(np.mean(audio**2)))
                if rms > 0.0001:
                    print(f"✅ Device {i} ({dev['name']}) at {rate}Hz - RMS: {rms:.4f} WORKS!")
                else:
                    print(f"❌ Device {i} ({dev['name']}) at {rate}Hz - RMS: {rms:.4f} silent")
                break
            except Exception as e:
                print(f"❌ Device {i} ({dev['name']}) at {rate}Hz - Error: {str(e)[:50]}")