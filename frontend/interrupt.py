"""Runtime additions for Jarvis interruption and orb presentation."""

import math

from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient, QFont

from frontend.window import JarvisWindow, JarvisOrb
from voice.wake_word import StopWordWorker


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
    orb_gradient.setColorAt(
        0.78,
        QColor(primary.red(), primary.green(), primary.blue(), 35),
    )
    orb_gradient.setColorAt(1.0, QColor("#02070D"))

    painter.setBrush(orb_gradient)
    painter.setPen(QPen(
        QColor(primary.red(), primary.green(), primary.blue(), 230),
        1,
    ))
    painter.drawEllipse(center, dynamic_radius, dynamic_radius)

    inner_radius = dynamic_radius * 0.65
    inner_gradient = QRadialGradient(center, inner_radius)
    inner_gradient.setColorAt(
        0.0,
        QColor(primary.red(), primary.green(), primary.blue(), 22),
    )
    inner_gradient.setColorAt(
        1.0,
        QColor(primary.red(), primary.green(), primary.blue(), 0),
    )

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(inner_gradient)
    painter.drawEllipse(center, inner_radius, inner_radius)

    painter.setPen(QColor(220, 238, 255, 235))
    font = QFont("Segoe UI", 8)
    font.setWeight(QFont.Weight.Light)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
    painter.setFont(font)

    text = "J A R V I S"
    rect = painter.boundingRect(
        0,
        0,
        self.width(),
        self.height(),
        Qt.AlignmentFlag.AlignCenter,
        text,
    )
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


def _patched_window_init(self):
    _original_window_init(self)
    self.stop_worker = None
    self.response_cancelled = False


def _start_stop_listener(self):
    if self.stop_worker is not None and self.stop_worker.isRunning():
        return

    self.stop_worker = StopWordWorker()
    self.stop_worker.stop_detected.connect(self.handle_stop_command)
    self.stop_worker.error.connect(
        lambda error: print(f"[STOP] Listener error: {error}")
    )
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
    # Jarvis may finish generating the current answer after the user says
    # "Jarvis stop". Never feed those late tokens back into TTS/UI.
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
        QTimer.singleShot(
            700,
            lambda: self.status.set_status("●  IDLE", "#527086")
        )
    else:
        self.status.hide()
        self.interpreted_label.hide()
        self.response_label.hide()
        self.input.hide()
        QTimer.singleShot(400, self.start_wake_listener)


def _patched_tts_response_finished(self):
    # Stop command listening before the original handler can restart
    # passive wake listening in orb mode.
    self._stop_stop_listener()
    _original_tts_response_finished(self)


def _patched_show_orb_mode(self):
    _original_show_orb_mode(self)

    # The orb is now 210x210 instead of the old 150x150.
    self.setMaximumSize(230, 230)
    self.resize(230, 230)

    screen = self.screen()
    if screen is None:
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()

    geometry = screen.availableGeometry()
    margin = 8

    self.move(
        geometry.left() + margin,
        geometry.bottom() - self.height() - margin,
    )


def _patched_handle_error(self, error):
    self._stop_stop_listener()
    _original_handle_error(self, error)


JarvisWindow.__init__ = _patched_window_init
JarvisWindow.start_worker = _patched_start_worker
JarvisWindow.add_response_token = _patched_add_response_token
JarvisWindow.handle_response = _patched_handle_response
JarvisWindow.handle_stop_command = _handle_stop_command
JarvisWindow._start_stop_listener = _start_stop_listener
JarvisWindow._stop_stop_listener = _stop_stop_listener
JarvisWindow._stop_listener_finished = _stop_listener_finished
JarvisWindow.tts_response_finished = _patched_tts_response_finished
JarvisWindow.show_orb_mode = _patched_show_orb_mode
JarvisWindow.handle_error = _patched_handle_error
