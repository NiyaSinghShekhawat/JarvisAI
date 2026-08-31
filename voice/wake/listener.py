import time
import threading
import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QThread, pyqtSignal

from .clap_detector import ClapDetector
from .wake_word_detector import LocalWakeWordDetector


class WakeListener(QThread):
    """Single microphone owner for passive local wake detection."""

    wake_detected = pyqtSignal(str)
    level = pyqtSignal(float)
    error = pyqtSignal(str)

    def __init__(self, sample_rate=16000, parent=None):
        super().__init__(parent)
        self.sample_rate = sample_rate
        self.running = True
        self.clap = ClapDetector(sample_rate)
        self.wake_word = LocalWakeWordDetector()
        self._lock = threading.Lock()

    def run(self):
        print("[WAKE] Local wake listener started.")
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=320,
            ) as stream:
                self._calibrate(stream)
                print("[WAKE] Listening locally for double clap or 'Hey Jarvis'.")

                while self.running:
                    audio, _ = stream.read(320)
                    samples = np.squeeze(audio.copy())
                    rms = float(np.sqrt(np.mean(np.square(samples))))
                    self.level.emit(min(1.0, rms * 5.0))

                    if self.clap.process(samples):
                        print("[WAKE] DOUBLE CLAP DETECTED!")
                        self.wake_detected.emit("clap")
                        return

                    if self.wake_word.process(samples):
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
            audio, _ = stream.read(320)
            chunks.append(np.squeeze(audio.copy()))
        if chunks:
            self.clap.calibrate(np.concatenate(chunks))
            print(
                f"[WAKE] Noise calibrated: RMS={self.clap.noise_rms:.4f}, "
                f"peak={self.clap.noise_peak:.4f}"
            )

    def stop(self):
        self.running = False
