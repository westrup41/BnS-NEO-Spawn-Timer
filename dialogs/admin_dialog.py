from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from dialogs.message_dialog import MessageDialog
from styles import Style


class AdminDialog(QDialog):
    ACTIONS = [
        ("Очистить чат у всех", "clear_chat"),
        ("Удалить сообщение по ID", "delete_message"),
        ("Заблокировать User ID глобально", "ban_user"),
        ("Разблокировать User ID глобально", "unban_user"),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("StandaloneDialog")
        self.app = parent.app if hasattr(parent, "app") else parent
        self.setWindowTitle("Администрирование")
        self.setModal(True)
        self.setStyleSheet(Style.main(self.app.settings.app_scale))
        self.resize(520, 230)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Подписанная команда будет применена во всех комнатах."))
        self.action = QComboBox()
        for label, value in self.ACTIONS:
            self.action.addItem(label, value)
        self.target = QLineEdit()
        self.target.setPlaceholderText("ID сообщения или User ID (для очистки не нужен)")
        root.addWidget(self.action)
        root.addWidget(self.target)
        row = QHBoxLayout()
        send = QPushButton("Отправить")
        send.setObjectName("Danger")
        send.clicked.connect(self.send)
        cancel = QPushButton("Отмена")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(send)
        row.addWidget(cancel)
        root.addLayout(row)

    def send(self):
        action = self.action.currentData()
        target = self.target.text().strip()
        if action != "clear_chat" and not target:
            MessageDialog(self, "Нужен ID", "Введите ID сообщения или User ID.").exec()
            return
        if not MessageDialog(
            self, "Подтвердите команду",
            "Действие распространится на всех пользователей программы.",
            ok_text="Отправить", cancel_text="Отмена",
        ).exec_result():
            return
        if self.app.network.send_admin_command(action, target):
            MessageDialog(self, "Команда отправлена", "Подписанная команда опубликована.").exec()
            self.accept()
        else:
            MessageDialog(self, "Ошибка", "Нет сети или админ-ключ недоступен.").exec()
