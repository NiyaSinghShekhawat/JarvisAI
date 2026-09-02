import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QPushButton

from frontend.window import JarvisWindow
from frontend.styles import APP_STYLE
from voice.text_to_speech import TextToSpeech
from voice.speech_sanitizer import speech_safe_text

# Runtime UI/voice extensions.
import frontend.interrupt  # noqa: F401,E402


# ============================================================
# TTS SAFETY PROTOCOL
# ============================================================
_original_finish_response = TextToSpeech.finish_response


def _safe_finish_response(self):
    with self.lock:
        self.buffer = speech_safe_text(self.buffer)
    _original_finish_response(self)


TextToSpeech.finish_response = _safe_finish_response


# ============================================================
# PERSISTENT VOICE INPUT
# ============================================================
# Voice mode is now a conversation mode rather than a one-shot recording.
# Once enabled, Jarvis keeps opening the microphone for the next utterance
# automatically. That means:
#   1. User speaks -> Jarvis processes it.
#   2. Jarvis speaks -> microphone remains available.
#   3. User can interrupt Jarvis at any point with another command.
#   4. If the user says nothing, Jarvis simply waits for the next command.
#   5. The mode only stops when the user explicitly toggles voice OFF.
_original_window_init = JarvisWindow.__init__
_original_activate_voice = JarvisWindow.activate_voice
_original_voice_finished = JarvisWindow.voice_finished
_original_handle_voice_transcript = JarvisWindow.handle_voice_transcript
_original_handle_voice_error = JarvisWindow.handle_voice_error


def _find_voice_button(self):
    for button in self.findChildren(QPushButton):
        if button.toolTip() in (
            "Voice input",
            "Keep voice input on",
            "Turn voice input off",
        ):
            return button
    return None


def _set_voice_button_state(self, enabled):
    button = getattr(self, "voice_toggle_button", None)
    if button is None:
        return

    button.setToolTip("Turn voice input off" if enabled else "Keep voice input on")
    button.setStyleSheet(
        """
        QPushButton {
            color: #00E89A;
            font-size: 16px;
            border-radius: 17px;
            background: rgba(0, 232, 154, 18);
            border: 1px solid rgba(0, 232, 154, 75);
        }
        QPushButton:hover {
            color: #4DFFC0;
            background: rgba(0, 232, 154, 32);
            border: 1px solid rgba(0, 232, 154, 130);
        }
        """
        if enabled
        else
        """
        QPushButton {
            color: rgba(145, 180, 205, 180);
            font-size: 16px;
            border-radius: 17px;
            background: transparent;
        }
        QPushButton:hover {
            color: #29B6FF;
            background: rgba(0, 140, 255, 25);
        }
        QPushButton:pressed {
            background: rgba(0, 140, 255, 45);
        }
        """
    )
    button.style().unpolish(button)
    button.style().polish(button)


def _stop_voice_capture(self):
    thread = getattr(self, "voice_thread", None)
    worker = getattr(self, "voice_worker", None)

    if worker is not None:
        worker.stop()

    if thread is not None and thread.isRunning():
        thread.quit()
        thread.wait(1000)

    self.voice_thread = None
    self.voice_worker = None


def _turn_voice_off(self):
    self.voice_mode_enabled = False
    self._stop_voice_capture()
    self.orb.set_audio_level(0.0)

    if self.jarvis_mode == "full" and self.orb.state == "listening":
        self.orb.set_state("idle")
        self.status.set_status("●  IDLE", "#527086")
        self.interpreted_label.hide()

    self._set_voice_button_state(False)
    print("[JARVIS] Continuous voice input OFF.")


def _toggle_voice_input(self):
    if getattr(self, "voice_mode_enabled", False):
        self._turn_voice_off()
        return

    self.voice_mode_enabled = True
    self._set_voice_button_state(True)
    print("[JARVIS] Continuous voice input ON.")
    self._start_voice_capture()


def _start_voice_capture(self):
    if not getattr(self, "voice_mode_enabled", False):
        return

    if self.voice_thread is not None and self.voice_thread.isRunning():
        return

    # VoiceWorker still records one utterance at a time. The patched
    # voice_finished() starts the next utterance only after the previous
    # QThread has fully stopped and the other microphone users are idle.
    _original_activate_voice(self)


def _persistent_activate_voice(self):
    # Wake word, clap, and the microphone button all enter persistent mode.
    self.voice_mode_enabled = True
    self._set_voice_button_state(True)
    self._start_voice_capture()


def _persistent_voice_finished(self):
    _original_voice_finished(self)

    if not getattr(self, "voice_mode_enabled", False):
        return

    # Lifecycle coordination is installed after this module and replaces
    # this method with a guarded scheduler. Keep this fallback for imports
    # that do not load the lifecycle extension.
    QTimer.singleShot(80, self._start_voice_capture)


def _persistent_handle_voice_transcript(self, text):
    # The existing handler stops TTS before submitting the new command.
    # Because voice_mode_enabled stays true, the lifecycle manager starts
    # another capture when all other workers have released the microphone.
    _original_handle_voice_transcript(self, text)


def _persistent_handle_voice_error(self, error):
    _original_handle_voice_error(self, error)
    if getattr(self, "voice_mode_enabled", False):
        QTimer.singleShot(500, self._start_voice_capture)


def _persistent_window_init(self):
    _original_window_init(self)

    self.voice_mode_enabled = False
    self.voice_toggle_button = _find_voice_button(self)

    if self.voice_toggle_button is not None:
        try:
            self.voice_toggle_button.clicked.disconnect()
        except TypeError:
            pass

        self.voice_toggle_button.clicked.connect(self.toggle_voice_input)
        self._set_voice_button_state(False)


JarvisWindow.__init__ = _persistent_window_init
JarvisWindow.activate_voice = _persistent_activate_voice
JarvisWindow.voice_finished = _persistent_voice_finished
JarvisWindow.handle_voice_transcript = _persistent_handle_voice_transcript
JarvisWindow.handle_voice_error = _persistent_handle_voice_error
JarvisWindow._start_voice_capture = _start_voice_capture
JarvisWindow._stop_voice_capture = _stop_voice_capture
JarvisWindow._turn_voice_off = _turn_voice_off
JarvisWindow.toggle_voice_input = _toggle_voice_input
JarvisWindow._set_voice_button_state = _set_voice_button_state

# Final lifecycle patch: this must run after the persistent-voice monkeypatches
# above so it can coordinate STT, stop-word detection, LLM, and TTS ownership
# of the shared microphone without changing the existing voice architecture.
from frontend.voice_lifecycle import install_voice_lifecycle  # noqa: E402

install_voice_lifecycle()


def main():
    app = QApplication(sys.argv)

    app.setApplicationName("Jarvis")
    app.setStyleSheet(APP_STYLE)

    window = JarvisWindow()

    window.showFullScreen()
    window.raise_()
    window.activateWindow()

    # Passive wake detection remains available while continuous voice mode
    # is OFF. Saying the wake phrase still activates persistent voice mode.
    window.start_wake_listener()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
