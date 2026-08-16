APP_STYLE = """
/* =========================================================
   GLOBAL
   ========================================================= */

QMainWindow {
    background-color: #02070d;
    color: #dcecff;
}

QWidget {
    background: transparent;
    color: #dcecff;
    font-family: "Segoe UI";
}

QLineEdit {
    background-color: rgba(5, 18, 29, 210);
    border: 1px solid rgba(0, 145, 255, 80);
    border-radius: 18px;
    padding: 12px 18px;
    color: #dcecff;
    font-size: 14px;
}

QLineEdit:focus {
    border: 1px solid rgba(0, 180, 255, 160);
}

QLineEdit::placeholder {
    color: rgba(150, 180, 205, 110);
}

QPushButton {
    background: transparent;
    border: none;
}

QToolTip {
    background-color: #07131f;
    color: #dcecff;
    border: 1px solid #126ea8;
    padding: 5px;
}
"""