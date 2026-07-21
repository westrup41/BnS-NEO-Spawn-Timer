import threading

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from styles import Style
from utils import s


class NetworkDiagnosticsDialog(QDialog):
    reconnect_finished = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent.app if hasattr(parent, "app") else parent
        self.setWindowTitle("Диагностика сети")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setStyleSheet(Style.main(self.app.settings.app_scale))
        self.resize(s(620, self.app.settings.app_scale), s(520, self.app.settings.app_scale))
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        shell = QFrame(); shell.setObjectName("Shell"); outer.addWidget(shell)
        root = QVBoxLayout(shell); root.setContentsMargins(s(18, self.app.settings.app_scale), s(14, self.app.settings.app_scale), s(18, self.app.settings.app_scale), s(16, self.app.settings.app_scale))
        header = QHBoxLayout()
        title = QLabel("Диагностика сети"); title.setObjectName("DialogTitle")
        close = QPushButton("×"); close.setObjectName("Close"); close.setFixedSize(s(34, self.app.settings.app_scale), s(32, self.app.settings.app_scale)); close.clicked.connect(self.close)
        header.addWidget(title); header.addStretch(1); header.addWidget(close); root.addLayout(header)
        self.summary = QLabel()
        self.summary.setObjectName("SettingsSectionTitle")
        root.addWidget(self.summary)
        self.rows = QVBoxLayout()
        root.addLayout(self.rows)
        root.addStretch(1)
        buttons = QHBoxLayout()
        self.reconnect_btn = QPushButton("Переподключить")
        self.reconnect_btn.setObjectName("Primary")
        self.reconnect_btn.clicked.connect(self.reconnect_async)
        self.reconnect_finished.connect(self.on_reconnect_finished)
        buttons.addWidget(self.reconnect_btn)
        buttons.addStretch(1)
        root.addLayout(buttons)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def reconnect_async(self):
        if not self.reconnect_btn.isEnabled():
            return
        self.reconnect_btn.setEnabled(False)
        self.reconnect_btn.setText("Подключение…")

        def worker():
            try:
                self.app.network.reconnect()
            finally:
                self.reconnect_finished.emit()

        threading.Thread(target=worker, daemon=True).start()

    def on_reconnect_finished(self):
        self.reconnect_btn.setEnabled(True)
        self.reconnect_btn.setText("Переподключить")
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
            box.addWidget(QLabel(f"Пинг подключения: {latency}   Ошибка: {item['last_error'] or '—'}"))
            self.rows.addWidget(card)
