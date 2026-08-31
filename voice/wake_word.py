import time
import threading

import numpy as np
import sounddevice as sd
import speech_recognition as sr

from PyQt6.QtCore import QThread, pyqtSignal


class WakeWordWorker(QThread):
    """Passive listener for a conservative double-clap or 'Hey Jarvis'."""

    wake_detected = pyqtSignal(str)
    level = pyqtSignal(float)
    error = pyqtSignal(str)

    def __init__(self, sample_rate=16000, parent=None):
        super().__init__(parent)
        self.sample_rate = sample_rate

        # ----------------------------------------------------
        # ADAPTIVE NOISE FLOOR
        # ----------------------------------------------------
        self.noise_rms = 0.0
        self.noise_peak = 0.0
        self.noise_initialized = False
        self.calibration_seconds = 1.5

        # IMPORTANT: speech is deliberately excluded from clap detection.
        # A voice syllable can have a sharp peak, so peak/RMS alone is not
        # enough to identify a clap.
        self.min_rms = 0.055
        self.min_peak = 0.55
        self.rms_multiplier = 7.0
        self.peak_multiplier = 5.0
        self.min_zero_crossing_rate = 0.18
        self.crest_factor = 4.0
        self.max_speech_rms = 0.10

        self.clap_min_interval = 0.18
        self.clap_max_interval = 0.60
        self.clap_cooldown = 2.0
        self.clap_expiry = 0.75

        self.speech_check_interval = 1.0
        self.running = True
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = False

        self._last_clap_time = 0.0
        self._first_clap_time = None
        self._last_trigger_time = 0.0
        self._lock = threading.Lock()

    def run(self):
        print("[WAKE] Wake listener started.")

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1024,
            ) as stream:
                self._calibrate(stream)

                if not self.running:
                    return

                print(
                    f"[WAKE] Noise calibrated: RMS={self.noise_rms:.4f}, "
                    f"peak={self.noise_peak:.4f}"
                )
                print("[WAKE] Listening for double clap or 'Hey Jarvis'.")

                audio_buffer = []
                last_speech_check = time.time()

                while self.running:
                    audio, _ = stream.read(1024)
                    samples = np.squeeze(audio.copy())

                    rms = float(np.sqrt(np.mean(np.square(samples))))
                    peak = float(np.max(np.abs(samples)))
                    zcr = self._zero_crossing_rate(samples)

                    self._update_noise_floor(rms, peak)
                    self.level.emit(min(1.0, rms * 5.0))

                    # Do not let speech create clap candidates.
                    if self._is_clap(rms, peak, zcr):
                        self._register_clap()

                    if self._double_clap_ready():
                        print("[WAKE] DOUBLE CLAP DETECTED!")
                        self._last_trigger_time = time.time()
                        self._first_clap_time = None
                        audio_buffer.clear()
                        self.wake_detected.emit("clap")
                        return

                    # Speech recognition is independent of clap detection.
                    # Keep enough audio to recognize the complete phrase.
                    audio_buffer.append(audio.copy())
                    now = time.time()

                    if now - last_speech_check >= self.speech_check_interval:
                        last_speech_check = now

                        if audio_buffer:
                            audio = np.squeeze(np.concatenate(audio_buffer, axis=0))
                            audio_buffer.clear()

                            speech = self._recognize_audio(audio)
                            if speech:
                                print(f"[WAKE] Heard: {speech}")
                                if self._is_wake_phrase(speech):
                                    print("[WAKE] Hey Jarvis detected.")
                                    self._last_trigger_time = time.time()
                                    self._first_clap_time = None
                                    self.wake_detected.emit("voice")
                                    return

        except Exception as e:
            print(f"[WAKE ERROR] {e}")
            self.error.emit(str(e))

        print("[WAKE] Wake listener stopped.")

    def _calibrate(self, stream):
        """Measure the room/microphone floor before accepting claps."""
        print("[WAKE] Calibrating microphone noise floor for 1.5s...")

        samples = []
        deadline = time.time() + self.calibration_seconds

        while self.running and time.time() < deadline:
            audio, _ = stream.read(1024)
            audio = np.squeeze(audio)
            rms = float(np.sqrt(np.mean(np.square(audio))))
            peak = float(np.max(np.abs(audio)))
            samples.append((rms, peak))

        if not samples:
            return

        rms_values = np.array([x[0] for x in samples])
        peak_values = np.array([x[1] for x in samples])
        self.noise_rms = float(np.percentile(rms_values, 80))
        self.noise_peak = float(np.percentile(peak_values, 80))
        self.noise_initialized = True

    def _update_noise_floor(self, rms, peak):
        if not self.noise_initialized:
            return

        quiet_rms_limit = max(self.min_rms * 0.6, self.noise_rms * 1.5)
        quiet_peak_limit = max(self.min_peak * 0.30, self.noise_peak * 1.5)

        # Only track genuinely quiet audio. A voice/clap cannot raise the
        # baseline and make later wake events harder to detect.
        if rms < quiet_rms_limit and peak < quiet_peak_limit:
            alpha = 0.01
            self.noise_rms = (1 - alpha) * self.noise_rms + alpha * rms
            self.noise_peak = (1 - alpha) * self.noise_peak + alpha * peak

    @staticmethod
    def _zero_crossing_rate(samples):
        if len(samples) < 2:
            return 0.0
        signs = samples >= 0
        return float(np.mean(signs[1:] != signs[:-1]))

    def _is_clap(self, rms, peak, zcr):
        if not self.noise_initialized:
            return False

        # The most important false-positive guard: normal speech is not a
        # clap candidate, even when a consonant creates a sharp peak.
        if rms > self.max_speech_rms:
            return False

        rms_threshold = max(self.min_rms, self.noise_rms * self.rms_multiplier)
        peak_threshold = max(self.min_peak, self.noise_peak * self.peak_multiplier)

        return (
            rms >= rms_threshold
            and peak >= peak_threshold
            and zcr >= self.min_zero_crossing_rate
            and peak >= rms * self.crest_factor
        )

    def _register_clap(self):
        now = time.time()

        with self._lock:
            if now - self._last_clap_time < self.clap_min_interval:
                return

            if now - self._last_trigger_time < self.clap_cooldown:
                return

            if (
                self._first_clap_time is not None
                and now - self._first_clap_time > self.clap_expiry
            ):
                self._first_clap_time = None

            self._last_clap_time = now

            if self._first_clap_time is None:
                self._first_clap_time = now
                print("[WAKE] First clap detected.")
                return

            interval = now - self._first_clap_time
            if interval <= self.clap_max_interval:
                print(f"[WAKE] Second clap detected ({interval:.2f}s).")
                return

            self._first_clap_time = now

    def _double_clap_ready(self):
        with self._lock:
            if self._first_clap_time is None:
                return False

            interval = self._last_clap_time - self._first_clap_time
            return (
                self._last_clap_time > self._first_clap_time
                and self.clap_min_interval <= interval <= self.clap_max_interval
            )

    @staticmethod
    def _is_wake_phrase(text):
        # Strict phrase matching. 'Hey Jaggu', 'Hey Jarvis something', etc.
        # are not accepted unless the transcription genuinely starts with
        # the two words 'hey jarvis'.
        normalized = " ".join(text.lower().strip().split())
        normalized = normalized.replace(",", "").replace(".", "")
        words = normalized.split()
        return len(words) >= 2 and words[0] == "hey" and words[1] == "jarvis"

    def _recognize_audio(self, audio):
        if audio is None or len(audio) == 0:
            return ""

        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767).astype(np.int16)
        audio_data = sr.AudioData(pcm.tobytes(), self.sample_rate, 2)

        try:
            return self.recognizer.recognize_google(audio_data).strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[WAKE] Recognition unavailable: {e}")
            return ""

    def stop(self):
        self.running = False


