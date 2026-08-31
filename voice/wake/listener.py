import time

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from PyQt6.QtCore import QThread, pyqtSignal

from voice.audio_config import MIC_CHANNELS, MIC_DEVICE, MIC_SAMPLE_RATE, WAKE_SAMPLE_RATE
from .clap_detector import ClapDetector
from .wake_word_detector import LocalWakeWordDetector


class WakeListener(QThread):
    """Single microphone owner for passive local wake detection."""

    wake_detected = pyqtSignal(str)
    level = pyqtSignal(float)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sample_rate = MIC_SAMPLE_RATE
        self.running = True
        self.clap = ClapDetector(MIC_SAMPLE_RATE)
        self.wake_word = LocalWakeWordDetector()

    def run(self):
        print("[WAKE] Local wake listener started.")
        print(f"[WAKE] Microphone device: {MIC_DEVICE} @ {MIC_SAMPLE_RATE} Hz")

        try:
            with sd.InputStream(
                device=MIC_DEVICE,
                samplerate=MIC_SAMPLE_RATE,
                channels=MIC_CHANNELS,
                dtype="float32",
                blocksize=3840,  # 80 ms @ 48 kHz -> 1280 samples @ 16 kHz
            ) as stream:
                self._calibrate(stream)
                print("[WAKE] Listening locally for double clap or 'Hey Jarvis'.")

                while self.running:
                    audio, _ = stream.read(3840)
                    samples = np.squeeze(audio.copy())

                    if samples.size == 0:
                        continue

                    rms = float(np.sqrt(np.mean(np.square(samples))))
                    self.level.emit(min(1.0, rms * 5.0))

                    if self.clap.process(samples):
                        print("[WAKE] DOUBLE CLAP DETECTED!")
                        self.wake_detected.emit("clap")
                        return

                    # Capture is 48 kHz because that is the microphone's native
                    # WASAPI rate. openWakeWord expects 16 kHz, so resample
                    # exactly one 80 ms frame before inference.
                    wake_samples = resample_poly(
                        samples,
                        WAKE_SAMPLE_RATE,
                        MIC_SAMPLE_RATE,
                    )
                    wake_samples = np.asarray(wake_samples, dtype=np.float32)

                    if self.wake_word.process(
                        (np.clip(wake_samples, -1.0, 1.0) * 32767).astype(np.int16)
                    ):
                        self.wake_detected.emit("voice")
                        return

        except Exception as exc:
            print(f"[WAKE ERROR] {exc}")
            self.error.emit(str(exc))

        print("[WAKE] Local wake listener stopped.")

    def _calibrate(self, stream):
        print("[WAKE] Calibrating microphone noise floor for 1.5s...")
        chunks = []
        deadline = time.monotonic() + 1.5

        while self.running and time.monotonic() < deadline:
            audio, _ = stream.read(3840)
            chunks.append(np.squeeze(audio.copy()))

        if chunks:
            self.clap.calibrate(np.concatenate(chunks))
            print(
                f"[WAKE] Noise calibrated: RMS={self.clap.noise_rms:.4f}, "
                f"peak={self.clap.noise_peak:.4f}"
            )

    def stop(self):
        self.running = False
