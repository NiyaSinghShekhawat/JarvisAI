from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from backend.tools.gmail import get_email, get_recent_emails


class EmailViewer(QDialog):
    """Native Jarvis mail reader: browse messages and read their contents."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jarvis · Mail")
        self.resize(1050, 680)
        self.setModal(False)
        self.setStyleSheet("""
            QDialog { background: #02070D; color: #DCEEFF; }
            QLabel { color: #DCEEFF; }
            QListWidget, QTextBrowser {
                background: #06111A;
                color: #DCEEFF;
                border: 1px solid rgba(0,140,255,70);
                border-radius: 10px;
                padding: 8px;
            }
            QListWidget::item { padding: 10px 8px; border-bottom: 1px solid rgba(113,137,159,30); }
            QListWidget::item:selected { background: rgba(0,140,255,45); }
            QPushButton {
                color: #9FB8CC;
                background: rgba(0,100,180,20);
                border: 1px solid rgba(0,140,255,70);
                border-radius: 8px;
                padding: 8px 14px;
            }
            QPushButton:hover { color: #29B6FF; background: rgba(0,140,255,35); }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("MAIL")
        title.setStyleSheet("font-size: 18px; letter-spacing: 4px; color: #29B6FF;")
        header.addWidget(title)
        header.addStretch()
        self.refresh_button = QPushButton("↻  Refresh")
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.message_list = QListWidget()
        self.message_list.setMinimumWidth(330)
        splitter.addWidget(self.message_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(8)

        self.subject = QLabel("Select an email")
        self.subject.setWordWrap(True)
        self.subject.setStyleSheet("font-size: 19px; font-weight: 600; color: #DCEEFF;")

        self.meta = QLabel("")
        self.meta.setWordWrap(True)
        self.meta.setStyleSheet("font-size: 12px; color: #71899F;")

        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(True)
        self.body.setPlaceholderText("Email contents will appear here.")

        right_layout.addWidget(self.subject)
        right_layout.addWidget(self.meta)
        right_layout.addWidget(self.body, 1)
        splitter.addWidget(right)
        splitter.setSizes([360, 640])

        root.addWidget(splitter, 1)

        self.refresh_button.clicked.connect(self.load_emails)
        self.message_list.currentItemChanged.connect(self.open_selected)

        self.emails = []
        self.load_emails()

    def load_emails(self):
        self.message_list.clear()
        self.subject.setText("Loading mail…")
        self.meta.clear()
        self.body.clear()

        try:
            self.emails = get_recent_emails(limit=15)
        except Exception as exc:
            self.subject.setText("Could not load mail")
            QMessageBox.warning(self, "Jarvis Mail", str(exc))
            return

        if not self.emails:
            self.subject.setText("No recent mail")
            return

        for email in self.emails:
            subject = email.get("subject") or "(no subject)"
            sender = email.get("from") or "Unknown sender"
            item = QListWidgetItem(f"{subject}\n{sender}")
            item.setData(Qt.ItemDataRole.UserRole, email.get("id"))
            self.message_list.addItem(item)

        self.message_list.setCurrentRow(0)

    def open_selected(self, current, previous):
        if current is None:
            return

        email_id = current.data(Qt.ItemDataRole.UserRole)
        if not email_id:
            return

        try:
            email = get_email(email_id)
        except Exception as exc:
            QMessageBox.warning(self, "Jarvis Mail", str(exc))
            return

        self.subject.setText(email.get("subject") or "(no subject)")
        self.meta.setText(
            f"From: {email.get('from', '')}\n"
            f"To: {email.get('to', '')}\n"
            f"Date: {email.get('date', '')}"
        )

        body = email.get("body") or email.get("snippet") or "(No readable message body.)"
        self.body.setPlainText(body)
