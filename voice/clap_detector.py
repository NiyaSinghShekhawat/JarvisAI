import time
import threading

import numpy as np
import sounddevice as sd

from PyQt6.QtCore import QThread, pyqtSignal


class ClapDetector(QThread):
    """
    Background double-clap detector.

    Pipeline:

        Microphone
            ↓
        Audio RMS
            ↓
        Clap detection
            ↓
        Two claps within a short window
            ↓
        clap_detected signal

    The detector runs continuously in the background and does
    not perform speech recognition.
    """

    clap_detected = pyqtSignal()
    level = pyqtSignal(float)
    error = pyqtSignal(str)

    def __init__(
        self,
        parent=None,
        sample_rate=16000,
        channels=1,
        clap_threshold=0.25,
        min_clap_interval=0.08,
        max_clap_interval=0.75,
        cooldown=1.5,
    ):
        super().__init__(parent)

        self.input_device = 1

        device_info = sd.query_devices(
            self.input_device,
            "input"
        )

        self.sample_rate = int(
            device_info["default_samplerate"]
        )

        print(
            f"[CLAP] Using microphone: "
            f"{device_info['name']}"
        )

        print(
            f"[CLAP] Sample rate: "
            f"{self.sample_rate}"
        )
        

        self.sample_rate = sample_rate
        self.channels = channels

        # ----------------------------------------------------
        # Detection settings
        # ----------------------------------------------------

        self.clap_threshold = clap_threshold

        # Prevent one clap from being detected multiple times
        self.min_clap_interval = min_clap_interval

        # Maximum time allowed between clap 1 and clap 2
        self.max_clap_interval = max_clap_interval

        # Prevent repeated triggering
        self.cooldown = cooldown

        # ----------------------------------------------------
        # State
        # ----------------------------------------------------

        self._running = False

        self._last_clap_time = 0.0
        self._first_clap_time = None
        self._last_trigger_time = 0.0

        self._lock = threading.Lock()

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        self._running = True

        print("[CLAP] Double-clap detector started.")

        try:

            with sd.InputStream(
                device=self.input_device,
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            ):

                while self._running:

                    time.sleep(0.05)

        except Exception as e:

            message = str(e)

            print(
                f"[CLAP ERROR] {message}"
            )

            self.error.emit(message)

        finally:

            self._running = False

            print(
                "[CLAP] Double-clap detector stopped."
            )

    # ========================================================
    # AUDIO CALLBACK
    # ========================================================

    def _audio_callback(
        self,
        indata,
        frames,
        time_info,
        status,
    ):

        if not self._running:
            return

        if status:
            print(
                f"[CLAP MICROPHONE] {status}"
            )

        audio = indata.copy()

        # ========================================================
        # MEASURE MICROPHONE
        # ========================================================

        rms = float(
            np.sqrt(
                np.mean(
                    np.square(audio)
                )
            )
        )

        peak = float(
            np.max(
                np.abs(audio)
            )
        )

        # ========================================================
        # PRINT LEVEL PERIODICALLY
        # ========================================================

        now = time.time()

        if not hasattr(self, "_last_debug_print"):
            self._last_debug_print = 0.0

        if now - self._last_debug_print >= 0.5:

            print(
                f"[MIC] RMS={rms:.4f} | "
                f"PEAK={peak:.4f}"
            )

            self._last_debug_print = now

        # ========================================================
        # UI LEVEL
        # ========================================================

        level = min(
            1.0,
            rms * 8.0
        )

        self.level.emit(level)

        # ========================================================
        # CLAP DETECTION
        # ========================================================

        # Much lower RMS threshold than before.
        #
        # A clap can have a relatively low RMS because it is
        # extremely short.

        clap_detected = (
            rms >= 0.005
            and
            peak >= 0.20
        )

        if not clap_detected:
            return

        now = time.time()

        with self._lock:

            # ----------------------------------------------------
            # Prevent duplicate detection from the same clap
            # ----------------------------------------------------

            if (
                now - self._last_clap_time
                < self.min_clap_interval
            ):
                return

            self._last_clap_time = now

            print(
                f"[CLAP] Sound detected "
                f"RMS={rms:.4f} "
                f"PEAK={peak:.4f}"
            )

            # ----------------------------------------------------
            # FIRST CLAP
            # ----------------------------------------------------

            if self._first_clap_time is None:

                self._first_clap_time = now

                print(
                    "[CLAP] First clap detected."
                )

                return

            # ----------------------------------------------------
            # SECOND CLAP
            # ----------------------------------------------------

            interval = (
                now - self._first_clap_time
            )

            if interval <= self.max_clap_interval:

                if (
                    now - self._last_trigger_time
                    >= self.cooldown
                ):

                    print(
                        "[CLAP] DOUBLE CLAP DETECTED!"
                    )

                    self._last_trigger_time = now

                    self._first_clap_time = None

                    self.clap_detected.emit()

                else:

                    print(
                        "[CLAP] Ignored "
                        "(cooldown active)."
                    )

                    self._first_clap_time = None

            else:

                print(
                    "[CLAP] Second clap came too late."
                )

                self._first_clap_time = now
    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self._running = False

        print(
            "[CLAP] Stop requested."
        )

if __name__ == "__main__":

    detector = ClapDetector()

    detector.clap_detected.connect(
        lambda: print(
            ">>> DOUBLE CLAP EVENT <<<"
        )
    )

    detector.error.connect(
        lambda error: print(
            f">>> ERROR: {error}"
        )
    )

    detector.start()

    try:

        while detector.isRunning():

            time.sleep(0.1)

    except KeyboardInterrupt:

        print(
            "\nStopping clap detector..."
        )

        detector.stop()
        detector.wait()