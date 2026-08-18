import sys

from PyQt6.QtWidgets import QApplication

from frontend.window import JarvisWindow
from frontend.styles import APP_STYLE

# Runtime UI/voice extensions. This patches the existing window without
# disturbing the core window implementation while the hands-free controls
# are being developed.
import frontend.interrupt  # noqa: F401,E402


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
