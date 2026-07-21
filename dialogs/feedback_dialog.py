import threading
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QLineEdit, QTextEdit, QMessageBox
from dialogs.message_dialog import MessageDialog
from PySide6.QtCore import Qt, Signal
from config import APP_VERSION, FEEDBACK_WEBHOOK_URL
from utils import s
from styles import Style
from services.discord import post_discord_webhook

class FeedbackDialog(QDialog):
    feedback_result = Signal(bool, str)

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.parent_window = parent
        self.drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setStyleSheet(Style.main(parent.settings.app_scale))
        self.setFixedSize(s(470, parent.settings.app_scale), s(420, parent.settings.app_scale))
        self.feedback_result.connect(self.on_feedback_result)
        self.build()

    def build(self):
        sc = self.parent_window.settings.app_scale
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(22, sc), s(18, sc), s(22, sc), s(20, sc))
        layout.setSpacing(s(12, sc))

        top = QHBoxLayout()
        title = QLabel("Отзыв")
        title.setObjectName("SectionTitle")
        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(34, sc), s(32, sc))
        close.clicked.connect(self.close)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(close)
        layout.addLayout(top)

        nick_label = QLabel("Никнейм")
        nick_label.setObjectName("FormLabel")
        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("")
        self.nickname_input.setText(self.parent_window.settings.discord_nickname.strip())
        layout.addWidget(nick_label)
        layout.addWidget(self.nickname_input)

        text_label = QLabel("Что можно изменить/улучшить?")
        text_label.setObjectName("FormLabel")
        self.feedback_text = QTextEdit()
        self.feedback_text.setMinimumHeight(s(160, sc))
        layout.addWidget(text_label)
        layout.addWidget(self.feedback_text, 1)

        buttons = QHBoxLayout()
        self.send_btn = QPushButton("Отправить")
        self.send_btn.setObjectName("Primary")
        self.send_btn.clicked.connect(self.send_feedback)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("Ghost")
        cancel_btn.clicked.connect(self.close)
        buttons.addStretch(1)
        buttons.addWidget(self.send_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def send_feedback(self):
        nickname = self.nickname_input.text().strip() or "Без ника"
        message = self.feedback_text.toPlainText().strip()
        if not message:
            MessageDialog(self, "Отзыв", "Напиши отзыв.").exec()
            return
        if len(nickname) > 80:
            nickname = nickname[:80]
        if len(message) > 1700:
            message = message[:1700] + "…"
        content = f"Версия: {APP_VERSION}\nНик: {nickname}\nФидбэк: {message}"
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Отправляю...")

        def worker():
            ok, error = post_discord_webhook(FEEDBACK_WEBHOOK_URL, content, allow_everyone=False)
            self.feedback_result.emit(ok, error)
        threading.Thread(target=worker, daemon=True).start()

    def on_feedback_result(self, ok: bool, error: str):
        if ok:
            MessageDialog(self, "Отзыв", "Отзыв отправлен успешно.").exec()
            self.close()
            return
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Отправить")
        MessageDialog(self, "Отзыв", "Не удалось отправить отзыв.").exec()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        event.accept()
        
    def closeEvent(self, event):
        self.parent().feedback_dialog = None
        super().closeEvent(event)
