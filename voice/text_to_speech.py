import gc
import queue
import threading

import pyttsx3
from PyQt6.QtCore import QObject, pyqtSignal


class TextToSpeech(QObject):
    """Thread-isolated Windows SAPI5 text-to-speech service."""

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

    def _run(self):
        import pythoncom

        pythoncom.CoInitialize()
        print("[TTS] COM initialized.")
        print("[TTS] TTS worker started.")

        try:
            while self.running:
                item = self.queue.get()

                if item is None:
                    break

                if item[0] != "speak":
                    continue

                text = item[1]
                if not text or not text.strip():
                    continue

                # IMPORTANT: create a fresh SAPI5 engine for every response.
                # On Windows, reusing one pyttsx3 SAPI5 instance across
                # multiple runAndWait() cycles can silently fail after the
                # first utterance. The COM thread itself remains persistent.
                with self.engine_lock:
                    if self.stop_requested:
                        self.stop_requested = False
                        continue
                    self.currently_speaking = True

                engine = None
                interrupted = False

                try:
                    engine = pyttsx3.init("sapi5")
                    voices = engine.getProperty("voices")

                    if voices:
                        engine.setProperty("voice", voices[0].id)
                        print(f"[TTS] Voice: {voices[0].name}")

                    engine.setProperty("rate", self.rate)
                    engine.setProperty("volume", self.volume)

                    with self.engine_lock:
                        self.current_engine = engine
                        interrupted = self.stop_requested

                    if interrupted:
                        continue

                    print(f"[TTS] Speaking: {text}")
                    self.speaking_started.emit()

                    engine.say(text)
                    engine.runAndWait()

                    with self.engine_lock:
                        interrupted = self.stop_requested

                except Exception as e:
                    print(f"[TTS ERROR] {e}")
                    self.error.emit(str(e))

                finally:
                    with self.engine_lock:
                        self.currently_speaking = False
                        self.current_engine = None
                        self.stop_requested = False

                    try:
                        if engine is not None:
                            engine.stop()
                    except Exception:
                        pass

                    # Release the SAPI COM object before the next response.
                    del engine
                    gc.collect()

                    self.level.emit(0.0)
                    self.speaking_finished.emit()

                    if interrupted:
                        print("[TTS] Speech interrupted.")
                        self.speech_interrupted.emit()
                    else:
                        print("[TTS] Speech finished.")
                        self.response_finished.emit()

        except Exception as e:
            print(f"[TTS WORKER ERROR] {e}")
            self.error.emit(str(e))

        finally:
            with self.engine_lock:
                self.current_engine = None
                self.currently_speaking = False

            pythoncom.CoUninitialize()
            print("[TTS] COM uninitialized.")

    def feed(self, token):
        if not token:
            return

        with self.lock:
            self.buffer += token

    def finish_response(self):
        with self.lock:
            text = self.buffer.strip()
            self.buffer = ""

        if not text:
            print("[TTS] finish_response called with empty buffer.")
            return

        print(f"[TTS] Queueing: {text}")
        self.queue.put(("speak", text))

    def stop_speaking(self):
        with self.lock:
            self.buffer = ""

        # Remove waiting responses, but do not leave the queue in a broken
        # state for the next request.
        try:
            while True:
                self.queue.get_nowait()
        except queue.Empty:
            pass

        with self.engine_lock:
            engine = self.current_engine
            active = self.currently_speaking

            if not active or engine is None:
                self.stop_requested = False
                print("[TTS] No active speech. Pending speech cleared.")
                return

            self.stop_requested = True

        try:
            engine.stop()
            print("[TTS] Current speech interrupted.")
        except Exception as e:
            print(f"[TTS] Could not stop engine: {e}")

    def shutdown(self):
        self.running = False
        self.stop_speaking()
        self.queue.put(None)

        if self.thread.is_alive():
            self.thread.join(timeout=2)
