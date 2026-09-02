"""Safe voice-worker lifecycle coordination for continuous Jarvis voice mode."""

from PyQt6.QtCore import QTimer

import frontend.interrupt as interrupt_runtime
from frontend.window import JarvisWindow


_INSTALLED = False


def install_voice_lifecycle():
    """Install lifecycle guards after the normal runtime monkeypatches exist."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    app_module = __import__("frontend.app", fromlist=["_original_voice_finished"])

    original_start_worker = interrupt_runtime._original_start_worker
    original_voice_finished = app_module._original_voice_finished
    original_handle_voice_error = app_module._original_handle_voice_error
    original_tts_started = JarvisWindow.tts_started
    original_tts_response_finished = JarvisWindow.tts_response_finished
    original_handle_response = JarvisWindow.handle_response

    def schedule_voice_capture(self, delay=80):
        """Wait until every other microphone/response worker is finished."""
        if not getattr(self, "voice_mode_enabled", False):
            return

        def attempt():
            if not getattr(self, "voice_mode_enabled", False):
                return

            voice_thread = getattr(self, "voice_thread", None)
            if voice_thread is not None and voice_thread.isRunning():
                QTimer.singleShot(100, attempt)
                return

            stop_worker = getattr(self, "stop_worker", None)
            if stop_worker is not None and stop_worker.isRunning():
                QTimer.singleShot(100, attempt)
                return

            response_thread = getattr(self, "worker_thread", None)
            if response_thread is not None and response_thread.isRunning():
                QTimer.singleShot(100, attempt)
                return

            if getattr(self.tts, "currently_speaking", False):
                QTimer.singleShot(100, attempt)
                return

            self._start_voice_capture()

        QTimer.singleShot(delay, attempt)

    def safe_start_worker(self, message):
        """Start LLM work without opening a second microphone listener."""
        self.response_cancelled = False
        self._stop_stop_listener()
        original_start_worker(self, message)

    def safe_start_voice_capture(self):
        """Never create a new VoiceWorker while another audio worker is alive."""
        if not getattr(self, "voice_mode_enabled", False):
            return

        voice_thread = getattr(self, "voice_thread", None)
        if voice_thread is not None:
            if voice_thread.isRunning():
                return
            self.voice_thread = None
            self.voice_worker = None

        stop_worker = getattr(self, "stop_worker", None)
        if stop_worker is not None and stop_worker.isRunning():
            QTimer.singleShot(100, self._start_voice_capture)
            return

        if getattr(self.tts, "currently_speaking", False):
            return

        # Use the original window implementation so this lifecycle layer does
        # not recursively call the persistent-voice monkeypatch.
        app_module._original_activate_voice(self)

    def safe_voice_finished(self):
        """Start the next capture only after Qt has fully stopped this thread."""
        original_voice_finished(self)
        self._schedule_voice_capture(80)

    def safe_voice_error(self, error):
        """Retry microphone errors without stacking QThreads."""
        original_handle_voice_error(self, error)
        if getattr(self, "voice_mode_enabled", False):
            self._schedule_voice_capture(500)

    def safe_tts_started(self):
        """Run the stop-word listener only while no STT capture owns the mic."""
        original_tts_started(self)
        if getattr(self, "voice_mode_enabled", False):
            # Continuous STT is intentionally paused during speech, so the
            # stop-word listener is the sole microphone consumer here.
            self._start_stop_listener()

    def safe_tts_response_finished(self):
        """Release the stop listener, then resume continuous voice capture."""
        self._stop_stop_listener()
        original_tts_response_finished(self)
        self._schedule_voice_capture(80)

    def safe_handle_response(self, result):
        """Resume voice mode after visual answers that do not use TTS."""
        original_handle_response(self, result)
        if getattr(self, "voice_mode_enabled", False) and getattr(self, "visual_response_mode", False):
            self._schedule_voice_capture(120)

    JarvisWindow.start_worker = safe_start_worker
    JarvisWindow._start_voice_capture = safe_start_voice_capture
    JarvisWindow.voice_finished = safe_voice_finished
    JarvisWindow.handle_voice_error = safe_voice_error
    JarvisWindow.tts_started = safe_tts_started
    JarvisWindow.tts_response_finished = safe_tts_response_finished
    JarvisWindow.handle_response = safe_handle_response
    JarvisWindow._schedule_voice_capture = schedule_voice_capture


__all__ = ["install_voice_lifecycle"]