class StopWordWorker(QThread):
    """Detect 'Jarvis stop' while Jarvis is processing or speaking."""

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
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1024,
            ) as stream:
                while self.running:
                    audio_chunks = []
                    deadline = time.time() + self.check_interval

                    while self.running and time.time() < deadline:
                        audio, _ = stream.read(1024)
                        audio_chunks.append(audio.copy())

                    if not self.running or not audio_chunks:
                        continue

                    audio = np.squeeze(np.concatenate(audio_chunks, axis=0))
                    text = self._recognize_audio(audio)

                    if text:
                        normalized = " ".join(text.lower().strip().split())
                        print(f"[STOP] Heard: {text}")
                        if "jarvis stop" in normalized:
                            print("[STOP] 'Jarvis stop' detected.")
                            self.stop_detected.emit()
                            return

        except Exception as e:
            print(f"[STOP ERROR] {e}")
            self.error.emit(str(e))

    def _recognize_audio(self, audio):
        if audio is None or len(audio) == 0:
            return ""

        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767).astype(np.int16)
        audio_data = sr.AudioData(pcm.tobytes(), self.sample_rate, 2)

        try:
            return self.recognizer.recognize_google(audio_data).strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[STOP] Recognition unavailable: {e}")
            return ""

    def stop(self):
        self.running = False
