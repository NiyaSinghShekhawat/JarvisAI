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

    The worker stays active while Jarvis is idle.

    When a wake event is detected it emits:
        wake_detected("voice")
        wake_detected("clap")
    """

    wake_detected = pyqtSignal(str)

    level = pyqtSignal(float)

    error = pyqtSignal(str)

    def __init__(
        self,
        sample_rate=16000,
        clap_threshold=0.35,
        clap_window=0.65,
        speech_check_interval=2.5,
        parent=None,
    ):
        super().__init__(parent)

        self.sample_rate = sample_rate

        self.clap_threshold = clap_threshold
        self.clap_window = clap_window

        self.speech_check_interval = (
            speech_check_interval
        )

        self.running = True

        self.recognizer = sr.Recognizer()

        self.last_clap_time = None

        self._lock = threading.Lock()

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        print("[WAKE] Wake listener started.")

        try:

            while self.running:

                triggered = self._listen_cycle()

                if triggered:
                    self.wake_detected.emit(
                        triggered
                    )

                    # Give the main application time
                    # to take over the microphone.
                    time.sleep(0.5)

        except Exception as e:

            print(
                f"[WAKE ERROR] {e}"
            )

            self.error.emit(
                str(e)
            )

        print("[WAKE] Wake listener stopped.")

    # ========================================================
    # LISTEN CYCLE
    # ========================================================

    def _listen_cycle(self):

        audio_buffer = []

        clap_times = []

        speech_recognition_audio = []

        start_time = time.time()

        last_speech_check = start_time

        clap_detected = False

        def callback(
            indata,
            frames,
            time_info,
            status,
        ):

            nonlocal clap_detected

            if status:
                print(
                    f"[WAKE MIC] {status}"
                )

            audio = indata.copy()

            audio_buffer.append(
                audio
            )

            # ------------------------------------------------
            # RMS
            # ------------------------------------------------

            rms = float(
                np.sqrt(
                    np.mean(
                        np.square(audio)
                    )
                )
            )

            level = min(
                1.0,
                rms * 8.0
            )

            self.level.emit(
                level
            )

            # ------------------------------------------------
            # CLAP DETECTION
            # ------------------------------------------------

            if rms >= self.clap_threshold:

                now = time.time()

                clap_times.append(now)

                # Remove old claps
                clap_times[:] = [
                    t
                    for t in clap_times
                    if now - t <= self.clap_window
                ]

                if len(clap_times) >= 2:

                    clap_detected = True

        # ====================================================
        # MICROPHONE
        # ====================================================

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=callback,
            blocksize=1024,
        ):

            while self.running:

                # --------------------------------------------
                # DOUBLE CLAP
                # --------------------------------------------

                if clap_detected:

                    print(
                        "[WAKE] Double clap detected."
                    )

                    return "clap"

                # --------------------------------------------
                # PERIODIC SPEECH CHECK
                # --------------------------------------------

                now = time.time()

                if (
                    now - last_speech_check
                    >= self.speech_check_interval
                ):

                    last_speech_check = now

                    if audio_buffer:

                        audio = np.concatenate(
                            audio_buffer,
                            axis=0
                        )

                        audio = np.squeeze(
                            audio
                        )

                        # Keep only recent audio
                        audio_buffer.clear()

                        speech = self._recognize_audio(
                            audio
                        )

                        if speech:

                            print(
                                f"[WAKE] Heard: {speech}"
                            )

                            normalized = (
                                speech
                                .lower()
                                .strip()
                            )

                            if (
                                "hey jarvis"
                                in normalized
                                or
                                "hey jarvis"
                                in normalized.replace(
                                    ",",
                                    ""
                                )
                            ):

                                print(
                                    "[WAKE] Hey Jarvis detected."
                                )

                                return "voice"

                time.sleep(0.05)

        return None

    # ========================================================
    # SPEECH RECOGNITION
    # ========================================================

    def _recognize_audio(self, audio):

        if audio is None:
            return ""

        if len(audio) == 0:
            return ""

        audio = np.clip(
            audio,
            -1.0,
            1.0
        )

        pcm = (
            audio * 32767
        ).astype(
            np.int16
        )

        audio_data = sr.AudioData(
            pcm.tobytes(),
            self.sample_rate,
            2,
        )

        try:

            return self.recognizer.recognize_google(
                audio_data
            ).strip()

        except sr.UnknownValueError:

            return ""

        except sr.RequestError as e:

            print(
                f"[WAKE] Recognition unavailable: {e}"
            )

            return ""

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self.running = False