import html

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QTextBrowser, QVBoxLayout


class ResponseCard(QFrame):
    """Theme-matched visual response surface displayed above the Jarvis orb."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("responseCard")
        self.setMinimumWidth(560)
        self.setMaximumWidth(920)
        self.setMaximumHeight(320)
        self.setStyleSheet("""
            QFrame#responseCard {
                background: rgba(4, 18, 29, 235);
                border: 1px solid rgba(41, 182, 255, 85);
                border-radius: 16px;
            }
            QLabel#responseCardTitle {
                color: #29B6FF;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 3px;
                background: transparent;
                border: none;
            }
            QTextBrowser#responseCardBody {
                color: #DCEEFF;
                background: transparent;
                border: none;
                padding: 0;
                font-size: 14px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        self.title = QLabel("JARVIS")
        self.title.setObjectName("responseCardTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.title)

        self.body = QTextBrowser()
        self.body.setObjectName("responseCardBody")
        self.body.setOpenExternalLinks(True)
        self.body.setReadOnly(True)
        layout.addWidget(self.body, 1)

    def clear(self):
        self.title.setText("JARVIS")
        self.body.clear()

    def set_text(self, text):
        self.body.setPlainText(text)

    def set_markdown(self, text):
        self.body.setMarkdown(text)

    def set_email(self, email):
        subject = email.get("subject") or "(no subject)"
        sender = email.get("from") or "Unknown sender"
        date = email.get("date") or ""
        body = email.get("body") or email.get("snippet") or "(No readable message body.)"

        self.title.setText("MAIL  /  MESSAGE")
        metadata = (
            f"<div style='color:#71899F;font-size:11px;'>"
            f"<b style='color:#9FB8CC;'>FROM</b>&nbsp;&nbsp;{html.escape(sender)}"
            f"&nbsp;&nbsp;&nbsp; <b style='color:#9FB8CC;'>DATE</b>&nbsp;&nbsp;{html.escape(date)}"
            f"</div><br>"
        )
        subject_html = (
            f"<div style='font-size:18px;font-weight:600;color:#DCEEFF;'>"
            f"{html.escape(subject)}</div><br>"
        )
        body_html = f"<div style='font-size:14px;color:#DCEEFF;line-height:1.45;'>{html.escape(body).replace(chr(10), '<br>')}</div>"
        self.body.setHtml(metadata + subject_html + body_html)

    def set_email_list(self, emails, title="MAIL  /  RECENT"):
        self.title.setText(title)
        if not emails:
            self.body.setPlainText("No recent mail found.")
            return

        lines = []
        for index, email in enumerate(emails, start=1):
            subject = email.get("subject") or "(no subject)"
            sender = email.get("from") or "Unknown sender"
            snippet = email.get("snippet") or ""
            lines.append(
                f"### {index}. {subject}\n"
                f"**From:** {sender}\n"
                f"{snippet}"
            )
        self.body.setMarkdown("\n\n---\n\n".join(lines))
