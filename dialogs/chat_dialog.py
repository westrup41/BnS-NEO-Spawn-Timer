from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QEvent, QPoint
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMenu, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from config import CHAT_MAX_LENGTH, COLORS
from styles import Style
from utils import s


class ChatDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.settings = parent.settings
        self.drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.setFixedSize(s(500, self.settings.app_scale), s(590, self.settings.app_scale))
        self.build()
        self.refresh_messages(scroll_to_bottom=True)

    def build(self):
        sc = self.settings.app_scale
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame()
        shell.setObjectName("Shell")
        self.shell = shell
        root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(18, sc), s(16, sc), s(18, sc), s(18, sc))
        layout.setSpacing(s(10, sc))

        top = QHBoxLayout()
        title = QLabel("Чат")
        title.setObjectName("SectionTitle")
        self.online_label = QLabel()
        self.online_label.setObjectName("FormLabel")
        close = QPushButton("—")
        close.setObjectName("Chrome")
        close.setFixedSize(s(34, sc), s(32, sc))
        close.setToolTip("Свернуть чат")
        close.clicked.connect(self.hide)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.online_label)
        top.addWidget(close)
        layout.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ChatScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.message_host = QWidget()
        self.message_host.setObjectName("ChatContent")
        self.messages_layout = QVBoxLayout(self.message_host)
        self.messages_layout.setContentsMargins(0, 0, s(6, sc), 0)
        self.messages_layout.setSpacing(s(8, sc))
        self.messages_layout.addStretch(1)
        self.scroll.setWidget(self.message_host)
        layout.addWidget(self.scroll, 1)

        self.emoji_panel = QFrame(shell)
        self.emoji_panel.setObjectName("EmojiPanel")
        emoji_grid = QGridLayout(self.emoji_panel)
        emoji_grid.setContentsMargins(s(8, sc), s(8, sc), s(8, sc), s(8, sc))
        emoji_grid.setSpacing(s(4, sc))
        emojis = ["🗿", "6️⃣7️⃣", "💩", "🤡", "💀", "😭", "😂", "🤣", "🔥", "👀",
                  "🤔", "😎", "🥶", "🫡", "🤝", "👍", "👎", "❤️", "🙏", "🚨"]
        for index, emoji in enumerate(emojis):
            button = QPushButton(emoji)
            button.setObjectName("EmojiButton")
            button.setFixedSize(s(42, sc), s(34, sc))
            button.setAutoDefault(False)
            button.clicked.connect(lambda checked=False, value=emoji: self.insert_emoji(value))
            emoji_grid.addWidget(button, index // 8, index % 8)
        self.emoji_panel.adjustSize()
        self.emoji_panel.hide()

        input_row = QHBoxLayout()
        input_row.setSpacing(s(8, sc))
        self.emoji_btn = QPushButton("😊")
        self.emoji_btn.setObjectName("EmojiPickerButton")
        self.emoji_btn.setToolTip("Частые эмодзи")
        self.emoji_btn.setFixedSize(s(42, sc), s(38, sc))
        self.emoji_btn.setAutoDefault(False)
        self.emoji_btn.clicked.connect(self.toggle_emoji_panel)
        self.input = QLineEdit()
        self.input.setMaxLength(CHAT_MAX_LENGTH)
        self.input.setPlaceholderText("Сообщение…")
        self.input.textChanged.connect(self.update_counter)
        self.input.installEventFilter(self)
        self.counter = QLabel(f"0/{CHAT_MAX_LENGTH}")
        self.counter.setObjectName("FormLabel")
        self.send_btn = QPushButton("Отправить")
        self.send_btn.setObjectName("Primary")
        self.send_btn.setAutoDefault(False)
        self.send_btn.setDefault(False)
        self.send_btn.clicked.connect(self.send_message)
        input_row.addWidget(self.emoji_btn)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.counter)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)
        self.update_enabled_state()
        self.update_online_state(self.app.internet_available)

        top_widget = title.parentWidget() or shell
        top_widget.mousePressEvent = self.mousePressEvent
        top_widget.mouseMoveEvent = self.mouseMoveEvent
        top_widget.mouseReleaseEvent = self.mouseReleaseEvent

    def update_enabled_state(self):
        chat_enabled = bool(self.settings.chat_enabled)
        enabled = chat_enabled and bool(self.app.internet_available)
        self.input.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.emoji_btn.setEnabled(enabled)
        if not chat_enabled:
            self.input.setPlaceholderText("Чат отключён в онлайн-функциях")
        elif not self.app.internet_available:
            self.input.setPlaceholderText("Нет подключения к онлайн-узлам")
        else:
            self.input.setPlaceholderText("Сообщение…")

    def update_online_state(self, available):
        self.online_label.setText("● онлайн" if available else "● нет сети")
        self.online_label.setStyleSheet(
            f"color: {COLORS['success'] if available else COLORS['text_disabled']};"
        )
        self.update_enabled_state()

    def update_counter(self, text):
        self.counter.setText(f"{len(text)}/{CHAT_MAX_LENGTH}")

    def send_message(self):
        text = self.input.text().strip()
        if not text or not self.settings.chat_enabled:
            return
        if self.app.send_chat_message(text[:CHAT_MAX_LENGTH]):
            self.input.clear()

    def insert_emoji(self, value: str):
        current = self.input.text()
        cursor = self.input.cursorPosition()
        room = CHAT_MAX_LENGTH - len(current)
        if room <= 0:
            return
        value = value[:room]
        self.input.setText(current[:cursor] + value + current[cursor:])
        self.input.setCursorPosition(cursor + len(value))
        self.input.setFocus()

    def toggle_emoji_panel(self):
        if self.emoji_panel.isVisible():
            self.emoji_panel.hide()
            return
        self.emoji_panel.adjustSize()
        point = self.emoji_btn.mapTo(self.shell, QPoint(0, 0))
        x = max(s(10, self.settings.app_scale), point.x())
        y = max(
            s(48, self.settings.app_scale),
            point.y() - self.emoji_panel.height() - s(8, self.settings.app_scale),
        )
        self.emoji_panel.move(x, y)
        self.emoji_panel.show()
        self.emoji_panel.raise_()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.input.hasFocus():
            self.send_message()
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event):
        if watched is self.input and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.send_message()
                return True
        return super().eventFilter(watched, event)

    def reject(self):
        # Закрытие чата контролируется только кнопкой в заголовке.
        return

    def refresh_messages(self, scroll_to_bottom=False):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(1)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for message in self.app.chat_history.all():
            self.messages_layout.addWidget(self.make_message(message))
        if scroll_to_bottom:
            self.schedule_scroll_to_bottom()

    def schedule_scroll_to_bottom(self):
        def scroll():
            bar = self.scroll.verticalScrollBar()
            bar.setValue(bar.maximum())
        QTimer.singleShot(0, scroll)
        QTimer.singleShot(50, scroll)
        QTimer.singleShot(150, scroll)

    def make_message(self, message):
        sc = self.settings.app_scale
        card = QFrame()
        card.setObjectName("ChatMessage")
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda position, item=message, widget=card: self.open_message_menu(widget, position, item)
        )
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        box = QVBoxLayout(card)
        box.setContentsMargins(s(11, sc), s(8, sc), s(11, sc), s(8, sc))
        box.setSpacing(s(4, sc))

        header = QHBoxLayout()
        reputation = self.app.chat_history.reputation(message.get("author_id", ""))
        nick = QLabel(f"{message.get('nickname', 'Неизвестный')}  •  репутация {reputation:+d}")
        nick.setObjectName("ChatNick")
        try:
            timestamp = datetime.fromisoformat(message.get("timestamp", ""))
            time_text = timestamp.strftime("%H:%M")
        except Exception:
            time_text = ""
        time_label = QLabel(time_text)
        time_label.setObjectName("FormLabel")
        header.addWidget(nick)
        header.addStretch(1)
        header.addWidget(time_label)
        box.addLayout(header)

        if self.app.is_user_alert_blocked(message.get("author_id", "")):
            marker = QLabel("Алерты пользователя заблокированы")
            marker.setObjectName("FormLabel")
            box.addWidget(marker)

        text = QLabel(message.get("message", ""))
        text.setObjectName("ChatText")
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        box.addWidget(text)

        if message.get("type") == "spawn":
            reactions = message.get("reactions", {})
            likes = sum(1 for value in reactions.values() if value > 0)
            dislikes = sum(1 for value in reactions.values() if value < 0)
            own_vote = reactions.get(self.app.get_user_id(), 0)
            reaction_row = QHBoxLayout()
            reaction_row.addStretch(1)
            like = QPushButton(f"👍 {likes}")
            dislike = QPushButton(f"👎 {dislikes}")
            like.setObjectName("Success" if own_vote > 0 else "Ghost")
            dislike.setObjectName("Danger" if own_vote < 0 else "Ghost")
            like.clicked.connect(lambda checked=False, mid=message["id"]: self.app.react_to_message(mid, 1))
            dislike.clicked.connect(lambda checked=False, mid=message["id"]: self.app.react_to_message(mid, -1))
            reaction_row.addWidget(like)
            reaction_row.addWidget(dislike)
            box.addLayout(reaction_row)
        return card

    def open_message_menu(self, card, position, message):
        user_id = str(message.get("author_id") or "")
        if not user_id or user_id == self.app.get_user_id():
            return
        blocked = self.app.is_user_alert_blocked(user_id)
        chat_blocked = self.app.is_user_chat_blocked(user_id)
        menu = QMenu(self)
        action = menu.addAction(
            "Разблокировать алерты этого пользователя" if blocked
            else "Заблокировать алерты этого пользователя"
        )
        chat_action = menu.addAction(
            "Разблокировать сообщения этого пользователя" if chat_blocked
            else "Блокировать сообщения этого пользователя"
        )
        copy_id = menu.addAction("Копировать User ID")
        copy_message_id = menu.addAction("Копировать ID сообщения")
        selected = menu.exec(card.mapToGlobal(position))
        if selected is action:
            self.app.set_user_alert_blocked(
                user_id,
                not blocked,
                str(message.get("nickname") or "Неизвестный"),
            )
            self.refresh_messages(scroll_to_bottom=False)
        elif selected is chat_action:
            self.app.set_user_chat_blocked(
                user_id, not chat_blocked,
                str(message.get("nickname") or "Неизвестный"),
            )
        elif selected is copy_id:
            QApplication.clipboard().setText(user_id)
        elif selected is copy_message_id:
            QApplication.clipboard().setText(str(message.get("id") or ""))

    def showEvent(self, event):
        super().showEvent(event)
        self.app.set_chat_unread(False)
        self.refresh_messages(scroll_to_bottom=True)

    def closeEvent(self, event):
        self.app.chat_dialog = None
        super().closeEvent(event)

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
