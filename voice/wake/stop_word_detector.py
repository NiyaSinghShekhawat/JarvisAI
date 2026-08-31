import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal


class StopWordWorker(QThread):
    """Detect 'Jarvis stop' while Jarvis is active.

    This remains a separate command listener for now; the passive wake path
    itself has a single microphone owner. It can be migrated onto the shared
    active audio stream in a later phase.
    """
    stop_detected = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, sample_rate=16000, check_interval=0.8, parent=None):
        super().__init__(parent)
        self.sample_rate = sample_rate
        self.check_interval = check_interval
        self.running = True
        self.recognizer = sr.Recognizer()

    def run(self):
        print("[STOP] Stop-word listener started.")
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1,
                                dtype="float32", blocksize=1024) as stream:
                while self.running:
                    chunks = []
                    deadline = time.monotonic() + self.check_interval
                    while self.running and time.monotonic() < deadline:
                        audio, _ = stream.read(1024)
                        chunks.append(audio.copy())
                    if not self.running or not chunks:
                        continue

                    audio = np.squeeze(np.concatenate(chunks, axis=0))
                    text = self._recognize_audio(audio)
                    if text:
                        print(f"[STOP] Heard: {text}")
                        if "jarvis stop" in " ".join(text.lower().split()):
                            print("[STOP] 'Jarvis stop' detected.")
                            self.stop_detected.emit()
                            return
        except Exception as exc:
            print(f"[STOP ERROR] {exc}")
            self.error.emit(str(exc))

    def _recognize_audio(self, audio):
        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767).astype(np.int16)
        data = sr.AudioData(pcm.tobytes(), self.sample_rate, 2)
        try:
            return self.recognizer.recognize_google(data).strip()
        except (sr.UnknownValueError, sr.RequestError):
            return ""

    def stop(self):
        self.running = False
