"""Runtime additions for Jarvis interruption, orb presentation, mail UI, personality controls, and sci-fi HUD."""

import math

from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient, QFont
from PyQt6.QtWidgets import QPushButton

from frontend.window import JarvisWindow, JarvisOrb
from frontend.email_viewer import EmailViewer
from frontend.hud import JarvisHUD
from voice.wake_word import StopWordWorker
from backend.brain.router import set_roast_mode, is_roast_mode


# ============================================================
# LARGER ORB
# ============================================================

_original_orb_init = JarvisOrb.__init__


def _larger_orb_init(self):
    _original_orb_init(self)
    self.setFixedSize(210, 210)


JarvisOrb.__init__ = _larger_orb_init


def _larger_orb_paint(self, event):
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    center = QPointF(self.width() / 2, self.height() / 2)
    base_radius = 50

    if self.state == "listening":
        primary = QColor("#00E89A")
        activity = self.audio_level
    elif self.state == "speaking":
        primary = QColor("#29B6FF")
        activity = self.speaking_level
    elif self.state == "processing":
        primary = QColor("#008CFF")
        activity = (math.sin(self.phase * 2.2) * 0.5 + 0.5) * 0.18
    else:
        primary = QColor("#008CFF")
        activity = (math.sin(self.phase * 1.5) * 0.5 + 0.5) * 0.08

    dynamic_radius = base_radius + activity * 10
    glow_radius = dynamic_radius * 1.75

    glow = QRadialGradient(center, glow_radius)
    glow.setColorAt(0.0, QColor(primary.red(), primary.green(), primary.blue(), 80))
    glow.setColorAt(0.35, QColor(primary.red(), primary.green(), primary.blue(), 32))
    glow.setColorAt(0.70, QColor(primary.red(), primary.green(), primary.blue(), 8))
    glow.setColorAt(1.0, QColor(primary.red(), primary.green(), primary.blue(), 0))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(center, glow_radius, glow_radius)

    ring_pen = QPen(QColor(primary.red(), primary.green(), primary.blue(), 210))
    ring_pen.setWidth(1)
    painter.setPen(ring_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(center, dynamic_radius + 2, dynamic_radius + 2)

    orb_gradient = QRadialGradient(
        center - QPointF(dynamic_radius * 0.30, dynamic_radius * 0.30),
        dynamic_radius * 1.4,
    )
    orb_gradient.setColorAt(0.0, QColor("#0A263A"))
    orb_gradient.setColorAt(0.45, QColor("#041521"))
    orb_gradient.setColorAt(0.78, QColor(primary.red(), primary.green(), primary.blue(), 35))
    orb_gradient.setColorAt(1.0, QColor("#02070D"))

    painter.setBrush(orb_gradient)
    painter.setPen(QPen(QColor(primary.red(), primary.green(), primary.blue(), 230), 1))
    painter.drawEllipse(center, dynamic_radius, dynamic_radius)

    inner_radius = dynamic_radius * 0.65
    inner_gradient = QRadialGradient(center, inner_radius)
    inner_gradient.setColorAt(0.0, QColor(primary.red(), primary.green(), primary.blue(), 22))
    inner_gradient.setColorAt(1.0, QColor(primary.red(), primary.green(), primary.blue(), 0))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(inner_gradient)
    painter.drawEllipse(center, inner_radius, inner_radius)

    painter.setPen(QColor(220, 238, 255, 235))
    font = QFont("Segoe UI", 8)
    font.setWeight(QFont.Weight.Light)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
    painter.setFont(font)

    text = "J A R V I S"
    rect = painter.boundingRect(0, 0, self.width(), self.height(), Qt.AlignmentFlag.AlignCenter, text)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    painter.end()


JarvisOrb.paintEvent = _larger_orb_paint


# ============================================================
# WINDOW PATCHES
# ============================================================

_original_window_init = JarvisWindow.__init__
_original_start_worker = JarvisWindow.start_worker
_original_add_response_token = JarvisWindow.add_response_token
_original_handle_response = JarvisWindow.handle_response
_original_handle_error = JarvisWindow.handle_error
_original_tts_response_finished = JarvisWindow.tts_response_finished
_original_show_orb_mode = JarvisWindow.show_orb_mode


def _open_email_viewer(self):
    """Open the native Gmail reader without leaving the Jarvis UI."""
    if getattr(self, "email_viewer", None) is None:
        self.email_viewer = EmailViewer(self)

    self.email_viewer.show()
    self.email_viewer.raise_()
    self.email_viewer.activateWindow()


def _connect_mail_button(self):
    """Find the existing Gmail icon and connect it to the mail reader."""
    for button in self.findChildren(__import__("PyQt6.QtWidgets", fromlist=["QPushButton"]).QPushButton):
        if button.toolTip() == "Gmail":
            try:
                button.clicked.disconnect()
            except TypeError:
                pass
            button.clicked.connect(self.open_email_viewer)
            return


def _add_roast_toggle(self):
    """Add a small persistent personality toggle to the bottom bar."""
    if getattr(self, "roast_button", None) is not None:
        return

    self.roast_button = QPushButton("ROAST")
    self.roast_button.setCheckable(True)
    self.roast_button.setChecked(is_roast_mode())
    self.roast_button.setFixedHeight(30)
    self.roast_button.setToolTip("Toggle Jarvis Roast Mode")
    self.roast_button.setStyleSheet(
        """
        QPushButton {
            color: #71899F;
            background: transparent;
            border: 1px solid rgba(113,137,159,70);
            border-radius: 15px;
            padding: 0 12px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            color: #FFAA44;
            border-color: rgba(255,170,68,150);
            background: rgba(255,170,68,15);
        }
        QPushButton:checked {
            color: #FFAA44;
            border-color: rgba(255,170,68,190);
            background: rgba(255,170,68,20);
        }
        """
    )

    def toggle_roast(checked):
        set_roast_mode(checked)
        if self.jarvis_mode == "full":
            self.status.set_status(
                "●  ROAST MODE" if checked else "●  IDLE",
                "#FFAA44" if checked else "#527086",
            )

    self.roast_button.toggled.connect(toggle_roast)
    self.bottom.insertWidget(0, self.roast_button)


def _install_hud(self):
    """Install the non-interactive sci-fi command-center overlay."""
    if getattr(self, "jarvis_hud", None) is not None:
        return

    self.jarvis_hud = JarvisHUD(self)
    self.jarvis_hud.sync_geometry()
    self.jarvis_hud.lower()


def _patched_window_init(self):
    _original_window_init(self)
    self.stop_worker = None
    self.response_cancelled = False
    self.email_viewer = None
    self.open_email_viewer = lambda: _open_email_viewer(self)
    _add_roast_toggle(self)
    _install_hud(self)
    QTimer.singleShot(0, lambda: _connect_mail_button(self))


def _start_stop_listener(self):
    if self.stop_worker is not None and self.stop_worker.isRunning():
        return

    self.stop_worker = StopWordWorker()
    self.stop_worker.stop_detected.connect(self.handle_stop_command)
    self.stop_worker.error.connect(lambda error: print(f"[STOP] Listener error: {error}"))
    self.stop_worker.finished.connect(self._stop_listener_finished)
    self.stop_worker.start()


def _stop_stop_listener(self):
    worker = self.stop_worker
    if worker is None:
        return

    if worker.isRunning():
        worker.stop()
        worker.wait(1000)

    if self.stop_worker is worker:
        self.stop_worker = None


def _stop_listener_finished(self):
    worker = self.sender()
    if self.stop_worker is worker:
        self.stop_worker = None


def _patched_start_worker(self, message):
    self.response_cancelled = False
    _original_start_worker(self, message)
    self._start_stop_listener()


def _patched_add_response_token(self, token):
    if self.response_cancelled:
        return
    _original_add_response_token(self, token)


def _patched_handle_response(self, result):
    if self.response_cancelled:
        self.tts.stop_speaking()
        return
    _original_handle_response(self, result)


def _handle_stop_command(self):
    if self.response_cancelled:
        return

    print("[JARVIS] STOP command received.")
    self.response_cancelled = True
    self._stop_stop_listener()
    self.tts.stop_speaking()

    self.orb.set_speaking_level(0.0)
    self.orb.set_state("idle")

    if self.jarvis_mode == "full":
        self.status.set_status("●  STOPPED", "#FFAA44")
        self.response_label.hide()
        QTimer.singleShot(700, lambda: self.status.set_status("●  ROAST MODE" if is_roast_mode() else "●  IDLE", "#FFAA44" if is_roast_mode() else "#527086"))
    else:
        self.status.hide()
        self.interpreted_label.hide()
        self.response_label.hide()
        self.input.hide()
        QTimer.singleShot(400, self.start_wake_listener)


def _patched_tts_response_finished(self):
    self._stop_stop_listener()
    _original_tts_response_finished(self)


def _patched_show_orb_mode(self):
    _original_show_orb_mode(self)

    self.setMaximumSize(230, 230)
    self.resize(230, 230)

    screen = self.screen()
    if screen is None:
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()

    geometry = screen.availableGeometry()
    margin = 8
    self.move(geometry.left() + margin, geometry.bottom() - self.height() - margin)


def _patched_handle_error(self, error):
    self._stop_stop_listener()
    _original_handle_error(self, error)


def _patched_handle_wake(self, wake_type):
    """Wake triggers switch to the already-running Jarvis application."""
    mode = "FULLSCREEN" if wake_type in ("clap", "wake_up") else "FULLSCREEN"
    print(f"[JARVIS] Wake event: {wake_type} -> {mode}")
    self.stop_wake_listener()
    self.show_fullscreen_mode()
    self.activate_voice()


def _show_fullscreen_mode(self):
    """Restore the full UI and occupy the available screen."""
    self.jarvis_mode = "full"

    if self.orb_container is not None:
        self.orb_container.hide()
        self.orb.setParent(self.full_central)
        self.orb_container.deleteLater()
        self.orb_container = None

    self.setCentralWidget(self.full_central)
    self.full_central.show()

    self.status.show()
    self.interpreted_label.hide()
    self.response_label.hide()
    self.input.show()

    self.setMinimumSize(0, 0)
    self.setMaximumSize(16777215, 16777215)
    self.setWindowFlags(Qt.WindowType.Window)
    self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
    self.showFullScreen()
    self.raise_()
    self.activateWindow()

    if getattr(self, "jarvis_hud", None) is not None:
        self.jarvis_hud.show()
        self.jarvis_hud.lower()
        self.jarvis_hud.sync_geometry()

    print("[JARVIS] Fullscreen interface active.")


JarvisWindow.__init__ = _patched_window_init
JarvisWindow.start_worker = _patched_start_worker
JarvisWindow.add_response_token = _patched_add_response_token
JarvisWindow.handle_response = _patched_handle_response
JarvisWindow.handle_wake = _patched_handle_wake
JarvisWindow.show_fullscreen_mode = _show_fullscreen_mode
JarvisWindow.handle_stop_command = _handle_stop_command
JarvisWindow._start_stop_listener = _start_stop_listener
JarvisWindow._stop_stop_listener = _stop_stop_listener
JarvisWindow._stop_listener_finished = _stop_listener_finished
JarvisWindow.tts_response_finished = _patched_tts_response_finished
JarvisWindow.show_orb_mode = _patched_show_orb_mode
JarvisWindow.handle_error = _patched_handle_error
