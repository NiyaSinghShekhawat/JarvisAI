import math
import time

from PyQt6.QtCore import (
    Qt,
    QThread,
    QObject,
    pyqtSignal,
    QTimer,
    QPointF,
)

from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QRadialGradient,
    QFont,
)

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
)

from backend.brain.router import process_request_stream
from voice.voice_worker import VoiceWorker
from voice.text_to_speech import TextToSpeech

# ============================================================
# COLORS
# ============================================================

BG = QColor("#02070D")

BLUE = QColor("#008CFF")
BLUE_BRIGHT = QColor("#29B6FF")

GREEN = QColor("#00E89A")
GREEN_BRIGHT = QColor("#4DFFC0")

TEXT = QColor("#DCEEFF")
MUTED = QColor("#71899F")


# ============================================================
# WORKER
# ============================================================

class JarvisWorker(QThread):

    token_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, user_input, conversation):
        super().__init__()

        self.user_input = user_input
        self.conversation = conversation

    def run(self):

        try:

            full_response = ""

            for event in process_request_stream(
                self.user_input,
                self.conversation
            ):

                if event["type"] == "text":

                    token = event["content"]

                    full_response += token

                    self.token_received.emit(
                        token
                    )

            self.finished.emit(
                full_response
            )

        except Exception as e:

            self.failed.emit(
                str(e)
            )
# ============================================================
# ORB
# ============================================================

