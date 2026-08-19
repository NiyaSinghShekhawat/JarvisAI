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
            name="JarvisTTS",
            daemon=True,
        )
        self.thread.start()

    # ========================================================
    # TTS THREAD
    # ========================================================

    def _run(self):
        """Own the SAPI5 engine for the entire lifetime of this thread."""
        import pythoncom

        engine = None

        try:
            pythoncom.CoInitialize()
            print("[TTS] COM initialized.")
            print("[TTS] TTS worker started.")

            engine = pyttsx3.init("sapi5")
            voices = engine.getProperty("voices")

            if voices:
                engine.setProperty("voice", voices[0].id)
                print(f"[TTS] Voice: {voices[0].name}")

            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)

            with self.engine_lock:
                self.current_engine = engine

            while self.running:
                item = self.queue.get()

                try:
                    if item is None:
                        break

                    command = item[0]
                    if command != "speak":
                        continue

                    text = item[1]
                    if not text or not text.strip():
                        continue

                    # A stop requested before this item began means this
                    # response was cancelled. Do not poison future responses.
                    with self.engine_lock:
                        if self.stop_requested:
                            self.stop_requested = False
                            continue
                        self.currently_speaking = True

                    print(f"[TTS] Speaking: {text}")
                    self.speaking_started.emit()

                    interrupted = False
                    failed = False

                    try:
                        engine.say(text)
                        engine.runAndWait()

                        with self.engine_lock:
                            interrupted = self.stop_requested

                    except Exception as e:
                        failed = True
                        print(f"[TTS ERROR] {e}")
                        self.error.emit(str(e))

                    finally:
                        with self.engine_lock:
                            interrupted = interrupted or self.stop_requested
                            self.currently_speaking = False

                        # IMPORTANT:
                        # Do NOT call engine.stop() after a normal response.
                        # SAPI5 can be left in a bad state when stop() is called
                        # after runAndWait() has already completed. This was the
                        # reason the first response worked and later responses
                        # became silent.
                        if interrupted or failed:
                            try:
                                engine.stop()
                            except Exception:
                                pass

                        with self.engine_lock:
                            self.stop_requested = False

                        self.level.emit(0.0)
                        self.speaking_finished.emit()

                        if interrupted and not failed:
                            print("[TTS] Speech interrupted.")
                            self.speech_interrupted.emit()
                        elif not failed:
                            self.response_finished.emit()

                finally:
                    self.queue.task_done()

            print("[TTS] TTS worker stopped.")

        except Exception as e:
            print(f"[TTS WORKER ERROR] {e}")
            self.error.emit(str(e))

        finally:
            with self.engine_lock:
                self.current_engine = None
                self.currently_speaking = False

            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass

            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

            print("[TTS] COM uninitialized.")

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

        # Remove responses that have not started yet.
        try:
            while True:
                self.queue.get_nowait()
                self.queue.task_done()
        except queue.Empty:
            pass

        with self.engine_lock:
            engine = self.current_engine
            active = self.currently_speaking

            if not active:
                self.stop_requested = False
                print("[TTS] No active speech. Pending speech cleared.")
                return

            self.stop_requested = True

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
