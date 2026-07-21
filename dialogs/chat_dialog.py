from datetime import datetime

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu,
    QPushButton, QScrollArea, QSizePolicy, QTextEdit, QVBoxLayout, QWidget,
)

from config import CHAT_MAX_LENGTH, COLORS
from resources import resource_path, ui_icon
from styles import Style
from utils import s
from widgets.avatar import avatar_pixmap
from widgets.ui_primitives import ArtworkShell


class ComposerEdit(QTextEdit):
    def __init__(self, scale, parent=None):
        super().__init__(parent)
        self.scale = scale
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.textChanged.connect(self.adjust_height)
        self.adjust_height()

    def adjust_height(self):
        width = max(80, self.viewport().width())
        self.document().setTextWidth(width)
        wanted = int(self.document().size().height()) + s(14, self.scale)
        self.setFixedHeight(max(s(38, self.scale), min(s(104, self.scale), wanted)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_height()


class ChatDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.settings = parent.settings
        self.drag_pos = None
        self._rendered_signature = None
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.setFixedSize(s(370, self.settings.app_scale), max(s(520, self.settings.app_scale), parent.height()))
        self.build()
        self.refresh_messages(scroll_to_bottom=True)

    def build(self):
        sc = self.settings.app_scale
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        shell = ArtworkShell(self.app, "assets/themes/blade_soul_chat.png", opacity=0.40); self.shell = shell; root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(14, sc), s(14, sc), s(14, sc), s(14, sc)); layout.setSpacing(s(9, sc))

        top_frame = QFrame(); top_frame.setObjectName("ChatHeader")
        top = QHBoxLayout(top_frame); top.setContentsMargins(s(4, sc), 0, 0, 0)
        title = QLabel("Чат"); title.setObjectName("SectionTitle")
        self.online_label = QLabel(); self.online_label.setObjectName("FormLabel")
        close = QPushButton(""); self.close_btn = close; close.setObjectName("Chrome"); close.setIcon(ui_icon("minimize"))
        close.setIconSize(QSize(s(18, sc), s(18, sc))); close.setFixedSize(s(34, sc), s(32, sc)); close.clicked.connect(self.app.hide_chat_panel)
        top.addWidget(title); top.addStretch(1); top.addWidget(self.online_label); top.addWidget(close)
        layout.addWidget(top_frame)

        self.scroll = QScrollArea(); self.scroll.setObjectName("ChatScroll"); self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame); self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.message_host = QWidget(); self.message_host.setObjectName("ChatContent")
        self.messages_layout = QVBoxLayout(self.message_host)
        self.messages_layout.setContentsMargins(0, s(4, sc), s(5, sc), s(4, sc)); self.messages_layout.setSpacing(s(9, sc))
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.message_host); layout.addWidget(self.scroll, 1)

        self.emoji_panel = QFrame(shell); self.emoji_panel.setObjectName("EmojiPanel")
        emoji_grid = QGridLayout(self.emoji_panel); emoji_grid.setContentsMargins(s(8, sc), s(8, sc), s(8, sc), s(8, sc)); emoji_grid.setSpacing(s(4, sc))
        emojis = ["🗿", "6️⃣7️⃣", "💩", "🤡", "💀", "😭", "😂", "🤣", "🔥", "👀", "🤔", "😎", "🥶", "🫡", "🤝", "👍", "👎", "❤️", "🙏", "🚨"]
        for index, emoji in enumerate(emojis):
            button = QPushButton(emoji); button.setObjectName("EmojiButton"); button.setFixedSize(s(38, sc), s(34, sc)); button.setAutoDefault(False)
            button.clicked.connect(lambda checked=False, value=emoji: self.insert_emoji(value)); emoji_grid.addWidget(button, index // 7, index % 7)
        self.emoji_panel.adjustSize(); self.emoji_panel.hide()

        composer = QFrame(); composer.setObjectName("ChatComposer")
        composer_row = QHBoxLayout(composer); composer_row.setContentsMargins(s(5, sc), s(4, sc), s(5, sc), s(4, sc)); composer_row.setSpacing(s(5, sc))
        self.emoji_btn = QPushButton(""); self.emoji_btn.setObjectName("ComposerCircle"); self.emoji_btn.setFixedSize(s(36, sc), s(36, sc)); self.emoji_btn.setIcon(ui_icon("emoji_face")); self.emoji_btn.setIconSize(QSize(s(19, sc), s(19, sc))); self.emoji_btn.clicked.connect(self.toggle_emoji_panel)
        self.input = ComposerEdit(sc); self.input.setObjectName("ChatInput"); self.input.setPlaceholderText("Сообщение…"); self.input.textChanged.connect(self.update_counter); self.input.installEventFilter(self)
        self.send_btn = QPushButton(""); self.send_btn.setObjectName("ComposerSend"); self.send_btn.setFixedSize(s(36, sc), s(36, sc))
        self.send_btn.setIcon(QIcon(resource_path("assets/icons/send_up.png"))); self.send_btn.setIconSize(QSize(s(18, sc), s(18, sc))); self.send_btn.clicked.connect(self.send_message)
        composer_row.addWidget(self.emoji_btn, 0, Qt.AlignBottom); composer_row.addWidget(self.input, 1); composer_row.addWidget(self.send_btn, 0, Qt.AlignBottom)
        layout.addWidget(composer)
        self.counter = QLabel(f"0/{CHAT_MAX_LENGTH}"); self.counter.setObjectName("ChatCounter"); self.counter.setAlignment(Qt.AlignRight); layout.addWidget(self.counter)
        self.update_online_state(self.app.internet_available)

        top_frame.mousePressEvent = self.mousePressEvent; top_frame.mouseMoveEvent = self.mouseMoveEvent; top_frame.mouseReleaseEvent = self.mouseReleaseEvent

    def update_enabled_state(self):
        enabled = bool(self.settings.chat_enabled and self.app.internet_available)
        for widget in (self.input, self.send_btn, self.emoji_btn): widget.setEnabled(enabled)
        self.input.setPlaceholderText("Сообщение…" if enabled else "Нет подключения" if self.settings.chat_enabled else "Чат отключён")

    def update_online_state(self, available):
        self.online_label.setText("● онлайн" if available else "● нет сети")
        self.online_label.setStyleSheet(f"color: {COLORS['success'] if available else COLORS['text_disabled']};")
        self.update_enabled_state()

    def update_counter(self):
        text = self.input.toPlainText()
        if len(text) > CHAT_MAX_LENGTH:
            position = self.input.textCursor().position()
            self.input.blockSignals(True); self.input.setPlainText(text[:CHAT_MAX_LENGTH]); self.input.blockSignals(False)
            cursor = self.input.textCursor(); cursor.setPosition(min(position, CHAT_MAX_LENGTH)); self.input.setTextCursor(cursor)
            text = self.input.toPlainText()
        self.counter.setText(f"{len(text)}/{CHAT_MAX_LENGTH}")
        self.input.adjust_height()

    def send_message(self):
        text = self.input.toPlainText().strip()
        if text and self.settings.chat_enabled and self.app.send_chat_message(text[:CHAT_MAX_LENGTH]):
            self.input.clear(); self.input.adjust_height()

    def insert_emoji(self, value):
        cursor = self.input.textCursor(); current = self.input.toPlainText(); room = CHAT_MAX_LENGTH - len(current)
        if room <= 0: return
        cursor.insertText(value[:room]); self.input.setTextCursor(cursor); self.input.setFocus()

    def toggle_emoji_panel(self):
        if self.emoji_panel.isVisible(): self.emoji_panel.hide(); return
        self.emoji_panel.adjustSize(); point = self.emoji_btn.mapTo(self.shell, QPoint(0, 0))
        self.emoji_panel.move(max(s(8, self.settings.app_scale), point.x()), max(s(44, self.settings.app_scale), point.y() - self.emoji_panel.height() - s(8, self.settings.app_scale)))
        self.emoji_panel.show(); self.emoji_panel.raise_()

    def eventFilter(self, watched, event):
        if watched is self.input and event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self.send_message(); return True
        return super().eventFilter(watched, event)

    def reject(self):
        self.app.hide_chat_panel()

    def apply_visual_settings(self):
        """Refresh the live panel after changing theme without losing its history."""
        self.setFixedSize(s(370, self.settings.app_scale), max(s(520, self.settings.app_scale), self.app.height()))
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.close_btn.setIcon(ui_icon("minimize"))
        self.emoji_btn.setIcon(ui_icon("emoji_face"))
        self.shell.update()
        self.update_online_state(self.app.internet_available)
        self.refresh_messages(scroll_to_bottom=True, force=True)

    def refresh_messages(self, scroll_to_bottom=False, force=False):
        messages = self.app.chat_history.all()
        signature = tuple(
            (item.get("id"), tuple(sorted(item.get("reactions", {}).items())))
            for item in messages
        )
        if not force and signature == self._rendered_signature:
            if scroll_to_bottom:
                self.schedule_scroll_to_bottom()
            return
        self._rendered_signature = signature
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0); widget = item.widget()
            if widget is not None:
                widget.hide(); widget.setParent(None); widget.deleteLater()
        if messages:
            for message in messages:
                self.messages_layout.addWidget(self.make_message(message))
        else:
            empty = QLabel("Сообщений пока нет")
            empty.setObjectName("ChatEmptyState")
            empty.setAlignment(Qt.AlignCenter)
            self.messages_layout.addWidget(empty)
        if scroll_to_bottom: self.schedule_scroll_to_bottom()

    def schedule_scroll_to_bottom(self):
        def scroll():
            bar = self.scroll.verticalScrollBar(); bar.setValue(bar.maximum())
        QTimer.singleShot(0, scroll); QTimer.singleShot(80, scroll); QTimer.singleShot(260, scroll)

    def make_message(self, message):
        sc = self.settings.app_scale
        row = QWidget(); row.setObjectName("ChatMessageRow"); row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum); outer = QHBoxLayout(row); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(s(8, sc))
        avatar = QLabel(); avatar.setPixmap(avatar_pixmap(message.get("avatar_id", -1), s(42, sc))); avatar.setFixedSize(s(42, sc), s(42, sc)); avatar.setAlignment(Qt.AlignTop)
        outer.addWidget(avatar, 0, Qt.AlignTop)
        bubble = QFrame(); bubble.setObjectName("ChatBubble"); bubble.setContextMenuPolicy(Qt.CustomContextMenu)
        bubble.customContextMenuRequested.connect(lambda position, item=message, widget=bubble: self.open_message_menu(widget, position, item))
        bubble.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        box = QVBoxLayout(bubble); box.setContentsMargins(s(10, sc), s(7, sc), s(10, sc), s(7, sc)); box.setSpacing(s(4, sc))
        header = QHBoxLayout(); header.setSpacing(s(6, sc))
        reputation = self.app.chat_history.reputation(message.get("author_id", ""))
        nick = QLabel(str(message.get("nickname") or "Неизвестный")); nick.setObjectName("ChatNick")
        rep_text = f"{reputation:+d}" + (" ★" if reputation >= 20 else "")
        rep = QLabel(rep_text); rep.setObjectName("ChatReputation")
        rep.setProperty("tone", "positive" if reputation >= 6 else "negative" if reputation <= -6 else "neutral")
        try: time_text = datetime.fromisoformat(str(message.get("timestamp") or "")).strftime("%H:%M")
        except Exception: time_text = ""
        time_label = QLabel(time_text); time_label.setObjectName("ChatTime")
        header.addWidget(nick); header.addWidget(rep); header.addStretch(1); header.addWidget(time_label); box.addLayout(header)
        text = QLabel(str(message.get("message") or "")); text.setObjectName("ChatText"); text.setWordWrap(True); text.setTextInteractionFlags(Qt.TextSelectableByMouse); box.addWidget(text)
        if message.get("type") == "spawn":
            reactions = message.get("reactions", {}); likes = sum(1 for value in reactions.values() if value > 0); dislikes = sum(1 for value in reactions.values() if value < 0); own = reactions.get(self.app.get_user_id(), 0)
            chips = QHBoxLayout(); chips.setSpacing(s(5, sc))
            like = QPushButton(f"👍  {likes}"); dislike = QPushButton(f"👎  {dislikes}")
            like.setObjectName("ReactionChip"); dislike.setObjectName("ReactionChip"); like.setProperty("active", "true" if own > 0 else "false"); dislike.setProperty("active", "true" if own < 0 else "false")
            like.clicked.connect(lambda checked=False, mid=message["id"]: self.app.react_to_message(mid, 1)); dislike.clicked.connect(lambda checked=False, mid=message["id"]: self.app.react_to_message(mid, -1))
            chips.addWidget(like); chips.addWidget(dislike); chips.addStretch(1); box.addLayout(chips)
        outer.addWidget(bubble, 1)
        return row

    def open_message_menu(self, card, position, message):
        user_id = str(message.get("author_id") or "")
        if not user_id or user_id == self.app.get_user_id(): return
        blocked = self.app.is_user_alert_blocked(user_id); chat_blocked = self.app.is_user_chat_blocked(user_id)
        menu = QMenu(self); alert_action = menu.addAction("Разблокировать алерты" if blocked else "Блокировать алерты"); chat_action = menu.addAction("Разблокировать сообщения" if chat_blocked else "Блокировать сообщения"); copy_id = menu.addAction("Копировать User ID"); copy_message_id = menu.addAction("Копировать ID сообщения")
        selected = menu.exec(card.mapToGlobal(position))
        if selected is alert_action: self.app.set_user_alert_blocked(user_id, not blocked, str(message.get("nickname") or "Неизвестный")); self.refresh_messages(False)
        elif selected is chat_action: self.app.set_user_chat_blocked(user_id, not chat_blocked, str(message.get("nickname") or "Неизвестный"))
        elif selected is copy_id: QApplication.clipboard().setText(user_id)
        elif selected is copy_message_id: QApplication.clipboard().setText(str(message.get("id") or ""))

    def showEvent(self, event):
        super().showEvent(event); self.app.set_chat_unread(False); self.refresh_messages(True)

    def closeEvent(self, event):
        self.app.chat_dialog = None; super().closeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()
    def mouseMoveEvent(self, event):
        if self.drag_pos is not None: self.move(event.globalPosition().toPoint() - self.drag_pos); event.accept()
    def mouseReleaseEvent(self, event): self.drag_pos = None; event.accept()