class JarvisOrb(QWidget):
    """
    Central Jarvis orb.

    Current states:
        idle
        listening
        processing
        speaking

    Later:
        set_audio_level() can be connected directly
        to microphone amplitude.

        set_speaking_level() can be connected directly
        to TTS audio amplitude.
    """

    def __init__(self):
        super().__init__()

        self.setMinimumSize(420, 420)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.state = "idle"

        self.audio_level = 0.0
        self.speaking_level = 0.0

        self.phase = 0.0

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate)
        self.animation_timer.start(30)

    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    def set_state(self, state):
        self.state = state
        self.update()

    # --------------------------------------------------------
    # MICROPHONE INPUT
    # --------------------------------------------------------

    def set_audio_level(self, level):
        """
        level should be between 0.0 and 1.0.

        This will later receive real microphone amplitude.
        """

        self.audio_level = max(
            0.0,
            min(1.0, float(level))
        )

        self.update()

    # --------------------------------------------------------
    # TTS INPUT
    # --------------------------------------------------------

    def set_speaking_level(self, level):
        """
        level should be between 0.0 and 1.0.

        Later this will be driven by Jarvis's TTS audio.
        """

        self.speaking_level = max(
            0.0,
            min(1.0, float(level))
        )

        self.update()

    # --------------------------------------------------------
    # ANIMATION
    # --------------------------------------------------------

    def animate(self):
        self.phase += 0.055

        if self.state == "listening":
            # Temporary simulated movement until microphone
            # amplitude is connected.
            simulated = (
                math.sin(self.phase * 2.7) * 0.5 + 0.5
            )

            self.audio_level *= 0.85

            if self.audio_level < 0.02:
                self.audio_level = simulated * 0.10

            elif self.state == "speaking":

                # Real TTS activity drives the orb.
                self.speaking_level *= 0.92

        else:
            self.audio_level *= 0.90
            self.speaking_level *= 0.90

        self.update()

    # --------------------------------------------------------
    # PAINT
    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        center = QPointF(
            self.width() / 2,
            self.height() / 2
        )

        base_radius = min(
            self.width(),
            self.height()
        ) * 0.30

        # ----------------------------------------------------
        # STATE COLOR
        # ----------------------------------------------------

        if self.state == "listening":
            primary = GREEN
            secondary = GREEN_BRIGHT

            response_level = self.audio_level

        elif self.state == "speaking":
            primary = BLUE_BRIGHT
            secondary = BLUE

            response_level = self.speaking_level

        elif self.state == "processing":
            primary = BLUE
            secondary = BLUE_BRIGHT

            response_level = (
                math.sin(self.phase * 2) * 0.5 + 0.5
            ) * 0.12

        else:
            primary = BLUE
            secondary = GREEN

            response_level = 0.03

        # ----------------------------------------------------
        # OUTER RADAR RINGS
        # ----------------------------------------------------

        for i in range(5):

            ring_radius = (
                base_radius
                + 22
                + (i * 18)
            )

            opacity = max(
                20,
                90 - i * 15
            )

            pen = QPen(
                QColor(
                    primary.red(),
                    primary.green(),
                    primary.blue(),
                    opacity
                )
            )

            pen.setWidth(1)

            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            painter.drawEllipse(
                center,
                ring_radius,
                ring_radius
            )

        # ----------------------------------------------------
        # AUDIO EXPANSION
        # ----------------------------------------------------

        dynamic_radius = (
            base_radius
            + response_level * 70
        )

        # ----------------------------------------------------
        # OUTER GLOW
        # ----------------------------------------------------

        glow = QRadialGradient(
            center,
            dynamic_radius * 1.7
        )

        glow.setColorAt(
            0.0,
            QColor(
                primary.red(),
                primary.green(),
                primary.blue(),
                80
            )
        )

        glow.setColorAt(
            0.45,
            QColor(
                primary.red(),
                primary.green(),
                primary.blue(),
                30
            )
        )

        glow.setColorAt(
            1.0,
            QColor(
                primary.red(),
                primary.green(),
                primary.blue(),
                0
            )
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)

        painter.drawEllipse(
            center,
            dynamic_radius * 1.7,
            dynamic_radius * 1.7
        )

        # ----------------------------------------------------
        # ORB BODY
        # ----------------------------------------------------

        gradient = QRadialGradient(
            center - QPointF(
                dynamic_radius * 0.25,
                dynamic_radius * 0.25
            ),
            dynamic_radius * 1.3
        )

        gradient.setColorAt(
            0.0,
            QColor("#071C2C")
        )

        gradient.setColorAt(
            0.45,
            QColor("#04131F")
        )

        gradient.setColorAt(
            0.82,
            QColor(
                primary.red(),
                primary.green(),
                primary.blue(),
                70
            )
        )

        gradient.setColorAt(
            1.0,
            QColor("#02070D")
        )

        painter.setBrush(gradient)

        painter.setPen(
            QPen(
                primary,
                2
            )
        )

        painter.drawEllipse(
            center,
            dynamic_radius,
            dynamic_radius
        )

        # ----------------------------------------------------
        # INNER CORE
        # ----------------------------------------------------

        core_radius = dynamic_radius * 0.72

        core_gradient = QRadialGradient(
            center,
            core_radius
        )

        core_gradient.setColorAt(
            0.0,
            QColor(
                primary.red(),
                primary.green(),
                primary.blue(),
                22
            )
        )

        core_gradient.setColorAt(
            1.0,
            QColor(0, 0, 0, 0)
        )

        painter.setBrush(core_gradient)
        painter.setPen(Qt.PenStyle.NoPen)

        painter.drawEllipse(
            center,
            core_radius,
            core_radius
        )

        # ----------------------------------------------------
        # ORBIT DOTS
        # ----------------------------------------------------

        for i in range(12):

            angle = (
                self.phase * 0.5
                + (math.pi * 2 / 12) * i
            )

            orbit_radius = (
                dynamic_radius + 15
            )

            x = (
                center.x()
                + math.cos(angle)
                * orbit_radius
            )

            y = (
                center.y()
                + math.sin(angle)
                * orbit_radius
            )

            dot_radius = 2.2

            painter.setBrush(
                QColor(
                    secondary.red(),
                    secondary.green(),
                    secondary.blue(),
                    150
                )
            )

            painter.drawEllipse(
                QPointF(x, y),
                dot_radius,
                dot_radius
            )

        # ----------------------------------------------------
        # JARVIS TEXT
        # ----------------------------------------------------

        painter.setPen(TEXT)

        font = QFont(
            "Segoe UI",
            18
        )

        font.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing,
            8
        )

        font.setWeight(
            QFont.Weight.Light
        )

        painter.setFont(font)

        text = "J A R V I S"

        rect = painter.boundingRect(
            0,
            0,
            self.width(),
            self.height(),
            Qt.AlignmentFlag.AlignCenter,
            text
        )

        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            text
        )

        painter.end()


# ============================================================
# STATUS LABEL
# ============================================================

