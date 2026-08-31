import re
import time

import numpy as np
import sounddevice as sd
import speech_recognition as sr
from scipy.signal import resample_poly
from PyQt6.QtCore import QThread, pyqtSignal

from voice.audio_config import MIC_CHANNELS, MIC_DEVICE, MIC_SAMPLE_RATE, WAKE_SAMPLE_RATE
from .clap_detector import ClapDetector
from .wake_word_detector import LocalWakeWordDetector


WAKE_PHRASES = (
    "wake up jarvis",
    "wake up, jarvis",
    "wake jarvis",
)


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
        self.recognizer = sr.Recognizer()
        self._last_phrase_check = 0.0
        self._stt_error_logged = False

    def run(self):
        print("[WAKE] Local wake listener started.")
        print(f"[WAKE] Microphone device: {MIC_DEVICE} @ {MIC_SAMPLE_RATE} Hz")
        print("[WAKE] Wake phrases: 'Hey Jarvis' / 'Wake up Jarvis' / double clap")

        try:
            with sd.InputStream(
                device=MIC_DEVICE,
                samplerate=MIC_SAMPLE_RATE,
                channels=MIC_CHANNELS,
                dtype="float32",
                blocksize=3840,  # 80 ms @ 48 kHz -> 1280 samples @ 16 kHz
            ) as stream:
                self._calibrate(stream)
                print("[WAKE] Listening locally for wake triggers.")

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

                    wake_samples = resample_poly(
                        samples,
                        WAKE_SAMPLE_RATE,
                        MIC_SAMPLE_RATE,
                    )
                    wake_samples = np.asarray(wake_samples, dtype=np.float32)
                    wake_pcm = (np.clip(wake_samples, -1.0, 1.0) * 32767).astype(np.int16)

                    # Native openWakeWord detector: "Hey Jarvis".
                    if self.wake_word.process(wake_pcm):
                        self.wake_detected.emit("voice")
                        return

                    # Compatibility fallback for "Wake up Jarvis". This only
                    # invokes online speech recognition after a clear voice
                    # activity spike, so the passive listener does not stream
                    # continuous audio to the service.
                    if rms >= 0.05 and (time.monotonic() - self._last_phrase_check) >= 1.5:
                        self._last_phrase_check = time.monotonic()
                        if self._detect_wake_phrase(stream, wake_pcm):
                            self.wake_detected.emit("voice")
                            return

        except Exception as exc:
            print(f"[WAKE ERROR] {exc}")
            self.error.emit(str(exc))

        print("[WAKE] Local wake listener stopped.")

    def _detect_wake_phrase(self, stream, initial_pcm):
        """Briefly capture candidate speech and look for a wake phrase."""
        frames = [initial_pcm]
        deadline = time.monotonic() + 1.8

        while self.running and time.monotonic() < deadline:
            audio, _ = stream.read(3840)
            samples = np.squeeze(audio.copy())
            if samples.size == 0:
                continue

            wake_samples = resample_poly(
                samples,
                WAKE_SAMPLE_RATE,
                MIC_SAMPLE_RATE,
            )
            wake_pcm = (np.clip(wake_samples, -1.0, 1.0) * 32767).astype(np.int16)
            frames.append(wake_pcm)

        audio_pcm = np.concatenate(frames)
        audio_data = sr.AudioData(
            audio_pcm.tobytes(),
            WAKE_SAMPLE_RATE,
            2,
        )

        try:
            text = self.recognizer.recognize_google(audio_data).strip().lower()
        except sr.UnknownValueError:
            return False
        except sr.RequestError as exc:
            if not self._stt_error_logged:
                print(f"[WAKE] Wake-phrase fallback unavailable: {exc}")
                self._stt_error_logged = True
            return False

        normalized = re.sub(r"[^a-z ]", " ", text)
        normalized = " ".join(normalized.split())

        for phrase in WAKE_PHRASES:
            phrase = re.sub(r"[^a-z ]", " ", phrase)
            phrase = " ".join(phrase.split())
            if phrase in normalized:
                print(f"[WAKE] Wake phrase detected by fallback STT: '{text}'")
                return True

        return False

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
