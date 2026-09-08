from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from voice.speech_to_text import SpeechToText


class VoiceWorker(QObject):
    """Microphone capture worker owned by a dedicated QThread."""

    transcript = pyqtSignal(str)
    level = pyqtSignal(float)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.speech_to_text = SpeechToText()
        self._stop_requested = False

    def on_audio_level(self, value: float):
        if not self._stop_requested:
            self.level.emit(value)

    @pyqtSlot()
    def run(self):
        try:
            self._stop_requested = False

            audio = self.speech_to_text.record_until_silence(
                level_callback=self.on_audio_level,
                stop_callback=lambda: self._stop_requested,
            )

            if self._stop_requested:
                self.finished.emit()
                return

            if not audio:
                self.finished.emit()
                return

            text = self.speech_to_text.transcribe(audio)

            if self._stop_requested:
                self.finished.emit()
                return

            if text:
                self.transcript.emit(text)

            self.finished.emit()

        except Exception as e:
            message = str(e)
            print(f"[VoiceWorker ERROR] {message}")
            if not self._stop_requested:
                self.error.emit(message)
                self.failed.emit(message)
            self.finished.emit()

    def stop(self):
        """Request capture cancellation; the STT loop exits promptly."""
        self._stop_requested = True
