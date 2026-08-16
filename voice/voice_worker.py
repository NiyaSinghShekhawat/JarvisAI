from PyQt6.QtCore import QThread, pyqtSignal

from voice.speech_to_text import SpeechToText


class VoiceWorker(QThread):
    """
    Background worker for Jarvis voice input.

    Pipeline:

        Microphone
            ↓
        SpeechToText
            ↓
        VoiceWorker
            ↓
        transcript signal
            ↓
        JarvisWindow
    """

    # ========================================================
    # SIGNALS
    # ========================================================

    transcript = pyqtSignal(str)

    level = pyqtSignal(float)

    error = pyqtSignal(str)

    finished = pyqtSignal()

    # Some existing UI code may use `failed`
    # instead of `error`, so provide both.
    failed = pyqtSignal(str)

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self, parent=None):
        super().__init__(parent)

        self.speech_to_text = SpeechToText()

        self._stop_requested = False

    # ========================================================
    # MICROPHONE LEVEL
    # ========================================================

    def on_audio_level(self, value: float):
        """
        Called continuously by SpeechToText while recording.
        """

        if self._stop_requested:
            return

        self.level.emit(value)

    # ========================================================
    # RUN
    # ========================================================

    def run(self):
        """
        Runs inside the QThread.

        This prevents microphone recording and transcription
        from blocking the PyQt UI thread.
        """

        try:

            self._stop_requested = False

            # -----------------------------------------------
            # RECORD
            # -----------------------------------------------

            audio = (
                self.speech_to_text
                .record_until_silence(
                    level_callback=self.on_audio_level
                )
            )

            if self._stop_requested:
                return

            # -----------------------------------------------
            # Nothing was spoken
            # -----------------------------------------------

            if not audio:

                self.finished.emit()

                return

            # -----------------------------------------------
            # TRANSCRIBE
            # -----------------------------------------------

            text = (
                self.speech_to_text
                .transcribe(audio)
            )

            if self._stop_requested:
                return

            # -----------------------------------------------
            # SEND TRANSCRIPT TO UI
            # -----------------------------------------------

            if text:

                self.transcript.emit(text)

            self.finished.emit()

        except Exception as e:

            message = str(e)

            print(
                f"[VoiceWorker ERROR] {message}"
            )

            self.error.emit(message)

            self.failed.emit(message)

            self.finished.emit()

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):
        """
        Request the worker to stop.

        Note:
        The current microphone recorder checks this only
        between recording stages. Full immediate microphone
        interruption can be added later.
        """

        self._stop_requested = True