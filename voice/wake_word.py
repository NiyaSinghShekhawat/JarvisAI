import time
import threading

import numpy as np
import sounddevice as sd
import speech_recognition as sr

from PyQt6.QtCore import QThread, pyqtSignal


class WakeWordWorker(QThread):
    """
    Passive wake listener for Jarvis.

    Detects:
        1. "Hey Jarvis"
        2. Double clap

    The listener is intentionally lightweight: it continuously monitors
    the microphone and only hands control to VoiceWorker after a wake event.
    """

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

        # Clap detection is based on a short loud transient rather than
        # a high RMS threshold. A clap is brief, so RMS can be relatively low.
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

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        print("[WAKE] Wake listener started.")
        print(
            "[WAKE] Double clap: "
            f"RMS>={self.clap_rms_threshold}, "
            f"PEAK>={self.clap_peak_threshold}, "
            f"window={self.clap_max_interval}s"
        )

        try:

            while self.running:

                triggered = self._listen_cycle()

                if triggered:
                    self.wake_detected.emit(triggered)

                    # Give the main application time to stop this worker
                    # before VoiceWorker starts using the microphone.
                    time.sleep(0.5)

        except Exception as e:

            print(f"[WAKE ERROR] {e}")
            self.error.emit(str(e))

        print("[WAKE] Wake listener stopped.")

    # ========================================================
    # LISTEN CYCLE
    # ========================================================

    def _listen_cycle(self):

        audio_buffer = []
        start_time = time.time()
        last_speech_check = start_time

        def callback(indata, frames, time_info, status):

            if status:
                print(f"[WAKE MIC] {status}")

            audio = indata.copy()
            audio_buffer.append(audio)

            rms = float(
                np.sqrt(np.mean(np.square(audio)))
            )

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

                # ------------------------------------------------
                # DOUBLE CLAP
                # ------------------------------------------------
                if self._double_clap_ready():
                    print("[WAKE] DOUBLE CLAP DETECTED!")
                    self._last_trigger_time = time.time()
                    self._first_clap_time = None
                    return "clap"

                # ------------------------------------------------
                # PERIODIC SPEECH CHECK
                # ------------------------------------------------
                now = time.time()

                if now - last_speech_check >= self.speech_check_interval:

                    last_speech_check = now

                    if audio_buffer:

                        audio = np.concatenate(
                            audio_buffer,
                            axis=0,
                        )

                        audio = np.squeeze(audio)
                        audio_buffer.clear()

                        speech = self._recognize_audio(audio)

                        if speech:

                            print(f"[WAKE] Heard: {speech}")

                            normalized = (
                                speech.lower()
                                .strip()
                                .replace(",", "")
                            )

                            if "hey jarvis" in normalized:
                                print("[WAKE] Hey Jarvis detected.")
                                return "voice"

                # Don't busy-spin the worker thread.
                time.sleep(0.03)

        return None

    # ========================================================
    # CLAP DETECTION
    # ========================================================

    def _is_clap(self, rms, peak):
        """Return True for a short, sufficiently loud microphone transient."""

        return (
            rms >= self.clap_rms_threshold
            and peak >= self.clap_peak_threshold
        )

    def _register_clap(self):

        now = time.time()

        with self._lock:

            # Prevent the same physical clap from generating multiple
            # detections across adjacent audio blocks.
            if now - self._last_clap_time < self.clap_min_interval:
                return

            # Don't accept another trigger during cooldown.
            if now - self._last_trigger_time < self.clap_cooldown:
                return

            self._last_clap_time = now

            if self._first_clap_time is None:
                self._first_clap_time = now
                print("[WAKE] First clap detected.")
                return

            interval = now - self._first_clap_time

            if interval <= self.clap_max_interval:
                print(
                    f"[WAKE] Second clap detected "
                    f"({interval:.2f}s after first)."
                )
                return

            # The previous first clap expired. Treat this as the new first clap.
            print("[WAKE] Previous clap window expired; restarting pair.")
            self._first_clap_time = now

    def _double_clap_ready(self):

        with self._lock:

            if self._first_clap_time is None:
                return False

            elapsed = time.time() - self._first_clap_time

            # _register_clap leaves the timestamp in place when the second
            # clap arrives; this method converts that into a wake event.
            return (
                elapsed <= self.clap_max_interval
                and self._last_clap_time > self._first_clap_time
                and self._last_clap_time - self._first_clap_time
                <= self.clap_max_interval
            )

    # ========================================================
    # SPEECH RECOGNITION
    # ========================================================

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

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):
        self.running = False
