import time
import threading

import numpy as np
import sounddevice as sd
import speech_recognition as sr

from PyQt6.QtCore import QThread, pyqtSignal


class WakeWordWorker(QThread):
    """Passive listener for Hey Jarvis and double-clap wake events."""

    wake_detected = pyqtSignal(str)
    level = pyqtSignal(float)
    error = pyqtSignal(str)

    def __init__(
        self,
        sample_rate=16000,
        clap_min_interval=0.08,
        clap_max_interval=0.75,
        clap_cooldown=1.5,
        speech_check_interval=2.5,
        parent=None,
    ):
        super().__init__(parent)

        self.sample_rate = sample_rate
        self.clap_rms_threshold = 0.005
        self.clap_peak_threshold = 0.20
        self.clap_min_interval = clap_min_interval
        self.clap_max_interval = clap_max_interval
        self.clap_cooldown = clap_cooldown
        self.speech_check_interval = speech_check_interval

        self.running = True
        self.recognizer = sr.Recognizer()
        self._last_clap_time = 0.0
        self._first_clap_time = None
        self._last_trigger_time = 0.0
        self._lock = threading.Lock()

    def run(self):
        print("[WAKE] Wake listener started.")
        try:
            while self.running:
                triggered = self._listen_cycle()
                if triggered:
                    self.wake_detected.emit(triggered)
                    time.sleep(0.5)
        except Exception as e:
            print(f"[WAKE ERROR] {e}")
            self.error.emit(str(e))
        print("[WAKE] Wake listener stopped.")

    def _listen_cycle(self):
        audio_buffer = []
        last_speech_check = time.time()

        def callback(indata, frames, time_info, status):
            if status:
                print(f"[WAKE MIC] {status}")

            audio = indata.copy()
            audio_buffer.append(audio)

            rms = float(np.sqrt(np.mean(np.square(audio))))
            peak = float(np.max(np.abs(audio)))

            self.level.emit(min(1.0, rms * 8.0))

            if self._is_clap(rms, peak):
                self._register_clap()

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=callback,
            blocksize=1024,
        ):
            while self.running:

                if self._double_clap_ready():
                    print("[WAKE] DOUBLE CLAP DETECTED!")
                    self._last_trigger_time = time.time()
                    self._first_clap_time = None
                    return "clap"

                now = time.time()

                if now - last_speech_check >= self.speech_check_interval:
                    last_speech_check = now

                    if audio_buffer:
                        audio = np.squeeze(
                            np.concatenate(audio_buffer, axis=0)
                        )
                        audio_buffer.clear()

                        speech = self._recognize_audio(audio)

                        if speech:
                            print(f"[WAKE] Heard: {speech}")
                            normalized = speech.lower().strip().replace(",", "")
                            if "hey jarvis" in normalized:
                                print("[WAKE] Hey Jarvis detected.")
                                return "voice"

                time.sleep(0.03)

        return None

    def _is_clap(self, rms, peak):
        return (
            rms >= self.clap_rms_threshold
            and peak >= self.clap_peak_threshold
        )

    def _register_clap(self):
        now = time.time()

        with self._lock:
            if now - self._last_clap_time < self.clap_min_interval:
                return

            if now - self._last_trigger_time < self.clap_cooldown:
                return

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
            print("[WAKE] Clap window expired; restarting pair.")

    def _double_clap_ready(self):
        with self._lock:
            if self._first_clap_time is None:
                return False

            elapsed = time.time() - self._first_clap_time

            return (
                elapsed <= self.clap_max_interval
                and self._last_clap_time > self._first_clap_time
                and self._last_clap_time - self._first_clap_time <= self.clap_max_interval
            )

    def _recognize_audio(self, audio):
        if audio is None or len(audio) == 0:
            return ""

        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767).astype(np.int16)

        audio_data = sr.AudioData(
            pcm.tobytes(),
            self.sample_rate,
            2,
        )

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
    """
    Short-lived listener used while Jarvis is processing/speaking.

    Detects phrases containing "jarvis stop" and emits stop_detected.
    It is separate from the passive wake listener so the two microphone
    ownership phases never overlap.
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

                    audio = np.squeeze(
                        np.concatenate(audio_chunks, axis=0)
                    )

                    text = self._recognize_audio(audio)

                    if text:
                        normalized = (
                            text.lower()
                            .strip()
                            .replace(",", "")
                        )

                        print(f"[STOP] Heard: {text}")

                        if "jarvis stop" in normalized:
                            print("[STOP] 'Jarvis stop' detected.")
                            self.stop_detected.emit()
                            return

        except Exception as e:
            print(f"[STOP ERROR] {e}")
            self.error.emit(str(e))

        print("[STOP] Stop-word listener stopped.")

    def _recognize_audio(self, audio):
        if audio is None or len(audio) == 0:
            return ""

        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767).astype(np.int16)

        audio_data = sr.AudioData(
            pcm.tobytes(),
            self.sample_rate,
            2,
        )

        try:
            return self.recognizer.recognize_google(audio_data).strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[STOP] Recognition unavailable: {e}")
            return ""

    def stop(self):
        self.running = False
