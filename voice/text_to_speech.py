import queue
import threading

import pyttsx3
from PyQt6.QtCore import QObject, pyqtSignal


class TextToSpeech(QObject):

    speaking_started = pyqtSignal()
    speaking_finished = pyqtSignal()
    response_finished = pyqtSignal()
    level = pyqtSignal(float)
    error = pyqtSignal(str)
    
    def __init__(
        self,
        rate=180,
        volume=1.0
    ):
        super().__init__()

        self.rate = rate
        self.volume = volume

        # ====================================================
        # RESPONSE QUEUE
        # ====================================================

        self.queue = queue.Queue()

        self.running = True

        # Complete response currently being built
        self.buffer = ""

        self.lock = threading.Lock()

        self.currently_speaking = False

        # ====================================================
        # DEDICATED TTS THREAD
        # ====================================================

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )

        self.thread.start()

    # ========================================================
    # TTS THREAD
    
    def _run(self):
        # ========================================================
        VOICE_INDEX = 0  # Microsoft David
        engine = pyttsx3.init("sapi5")
        voices = engine.getProperty("voices")

        engine.setProperty(
            "voice",
            voices[VOICE_INDEX].id
        )

        engine.setProperty(
            "rate",
            180
        )

        engine.setProperty(
            "volume",
            1.0
        )

        for voice in voices:

            if "David" in voice.name:

                engine.setProperty(
                    "voice",
                    voice.id
                )

                break


        try:

            print("[TTS] TTS worker started.")

            while self.running:

                item = self.queue.get()

                if item is None:
                    break

                command = item[0]

                # =================================================
                # SPEAK
                # =================================================

                if command == "speak":

                    text = item[1]

                    if not text.strip():
                        continue

                    print(
                        f"[TTS] Speaking: {text}"
                    )

                    engine = None

                    try:

                        # ================================================
                        # CREATE FRESH SAPI5 ENGINE
                        # ================================================

                        engine = pyttsx3.init("sapi5")

                        # Get installed voices
                        voices = engine.getProperty("voices")

                        # Microsoft David
                        engine.setProperty(
                            "voice",
                            voices[0].id
                        )

                        # Natural-ish speaking speed
                        engine.setProperty(
                            "rate",
                            165
                        )

                        engine.setProperty(
                            "volume",
                            1.0
                        )

                        # ================================================
                        # SPEAK
                        # ================================================

                        self.currently_speaking = True

                        self.speaking_started.emit()

                        engine.say(text)

                        engine.runAndWait()

                    except Exception as e:

                        print(
                            f"[TTS ERROR] {e}"
                        )

                        self.error.emit(
                            str(e)
                        )

                    finally:

                        try:

                            if engine:
                                engine.stop()

                        except Exception:
                            pass

                        engine = None

                        self.currently_speaking = False

                        self.level.emit(0.0)

                        self.speaking_finished.emit()

                        self.response_finished.emit()

            print("[TTS] TTS worker stopped.")

        except Exception as e:

            print(
                f"[TTS WORKER ERROR] {e}"
            )

            self.error.emit(
                str(e)
            )

    # ========================================================
    # FEED TOKEN
    # ========================================================

    def feed(self, token):

        if not token:
            return

        with self.lock:

            self.buffer += token

        print(
            f"[TTS FEED] {repr(token)}"
        )

    # ========================================================
    # RESPONSE FINISHED
    # ========================================================

    def finish_response(self):

        with self.lock:

            text = self.buffer.strip()

            self.buffer = ""

        if not text:
            return

        print(
            "[TTS] Response complete."
        )

        print(
            f"[TTS] Queueing: {text}"
        )

        self.queue.put(
            (
                "speak",
                text
            )
        )

    # ========================================================
    # STOP CURRENT SPEECH
    # ========================================================

    def stop_speaking(self):

        with self.lock:

            self.buffer = ""

        # ---------------------------------------------
        # Clear pending responses
        # ---------------------------------------------

        try:

            while True:

                self.queue.get_nowait()

        except queue.Empty:
            pass

        print(
            "[TTS] Pending speech cleared."
        )

    # ========================================================
    # SHUTDOWN
    # ========================================================

    def shutdown(self):

        self.running = False

        self.queue.put(
            None
        )

        if self.thread.is_alive():

            self.thread.join(
                timeout=2
            )
