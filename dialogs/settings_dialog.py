import os
import json
import secrets
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox, QScrollArea, QWidget, QFileDialog
from dialogs.message_dialog import MessageDialog
from PySide6.QtCore import Qt, QSize
from utils import s
from styles import Style
from widgets.slider import DiscordSlider
from dialogs.webhooks_dialog import WebhooksDialog
from dialogs.blocked_users_dialog import BlockedUsersDialog
from dialogs.network_diagnostics_dialog import NetworkDiagnosticsDialog
from dialogs.admin_dialog import AdminDialog
from services.admin import ADMIN_KEY_FILE
from resources import make_room_icon, is_admin_build
from services.audio import stop_alert_sound, play_alert, resolve_audio_path, copy_custom_sound_to_storage
from config import COLORS

class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.app = parent
        self.settings = parent.settings
        self.drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.setFixedSize(max(500, s(500, self.settings.app_scale)), s(790, self.settings.app_scale))
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
        close.clicked.connect(self.close)
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
        self.incoming_alert_sound = QCheckBox("Звук алертов от других пользователей")
        self.incoming_alert_sound.setChecked(self.settings.incoming_alert_sound_enabled)
        sound_layout.addWidget(self.incoming_alert_sound)

        sound_layout.addSpacing(s(8, sc))
        self.sound_volume_label = QLabel()
        self.sound_volume_label.setObjectName("FormLabel")
        self.sound_volume_slider = DiscordSlider(sc)
        self.sound_volume_slider.setMaximumWidth(s(360, sc))
        self.sound_volume_slider.setRange(0, 100)
        self.sound_volume_slider.setValue(int(self.settings.sound_volume))
        self.sound.toggled.connect(self.on_sound_toggled)
        self.incoming_alert_sound.toggled.connect(self.on_sound_toggled)
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
        discord_title = QLabel("Онлайн-функции")
        discord_title.setObjectName("GroupTitle")
        discord_layout.addWidget(discord_title)

        self.chat_enabled = QCheckBox("Чат")
        self.chat_enabled.setChecked(self.settings.chat_enabled)
        discord_layout.addWidget(self.chat_enabled)

        self.global_notifications = QCheckBox("Получать алерты от других пользователей")
        self.global_notifications.setChecked(self.settings.global_notifications)
        discord_layout.addWidget(self.global_notifications)

        room_label = QLabel("Комната чата и алертов")
        room_label.setObjectName("FormLabel")
        room_mode_row = QHBoxLayout()
        self.room_private = bool(self.settings.online_room_private)
        self.room_switch = QFrame()
        self.room_switch.setObjectName("RoomSwitch")
        switch_layout = QHBoxLayout(self.room_switch)
        switch_layout.setContentsMargins(s(2, sc), s(2, sc), s(2, sc), s(2, sc))
        switch_layout.setSpacing(s(2, sc))
        self.room_global_btn = QPushButton()
        self.room_private_btn = QPushButton()
        for button in (self.room_global_btn, self.room_private_btn):
            button.setObjectName("RoomSegment")
            button.setFixedSize(s(48, sc), s(36, sc))
            button.setIconSize(QSize(s(22, sc), s(22, sc)))
        self.room_global_btn.clicked.connect(lambda: self.set_room_private(False))
        self.room_private_btn.clicked.connect(lambda: self.set_room_private(True))
        switch_layout.addWidget(self.room_global_btn)
        switch_layout.addWidget(self.room_private_btn)
        room_mode_row.addWidget(self.room_switch)
        room_mode_row.addStretch(1)
        self.room_code = QLineEdit()
        self.room_code.setMaxLength(64)
        self.room_code.setEchoMode(QLineEdit.Normal)
        self.room_code.setMaximumWidth(s(380, sc))
        self.room_code.setPlaceholderText("Код приватной комнаты")
        self.room_code.setText(self.settings.online_room_code)
        self.room_code.textChanged.connect(lambda: self.copy_room_btn.setEnabled(
            self.room_private and bool(self.room_code.text().strip())
        ) if hasattr(self, "copy_room_btn") else None)
        discord_layout.addWidget(room_label)
        discord_layout.addLayout(room_mode_row)
        discord_layout.addWidget(self.room_code)
        room_code_row = QHBoxLayout()
        self.generate_room_btn = QPushButton("Создать код")
        self.generate_room_btn.setObjectName("Primary")
        self.generate_room_btn.clicked.connect(self.generate_room_code)
        room_code_row.addWidget(self.generate_room_btn)
        self.copy_room_btn = QPushButton("Копировать")
        self.copy_room_btn.setObjectName("Ghost")
        self.copy_room_btn.clicked.connect(self.copy_room_code)
        room_code_row.addWidget(self.copy_room_btn)
        room_code_row.addStretch(1)
        discord_layout.addLayout(room_code_row)
        self.update_room_mode()

        user_id = self.app.get_user_id()
        identity_label = QLabel(f"Ваш ID:\n{user_id[:32]}\n{user_id[32:]}")
        identity_label.setObjectName("FormLabel")
        identity_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        identity_label.setWordWrap(True)
        discord_layout.addWidget(identity_label)

        nick_label = QLabel("Никнейм отправителя")
        nick_label.setObjectName("FormLabel")
        self.discord_nickname = QLineEdit()
        self.discord_nickname.setMaxLength(16)
        self.discord_nickname.setPlaceholderText("Например: Westrup")
        self.discord_nickname.setText(self.settings.discord_nickname)
        discord_layout.addWidget(nick_label)
        discord_layout.addWidget(self.discord_nickname)
        
        message_label = QLabel("Текст Discord-уведомления")
        message_label.setObjectName("FormLabel")

        self.discord_message = QLineEdit()
        self.discord_message.setPlaceholderText("@everyone 🚨 Императорское древо")
        self.discord_message.setText(self.settings.discord_message)

        discord_layout.addWidget(message_label)
        discord_layout.addWidget(self.discord_message)

        webhook_row = QHBoxLayout()
        webhook_row.setSpacing(s(8, sc))
        self.webhooks_btn = QPushButton("Вебхуки")
        self.webhooks_btn.setObjectName("Primary")
        self.webhooks_btn.setFixedWidth(s(112, sc))
        self.webhooks_btn.clicked.connect(self.open_webhooks_dialog)
        webhook_row.addWidget(self.webhooks_btn)
        blocked_btn = QPushButton("Черный список")
        blocked_btn.setObjectName("Ghost")
        blocked_btn.setFixedWidth(s(140, sc))
        blocked_btn.clicked.connect(lambda: BlockedUsersDialog(self).exec())
        webhook_row.addWidget(blocked_btn)
        webhook_row.addStretch(1)
        discord_layout.addLayout(webhook_row)
        online_tools_row = QHBoxLayout()
        online_tools_row.setSpacing(s(8, sc))
        diagnostics_btn = QPushButton("Диагностика")
        diagnostics_btn.setObjectName("Ghost")
        diagnostics_btn.clicked.connect(self.open_diagnostics)
        online_tools_row.addWidget(diagnostics_btn)
        if ADMIN_KEY_FILE.exists() and is_admin_build():
            admin_btn = QPushButton("Админ")
            admin_btn.setObjectName("Danger")
            admin_btn.clicked.connect(lambda: AdminDialog(self).exec())
            online_tools_row.addWidget(admin_btn)
        online_tools_row.addStretch(1)
        discord_layout.addLayout(online_tools_row)
        self.discord_webhooks = (list(self.settings.discord_webhooks) + [""] * 10)[:10]
        self.update_webhooks_count()
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

        self.hide_to_tray = QCheckBox("Скрывать в трей при закрытии")
        self.hide_to_tray.setChecked(self.settings.hide_to_tray)
        ui_layout.addWidget(self.hide_to_tray)
        self.event_enabled = QCheckBox("Event")
        self.event_enabled.setChecked(self.settings.event_enabled)
        ui_layout.addWidget(self.event_enabled)
        ui_layout.addSpacing(s(8, sc))

        theme_label = QLabel("Тема оформления")
        theme_label.setObjectName("FormLabel")
        self.ui_theme = QComboBox()
        self.ui_theme.setMaximumWidth(s(230, sc))
        self.ui_theme.addItem("Classic", "classic")
        self.ui_theme.addItem("Midnight", "midnight")
        self.ui_theme.addItem("Starlight", "starlight")
        theme_index = self.ui_theme.findData(self.settings.ui_theme)
        self.ui_theme.setCurrentIndex(max(0, theme_index))
        ui_layout.addWidget(theme_label)
        ui_layout.addWidget(self.ui_theme)
        ui_layout.addSpacing(s(8, sc))

        self.app_scale_label = QLabel()
        self.app_scale_label.setObjectName("FormLabel")
        self.app_scale_slider = DiscordSlider(sc)
        self.app_scale_slider.setMaximumWidth(s(360, sc))
        self.app_scale_slider.setRange(82, 122)
        self.app_scale_slider.setValue(int(self.settings.app_scale * 100))
        self.app_scale_slider.valueChanged.connect(self.update_labels)
        ui_layout.addWidget(self.app_scale_label)
        ui_layout.addWidget(self.app_scale_slider)
        content_layout.addWidget(ui_group)
        
        updates_group = QFrame()
        updates_group.setObjectName("SettingsGroup")
        updates_layout = QVBoxLayout(updates_group)
        updates_layout.setContentsMargins(s(14, sc), s(12, sc), s(14, sc), s(12, sc))
        updates_layout.setSpacing(s(8, sc))

        updates_title = QLabel("Обновления")
        updates_title.setObjectName("GroupTitle")
        updates_layout.addWidget(updates_title)

        interval_label = QLabel("Проверять обновления")
        interval_label.setObjectName("FormLabel")
        updates_layout.addWidget(interval_label)

        self.update_interval = QComboBox()
        self.update_interval.setMaximumWidth(s(230, sc))
        self.update_interval.addItem("Никогда", "never")
        self.update_interval.addItem("Раз в неделю", "week")
        self.update_interval.addItem("Раз в месяц", "month")

        index = self.update_interval.findData(self.settings.update_check_interval)
        if index >= 0:
            self.update_interval.setCurrentIndex(index)

        updates_layout.addWidget(self.update_interval)

        content_layout.addWidget(updates_group)

        backup_group = QFrame()
        backup_group.setObjectName("SettingsGroup")
        backup_layout = QVBoxLayout(backup_group)
        backup_layout.setContentsMargins(s(14, sc), s(12, sc), s(14, sc), s(12, sc))
        backup_title = QLabel("Резервная копия")
        backup_title.setObjectName("GroupTitle")
        backup_layout.addWidget(backup_title)
        backup_row = QHBoxLayout()
        export_btn = QPushButton("Экспорт")
        export_btn.setObjectName("Ghost")
        export_btn.clicked.connect(self.export_settings)
        import_btn = QPushButton("Восстановить")
        import_btn.setObjectName("Primary")
        import_btn.clicked.connect(self.import_settings)
        backup_row.addWidget(export_btn)
        backup_row.addWidget(import_btn)
        backup_row.addStretch(1)
        backup_layout.addLayout(backup_row)
        content_layout.addWidget(backup_group)

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
        self.block2 = QCheckBox("Event")
        self.block2.setChecked(self.settings.overlay_block2)
        self.block2.setEnabled(self.settings.event_enabled)
        self.event_enabled.toggled.connect(self.on_event_toggled)
        self.block3 = QCheckBox("Мировой босс")
        self.block3.setChecked(self.settings.overlay_block3)
        self.lock = QCheckBox("Закрепить оверлей")
        self.lock.setChecked(self.settings.overlay_locked)

        overlay_layout.addWidget(self.overlay)
        overlay_layout.addLayout(self._indented_checkbox(self.block1, sc))
        overlay_layout.addLayout(self._indented_checkbox(self.block2, sc))
        overlay_layout.addLayout(self._indented_checkbox(self.block3, sc))
        overlay_layout.addWidget(self.lock)

        self.overlay.toggled.connect(self.on_overlay_toggled)
        self.block1.toggled.connect(self.on_overlay_block_toggled)
        self.block2.toggled.connect(self.on_overlay_block_toggled)
        self.block3.toggled.connect(self.on_overlay_block_toggled)

        overlay_layout.addSpacing(s(8, sc))
        self.alpha_label = QLabel()
        self.alpha_label.setObjectName("FormLabel")
        self.alpha_slider = DiscordSlider(sc)
        self.alpha_slider.setMaximumWidth(s(360, sc))
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(int((1 - self.settings.overlay_alpha) * 100))
        self.alpha_slider.valueChanged.connect(self.update_labels)
        overlay_layout.addWidget(self.alpha_label)
        overlay_layout.addWidget(self.alpha_slider)

        self.overlay_scale_label = QLabel()
        self.overlay_scale_label.setObjectName("FormLabel")
        self.overlay_scale_slider = DiscordSlider(sc)
        self.overlay_scale_slider.setMaximumWidth(s(360, sc))
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
        cancel_btn.clicked.connect(self.close)
        buttons.addWidget(save_btn)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        self.update_labels()

    def on_sound_toggled(self, checked: bool):
        if checked:
            if self.sound_volume_slider.value() <= 0:
                self.sound_volume_slider.setValue(50)
        self.update_labels()

    def on_sound_volume_changed(self, value: int):
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
                MessageDialog(self, "Ошибка", "Не удалось скопировать файл.").exec()
                return
            self.custom_sound_value = stored_path
            self.update_custom_sound_button()
        except Exception as exc:
            MessageDialog(self, "Ошибка", "Не удалось скопировать файл.",str(exc)).exec()

    def update_webhooks_count(self):
        count = sum(1 for url in self.discord_webhooks if str(url).strip())
        self.webhooks_btn.setText(f"Вебхуки ({count})" if count else "Вебхуки")

    def open_webhooks_dialog(self):
        dialog = WebhooksDialog(self, self.discord_webhooks)
        geo = self.geometry()
        dialog.move(geo.x() + s(18, self.settings.app_scale), geo.y() + s(38, self.settings.app_scale))
        if dialog.exec() == QDialog.Accepted:
            self.discord_webhooks = dialog.get_urls()
            self.update_webhooks_count()

    def open_diagnostics(self):
        self.network_diagnostics = NetworkDiagnosticsDialog(self)
        self.network_diagnostics.show()

    def _indented_checkbox(self, checkbox, sc):
        row = QHBoxLayout()
        row.setContentsMargins(s(24, sc), 0, 0, 0)
        row.addWidget(checkbox)
        row.addStretch(1)
        return row

    def on_overlay_toggled(self, checked: bool):
        if not checked:
            self.block1.blockSignals(True)
            self.block2.blockSignals(True)
            self.block3.blockSignals(True)
            self.block1.setChecked(False)
            self.block2.setChecked(False)
            self.block3.setChecked(False)
            self.block1.blockSignals(False)
            self.block2.blockSignals(False)
            self.block3.blockSignals(False)

    def on_event_toggled(self, checked: bool):
        self.block2.setEnabled(checked)
        if not checked:
            self.block2.setChecked(False)

    def on_overlay_block_toggled(self, checked: bool):
        if checked and not self.overlay.isChecked():
            self.overlay.setChecked(True)
            return
        if not self.block1.isChecked() and not self.block2.isChecked() and not self.block3.isChecked() and self.overlay.isChecked():
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
        if self.room_private and not self.room_code.text().strip():
            MessageDialog(
                self, "Нужен код комнаты",
                "Введите код, полученный от владельца комнаты, или нажмите «Создать код».",
            ).exec()
            return False
        nickname = self.discord_nickname.text().strip()
        volume_value = max(0, min(100, int(self.sound_volume_slider.value())))
        self.settings.sound_volume = volume_value
        self.settings.sound_enabled = self.sound.isChecked() and volume_value > 0
        self.settings.incoming_alert_sound_enabled = self.incoming_alert_sound.isChecked() and volume_value > 0
        custom_sound_value = str(getattr(self, "custom_sound_value", "")).strip()
        if custom_sound_value and os.path.exists(resolve_audio_path(custom_sound_value)):
            try: custom_sound_value = copy_custom_sound_to_storage(custom_sound_value) or custom_sound_value
            except Exception: pass
        self.settings.custom_sound_path = custom_sound_value
        self.settings.discord_nickname = nickname[:16]
        message = self.discord_message.text().strip()
        self.settings.discord_message = message or "@everyone 🚨 Императорское древо"
        self.settings.discord_webhooks = (list(self.discord_webhooks) + [""] * 10)[:10]
        self.settings.chat_enabled = self.chat_enabled.isChecked()
        self.settings.global_notifications = self.global_notifications.isChecked()
        previous_room = self.settings.online_room_code if self.settings.online_room_private else ""
        self.settings.online_room_private = self.room_private
        self.settings.online_room_code = self.room_code.text().strip()[:64]
        self.settings.hide_to_tray = self.hide_to_tray.isChecked()
        self.settings.event_enabled = self.event_enabled.isChecked()
        self.settings.ui_theme = self.ui_theme.currentData()
        self.settings.theme_choice_version = 1
        self.settings.update_check_interval = self.update_interval.currentData()
        block1_enabled = self.block1.isChecked()
        block2_enabled = self.block2.isChecked() and self.settings.event_enabled
        block3_enabled = self.block3.isChecked()
        overlay_enabled = self.overlay.isChecked() and (block1_enabled or block2_enabled or block3_enabled)
        self.settings.overlay_enabled = overlay_enabled
        self.settings.overlay_locked = self.lock.isChecked()
        self.settings.overlay_block1 = block1_enabled if overlay_enabled else False
        self.settings.overlay_block2 = block2_enabled if overlay_enabled else False
        self.settings.overlay_block3 = block3_enabled if overlay_enabled else False
        self.settings.overlay_alpha = 1 - (self.alpha_slider.value() / 100)
        self.settings.app_scale = self.app_scale_slider.value() / 100
        self.settings.overlay_scale = self.overlay_scale_slider.value() / 100
        self.settings.save()
        Style.set_theme(self.settings.ui_theme)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.update_room_mode()
        effective_room = self.settings.online_room_code if self.settings.online_room_private else ""
        if previous_room != effective_room:
            self.app.chat_history.set_room(effective_room)
            self.app.chat_history.prune(self.app._message_allowed)
            self.app.network.set_room(effective_room)
            self.app.notify_chat_changed(unread=False)
        self.app.apply_visual_settings(rebuild=True)
        self.app.apply_overlay_settings()
        if self.app.chat_dialog is not None:
            self.app.chat_dialog.setStyleSheet(Style.main(self.settings.app_scale))
            self.app.chat_dialog.refresh_messages(scroll_to_bottom=False)
            self.app.chat_dialog.update_enabled_state()
        if self.app.about_dialog is not None:
            self.app.about_dialog.setStyleSheet(Style.main(self.settings.app_scale))
        return True

    def update_room_mode(self):
        self.room_global_btn.setIcon(make_room_icon(
            False, s(24, self.settings.app_scale), "#FFFFFF" if not self.room_private else COLORS["text_disabled"]
        ))
        self.room_private_btn.setIcon(make_room_icon(
            True, s(24, self.settings.app_scale), "#FFFFFF" if self.room_private else COLORS["text_disabled"]
        ))
        self.room_global_btn.setToolTip("Глобальная комната")
        self.room_private_btn.setToolTip("Приватная комната — вход по коду")
        for button, active in ((self.room_global_btn, not self.room_private),
                               (self.room_private_btn, self.room_private)):
            button.setProperty("active", "true" if active else "false")
            button.style().unpolish(button)
            button.style().polish(button)
        self.room_code.setEnabled(self.room_private)
        self.generate_room_btn.setEnabled(self.room_private)
        self.copy_room_btn.setEnabled(self.room_private and bool(self.room_code.text().strip()))

    def set_room_private(self, private: bool):
        self.room_private = bool(private)
        self.update_room_mode()

    def generate_room_code(self):
        self.room_code.setText(secrets.token_urlsafe(15))
        self.copy_room_btn.setEnabled(True)
        self.room_code.setFocus()
        self.room_code.selectAll()

    def copy_room_code(self):
        code = self.room_code.text().strip()
        if code:
            QApplication.clipboard().setText(code)
            self.copy_room_btn.setText("Скопировано")

    def export_settings(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт настроек", "bns-neo-settings.json", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(self.settings.export_public(), file, ensure_ascii=False, indent=2)
        except Exception as exc:
            MessageDialog(self, "Ошибка экспорта", str(exc)).exec()

    def import_settings(self):
        path, _ = QFileDialog.getOpenFileName(self, "Восстановить настройки", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as file:
                self.settings.import_public(json.load(file))
            MessageDialog(self, "Настройки восстановлены", "Перезапустите программу, чтобы применить все параметры.").exec()
        except Exception as exc:
            MessageDialog(self, "Ошибка восстановления", str(exc)).exec()

    def save_and_close(self):
        if self.apply():
            self.close()

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
        self.parent().settings_dialog = None
        super().closeEvent(event)
