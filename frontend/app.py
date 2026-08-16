import sys

from PyQt6.QtWidgets import QApplication

from frontend.window import JarvisWindow
from frontend.styles import APP_STYLE


def main():
    app = QApplication(sys.argv)

    app.setApplicationName("Jarvis")
    app.setStyleSheet(APP_STYLE)

    window = JarvisWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()