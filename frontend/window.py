import math
import re
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
    QApplication,
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
from voice.wake_word import WakeWordWorker
from frontend.response_card import ResponseCard

BG = QColor("#02070D")
BLUE = QColor("#008CFF")
BLUE_BRIGHT = QColor("#29B6FF")
GREEN = QColor("#00E89A")
GREEN_BRIGHT = QColor("#4DFFC0")
TEXT = QColor("#DCEEFF")
MUTED = QColor("#71899F")


class JarvisWorker(QThread):
    token_received = pyqtSignal(str)
    tool_result = pyqtSignal(str, object)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, user_input, conversation):
        super().__init__()
        self.user_input = user_input
        self.conversation = conversation

    def run(self):
        try:
            full_response = ""
            for event in process_request_stream(self.user_input, self.conversation):
                if event["type"] == "text":
                    token = event["content"]
                    full_response += token
                    self.token_received.emit(token)
                elif event["type"] == "tool_result":
                    self.tool_result.emit(event["tool"], event["result"])
            self.finished.emit(full_response)
        except Exception as e:
            self.failed.emit(str(e))


class JarvisOrb(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(150, 150)
        self.state = "idle"
        self.audio_level = 0.0
        self.speaking_level = 0.0
        self.phase = 0.0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate)
        self.animation_timer.start(30)

    def set_state(self, state):
        self.state = state
        self.update()

    def set_audio_level(self, level):
        self.audio_level = max(0.0, min(1.0, float(level)))
        self.update()

    def set_speaking_level(self, level):
        self.speaking_level = max(0.0, min(1.0, float(level)))
        self.update()

    def animate(self):
        self.phase += 0.055
        if self.state == "listening":
            self.audio_level *= 0.88
            if self.audio_level < 0.02:
                simulated = math.sin(self.phase * 2.7) * 0.5 + 0.5
                self.audio_level = simulated * 0.08
        elif self.state == "speaking":
            self.speaking_level *= 0.92
        elif self.state == "processing":
            pass
        else:
            self.audio_level *= 0.90
            self.speaking_level *= 0.90
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        base_radius = 32

        if self.state == "listening":
            primary = GREEN
            secondary = GREEN_BRIGHT
            activity = self.audio_level
        elif self.state == "speaking":
            primary = BLUE_BRIGHT
            secondary = BLUE
            activity = self.speaking_level
        elif self.state == "processing":
            primary = BLUE
            secondary = BLUE_BRIGHT
            activity = (math.sin(self.phase * 2.2) * 0.5 + 0.5) * 0.18
        else:
            primary = BLUE
            secondary = BLUE_BRIGHT
            activity = (math.sin(self.phase * 1.5) * 0.5 + 0.5) * 0.08

        dynamic_radius = base_radius + activity * 7
        glow_radius = dynamic_radius * 1.75
        glow = QRadialGradient(center, glow_radius)
        glow.setColorAt(0.0, QColor(primary.red(), primary.green(), primary.blue(), 70))
        glow.setColorAt(0.35, QColor(primary.red(), primary.green(), primary.blue(), 30))
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
        inner_gradient.setColorAt(0.0, QColor(primary.red(), primary.green(), primary.blue(), 20))
        inner_gradient.setColorAt(1.0, QColor(primary.red(), primary.green(), primary.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(inner_gradient)
        painter.drawEllipse(center, inner_radius, inner_radius)

        painter.setPen(QColor(220, 238, 255, 235))
        font = QFont("Segoe UI", 7)
        font.setWeight(QFont.Weight.Light)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.2)
        painter.setFont(font)
        text = "J A R V I S"
        rect = painter.boundingRect(0, 0, self.width(), self.height(), Qt.AlignmentFlag.AlignCenter, text)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()


class StatusLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                color: #00E89A;
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 3px;
            }
        """)

    def set_status(self, text, color):
        self.setText(text)
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 3px;
            }}
        """)


class IconButton(QPushButton):
    def __init__(self, icon, tooltip):
        super().__init__(icon)
        self.setToolTip(tooltip)
        self.setFixedSize(34, 34)
        self.setStyleSheet("""
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
        """)


