import math

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QFont
from PyQt6.QtWidgets import QWidget


class JarvisHUD(QWidget):
    """Decorative sci-fi command-center layer for the Jarvis UI."""

    def __init__(self, window):
        super().__init__(window.full_central)
        self.window = window
        self.phase = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("JarvisHUD")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)

    def _tick(self):
        self.phase += 0.035
        self.update()

    def sync_geometry(self):
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())

    def _state(self):
        try:
            return self.window.orb.state
        except Exception:
            return "idle"

    def _accent(self):
        state = self._state()
        if state == "listening":
            return QColor("#00E89A")
        if state == "speaking":
            return QColor("#29B6FF")
        if state == "processing":
            return QColor("#008CFF")
        return QColor("#008CFF")

    def _panel(self, painter, rect, title, lines, accent):
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 55), 1))
        painter.setBrush(QColor(3, 14, 24, 145))
        painter.drawRoundedRect(rect, 8, 8)

        # Angular corner marks
        c = QColor(accent.red(), accent.green(), accent.blue(), 150)
        pen = QPen(c, 1)
        painter.setPen(pen)
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        mark = 10
        painter.drawLine(QPointF(x, y + mark), QPointF(x, y))
        painter.drawLine(QPointF(x, y), QPointF(x + mark, y))
        painter.drawLine(QPointF(x + w - mark, y), QPointF(x + w, y))
        painter.drawLine(QPointF(x + w, y), QPointF(x + w, y + mark))

        font = QFont("Consolas", 8)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        painter.setFont(font)
        painter.setPen(QColor(accent.red(), accent.green(), accent.blue(), 210))
        painter.drawText(QRectF(x + 12, y + 10, w - 24, 16), Qt.AlignmentFlag.AlignLeft, title)

        font2 = QFont("Consolas", 7)
        painter.setFont(font2)
        painter.setPen(QColor("#7892A6"))
        yy = y + 30
        for line in lines:
            painter.drawText(QRectF(x + 12, yy, w - 24, 13), Qt.AlignmentFlag.AlignLeft, line)
            yy += 14

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        accent = self._accent()
        alpha = 28 + int((math.sin(self.phase) + 1) * 7)

        # Faint technical grid
        pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), alpha), 1)
        painter.setPen(pen)
        step = 55
        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)

        # Horizontal scan line
        scan_y = int((math.sin(self.phase * 0.55) * 0.5 + 0.5) * max(1, h))
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 18), 1))
        painter.drawLine(0, scan_y, w, scan_y)

        # Top-left system panel
        self._panel(
            painter,
            QRectF(26, 72, 185, 92),
            "SYSTEM / CORE",
            [
                "● NEURAL CORE   ONLINE",
                "● MEMORY        ACTIVE",
                "● VOICE         READY",
                "● LINK          STABLE",
            ],
            accent,
        )

        # Top-right module panel
        self._panel(
            painter,
            QRectF(w - 211, 72, 185, 108),
            "MODULES",
            [
                "WEATHER       READY",
                "GMAIL         READY",
                "DRIVE         READY",
                "WEB           READY",
                "TOOLS         ARMED",
            ],
            accent,
        )

        # Left telemetry rail
        self._panel(
            painter,
            QRectF(26, h * 0.50 - 45, 185, 90),
            "TELEMETRY",
            [
                f"ACTIVITY   {int((math.sin(self.phase * 2) + 1) * 50):02d}%",
                "AUDIO      24.0 kHz",
                "ENGINE     GROQ",
                "MODEL      ONLINE",
            ],
            accent,
        )

        # Right activity rail
        state = self._state().upper()
        self._panel(
            painter,
            QRectF(w - 211, h * 0.50 - 45, 185, 90),
            "ACTIVITY",
            [
                f"STATE      {state}",
                "STREAM     ENABLED",
                "CONTEXT    ACTIVE",
                "SESSION    LIVE",
            ],
            accent,
        )

        # Bottom micro telemetry
        painter.setPen(QColor(accent.red(), accent.green(), accent.blue(), 120))
        font = QFont("Consolas", 7)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        painter.setFont(font)
        painter.drawText(28, h - 25, "JARVIS // PERSONAL AI SYSTEM")
        painter.drawText(w - 210, h - 25, "SECURE CHANNEL // 01")

        # Decorative target brackets around the orb area
        cx, cy = w / 2, h / 2 - 10
        size = 145
        bracket = 18
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 65), 1))
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            x = cx + sx * size
            y = cy + sy * size
            painter.drawLine(QPointF(x, y), QPointF(x + sx * bracket, y))
            painter.drawLine(QPointF(x, y), QPointF(x, y + sy * bracket))

        painter.end()