class StatusLabel(QLabel):

    def __init__(self):
        super().__init__()

        self.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.setStyleSheet(
            """
            QLabel {
                color: #00E89A;
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 3px;
            }
            """
        )

    def set_status(self, text, color):
        self.setText(text)

        self.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 3px;
            }}
            """
        )


# ============================================================
# ICON BUTTON
# ============================================================

class IconButton(QPushButton):

    def __init__(self, icon, tooltip):
        super().__init__(icon)

        self.setToolTip(tooltip)

        self.setFixedSize(34,34)

        self.setStyleSheet(
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


# ============================================================
# MAIN WINDOW
# ============================================================

class JarvisWindow(QMainWindow):

    def add_response_token(self, token):

        # ----------------------------------------------------
        # SHOW TOKEN IMMEDIATELY
        # ----------------------------------------------------

        current_text = (
            self.response_label.text()
        )

        self.response_label.setText(
            current_text + token
        )

        self.response_label.show()

        print(
            f"[TTS FEED] {repr(token)}"
        )

        # ----------------------------------------------------
        # SEND TOKEN TO TTS
        # ----------------------------------------------------

        self.tts.feed(
            token
        )


    def response_finished(self, response):

        print("Jarvis finished responding.")


    def response_error(self, error):

        self.response_label.setText(
            f"Error: {error}"
        )

    def __init__(self):
        super().__init__()

        self.conversation = []

        self.worker_thread = None
        self.worker = None

        self.voice_thread = None
        self.voice_worker = None

        # ========================================================
        # TEXT TO SPEECH
        # ========================================================

        self.tts = TextToSpeech(
            rate=180,
            volume=1.0
        )

        self.tts.level.connect(
            self.update_speaking_level
        )

        self.tts.speaking_started.connect(
            self.tts_started
        )

        self.tts.speaking_finished.connect(
            self.tts_finished
        )

        self.tts.response_finished.connect(
            self.tts_response_finished
        )

        self.tts.error.connect(
            self.tts_error
        )

        self.setWindowTitle("Jarvis")

        self.setMinimumSize(
            900,
            700
        )

        self.resize(
            1200,
            850
        )

        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #02070D;
            }
            """
        )

        self.build_ui()

    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)

        root.setContentsMargins(
            30,
            20,
            30,
            18
        )

        root.setSpacing(0)

        # ----------------------------------------------------
        # TOP BAR
        # ----------------------------------------------------

        top = QHBoxLayout()

        top.setContentsMargins(
            0,
            0,
            0,
            0
        )

        # Small Jarvis mark
        logo = QLabel("◉")

        logo.setStyleSheet(
            """
            QLabel {
                color: #008CFF;
                font-size: 18px;
            }
            """
        )

        top.addWidget(logo)

        top.addStretch()

        title = QLabel("J A R V I S")

        title.setStyleSheet(
            """
            QLabel {
                color: #008CFF;
                font-size: 17px;
                font-weight: 300;
                letter-spacing: 7px;
            }
            """
        )

        top.addWidget(title)

        top.addStretch()

        # Window controls
        minimize = QPushButton("—")
        close = QPushButton("×")

        for button in (minimize, close):

            button.setFixedSize(
                35,
                30
            )

            button.setStyleSheet(
                """
                QPushButton {
                    color: rgba(160,190,210,180);
                    background: transparent;
                    font-size: 18px;
                }

                QPushButton:hover {
                    color: #29B6FF;
                }
                """
            )

        minimize.clicked.connect(
            self.showMinimized
        )

        close.clicked.connect(
            self.close
        )

        top.addWidget(minimize)
        top.addWidget(close)

        root.addLayout(top)

        # ----------------------------------------------------
        # MAIN CONTENT
        # ----------------------------------------------------

        root.addStretch(1)

        self.orb = JarvisOrb()

        root.addWidget(
            self.orb,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        self.status = StatusLabel()

        self.status.set_status(
            "●  IDLE",
            "#527086"
        )

        root.addWidget(
            self.status,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        # ----------------------------------------------------
        # INTERPRETED SPEECH
        # ----------------------------------------------------

        self.interpreted_label = QLabel()

        self.interpreted_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.interpreted_label.setWordWrap(True)

        self.interpreted_label.setMinimumWidth(500)
        self.interpreted_label.setMaximumWidth(950)

        self.interpreted_label.setStyleSheet(
            """
            QLabel {
                color: #71899F;
                font-size: 13px;
                font-weight: 400;
                background: transparent;
                border: none;
                padding: 2px;
            }
            """
        )

        self.interpreted_label.hide()

        root.addWidget(
            self.interpreted_label,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        self.response_label = QLabel()

        self.response_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.response_label.setWordWrap(True)

        self.response_label.setMinimumWidth(500)
        self.response_label.setMaximumWidth(950)

        self.response_label.setStyleSheet(
            """
            QLabel {
                color: #DCEEFF;
                font-size: 15px;
                font-weight: 400;
                background: transparent;
                border: none;
                padding: 2px;
            }
            """
        )

        self.response_label.hide()

        root.addWidget(
            self.response_label,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        # ----------------------------------------------------
        # INPUT
        # ----------------------------------------------------

        input_row = QHBoxLayout()

        input_row.setSpacing(8)

        self.input = QLineEdit()

        self.input.setPlaceholderText(
            "Speak to Jarvis or type a message..."
        )

        self.input.setStyleSheet(
            """
            QLineEdit {
                color: #8FA8BD;
                background: transparent;
                border: none;
                border-bottom: 1px solid rgba(0, 140, 255, 45);
                padding: 8px 4px;
                font-size: 12px;
            }

            QLineEdit:focus {
                border-bottom: 1px solid rgba(41, 182, 255, 120);
            }
            """
        )

        self.input.returnPressed.connect(
            self.send_message
        )

        input_row.addWidget(
            self.input
        )

        send_button = QPushButton("↗")

        send_button.setFixedSize(
            48,
            48
        )

        send_button.setStyleSheet(
            """
            QPushButton {
                color: #29B6FF;
                border: 1px solid rgba(0,140,255,80);
                border-radius: 24px;
                font-size: 20px;
                background: rgba(0,100,180,20);
            }

            QPushButton:hover {
                background: rgba(0,140,255,40);
            }
            """
        )

        send_button.clicked.connect(
            self.send_message
        )

        input_row.addWidget(
            send_button
        )

        root.addLayout(input_row)

        # ----------------------------------------------------
        # BOTTOM BAR
        # ----------------------------------------------------

        bottom = QHBoxLayout()

        bottom.setContentsMargins(
            0,
            12,
            0,
            0
        )

        # LEFT
        mic_button = IconButton(
            "♩",
            "Voice input"
        )

        wave_button = IconButton(
            "〽",
            "Audio visualization"
        )

        keyboard_button = IconButton(
            "⌨",
            "Keyboard input"
        )

        bottom.addWidget(
            mic_button
        )

        bottom.addWidget(
            wave_button
        )

        bottom.addWidget(
            keyboard_button
        )

        bottom.addStretch()

        # RIGHT
        weather_button = IconButton(
            "☁",
            "Weather"
        )

        gmail_button = IconButton(
            "✉",
            "Gmail"
        )

        web_button = IconButton(
            "◎",
            "Web / Research"
        )

        settings_button = IconButton(
            "⚙",
            "Settings"
        )

        bottom.addWidget(
            weather_button
        )

        bottom.addWidget(
            gmail_button
        )

        bottom.addWidget(
            web_button
        )

        bottom.addWidget(
            settings_button
        )

        root.addLayout(bottom)

        # ----------------------------------------------------
        # CONNECTIONS
        # ----------------------------------------------------

        mic_button.clicked.connect(
            self.activate_voice
        )

    # ========================================================
    # SEND MESSAGE
    # ========================================================

    def send_message(self):
        user_input = self.input.text().strip()

        if not user_input:
            return

        

        self.input.clear()

        self.response_label.setText("")
        self.response_label.show()

        self.set_processing_state()

        self.start_worker(user_input)

        self.worker.failed.connect()
        self.response_error
        
        self.tts.stop_speaking()

    # ========================================================
    # PROCESSING
    # ========================================================

    def start_worker(self, message):

        self.worker_thread = QThread()

        self.worker = JarvisWorker(
            message,
            self.conversation
        )

        self.worker.moveToThread(
            self.worker_thread
        )

        self.worker_thread.started.connect(
            self.worker.run
        )

        self.worker.finished.connect(
            self.handle_response
        )

        self.worker.failed.connect(
            self.handle_error
        )

        self.worker.finished.connect(
            self.worker_thread.quit
        )
        
        self.worker.token_received.connect(
            self.add_response_token
        )

        self.worker.failed.connect(
            self.worker_thread.quit
        )

        self.worker_thread.finished.connect(
            self.worker.deleteLater
        )

        self.worker_thread.finished.connect(
            self.worker_thread.deleteLater
        )

        self.worker_thread.start()

    # ========================================================
    # RESPONSE
    # ========================================================

    def handle_response(self, result):

        if isinstance(result, dict):

            response = result.get(
                "response",
                ""
            )

        else:

            response = str(
                result
            )

        # ----------------------------------------------------
        # Flush anything still waiting inside TTS
        # ----------------------------------------------------

        self.tts.finish_response()

    # ========================================================
    # ERROR
    # ========================================================

    def handle_error(self, error):

        self.orb.set_state(
            "idle"
        )

        self.status.set_status(
            "●  ERROR",
            "#FF5577"
        )

        self.response_label.setText(
            error
        )

        self.response_label.show()

    # ========================================================
    # STATES
    # ========================================================

    def set_processing_state(self):

        self.orb.set_state(
            "processing"
        )

        self.status.set_status(
            "●  THINKING",
            "#008CFF"
        )

    def set_response_state(self, response):

        self.orb.set_state(
            "speaking"
        )

        self.status.set_status(
            "●  JARVIS SPEAKING",
            "#29B6FF"
        )

        self.response_label.setText(
            response
        )

        self.response_label.show()

    # ========================================================
    # VOICE
    # ========================================================

    def activate_voice(self):

        # Don't start another recording while one is active.
        if self.voice_thread is not None:
            return

        self.orb.set_state(
            "listening"
        )

        self.status.set_status(
            "●  LISTENING",
            "#00E89A"
        )

        self.interpreted_label.setText(
            "Listening..."
        )

        self.interpreted_label.show()

        self.response_label.hide()

        # ========================================================
        # VOICE THREAD
        # ========================================================

        self.voice_thread = QThread()

        self.voice_worker = VoiceWorker()

        self.voice_worker.moveToThread(
            self.voice_thread
        )

        # Start recording
        self.voice_thread.started.connect(
            self.voice_worker.run
        )

        # Microphone amplitude -> orb
        self.voice_worker.level.connect(
            self.update_microphone_level
        )

        # Speech recognized
        self.voice_worker.transcript.connect(
            self.handle_voice_transcript
        )

        # Errors
        self.voice_worker.error.connect(
            self.handle_voice_error
        )

        # Cleanup
        self.voice_worker.finished.connect(
            self.voice_thread.quit
        )

        self.voice_worker.finished.connect(
            self.voice_worker.deleteLater
        )

        self.voice_thread.finished.connect(
            self.voice_thread.deleteLater
        )

        self.voice_thread.finished.connect(
            self.voice_finished
        )

        self.voice_thread.start()
    # ========================================================
    # FUTURE AUDIO INTERFACE
    # ========================================================

    def update_microphone_level(self, level):

        self.orb.set_audio_level(
            level
        )

    def update_speaking_level(self, level):

        self.orb.set_speaking_level(
            level
        )

    # ========================================================
    # TTS
    # ========================================================

    def tts_started(self):

        self.orb.set_state(
            "speaking"
        )

        self.status.set_status(
            "●  JARVIS SPEAKING",
            "#29B6FF"
        )


    def tts_finished(self):

        self.orb.set_speaking_level(
            0.0
        )


    def tts_response_finished(self):

        self.orb.set_speaking_level(
            0.0
        )

        self.orb.set_state(
            "idle"
        )

        self.status.set_status(
            "●  IDLE",
            "#527086"
        )


    def tts_error(self, error):

        print(
            f"[TTS ERROR] {error}"
        )

        self.orb.set_speaking_level(
            0.0
        )


    def update_speaking_level(self, level):

        self.orb.set_speaking_level(
            level
        )

    def handle_voice_transcript(self, text):

        if not text:
            self.status.set_status(
                "●  DIDN'T HEAR THAT",
                "#FFAA44"
            )

            self.orb.set_state(
                "idle"
            )

            return

        self.tts.stop_speaking()

        # ========================================================
        # SHOW WHAT JARVIS HEARD
        # ========================================================

        self.interpreted_label.setText(
            f'"{text}"'
        )

        self.interpreted_label.show()

        # ========================================================
        # PREPARE RESPONSE
        # ========================================================

        self.response_label.clear()
        self.response_label.show()

        # ========================================================
        # NOW THINK
        # ========================================================

        self.set_processing_state()

        # ========================================================
        # SEND TO EXISTING ROUTER
        # ========================================================

        self.start_worker(
            text
        )

    def handle_voice_error(self, error):
        self.orb.set_state(
            "idle"
        )
        self.status.set_status(
            "●  MICROPHONE ERROR",
            "#FF5577"
        )
        self.interpreted_label.setText(
            error
        )
        self.interpreted_label.show()


    def voice_finished(self):
        self.voice_thread = None
        self.voice_worker = None