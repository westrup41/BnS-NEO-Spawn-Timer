from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from styles import Style
from utils import s


class NetworkDiagnosticsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("StandaloneDialog")
        self.app = parent.app if hasattr(parent, "app") else parent
        self.setWindowTitle("Диагностика сети")
        self.setModal(False)
        self.setStyleSheet(Style.main(self.app.settings.app_scale))
        self.resize(s(620, self.app.settings.app_scale), s(590, self.app.settings.app_scale))
        root = QVBoxLayout(self)
        self.summary = QLabel()
        self.summary.setObjectName("SectionTitle")
        root.addWidget(self.summary)
        self.rows = QVBoxLayout()
        root.addLayout(self.rows)
        root.addStretch(1)
        buttons = QHBoxLayout()
        reconnect = QPushButton("Переподключить")
        reconnect.setObjectName("Primary")
        reconnect.clicked.connect(self.app.network.reconnect)
        buttons.addWidget(reconnect)
        buttons.addStretch(1)
        root.addLayout(buttons)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def _data(self):
        return self.app.network.diagnostics()

    def refresh(self):
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        data = self._data()
        self.summary.setText(f"Узлы: {sum(x['connected'] for x in data)}/{len(data)} • {self.app.network.room_label()} комната")
        for item in data:
            card = QFrame()
            card.setObjectName("SettingsGroup")
            box = QVBoxLayout(card)
            status = "● онлайн" if item["connected"] else "● офлайн"
            latency = f"{item['latency_ms']} мс" if item["latency_ms"] is not None else "—"
            box.addWidget(QLabel(f"{item['host']}:{item['port']}   {status}"))
            box.addWidget(QLabel(f"Время подключения: {latency}   Ошибка: {item['last_error'] or '—'}"))
            self.rows.addWidget(card)
