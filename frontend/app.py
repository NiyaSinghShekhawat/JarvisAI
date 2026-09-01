import sys

from PyQt6.QtWidgets import QApplication

from frontend.window import JarvisWindow
from frontend.styles import APP_STYLE
from voice.text_to_speech import TextToSpeech
from voice.speech_sanitizer import speech_safe_text

# Runtime UI/voice extensions. This patches the existing window without
# disturbing the core window implementation while the hands-free controls
# are being developed.
import frontend.interrupt  # noqa: F401,E402


# ============================================================
# TTS SAFETY PROTOCOL
# ============================================================
# The UI should still display clickable URLs, but SAPI must never speak
# raw URLs or markdown formatting. We sanitize the complete response at
# the final TTS boundary so streaming tokens cannot split a URL and bypass
# the filter.
_original_finish_response = TextToSpeech.finish_response


def _safe_finish_response(self):
    with self.lock:
        self.buffer = speech_safe_text(self.buffer)
    _original_finish_response(self)


TextToSpeech.finish_response = _safe_finish_response


def main():

    app = QApplication(sys.argv)

    app.setApplicationName("Jarvis")
    app.setStyleSheet(APP_STYLE)

    window = JarvisWindow()

    # Start passive wake detection.
    # Jarvis remains invisible until activated.
    window.start_wake_listener()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()
