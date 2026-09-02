import gc
import json
import os
import queue
import re
import subprocess
import sys
import threading
import winsound

from PyQt6.QtCore import QObject, pyqtSignal

from voice.speech_sanitizer import speech_safe_text


class TextToSpeech(QObject):
    """
    Jarvis text-to-speech service.

    Primary:
        Kokoro-82M / am_adam, kept alive in a dedicated worker process.

    Fallback:
        Windows SAPI5 / pyttsx3.

    Kokoro is started and fully loaded once when the TTS worker starts. Normal
    speech interruptions never kill/reload the Kokoro process.
    """

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
        self.currently_speaking = False
        self.stop_requested = False

        self.kokoro_process = None
        self.kokoro_ready = threading.Event()
        self.kokoro_lock = threading.Lock()

        self.thread = threading.Thread(
            target=self._run,
            name="JarvisTTS",
            daemon=True,
        )
        self.thread.start()

    # ---------------------------------------------------------
    # Text preparation
    # ---------------------------------------------------------

    @staticmethod
    def _naturalize(text):
        """Prepare LLM output for natural speech."""
        text = speech_safe_text(text)
        if not text:
            return ""

        text = re.sub(r"^[\s•▪◦]+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*[|]+\s*", ", ", text)
        text = re.sub(r"\s{2,}", " ", text)
        text = re.sub(r"([.!?])\s+", r"\1  ", text)
        return text.strip()

    # ---------------------------------------------------------
    # Kokoro
    # ---------------------------------------------------------

    def _kokoro_python(self):
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        if os.name == "nt":
            return os.path.join(
                project_root,
                "kokoro-venv",
                "Scripts",
                "python.exe",
            )

        return os.path.join(
            project_root,
            "kokoro-venv",
            "bin",
            "python",
        )

    def _kokoro_script(self):
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        return os.path.join(project_root, "kokoro_worker.py")

    def _start_kokoro(self):
        """Start Kokoro and wait until its model is completely loaded."""
        with self.kokoro_lock:
            if self.kokoro_process is not None:
                if self.kokoro_process.poll() is None and self.kokoro_ready.is_set():
                    return True

                if self.kokoro_process.poll() is not None:
                    self.kokoro_process = None
                    self.kokoro_ready.clear()

            python_path = self._kokoro_python()
            worker_path = self._kokoro_script()

            if not os.path.exists(python_path):
                print(f"[KOKORO] Python not found: {python_path}")
                return False

            if not os.path.exists(worker_path):
                print(f"[KOKORO] Worker not found: {worker_path}")
                return False

            try:
                print("[KOKORO] Starting persistent worker...")
                self.kokoro_ready.clear()

                self.kokoro_process = subprocess.Popen(
                    [python_path, worker_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=sys.stderr,
                    text=True,
                    bufsize=1,
                )

                print("[KOKORO] Worker started. Loading model...")

                response = self.kokoro_process.stdout.readline()
                if not response:
                    raise RuntimeError(
                        "Kokoro worker exited before becoming ready."
                    )

                data = json.loads(response)
                if not data.get("ready"):
                    raise RuntimeError(
                        data.get("error", "Kokoro worker did not report ready.")
                    )

                self.kokoro_ready.set()
                print("[KOKORO] Model ready. Future speech will start immediately.")
                return True

            except Exception as e:
                print(f"[KOKORO ERROR] Could not initialize worker: {e}")
                self._kill_kokoro()
                return False

    def _kokoro_synthesize(self, text):
        """Send text to the already-loaded Kokoro worker."""
        if not self._start_kokoro():
            raise RuntimeError("Kokoro worker could not be started.")

        process = self.kokoro_process
        if process is None or process.stdin is None or process.stdout is None:
            raise RuntimeError("Kokoro worker pipes are unavailable.")

        request = json.dumps({
            "command": "speak",
            "text": text,
        })

        try:
            process.stdin.write(request + "\n")
            process.stdin.flush()

            response = process.stdout.readline()
            if not response:
                raise RuntimeError("Kokoro worker stopped unexpectedly.")

            data = json.loads(response)
            if "error" in data:
                # A synthesis error does not necessarily mean the worker died.
                raise RuntimeError(data["error"])

            audio_path = data.get("audio")
            if not audio_path:
                raise RuntimeError("Kokoro returned no audio path.")

            return audio_path

        except (BrokenPipeError, OSError, ValueError, json.JSONDecodeError) as e:
            # Only transport/protocol failures restart the worker. A normal
            # speech interruption must never kill the loaded model.
            if process.poll() is not None:
                self._kill_kokoro()
            raise RuntimeError(str(e)) from e

    def _kill_kokoro(self):
        """Terminate Kokoro only when the worker is actually unusable."""
        with self.kokoro_lock:
            process = self.kokoro_process
            self.kokoro_process = None
            self.kokoro_ready.clear()

            if process is None:
                return

            try:
                if process.stdin:
                    try:
                        process.stdin.close()
                    except Exception:
                        pass
                process.kill()
            except Exception:
                pass

            try:
                process.wait(timeout=1)
            except Exception:
                pass

    # ---------------------------------------------------------
    # Fallback SAPI
    # ---------------------------------------------------------

    @staticmethod
    def _sapi_speak(text, rate, volume):
        """Fallback Windows SAPI5 speech."""
        import pyttsx3

        engine = pyttsx3.init("sapi5")
        voices = engine.getProperty("voices") or []
        preferred = (
            "Microsoft David",
            "Microsoft Guy",
            "Microsoft Mark",
            "Microsoft Ryan",
            "Microsoft George",
        )

        selected = None
        for preferred_name in preferred:
            for voice in voices:
                name = getattr(voice, "name", "") or ""
                if preferred_name.lower() in name.lower():
                    selected = voice
                    break
            if selected:
                break

        if selected is None and voices:
            for voice in voices:
                if str(getattr(voice, "gender", "")).lower() == "male":
                    selected = voice
                    break

        if selected is None and voices:
            selected = voices[0]

        if selected:
            engine.setProperty("voice", selected.id)
            print(f"[TTS FALLBACK] Voice: {selected.name}")

        engine.setProperty("rate", rate)
        engine.setProperty("volume", volume)
        engine.say(text)
        engine.runAndWait()

        try:
            engine.stop()
        except Exception:
            pass

        del engine
        gc.collect()

    # ---------------------------------------------------------
    # Main worker
    # ---------------------------------------------------------

    def _run(self):
        print("[TTS] TTS worker started.")
        print("[TTS] Primary voice: Kokoro am_adam")
        print("[TTS] Fallback voice: Microsoft SAPI")

        # Preload Kokoro before the first response. This keeps model-loading
        # latency out of the first user question.
        kokoro_available = self._start_kokoro()
        if not kokoro_available:
            print("[TTS] Kokoro unavailable at startup; SAPI fallback enabled.")

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
                self.current_engine = None

            interrupted = False
            audio_path = None

            try:
                with self.engine_lock:
                    interrupted = self.stop_requested

                if interrupted:
                    continue

                print(f"[TTS] Speaking: {text}")
                self.speaking_started.emit()

                try:
                    audio_path = self._kokoro_synthesize(text)

                    with self.engine_lock:
                        interrupted = self.stop_requested
                        self.current_engine = "kokoro"

                    # If stop_speaking() happened while Kokoro was generating,
                    # discard the generated WAV instead of playing it.
                    if not interrupted:
                        print(f"[KOKORO] Playing: {audio_path}")
                        winsound.PlaySound(
                            audio_path,
                            winsound.SND_FILENAME,
                        )

                    with self.engine_lock:
                        interrupted = self.stop_requested

                except Exception as kokoro_error:
                    print(f"[KOKORO ERROR] {kokoro_error}")
                    print("[TTS] Falling back to Microsoft SAPI.")

                    with self.engine_lock:
                        interrupted = self.stop_requested

                    if not interrupted:
                        self.current_engine = "sapi"
                        self._sapi_speak(
                            text,
                            self.rate,
                            self.volume,
                        )

            except Exception as e:
                print(f"[TTS ERROR] {e}")
                self.error.emit(str(e))

            finally:
                with self.engine_lock:
                    self.currently_speaking = False
                    self.current_engine = None
                    self.stop_requested = False

                if audio_path:
                    try:
                        os.remove(audio_path)
                    except Exception:
                        pass

                self.level.emit(0.0)
                self.speaking_finished.emit()

                if interrupted:
                    print("[TTS] Speech interrupted.")
                    self.speech_interrupted.emit()
                else:
                    print("[TTS] Speech finished.")
                    self.response_finished.emit()

                gc.collect()

        self._kill_kokoro()
        print("[TTS] TTS worker stopped.")

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

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
            active = self.currently_speaking
            engine = self.current_engine

            if not active:
                self.stop_requested = False
                print("[TTS] No active speech. Pending speech cleared.")
                return

            # Keep this flag set even when Kokoro is currently synthesizing and
            # current_engine is None. The synthesis result will then be
            # discarded without killing/reloading the Kokoro worker.
            self.stop_requested = True

        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

        if engine not in (None, "kokoro"):
            # SAPI is interruptible through its engine object when available.
            try:
                if hasattr(engine, "stop"):
                    engine.stop()
            except Exception:
                pass

        print("[TTS] Current speech interrupted.")

    def shutdown(self):
        self.running = False
        self.stop_speaking()
        self.queue.put(None)

        if self.thread.is_alive():
            self.thread.join(timeout=2)

        self._kill_kokoro()
