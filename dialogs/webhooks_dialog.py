from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QLineEdit
from PySide6.QtCore import Qt
from utils import s
from styles import Style

class WebhooksDialog(QDialog):
    def __init__(self, parent, urls):
        super().__init__(parent)
        self.parent_dialog = parent
        self.urls = (list(urls) + [""] * 10)[:10]
        self.drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setStyleSheet(Style.main(parent.settings.app_scale))
        self.setFixedSize(s(590, parent.settings.app_scale), s(590, parent.settings.app_scale))
        self.inputs = []
        self.build()

    def build(self):
        sc = self.parent_dialog.settings.app_scale
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(22, sc), s(18, sc), s(22, sc), s(20, sc))
        layout.setSpacing(s(10, sc))

        top = QHBoxLayout()
        title = QLabel("Discord вебхуки")
        title.setObjectName("SectionTitle")
        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(34, sc), s(32, sc))
        close.clicked.connect(self.reject)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(close)
        layout.addLayout(top)

        for index in range(10):
            row = QHBoxLayout()
            row.setSpacing(s(8, sc))
            label = QLabel(f"#{index + 1}")
            label.setObjectName("FormLabel")
            label.setFixedWidth(s(26, sc))
            edit = QLineEdit()
            edit.setPlaceholderText("https://discord.com/api/webhooks/...")
            edit.setText(self.urls[index])
            self.inputs.append(edit)
            row.addWidget(label)
            row.addWidget(edit)
            layout.addLayout(row)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("Success")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("Ghost")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addStretch(1)
        layout.addLayout(buttons)

    def get_urls(self):
        return [edit.text().strip() for edit in self.inputs][:10]

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