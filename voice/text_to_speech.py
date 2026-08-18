import queue
import threading

import pyttsx3
from PyQt6.QtCore import QObject, pyqtSignal


class TextToSpeech(QObject):

    speaking_started = pyqtSignal()
    speaking_finished = pyqtSignal()
    response_finished = pyqtSignal()
    speech_interrupted = pyqtSignal()
    level = pyqtSignal(float)
    error = pyqtSignal(str)

    def __init__(self, rate=180, volume=1.0):
        super().__init__()

        self.rate = rate
        self.volume = volume

        self.queue = queue.Queue()
        self.running = True
        self.buffer = ""

        self.lock = threading.Lock()
        self.engine_lock = threading.Lock()
        self.current_engine = None
        self.stop_requested = False
        self.currently_speaking = False

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )
        self.thread.start()

    # ========================================================
    # TTS THREAD
    # ========================================================

    def _run(self):

        try:
            print("[TTS] TTS worker started.")

            while self.running:

                item = self.queue.get()

                if item is None:
                    break

                command = item[0]

                if command != "speak":
                    continue

                text = item[1]

                if not text.strip():
                    continue

                print(f"[TTS] Speaking: {text}")

                engine = None
                interrupted = False

                try:
                    engine = pyttsx3.init("sapi5")
                    voices = engine.getProperty("voices")

                    if voices:
                        engine.setProperty("voice", voices[0].id)

                    engine.setProperty("rate", 165)
                    engine.setProperty("volume", 1.0)

                    with self.engine_lock:
                        self.current_engine = engine
                        interrupted = self.stop_requested

                    if interrupted:
                        continue

                    self.currently_speaking = True
                    self.speaking_started.emit()

                    engine.say(text)
                    engine.runAndWait()

                    with self.engine_lock:
                        interrupted = self.stop_requested

                except Exception as e:
                    print(f"[TTS ERROR] {e}")
                    self.error.emit(str(e))

                finally:
                    try:
                        if engine:
                            engine.stop()
                    except Exception:
                        pass

                    with self.engine_lock:
                        self.current_engine = None
                        self.stop_requested = False

                    self.currently_speaking = False
                    self.level.emit(0.0)
                    self.speaking_finished.emit()

                    if interrupted:
                        print("[TTS] Speech interrupted.")
                        self.speech_interrupted.emit()
                    else:
                        self.response_finished.emit()

            print("[TTS] TTS worker stopped.")

        except Exception as e:
            print(f"[TTS WORKER ERROR] {e}")
            self.error.emit(str(e))

    # ========================================================
    # FEED TOKEN
    # ========================================================

    def feed(self, token):

        if not token:
            return

        with self.lock:
            self.buffer += token

    # ========================================================
    # RESPONSE FINISHED
    # ========================================================

    def finish_response(self):

        with self.lock:
            text = self.buffer.strip()
            self.buffer = ""

        if not text:
            return

        print(f"[TTS] Queueing: {text}")
        self.queue.put(("speak", text))

    # ========================================================
    # STOP CURRENT SPEECH
    # ========================================================

    def stop_speaking(self):

        with self.lock:
            self.buffer = ""

        # Clear any response that has not started speaking yet.
        try:
            while True:
                self.queue.get_nowait()
        except queue.Empty:
            pass

        with self.engine_lock:
            self.stop_requested = True
            engine = self.current_engine

        # pyttsx3.runAndWait() is blocking, so stopping the active
        # SAPI5 engine is required for a real-time interruption.
        if engine is not None:
            try:
                engine.stop()
            except Exception as e:
                print(f"[TTS] Could not stop engine: {e}")

        print("[TTS] Current speech interrupted / pending speech cleared.")

    # ========================================================
    # SHUTDOWN
    # ========================================================

    def shutdown(self):

        self.running = False
        self.stop_speaking()
        self.queue.put(None)

        if self.thread.is_alive():
            self.thread.join(timeout=2)
