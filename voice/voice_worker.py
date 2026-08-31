from PyQt6.QtCore import QThread, pyqtSignal

from voice.speech_to_text import SpeechToText


class VoiceWorker(QThread):
    """Background worker for Jarvis voice input."""

    transcript = pyqtSignal(str)
    level = pyqtSignal(float)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # SpeechToText uses the same explicit microphone configuration as the
        # passive wake listener, so both stages hear the same physical mic.
        self.speech_to_text = SpeechToText()
        self._stop_requested = False

    def on_audio_level(self, value: float):
        if not self._stop_requested:
            self.level.emit(value)

    def run(self):
        try:
            self._stop_requested = False

            audio = self.speech_to_text.record_until_silence(
                level_callback=self.on_audio_level
            )

            if self._stop_requested:
                return

            if not audio:
                self.finished.emit()
                return

            text = self.speech_to_text.transcribe(audio)

            if self._stop_requested:
                return

            if text:
                self.transcript.emit(text)

            self.finished.emit()

        except Exception as e:
            message = str(e)
            print(f"[VoiceWorker ERROR] {message}")
            self.error.emit(message)
            self.failed.emit(message)
            self.finished.emit()

    def stop(self):
        self._stop_requested = True
