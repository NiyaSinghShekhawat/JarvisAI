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

    app_module = __import__("frontend.app", fromlist=["_start_voice_capture"])

    original_start_worker = interrupt_runtime._original_start_worker
    original_start_voice_capture = app_module._start_voice_capture
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
        """Start the real STT worker without re-entering the monkeypatch chain."""
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

        # IMPORTANT: call the concrete worker-start implementation captured
        # before this lifecycle wrapper replaced _start_voice_capture. Never
        # route through activate_voice here; persistent activate_voice itself
        # delegates to _start_voice_capture and would recurse forever.
        original_start_voice_capture(self)

    def safe_voice_finished(self):
        """Do not reopen the microphone while Jarvis is processing or speaking."""
        original_voice_finished(self)
        if not getattr(self, "voice_mode_enabled", False):
            return

        # Normal answers are followed by TTS. Waiting for response_finished is
        # important: otherwise STT can reopen the shared microphone just before
        # the stop-word listener starts, creating two competing InputStreams.
        if getattr(self, "visual_response_mode", False):
            self._schedule_voice_capture(120)

    def safe_voice_error(self, error):
        """Retry microphone errors without stacking QThreads."""
        original_handle_voice_error(self, error)
        if getattr(self, "voice_mode_enabled", False):
            self._schedule_voice_capture(500)

    def safe_tts_started(self):
        """Run the stop-word listener only while no STT capture owns the mic."""
        original_tts_started(self)
        if getattr(self, "voice_mode_enabled", False):
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
