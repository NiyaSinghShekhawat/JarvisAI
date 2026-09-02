import gc
import queue
import re
import threading

import pyttsx3
from PyQt6.QtCore import QObject, pyqtSignal

from voice.speech_sanitizer import speech_safe_text


# Prefer the more natural Microsoft voices when they are installed.
# SAPI will fall back to the first available voice on the machine.
PREFERRED_VOICES = (
    "Microsoft Ava",
    "Microsoft Jenny",
    "Microsoft Zira",
    "Microsoft Aria",
    "Microsoft David",
)


class TextToSpeech(QObject):
    """Thread-isolated Windows SAPI5 text-to-speech service."""

    speaking_started = pyqtSignal()
    speaking_finished = pyqtSignal()
    response_finished = pyqtSignal()
    speech_interrupted = pyqtSignal()
    level = pyqtSignal(float)
    error = pyqtSignal(str)

    def __init__(self, rate=168, volume=1.0):
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

    @staticmethod
    def _select_voice(engine):
        """Choose a natural installed Microsoft voice, otherwise use default."""
        voices = engine.getProperty("voices") or []
        if not voices:
            return None

        for preferred in PREFERRED_VOICES:
            preferred_lower = preferred.lower()
            for voice in voices:
                name = getattr(voice, "name", "") or ""
                if preferred_lower in name.lower():
                    return voice

        return voices[0]

    @staticmethod
    def _naturalize(text):
        """Prepare visual LLM output for speech without changing its meaning."""
        text = speech_safe_text(text)
        if not text:
            return ""

        # Remove UI-oriented symbols that sound unnatural when spoken.
        text = re.sub(r"^[\s•▪◦]+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*[|]+\s*", ", ", text)
        text = re.sub(r"\s{2,}", " ", text)

        # Give SAPI a little breathing room around sentence boundaries.
        text = re.sub(r"([.!?])\s+", r"\1  ", text)
        return text.strip()

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

                text = self._naturalize(item[1])
                if not text:
                    continue

                with self.engine_lock:
                    if self.stop_requested:
                        self.stop_requested = False
                        continue
                    self.currently_speaking = True

                engine = None
                interrupted = False

                try:
                    engine = pyttsx3.init("sapi5")
                    voice = self._select_voice(engine)

                    if voice is not None:
                        engine.setProperty("voice", voice.id)
                        print(f"[TTS] Voice: {voice.name}")

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

        safe_text = self._naturalize(text)
        if not safe_text:
            return

        print(f"[TTS] Queueing: {safe_text}")
        self.queue.put(("speak", safe_text))

    def stop_speaking(self):
        with self.lock:
            self.buffer = ""

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
