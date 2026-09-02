import math
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QLinearGradient
from PyQt6.QtWidgets import QWidget


class JarvisHUD(QWidget):
    def __init__(self, window):
        super().__init__(window.full_central)
        self.window = window
        self.phase = 0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30)

    def tick(self):
        self.phase += 0.035
        # The HUD is a child of the central widget. Keep its geometry locked
        # to the central widget so the dashboard always follows fullscreen,
        # maximize, restore, and monitor-size changes.
        self.sync_geometry()
        self.update()

    def sync_geometry(self):
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())

    def state(self):
        try:
            return self.window.orb.state
        except Exception:
            return "idle"

    def accent(self):
        return {
            "listening": QColor("#00E89A"),
            "speaking": QColor("#35BFFF"),
            "processing": QColor("#7770FF"),
        }.get(self.state(), QColor("#258BFF"))

    def panel(self, p, r, title, lines, a):
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        g = QLinearGradient(x, y, x + w, y + h)
        g.setColorAt(0, QColor(10, 31, 49, 190))
        g.setColorAt(0.5, QColor(8, 24, 40, 120))
        g.setColorAt(1, QColor(2, 10, 21, 175))
        p.setBrush(g)
        p.setPen(QPen(QColor(a.red(), a.green(), a.blue(), 65), 1))
        p.drawRoundedRect(r, 9, 9)

        p.setPen(QPen(QColor(190, 230, 255, 28), 1))
        p.drawLine(QPointF(x + 10, y + 1), QPointF(x + w - 10, y + 1))

        p.setPen(QPen(QColor(a.red(), a.green(), a.blue(), 190), 1))
        m = 10
        corners = (
            (QPointF(x, y + m), QPointF(x, y)),
            (QPointF(x, y), QPointF(x + m, y)),
            (QPointF(x + w - m, y), QPointF(x + w, y)),
            (QPointF(x + w, y), QPointF(x + w, y + m)),
            (QPointF(x, y + h - m), QPointF(x, y + h)),
            (QPointF(x, y + h), QPointF(x + m, y + h)),
            (QPointF(x + w - m, y + h), QPointF(x + w, y + h)),
            (QPointF(x + w, y + h - m), QPointF(x + w, y + h)),
        )
        for start, end in corners:
            p.drawLine(start, end)

        f = QFont("Consolas", 8)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        p.setFont(f)
        p.setPen(QColor(a.red(), a.green(), a.blue(), 225))
        p.drawText(QRectF(x + 12, y + 8, w - 24, 16), Qt.AlignmentFlag.AlignLeft, title)

        p.setPen(QPen(QColor(a.red(), a.green(), a.blue(), 28), 1))
        p.drawLine(QPointF(x + 12, y + 29), QPointF(x + w - 12, y + 29))

        p.setFont(QFont("Consolas", 7))
        p.setPen(QColor(135, 168, 190, 210))
        yy = y + 38
        for s in lines:
            p.drawText(QRectF(x + 12, yy, w - 24, 13), Qt.AlignmentFlag.AlignLeft, s)
            yy += 14

    def edge(self, p, w, h, pos, span, c):
        peri = 2 * (w + h)
        st = pos % 1 * peri
        ln = span * peri

        def pt(d):
            d = d % peri
            if d < w:
                return QPointF(d, 3)
            d -= w
            if d < h:
                return QPointF(w - 3, d)
            d -= h
            if d < w:
                return QPointF(w - d, h - 3)
            return QPointF(3, h - d)

        for i in range(26):
            q = 1 - i / 26
            p.setPen(QPen(QColor(c.red(), c.green(), c.blue(), int(155 * q * q)), 2))
            p.drawLine(pt(st + ln * i / 26), pt(st + ln * (i + 1) / 26))

    def scanner(self, p, w, h, a):
        cx, cy = w - 90, h - 105
        r = 58
        rot = self.phase * 0.8
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(a.red(), a.green(), a.blue(), 30), 1))
        for rr in (r, r * 0.7, r * 0.4):
            p.drawEllipse(QPointF(cx, cy), rr, rr)

        p.setPen(QPen(QColor(140, 90, 255, 45), 1))
        p.drawEllipse(QRectF(cx - r, cy - r * 0.4, 2 * r, 0.8 * r))

        pts = []
        for z in (-1, 1):
            q = []
            for i in range(4):
                ang = math.pi / 4 + i * math.pi / 2 + rot
                q.append(QPointF(cx + math.cos(ang) * 26, cy + math.sin(ang) * 16 + z * 10))
            pts.append(q)

        p.setPen(QPen(QColor(70, 190, 255, 125), 1))
        for q in pts:
            for i in range(4):
                p.drawLine(q[i], q[(i + 1) % 4])
        for i in range(4):
            p.drawLine(pts[0][i], pts[1][i])

        ang = rot * 1.7
        e = QPointF(cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.7)
        p.setPen(QPen(QColor(a.red(), a.green(), a.blue(), 135), 1))
        p.drawLine(QPointF(cx, cy), e)
        p.drawEllipse(e, 3, 3)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        a = self.accent()

        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0, QColor(2, 10, 18, 18))
        g.setColorAt(0.5, QColor(2, 8, 16, 2))
        g.setColorAt(1, QColor(8, 8, 28, 22))
        p.fillRect(self.rect(), g)

        p.setPen(QPen(QColor(a.red(), a.green(), a.blue(), 17), 1))
        sx = max(72, w // 18)
        sy = max(64, h // 12)
        for x in range(0, w, sx):
            p.drawLine(QPointF(x, 0), QPointF(x, h))
        for y in range(0, h, sy):
            p.drawLine(QPointF(0, y), QPointF(w, y))

        scan = int((math.sin(self.phase * 0.32) * 0.5 + 0.5) * h)
        p.setPen(QPen(QColor(a.red(), a.green(), a.blue(), 12), 1))
        p.drawLine(QPointF(0, scan), QPointF(w, scan))

        # Responsive panel geometry. The HUD uses the full central widget,
        # so the four panels stay in the four screen quadrants instead of
        # being trapped inside the window's original launch-size rectangle.
        margin_x = max(28, int(w * 0.035))
        panel_w = min(300, max(235, int(w * 0.19)))
        left_x = margin_x
        right_x = w - panel_w - margin_x
        top_y = max(72, int(h * 0.09))
        bottom_y = max(top_y + 180, int(h * 0.62))

        self.panel(p, QRectF(left_x, top_y, panel_w, 126), "SYSTEM / CORE", [
            "NEURAL CORE   ONLINE",
            "MEMORY        ACTIVE",
            "VOICE         READY",
            "LINK          STABLE",
            "SECURITY      NOMINAL",
        ], a)
        self.panel(p, QRectF(right_x, top_y, panel_w, 126), "MODULES", [
            "WEATHER       READY",
            "GMAIL         READY",
            "DRIVE         READY",
            "WEB           READY",
            "TOOLS         ARMED",
            "VOICE         ONLINE",
        ], a)
        self.panel(p, QRectF(left_x, bottom_y, panel_w, 118), "TELEMETRY", [
            f"ACTIVITY   {int((math.sin(self.phase * 2) + 1) * 50):02d}%",
            "AUDIO      24.0 kHz",
            "ENGINE     GROQ",
            "MODEL      ONLINE",
            "LATENCY    NOMINAL",
        ], a)
        self.panel(p, QRectF(right_x, bottom_y, panel_w, 118), "ACTIVITY", [
            f"STATE      {self.state().upper()}",
            "STREAM     ENABLED",
            "CONTEXT    ACTIVE",
            "SESSION    LIVE",
            "LINK       SECURE",
        ], a)

        p.setFont(QFont("Consolas", 7))
        p.setPen(QColor(a.red(), a.green(), a.blue(), 120))
        p.drawText(left_x + 3, h - 28, "JARVIS // PERSONAL AI SYSTEM")
        p.drawText(right_x + 3, h - 28, "SECURE CHANNEL // 01")

        cx, cy = w / 2, h / 2 - 10
        size = min(195, w * 0.16)
        b = 24
        p.setPen(QPen(QColor(a.red(), a.green(), a.blue(), 42), 1))
        for sx2, sy2 in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            x = cx + sx2 * size
            y = cy + sy2 * size
            p.drawLine(QPointF(x, y), QPointF(x + sx2 * b, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + sy2 * b))

        self.scanner(p, w, h, a)
        p.setPen(QPen(QColor(a.red(), a.green(), a.blue(), 20), 1))
        p.drawRect(QRectF(3, 3, w - 6, h - 6))

        if self.state() == "listening":
            self.edge(p, w, h, (self.phase * 0.10) % 1, 0.22, QColor("#00E89A"))
        else:
            self.edge(p, w, h, (self.phase * 0.055) % 1, 0.17, a)
            self.edge(p, w, h, (self.phase * 0.055 + 0.48) % 1, 0.11, QColor("#8B5CFF"))

        p.end()
