from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from styles import Style
from utils import s


class BlockedUsersDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent.app if hasattr(parent, "app") else parent
        self.settings = self.app.settings
        self.drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.setFixedSize(s(650, self.settings.app_scale), s(470, self.settings.app_scale))
        self.build()

    def build(self):
        sc = self.settings.app_scale
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(20, sc), s(16, sc), s(20, sc), s(18, sc))
        layout.setSpacing(s(12, sc))

        top_frame = QFrame()
        top = QHBoxLayout(top_frame)
        top.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Черный список")
        title.setObjectName("SectionTitle")
        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(34, sc), s(32, sc))
        close.clicked.connect(self.accept)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(close)
        layout.addWidget(top_frame)
        top_frame.mousePressEvent = self.mousePressEvent
        top_frame.mouseMoveEvent = self.mouseMoveEvent
        top_frame.mouseReleaseEvent = self.mouseReleaseEvent
        title.mousePressEvent = self.mousePressEvent
        title.mouseMoveEvent = self.mouseMoveEvent
        title.mouseReleaseEvent = self.mouseReleaseEvent

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.host = QWidget()
        self.host.setObjectName("SettingsScrollContent")
        self.rows_layout = QVBoxLayout(self.host)
        self.rows_layout.setContentsMargins(0, 0, s(6, sc), 0)
        self.rows_layout.setSpacing(s(8, sc))
        scroll.setWidget(self.host)
        layout.addWidget(scroll, 1)
        self.refresh()

        done = QPushButton("Готово")
        done.setObjectName("Primary")
        done.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(done)
        layout.addLayout(row)

    def refresh(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        blocked = self.settings.blocked_alert_users
        if not blocked:
            self.rows_layout.addStretch(1)
            empty = QLabel("Список пуст")
            empty.setObjectName("FormLabel")
            empty.setAlignment(Qt.AlignCenter)
            self.rows_layout.addWidget(empty)
            self.rows_layout.addStretch(1)
        else:
            for user_id, nickname in blocked.items():
                self.rows_layout.addWidget(self.make_row(user_id, nickname))
            self.rows_layout.addStretch(1)

    def make_row(self, user_id: str, nickname: str):
        sc = self.settings.app_scale
        frame = QFrame()
        frame.setObjectName("SettingsGroup")
        row = QHBoxLayout(frame)
        row.setContentsMargins(s(10, sc), s(8, sc), s(10, sc), s(8, sc))
        id_label = QLabel(user_id)
        id_label.setObjectName("FormLabel")
        id_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        id_label.setToolTip(user_id)
        id_label.setMinimumWidth(s(300, sc))
        nick_label = QLabel(nickname or "Неизвестный")
        nick_label.setMinimumWidth(s(105, sc))
        remove = QPushButton("Удалить")
        remove.setObjectName("Danger")
        remove.clicked.connect(lambda checked=False, uid=user_id: self.remove_user(uid))
        row.addWidget(id_label, 1)
        row.addWidget(nick_label)
        row.addWidget(remove)
        return frame

    def remove_user(self, user_id: str):
        self.app.set_user_alert_blocked(user_id, False)
        self.refresh()

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