class JarvisWindow(QMainWindow):
    VISUAL_EMAIL_TOOLS = {"get_recent_emails", "get_email", "search_emails"}

    def __init__(self):
        super().__init__()
        self.conversation = []
        self.worker_thread = None
        self.worker = None
        self.voice_thread = None
        self.voice_worker = None
        self.wake_worker = None
        self.jarvis_mode = "full"
        self.wake_active = False
        self.full_central = None
        self.orb_container = None
        self.visual_response_mode = False
        self.tool_visual_active = False

        self.tts = TextToSpeech(rate=180, volume=1.0)
        self.tts.level.connect(self.update_speaking_level)
        self.tts.speaking_started.connect(self.tts_started)
        self.tts.speaking_finished.connect(self.tts_finished)
        self.tts.response_finished.connect(self.tts_response_finished)
        self.tts.error.connect(self.tts_error)

        self.setWindowTitle("Jarvis")
        self.setMinimumSize(900, 700)
        self.resize(1200, 850)
        self.setStyleSheet("QMainWindow { background-color: #02070D; }")
        self.build_ui()

    @staticmethod
    def is_visual_request(text):
        """Decide when the answer is better consumed as a visual card."""
        normalized = re.sub(r"\s+", " ", text.lower().strip())
        if "?" in normalized:
            return True

        visual_starts = (
            "what is ", "what are ", "what's ", "whats ", "who is ",
            "where is ", "when is ", "why is ", "why are ", "why does ",
            "how does ", "how do ", "how can ", "explain ", "define ",
            "compare ", "difference between ", "difference in ", "tell me about ",
            "give me the difference", "versus ", "vs ", "list the ",
        )
        if normalized.startswith(visual_starts):
            return True

        email_phrases = (
            "check my mail", "check my email", "read my mail", "read my email",
            "show my mail", "show my email", "open that mail", "open that email",
            "open the mail", "open the email", "content of that mail",
            "content of that email", "contents of that mail", "contents of that email",
            "recent emails", "recent mail", "my emails", "my mail",
        )
        return any(phrase in normalized for phrase in email_phrases)

    def add_response_token(self, token):
        current_text = self.response_label.text()
        self.response_label.setText(current_text + token)
        self.response_label.show()

        if self.visual_response_mode:
            self.presentation_card.set_text(self.presentation_card.body.toPlainText() + token)
            self.presentation_card.show()
            return

        print(f"[TTS FEED] {repr(token)}")
        self.tts.feed(token)

    def handle_tool_result(self, tool_name, result):
        if tool_name not in self.VISUAL_EMAIL_TOOLS or not self.visual_response_mode:
            return

        self.tool_visual_active = True
        if not isinstance(result, dict):
            self.presentation_card.set_text(str(result))
            self.presentation_card.show()
            return

        if not result.get("success", True) and result.get("error"):
            self.presentation_card.set_text(f"**Mail error**\n\n{result['error']}")
            self.presentation_card.show()
            return

        if tool_name == "get_email":
            self.presentation_card.set_email(result)
        elif tool_name in {"get_recent_emails", "search_emails"}:
            emails = result.get("emails") if isinstance(result.get("emails"), list) else result
            if isinstance(emails, list):
                self.presentation_card.set_email_list(emails)
            else:
                self.presentation_card.set_text(str(result))
        else:
            self.presentation_card.set_text(str(result))
        self.presentation_card.show()

    def response_finished(self, response):
        print("Jarvis finished responding.")

    def response_error(self, error):
        self.response_label.setText(f"Error: {error}")

    def build_ui(self):
        central = QWidget()
        self.full_central = central
        central.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(30, 20, 30, 18)
        root.setSpacing(0)

        self.top = QHBoxLayout()
        self.top.setContentsMargins(0, 0, 0, 0)
        logo = QLabel("◉")
        logo.setStyleSheet("QLabel { color: #008CFF; font-size: 18px; }")
        self.top.addWidget(logo)
        self.top.addStretch()
        title = QLabel("J A R V I S")
        title.setStyleSheet("QLabel { color: #008CFF; font-size: 17px; font-weight: 300; letter-spacing: 7px; }")
        self.top.addWidget(title)
        self.top.addStretch()

        minimize = QPushButton("—")
        close = QPushButton("×")
        for button in (minimize, close):
            button.setFixedSize(35, 30)
            button.setStyleSheet("""
                QPushButton { color: rgba(160,190,210,180); background: transparent; font-size: 18px; }
                QPushButton:hover { color: #29B6FF; }
            """)
        minimize.clicked.connect(self.showMinimized)
        close.clicked.connect(self.close)
        self.top.addWidget(minimize)
        self.top.addWidget(close)
        root.addLayout(self.top)
        root.addStretch(1)

        # Visual answers live in the empty space directly above the orb.
        self.presentation_card = ResponseCard()
        self.presentation_card.hide()
        root.addWidget(self.presentation_card, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addSpacing(14)

        self.orb = JarvisOrb()
        root.addWidget(self.orb, alignment=Qt.AlignmentFlag.AlignCenter)

        self.status = StatusLabel()
        self.status.set_status("●  IDLE", "#527086")
        root.addWidget(self.status, alignment=Qt.AlignmentFlag.AlignCenter)

        self.interpreted_label = QLabel()
        self.interpreted_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.interpreted_label.setWordWrap(True)
        self.interpreted_label.setMinimumWidth(500)
        self.interpreted_label.setMaximumWidth(950)
        self.interpreted_label.setStyleSheet("""
            QLabel { color: #71899F; font-size: 13px; font-weight: 400; background: transparent; border: none; padding: 2px; }
        """)
        self.interpreted_label.hide()
        root.addWidget(self.interpreted_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.response_label = QLabel()
        self.response_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.response_label.setWordWrap(True)
        self.response_label.setMinimumWidth(500)
        self.response_label.setMaximumWidth(950)
        self.response_label.setStyleSheet("""
            QLabel { color: #DCEEFF; font-size: 15px; font-weight: 400; background: transparent; border: none; padding: 2px; }
        """)
        self.response_label.hide()
        root.addWidget(self.response_label, alignment=Qt.AlignmentFlag.AlignCenter)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Speak to Jarvis or type a message...")
        self.input.setStyleSheet("""
            QLineEdit { color: #8FA8BD; background: transparent; border: none; border-bottom: 1px solid rgba(0, 140, 255, 45); padding: 8px 4px; font-size: 12px; }
            QLineEdit:focus { border-bottom: 1px solid rgba(41, 182, 255, 120); }
        """)
        self.input.returnPressed.connect(self.send_message)
        input_row.addWidget(self.input)

        send_button = QPushButton("↗")
        send_button.setFixedSize(48, 48)
        send_button.setStyleSheet("""
            QPushButton { color: #29B6FF; border: 1px solid rgba(0,140,255,80); border-radius: 24px; font-size: 20px; background: rgba(0,100,180,20); }
            QPushButton:hover { background: rgba(0,140,255,40); }
        """)
        send_button.clicked.connect(self.send_message)
        input_row.addWidget(send_button)
        root.addLayout(input_row)

        self.bottom = QHBoxLayout()
        self.bottom.setContentsMargins(0, 12, 0, 0)
        mic_button = IconButton("♩", "Voice input")
        wave_button = IconButton("〽", "Audio visualization")
        keyboard_button = IconButton("⌨", "Keyboard input")
        self.bottom.addWidget(mic_button)
        self.bottom.addWidget(wave_button)
        self.bottom.addWidget(keyboard_button)
        self.bottom.addStretch()
        weather_button = IconButton("☁", "Weather")
        gmail_button = IconButton("✉", "Gmail")
        web_button = IconButton("◎", "Web / Research")
        settings_button = IconButton("⚙", "Settings")
        self.bottom.addWidget(weather_button)
        self.bottom.addWidget(gmail_button)
        self.bottom.addWidget(web_button)
        self.bottom.addWidget(settings_button)
        root.addLayout(self.bottom)
        mic_button.clicked.connect(self.activate_voice)

    def begin_request(self, user_input):
        self.visual_response_mode = self.is_visual_request(user_input)
        self.tool_visual_active = False
        self.presentation_card.clear()
        self.presentation_card.hide()
        self.response_label.setText("")
        self.response_label.hide() if self.visual_response_mode else self.response_label.show()
        self.set_processing_state()
        self.start_worker(user_input)
        self.tts.stop_speaking()

    def send_message(self):
        user_input = self.input.text().strip()
        if not user_input:
            return
        self.input.clear()
        self.begin_request(user_input)

    def start_worker(self, message):
        self.worker_thread = QThread()
        self.worker = JarvisWorker(message, self.conversation)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.handle_response)
        self.worker.failed.connect(self.handle_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.token_received.connect(self.add_response_token)
        self.worker.tool_result.connect(self.handle_tool_result)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def handle_response(self, result):
        if self.visual_response_mode:
            # The complete answer is already visible in the card. Visual
            # requests do not need to be read back word-for-word.
            if not self.tool_visual_active:
                self.presentation_card.set_markdown(result)
                self.presentation_card.title.setText("JARVIS  /  ANSWER")
                self.presentation_card.show()
            self.orb.set_state("idle")
            self.status.set_status("●  DISPLAYING", "#29B6FF")
            QTimer.singleShot(1200, self._return_to_idle)
            return

        self.tts.finish_response()

    def _return_to_idle(self):
        if self.orb.state == "idle":
            self.status.set_status("●  IDLE", "#527086")

    def handle_error(self, error):
        self.orb.set_state("idle")
        self.status.set_status("●  ERROR", "#FF5577")
        self.response_label.setText(error)
        self.response_label.show()
        if self.visual_response_mode:
            self.presentation_card.set_text(error)
            self.presentation_card.show()

    def set_processing_state(self):
        self.orb.set_state("processing")
        if self.jarvis_mode == "full":
            self.status.set_status("●  THINKING", "#008CFF")
            self.status.show()
        else:
            self.status.hide()

    def set_response_state(self, response):
        self.orb.set_state("speaking")
        self.status.set_status("●  JARVIS SPEAKING", "#29B6FF")
        self.response_label.setText(response)
        self.response_label.show()

    def activate_voice(self):
        if self.voice_thread is not None:
            return
        self.orb.set_state("listening")
        if self.jarvis_mode == "full":
            self.status.set_status("●  LISTENING", "#00E89A")
            self.interpreted_label.setText("Listening...")
            self.interpreted_label.show()
            self.response_label.hide()
        else:
            self.status.hide()
            self.interpreted_label.hide()
            self.response_label.hide()
            self.input.hide()

        self.voice_thread = QThread()
        self.voice_worker = VoiceWorker()
        self.voice_worker.moveToThread(self.voice_thread)
        self.voice_thread.started.connect(self.voice_worker.run)
        self.voice_worker.level.connect(self.update_microphone_level)
        self.voice_worker.transcript.connect(self.handle_voice_transcript)
        self.voice_worker.error.connect(self.handle_voice_error)
        self.voice_worker.finished.connect(self.voice_thread.quit)
        self.voice_worker.finished.connect(self.voice_worker.deleteLater)
        self.voice_thread.finished.connect(self.voice_thread.deleteLater)
        self.voice_thread.finished.connect(self.voice_finished)
        self.voice_thread.start()

    def update_microphone_level(self, level):
        self.orb.set_audio_level(level)

    def update_speaking_level(self, level):
        self.orb.set_speaking_level(level)

    def tts_started(self):
        self.orb.set_state("speaking")
        if self.jarvis_mode == "full":
            self.status.set_status("●  JARVIS SPEAKING", "#29B6FF")
            self.status.show()
        else:
            self.status.hide()

    def tts_finished(self):
        self.orb.set_speaking_level(0.0)

    def tts_response_finished(self):
        self.orb.set_speaking_level(0.0)
        self.orb.set_state("idle")
        if self.jarvis_mode == "full":
            self.status.set_status("●  IDLE", "#527086")
            self.status.show()
        if self.jarvis_mode == "orb":
            QTimer.singleShot(500, self.start_wake_listener)

    def tts_error(self, error):
        print(f"[TTS ERROR] {error}")
        self.orb.set_speaking_level(0.0)

    def handle_voice_transcript(self, text):
        if not text:
            self.orb.set_state("idle")
            if self.jarvis_mode == "full":
                self.status.set_status("●  DIDN'T HEAR THAT", "#FFAA44")
            else:
                print("[JARVIS] Didn't hear anything.")
            return
        self.tts.stop_speaking()
        print(f"[JARVIS] Heard command: {text}")
        if self.jarvis_mode == "full":
            self.interpreted_label.setText(f'"{text}"')
            self.interpreted_label.show()
        else:
            self.interpreted_label.hide()
            self.status.hide()
            self.input.hide()
        self.set_processing_state()
        if self.jarvis_mode == "orb":
            self.status.hide()
            self.interpreted_label.hide()
            self.response_label.hide()
            self.input.hide()
        self.begin_request(text)

    def handle_voice_error(self, error):
        self.orb.set_state("idle")
        if self.jarvis_mode == "full":
            self.status.set_status("●  MICROPHONE ERROR", "#FF5577")
            self.status.show()
            self.interpreted_label.setText(error)
            self.interpreted_label.show()
        else:
            print(f"[JARVIS] Microphone error: {error}")
            self.status.hide()
            self.interpreted_label.hide()
            self.response_label.hide()
            self.input.hide()

    def voice_finished(self):
        self.voice_thread = None
        self.voice_worker = None

    def start_wake_listener(self):
        if self.wake_worker is not None:
            return
        print("[JARVIS] Starting wake listener...")
        self.wake_worker = WakeWordWorker()
        self.wake_worker.wake_detected.connect(self.handle_wake)
        self.wake_worker.error.connect(self.handle_voice_error)
        self.wake_worker.start()
        self.wake_active = True

    def stop_wake_listener(self):
        if self.wake_worker is None:
            return
        print("[JARVIS] Stopping wake listener...")
        self.wake_worker.stop()
        self.wake_worker.wait(1500)
        self.wake_worker = None
        self.wake_active = False

    def handle_wake(self, wake_type):
        print(f"[JARVIS] Wake event: {wake_type}")
        self.stop_wake_listener()
        if wake_type == "clap":
            print("[JARVIS] Opening full interface.")
            self.show_full_mode()
        elif wake_type == "voice":
            print("[JARVIS] Opening orb mode.")
            self.show_orb_mode()
        self.activate_voice()

    def show_full_mode(self):
        print("[JARVIS] Switching to full interface.")
        self.jarvis_mode = "full"
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)

        if self.orb_container is not None:
            self.orb_container.hide()
            self.orb.setParent(self.full_central)
            self.orb_container.deleteLater()
            self.orb_container = None

        self.setCentralWidget(self.full_central)
        self.full_central.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.full_central.show()
        self.status.show()
        self.interpreted_label.hide()
        self.response_label.hide()
        self.presentation_card.hide()
        self.input.show()

        self.setMinimumSize(900, 700)
        self.setMaximumSize(16777215, 16777215)

        self.showMaximized()
        self.raise_()
        self.activateWindow()
        print("[JARVIS] Full interface restored and maximized.")

    def show_orb_mode(self):
        self.jarvis_mode = "orb"
        print("[JARVIS] Switching to bottom-left orb mode.")
        self.status.hide()
        self.interpreted_label.hide()
        self.response_label.hide()
        self.presentation_card.hide()
        self.input.hide()

        self.orb_container = QWidget()
        self.orb_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.orb_container.setStyleSheet("background: transparent;")
        orb_layout = QVBoxLayout(self.orb_container)
        orb_layout.setContentsMargins(10, 10, 10, 10)
        orb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.orb.setParent(self.orb_container)
        self.orb.show()
        orb_layout.addWidget(self.orb, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.orb_container)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(0, 0)
        self.setMaximumSize(180, 180)
        self.resize(180, 180)

        screen = self.screen() or QApplication.primaryScreen()
        geometry = screen.availableGeometry()
        margin = 8
        x = geometry.left() + margin
        y = geometry.bottom() - self.height() - margin
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        print(f"[JARVIS] Orb positioned at bottom-left: x={x}, y={y}")
