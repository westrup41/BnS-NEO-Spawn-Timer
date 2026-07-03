import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QLineEdit, QCheckBox, QScrollArea, QWidget, QFileDialog, QMessageBox
from PySide6.QtCore import Qt
from utils import s
from styles import Style
from widgets.slider import DiscordSlider
from dialogs.webhooks_dialog import WebhooksDialog
from services.audio import stop_alert_sound, play_alert, resolve_audio_path, copy_custom_sound_to_storage

class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.settings = parent.settings
        self.drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.setFixedSize(s(430, self.settings.app_scale), s(790, self.settings.app_scale))
        self.build()

    def build(self):
        sc = self.settings.app_scale
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(22, sc), s(18, sc), s(22, sc), s(20, sc))
        layout.setSpacing(s(12, sc))

        top = QHBoxLayout()
        title = QLabel("Настройки")
        title.setObjectName("SectionTitle")
        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(34, sc), s(32, sc))
        close.clicked.connect(self.reject)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(close)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setViewportMargins(0, 0, s(6, sc), 0)
        scroll_widget = QWidget()
        scroll_widget.setObjectName("SettingsScrollContent")
        content_layout = QVBoxLayout(scroll_widget)
        content_layout.setContentsMargins(0, 0, s(8, sc), 0)
        content_layout.setSpacing(s(12, sc))

        sound_group = QFrame()
        sound_group.setObjectName("SettingsGroup")
        sound_layout = QVBoxLayout(sound_group)
        sound_layout.setContentsMargins(s(14, sc), s(2, sc), s(14, sc), s(12, sc))
        sound_layout.setSpacing(s(6, sc))
        sound_title = QLabel("Звук")
        sound_title.setObjectName("GroupTitle")
        sound_layout.addWidget(sound_title)
        sound_layout.addSpacing(s(8, sc))
        self.sound = QCheckBox("Звуковое оповещение за 10 минут до события")
        self.sound.setChecked(self.settings.sound_enabled)
        sound_layout.addWidget(self.sound)

        sound_layout.addSpacing(s(8, sc))
        self.sound_volume_label = QLabel()
        self.sound_volume_label.setObjectName("FormLabel")
        self.sound_volume_slider = DiscordSlider(sc)
        self.sound_volume_slider.setRange(0, 100)
        self.sound_volume_slider.setValue(int(self.settings.sound_volume if self.settings.sound_enabled else 0))
        self.sound.toggled.connect(self.on_sound_toggled)
        self.sound_volume_slider.valueChanged.connect(self.on_sound_volume_changed)
        sound_layout.addWidget(self.sound_volume_label)
        sound_layout.addWidget(self.sound_volume_slider)

        sound_layout.addSpacing(s(8, sc))
        custom_sound_label = QLabel("Кастомный звук оповещения")
        custom_sound_label.setObjectName("FormLabel")
        custom_sound_label.setWordWrap(True)
        sound_layout.addWidget(custom_sound_label)
        sound_row = QHBoxLayout()
        sound_row.setSpacing(s(8, sc))
        self.custom_sound_value = self.settings.custom_sound_path
        self.test_sound_active = False
        self.browse_sound_btn = QPushButton("Выбрать")
        self.browse_sound_btn.setObjectName("Ghost")
        self.browse_sound_btn.setFixedWidth(s(100, sc))
        self.browse_sound_btn.clicked.connect(self.choose_custom_sound)
        self.clear_sound_btn = QPushButton("×")
        self.clear_sound_btn.setObjectName("Ghost")
        self.clear_sound_btn.setFixedWidth(s(34, sc))
        self.clear_sound_btn.clicked.connect(self.clear_custom_sound)
        self.test_sound_btn = QPushButton("Проверить")
        self.test_sound_btn.setObjectName("Primary")
        self.test_sound_btn.setFixedWidth(s(108, sc))
        self.test_sound_btn.clicked.connect(self.test_custom_sound)
        sound_row.addWidget(self.browse_sound_btn)
        sound_row.addWidget(self.clear_sound_btn)
        sound_row.addWidget(self.test_sound_btn)
        sound_row.addStretch(1)
        sound_layout.addLayout(sound_row)
        self.update_custom_sound_button()
        content_layout.addWidget(sound_group)

        discord_group = QFrame()
        discord_group.setObjectName("SettingsGroup")
        discord_layout = QVBoxLayout(discord_group)
        discord_layout.setContentsMargins(s(14, sc), s(12, sc), s(14, sc), s(12, sc))
        discord_layout.setSpacing(s(8, sc))
        discord_title = QLabel("Discord-оповещения")
        discord_title.setObjectName("GroupTitle")
        discord_layout.addWidget(discord_title)

        nick_label = QLabel("Никнейм отправителя")
        nick_label.setObjectName("FormLabel")
        self.discord_nickname = QLineEdit()
        self.discord_nickname.setPlaceholderText("Например: Westrup")
        self.discord_nickname.setText(self.settings.discord_nickname)
        discord_layout.addWidget(nick_label)
        discord_layout.addWidget(self.discord_nickname)

        webhook_row = QHBoxLayout()
        webhook_row.setSpacing(s(8, sc))
        self.webhooks_btn = QPushButton("Вебхуки")
        self.webhooks_btn.setObjectName("Primary")
        self.webhooks_btn.setFixedWidth(s(112, sc))
        self.webhooks_btn.clicked.connect(self.open_webhooks_dialog)
        webhook_row.addWidget(self.webhooks_btn)
        webhook_row.addStretch(1)
        discord_layout.addLayout(webhook_row)
        self.discord_webhooks = (list(self.settings.discord_webhooks) + [""] * 10)[:10]
        content_layout.addWidget(discord_group)

        ui_group = QFrame()
        ui_group.setObjectName("SettingsGroup")
        ui_layout = QVBoxLayout(ui_group)
        ui_layout.setContentsMargins(s(14, sc), s(12, sc), s(14, sc), s(12, sc))
        ui_layout.setSpacing(s(6, sc))
        ui_title = QLabel("Интерфейс")
        ui_title.setObjectName("GroupTitle")
        ui_layout.addWidget(ui_title)
        ui_layout.addSpacing(s(8, sc))

        self.app_scale_label = QLabel()
        self.app_scale_label.setObjectName("FormLabel")
        self.app_scale_slider = DiscordSlider(sc)
        self.app_scale_slider.setRange(82, 122)
        self.app_scale_slider.setValue(int(self.settings.app_scale * 100))
        self.app_scale_slider.valueChanged.connect(self.update_labels)
        ui_layout.addWidget(self.app_scale_label)
        ui_layout.addWidget(self.app_scale_slider)
        content_layout.addWidget(ui_group)

        overlay_group = QFrame()
        overlay_group.setObjectName("SettingsGroup")
        overlay_layout = QVBoxLayout(overlay_group)
        overlay_layout.setContentsMargins(s(14, sc), s(12, sc), s(14, sc), s(12, sc))
        overlay_layout.setSpacing(s(6, sc))
        overlay_title = QLabel("Оверлей")
        overlay_title.setObjectName("GroupTitle")
        overlay_layout.addWidget(overlay_title)
        overlay_layout.addSpacing(s(8, sc))

        self.overlay = QCheckBox("Включить оверлей:")
        self.overlay.setChecked(self.settings.overlay_enabled)
        self.block1 = QCheckBox("Императорское древо")
        self.block1.setChecked(self.settings.overlay_block1)
        self.block3 = QCheckBox("Мировой босс")
        self.block3.setChecked(self.settings.overlay_block3)
        self.lock = QCheckBox("Закрепить оверлей")
        self.lock.setChecked(self.settings.overlay_locked)

        overlay_layout.addWidget(self.overlay)
        overlay_layout.addLayout(self._indented_checkbox(self.block1, sc))
        overlay_layout.addLayout(self._indented_checkbox(self.block3, sc))
        overlay_layout.addWidget(self.lock)

        self.overlay.toggled.connect(self.on_overlay_toggled)
        self.block1.toggled.connect(self.on_overlay_block_toggled)
        self.block3.toggled.connect(self.on_overlay_block_toggled)

        overlay_layout.addSpacing(s(8, sc))
        self.alpha_label = QLabel()
        self.alpha_label.setObjectName("FormLabel")
        self.alpha_slider = DiscordSlider(sc)
        self.alpha_slider.setRange(20, 100)
        self.alpha_slider.setValue(int(self.settings.overlay_alpha * 100))
        self.alpha_slider.valueChanged.connect(self.update_labels)
        overlay_layout.addWidget(self.alpha_label)
        overlay_layout.addWidget(self.alpha_slider)

        self.overlay_scale_label = QLabel()
        self.overlay_scale_label.setObjectName("FormLabel")
        self.overlay_scale_slider = DiscordSlider(sc)
        self.overlay_scale_slider.setRange(70, 160)
        self.overlay_scale_slider.setValue(int(self.settings.overlay_scale * 100))
        self.overlay_scale_slider.valueChanged.connect(self.update_labels)
        overlay_layout.addWidget(self.overlay_scale_label)
        overlay_layout.addWidget(self.overlay_scale_slider)
        content_layout.addWidget(overlay_group)
        content_layout.addStretch(1)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        apply_btn = QPushButton("Применить")
        apply_btn.setObjectName("Primary")
        apply_btn.clicked.connect(self.apply)
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("Success")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("Ghost")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        self.update_labels()

    def on_sound_toggled(self, checked: bool):
        if checked:
            if self.sound_volume_slider.value() <= 0:
                self.sound_volume_slider.setValue(50)
        else:
            if self.sound_volume_slider.value() != 0:
                self.sound_volume_slider.setValue(0)
        self.update_labels()

    def on_sound_volume_changed(self, value: int):
        self.sound.blockSignals(True)
        self.sound.setChecked(value > 0)
        self.sound.blockSignals(False)
        self.update_labels()

    def update_custom_sound_button(self):
        selected = bool(getattr(self, "custom_sound_value", ""))
        self.browse_sound_btn.setText("Выбрано" if selected else "Выбрать")
        self.browse_sound_btn.setObjectName("Success" if selected else "Ghost")
        self.browse_sound_btn.style().unpolish(self.browse_sound_btn)
        self.browse_sound_btn.style().polish(self.browse_sound_btn)
        self.clear_sound_btn.setEnabled(selected)

    def _finish_test_sound(self):
        if not getattr(self, "test_sound_active", False):
            return
        self.test_sound_active = False
        self.test_sound_btn.setText("Проверить")
        self.test_sound_btn.setObjectName("Primary")
        self.test_sound_btn.style().unpolish(self.test_sound_btn)
        self.test_sound_btn.style().polish(self.test_sound_btn)

    def test_custom_sound(self):
        if getattr(self, "test_sound_active", False):
            stop_alert_sound()
            self._finish_test_sound()
            return
        stop_alert_sound()
        volume = self.sound_volume_slider.value()
        if volume <= 0: return
        self.test_sound_active = True
        self.test_sound_btn.setText("Стоп")
        self.test_sound_btn.setObjectName("Danger")
        self.test_sound_btn.style().unpolish(self.test_sound_btn)
        self.test_sound_btn.style().polish(self.test_sound_btn)
        started = play_alert(True, self.custom_sound_value, volume, on_finished=self._finish_test_sound)
        if not started: self._finish_test_sound()

    def clear_custom_sound(self):
        self.custom_sound_value = ""
        self.update_custom_sound_button()

    def choose_custom_sound(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать звук оповещения", "", "Аудиофайлы (*.wav *.mp3 *.ogg *.flac *.m4a *.aac *.wma);;Все файлы (*.*)")
        if not path: return
        try:
            stored_path = copy_custom_sound_to_storage(path)
            if not stored_path:
                QMessageBox.warning(self, "Звук", "Не удалось скопировать файл.")
                return
            self.custom_sound_value = stored_path
            self.update_custom_sound_button()
        except Exception as exc:
            QMessageBox.warning(self, "Звук", f"Не удалось скопировать файл:\n{exc}")

    def update_webhooks_count(self): pass

    def open_webhooks_dialog(self):
        dialog = WebhooksDialog(self, self.discord_webhooks)
        geo = self.geometry()
        dialog.move(geo.x() + s(18, self.settings.app_scale), geo.y() + s(38, self.settings.app_scale))
        if dialog.exec() == QDialog.Accepted:
            self.discord_webhooks = dialog.get_urls()
            self.update_webhooks_count()

    def _indented_checkbox(self, checkbox, sc):
        row = QHBoxLayout()
        row.setContentsMargins(s(24, sc), 0, 0, 0)
        row.addWidget(checkbox)
        row.addStretch(1)
        return row

    def on_overlay_toggled(self, checked: bool):
        if not checked:
            self.block1.blockSignals(True)
            self.block3.blockSignals(True)
            self.block1.setChecked(False)
            self.block3.setChecked(False)
            self.block1.blockSignals(False)
            self.block3.blockSignals(False)

    def on_overlay_block_toggled(self, checked: bool):
        if checked and not self.overlay.isChecked():
            self.overlay.setChecked(True)
            return
        if not self.block1.isChecked() and not self.block3.isChecked() and self.overlay.isChecked():
            self.overlay.setChecked(False)

    def _range_percent(self, value: int, minimum: int, maximum: int) -> int:
        if maximum <= minimum: return 0
        return round((value - minimum) * 100 / (maximum - minimum))

    def update_labels(self):
        app_percent = self._range_percent(self.app_scale_slider.value(), 82, 122)
        overlay_percent = self._range_percent(self.overlay_scale_slider.value(), 70, 160)
        self.sound_volume_label.setText(f"Громкость оповещения: {self.sound_volume_slider.value()}%")
        self.alpha_label.setText(f"Прозрачность оверлея: {self.alpha_slider.value()}%")
        self.app_scale_label.setText(f"Размер программы: {app_percent}%")
        self.overlay_scale_label.setText(f"Размер оверлея: {overlay_percent}%")

    def apply(self):
        volume_value = max(0, min(100, int(self.sound_volume_slider.value())))
        self.settings.sound_volume = volume_value
        self.settings.sound_enabled = self.sound.isChecked() and volume_value > 0
        custom_sound_value = str(getattr(self, "custom_sound_value", "")).strip()
        if custom_sound_value and os.path.exists(resolve_audio_path(custom_sound_value)):
            try: custom_sound_value = copy_custom_sound_to_storage(custom_sound_value) or custom_sound_value
            except Exception: pass
        self.settings.custom_sound_path = custom_sound_value
        self.settings.discord_nickname = self.discord_nickname.text().strip()
        self.settings.discord_webhooks = (list(self.discord_webhooks) + [""] * 10)[:10]
        block1_enabled = self.block1.isChecked()
        block3_enabled = self.block3.isChecked()
        overlay_enabled = self.overlay.isChecked() and (block1_enabled or block3_enabled)
        self.settings.overlay_enabled = overlay_enabled
        self.settings.overlay_locked = self.lock.isChecked()
        self.settings.overlay_block1 = block1_enabled if overlay_enabled else False
        self.settings.overlay_block2 = False
        self.settings.overlay_block3 = block3_enabled if overlay_enabled else False
        self.settings.overlay_alpha = self.alpha_slider.value() / 100
        self.settings.app_scale = self.app_scale_slider.value() / 100
        self.settings.overlay_scale = self.overlay_scale_slider.value() / 100
        self.settings.save()
        self.app.apply_visual_settings(rebuild=True)
        self.app.apply_overlay_settings()

    def save_and_close(self):
        self.apply()
        self.accept()

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