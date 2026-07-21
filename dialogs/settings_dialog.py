import json
import os
import secrets

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QKeySequenceEdit, QLabel,
    QLineEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from dialogs.blocked_users_dialog import BlockedUsersDialog
from dialogs.message_dialog import MessageDialog
from dialogs.webhooks_dialog import WebhooksDialog
from dialogs.avatar_picker_dialog import AvatarPickerDialog
from dialogs.network_diagnostics_dialog import NetworkDiagnosticsDialog
from resources import is_admin_build
from services.audio import copy_custom_sound_to_storage, play_alert, resolve_audio_path
from services.ocr_pack import install_with_prompt
from styles import Style
from utils import s
from widgets.slider import DiscordSlider
from widgets.avatar import AvatarButton
from widgets.combo_delegate import ComboItemDelegate
from widgets.ui_primitives import ArtworkShell, ToggleButton


HOTKEY_ACTIONS = (
    ("toggle_channel_1", "Имп. дерево канал 1 старт/стоп"),
    ("toggle_channel_2", "Имп. дерево канал 2 старт/стоп"),
    ("toggle_channel_3", "Имп. дерево канал 3 старт/стоп"),
    ("alert_channel_1", "Имп. дерево отправить алерт 1"),
    ("alert_channel_2", "Имп. дерево отправить алерт 2"),
    ("alert_channel_3", "Имп. дерево отправить алерт 3"),
    ("toggle_chat_tracker", "Сканер чата старт/стоп"),
    ("toggle_sound", "Включить/заглушить звук"),
)


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.settings = parent.settings
        self.drag_pos = None
        self.discord_webhooks = list(self.settings.discord_webhooks)
        self.custom_sound_value = self.settings.custom_sound_path
        self.room_private = self.settings.online_room_private
        self.avatar_id = int(getattr(self.settings, "chat_avatar_id", -1))
        self._avatar_picker = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        screen = self.screen().availableGeometry()
        self.resize(min(screen.width() - 32, s(1040, self.settings.app_scale)), min(screen.height() - 32, s(680, self.settings.app_scale)))
        self.build()

    def build(self):
        sc = self.settings.app_scale
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self.shell = ArtworkShell(self.app, "assets/themes/blade_soul_settings.png", opacity=0.42); root.addWidget(self.shell)
        layout = QVBoxLayout(self.shell)
        layout.setContentsMargins(s(22, sc), s(16, sc), s(22, sc), s(18, sc))
        layout.setSpacing(s(12, sc))

        top = QFrame(); top.setObjectName("TopBar")
        top_row = QHBoxLayout(top); top_row.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Настройки"); title.setObjectName("SectionTitle")
        close = QPushButton("×"); close.setObjectName("Close"); close.setFixedSize(s(36, sc), s(32, sc)); close.clicked.connect(self.close)
        top_row.addWidget(title); top_row.addStretch(1); top_row.addWidget(close)
        top.mousePressEvent = self.mousePressEvent; top.mouseMoveEvent = self.mouseMoveEvent; top.mouseReleaseEvent = self.mouseReleaseEvent
        layout.addWidget(top)

        self.tabs = QTabWidget(); layout.addWidget(self.tabs, 1)
        self.tabs.addTab(self.build_general_tab(), "Основное")
        self.tabs.addTab(self.build_sound_tab(), "Звук")
        self.tabs.addTab(self.build_online_tab(), "Сеть")
        self.tabs.addTab(self.build_scanner_tab(), "Сканер")
        self.tabs.addTab(self.build_overlay_tab(), "Оверлей")
        self.tabs.addTab(self.build_hotkeys_tab(), "Хоткеи")

        controls = QHBoxLayout()
        reset_all = QPushButton("Сбросить всё"); reset_all.setObjectName("Danger"); reset_all.clicked.connect(self.reset_all_settings)
        import_btn = QPushButton("Импорт"); import_btn.setObjectName("Ghost"); import_btn.clicked.connect(self.import_settings)
        export_btn = QPushButton("Экспорт"); export_btn.setObjectName("Ghost"); export_btn.clicked.connect(self.export_settings)
        apply_btn = QPushButton("Применить"); apply_btn.setObjectName("Primary"); apply_btn.clicked.connect(self.apply)
        save_btn = QPushButton("Сохранить"); save_btn.setObjectName("Success"); save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("Отмена"); cancel_btn.setObjectName("Ghost"); cancel_btn.clicked.connect(self.close)
        controls.addWidget(reset_all); controls.addWidget(import_btn); controls.addWidget(export_btn); controls.addStretch(1)
        controls.addWidget(save_btn); controls.addWidget(apply_btn); controls.addWidget(cancel_btn)
        layout.addLayout(controls)

    def tab_page(self):
        page = QWidget(); page.setObjectName("SettingsPage")
        page.layout_box = QVBoxLayout(page)
        page.layout_box.setContentsMargins(s(18, self.settings.app_scale), s(16, self.settings.app_scale), s(18, self.settings.app_scale), s(16, self.settings.app_scale))
        page.layout_box.setSpacing(s(14, self.settings.app_scale))
        return page

    def settings_section(self, title):
        frame = QFrame(); frame.setObjectName("SettingsSection")
        box = QVBoxLayout(frame)
        box.setContentsMargins(s(16, self.settings.app_scale), s(12, self.settings.app_scale), s(16, self.settings.app_scale), s(14, self.settings.app_scale))
        box.setSpacing(s(10, self.settings.app_scale))
        box.setAlignment(Qt.AlignTop)
        heading = QLabel(title); heading.setObjectName("SettingsSectionTitle"); box.addWidget(heading)
        frame.content_layout = box
        return frame

    @staticmethod
    def align_toggles(*widgets):
        """Use one compact switch column inside each logical group."""
        if not widgets:
            return
        width = max(widget.sizeHint().width() for widget in widgets)
        for widget in widgets:
            widget.setFixedWidth(width)

    def build_general_tab(self):
        page = self.tab_page(); grid = QGridLayout(); grid.setHorizontalSpacing(s(18, self.settings.app_scale)); grid.setVerticalSpacing(0)
        self.tree_enabled = ToggleButton("Императорское древо"); self.tree_enabled.setChecked(self.settings.tree_section_enabled)
        self.event_enabled = ToggleButton("Event"); self.event_enabled.setChecked(self.settings.event_enabled)
        self.field_enabled = ToggleButton("Полевые боссы"); self.field_enabled.setChecked(self.settings.field_bosses_enabled)
        self.world_enabled = ToggleButton("Мировой босс"); self.world_enabled.setChecked(self.settings.world_section_enabled)
        self.hide_to_tray = ToggleButton("Сворачивать в трей при закрытии"); self.hide_to_tray.setChecked(self.settings.hide_to_tray)
        self.auto_update = ToggleButton("Автообновление"); self.auto_update.setChecked(self.settings.auto_update_enabled)
        self.align_toggles(self.tree_enabled, self.event_enabled, self.field_enabled, self.world_enabled)
        self.align_toggles(self.hide_to_tray, self.auto_update)
        for toggle in (self.tree_enabled, self.event_enabled, self.field_enabled, self.world_enabled):
            toggle.toggled.connect(self.sync_overlay_timer_availability)
        timers = self.settings_section("Таймеры")
        for widget in (self.tree_enabled, self.event_enabled, self.field_enabled, self.world_enabled): timers.content_layout.addWidget(widget)
        program = self.settings_section("Программа")
        program.content_layout.addWidget(self.hide_to_tray); program.content_layout.addWidget(self.auto_update)
        self.ui_theme = QComboBox()
        for label, value in (("Classic", "classic"), ("Midnight", "midnight"), ("Starlight", "starlight"), ("Blade & Soul", "blade_soul")):
            self.ui_theme.addItem(label, value)
        self.ui_theme.setCurrentIndex(max(0, self.ui_theme.findData(self.settings.ui_theme)))
        self.ui_theme.setItemDelegate(ComboItemDelegate(self.settings.app_scale, self.ui_theme))
        self.ui_theme.view().setMouseTracking(True)
        self.ui_theme.setFixedWidth(s(260, self.settings.app_scale))
        scale_row = QHBoxLayout(); self.app_scale = DiscordSlider(self.settings.app_scale); self.app_scale.setRange(0, 100); self.app_scale.setValue(round((self.settings.app_scale - 0.82) / 0.40 * 100))
        self.app_scale.setMinimumWidth(s(300, self.settings.app_scale))
        self.app_scale_value = QLabel(f"{self.app_scale.value()}%"); self.app_scale_value.setFixedWidth(s(46, self.settings.app_scale)); self.app_scale.valueChanged.connect(lambda v: self.app_scale_value.setText(f"{v}%"))
        scale_row.addWidget(self.app_scale, 1); scale_row.addWidget(self.app_scale_value)
        form = QFormLayout(); form.setVerticalSpacing(s(12, self.settings.app_scale)); form.addRow("Тема", self.ui_theme); form.addRow("Масштаб", scale_row)
        program.content_layout.addLayout(form); program.content_layout.addStretch(1)
        grid.addWidget(timers, 0, 0, Qt.AlignTop); grid.addWidget(program, 0, 1, Qt.AlignTop)
        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
        page.layout_box.addLayout(grid); page.layout_box.addStretch(1)
        return page

    def make_sound_row(self, label, volume):
        row = QHBoxLayout(); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(s(8, self.settings.app_scale)); name = QLabel(label); name.setFixedWidth(s(105, self.settings.app_scale))
        slider = DiscordSlider(self.settings.app_scale); slider.setRange(0, 100); slider.setValue(volume); slider.setFixedWidth(s(230, self.settings.app_scale))
        value = QLabel(f"{volume}%"); value.setFixedWidth(s(48, self.settings.app_scale)); slider.valueChanged.connect(lambda v, out=value: out.setText(f"{v}%"))
        row.addWidget(name); row.addWidget(slider, 1); row.addWidget(value)
        return row, slider

    def build_sound_tab(self):
        page = self.tab_page(); grid = QGridLayout(); grid.setHorizontalSpacing(s(18, self.settings.app_scale)); grid.setVerticalSpacing(0)
        notifications = self.settings_section("Оповещения")
        self.sound_enabled = ToggleButton("За 10 минут"); self.sound_enabled.setChecked(self.settings.sound_enabled)
        self.incoming_sound = ToggleButton("Аллерты"); self.incoming_sound.setChecked(self.settings.incoming_alert_sound_enabled)
        self.ocr_sound = ToggleButton("Сканер чата"); self.ocr_sound.setChecked(getattr(self.settings, "ocr_sound_enabled", True))
        tooltips = (
            (self.sound_enabled, "Оповещение за 10 минут<br>до окончания таймера"),
            (self.incoming_sound, 'Оповещение по кнопке «Аллерт»<br>от других игроков'),
            (self.ocr_sound, "Оповещение при нахождении в чате слов-триггеров<br>и/или оповещение от других игроков"),
        )
        for widget, tooltip in tooltips:
            widget.setProperty("allowTooltip", True)
            widget.setToolTip(f'<div style="width: 300px;">{tooltip}</div>')
        self.align_toggles(self.sound_enabled, self.incoming_sound, self.ocr_sound)
        notifications.content_layout.addWidget(self.sound_enabled); notifications.content_layout.addWidget(self.incoming_sound); notifications.content_layout.addWidget(self.ocr_sound)
        custom = QHBoxLayout(); custom.setContentsMargins(0, 0, 0, 0); custom.setSpacing(s(7, self.settings.app_scale))
        self.choose_sound_btn = QPushButton("Выбрано ✓" if self.custom_sound_value else "Выбрать звук"); self.choose_sound_btn.setObjectName("Ghost"); self.choose_sound_btn.clicked.connect(self.choose_custom_sound)
        reset = QPushButton("Сбросить"); reset.setObjectName("Ghost"); reset.clicked.connect(self.reset_custom_sound)
        test = QPushButton("Тест"); test.setObjectName("Primary"); test.clicked.connect(self.test_custom_sound)
        for button in (self.choose_sound_btn, reset, test): button.setFixedWidth(s(132, self.settings.app_scale))
        custom.addWidget(self.choose_sound_btn); custom.addWidget(reset); custom.addWidget(test); custom.addStretch(1)
        notifications.content_layout.addLayout(custom)
        volume_section = self.settings_section("Громкость звука")
        row, self.sound_volume = self.make_sound_row("Общая", self.settings.sound_volume)
        volume_section.content_layout.addLayout(row)
        volume_section.content_layout.addStretch(1)
        grid.addWidget(notifications, 0, 0, Qt.AlignTop); grid.addWidget(volume_section, 0, 1, Qt.AlignTop); grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
        page.layout_box.addLayout(grid); page.layout_box.addStretch(1)
        return page

    def build_online_tab(self):
        page = self.tab_page(); grid = QGridLayout(); grid.setHorizontalSpacing(s(18, self.settings.app_scale)); grid.setVerticalSpacing(0)
        self.chat_enabled = ToggleButton("Включить чат"); self.chat_enabled.setChecked(self.settings.chat_enabled)
        self.global_notifications = ToggleButton("Сетевые алерты"); self.global_notifications.setChecked(self.settings.global_notifications)
        self.chat_alerts = ToggleButton("Сетевые алерты сканера чата"); self.chat_alerts.setChecked(self.settings.chat_alerts_enabled)
        self.quorum = ToggleButton("Получение алертов сканера чата при нескольких подтверждениях"); self.quorum.setChecked(self.settings.chat_alert_quorum_enabled)
        self.quorum_count = QComboBox(); self.quorum_count.addItems(("2", "3", "4", "5")); self.quorum_count.setCurrentText(str(self.settings.chat_alert_quorum_count)); self.quorum_count.setFixedWidth(s(76, self.settings.app_scale))
        self.nickname = QLineEdit(self.settings.discord_nickname); self.nickname.setMaxLength(16); self.nickname.setPlaceholderText("Никнейм")
        # Keep each card compact: the short Chat switch must not inherit the
        # width of the deliberately descriptive alert labels.
        self.align_toggles(self.global_notifications, self.chat_alerts, self.quorum)
        chat_section = self.settings_section("Чат"); chat_section.content_layout.addWidget(self.chat_enabled)
        self.avatar_button = AvatarButton(self.avatar_id, s(54, self.settings.app_scale)); self.avatar_button.clicked.connect(self.choose_avatar)
        avatar_row = QHBoxLayout(); avatar_label = QLabel("Аватар"); avatar_label.setFixedWidth(s(92, self.settings.app_scale)); avatar_row.addWidget(avatar_label); avatar_row.addWidget(self.avatar_button); avatar_row.addStretch(1)
        nickname_row = QHBoxLayout(); nickname_label = QLabel("Никнейм"); nickname_label.setFixedWidth(s(92, self.settings.app_scale)); nickname_row.addWidget(nickname_label); nickname_row.addWidget(self.nickname, 1)
        chat_section.content_layout.addLayout(avatar_row); chat_section.content_layout.addLayout(nickname_row)
        alerts_section = self.settings_section("Аллерты"); alerts_section.content_layout.addWidget(self.global_notifications); alerts_section.content_layout.addWidget(self.chat_alerts)
        quorum_row = QHBoxLayout(); quorum_row.setContentsMargins(0, 0, 0, 0); quorum_row.setSpacing(s(8, self.settings.app_scale)); quorum_row.addWidget(self.quorum); quorum_row.addWidget(self.quorum_count); quorum_row.addStretch(1); alerts_section.content_layout.addLayout(quorum_row)
        diagnostics = QPushButton("Диагностика сети"); diagnostics.setObjectName("Ghost"); diagnostics.clicked.connect(self.open_network_diagnostics)
        diagnostic_row = QHBoxLayout(); diagnostic_row.setContentsMargins(0, 0, 0, 0); diagnostic_row.addWidget(diagnostics); diagnostic_row.addStretch(1); alerts_section.content_layout.addLayout(diagnostic_row)
        self.discord_message = QLineEdit(self.settings.discord_message)
        room_section = self.settings_section("Обмен алертами")
        room = QFormLayout(); room.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter); room.setFormAlignment(Qt.AlignTop); room.setHorizontalSpacing(s(12, self.settings.app_scale)); room.setVerticalSpacing(s(10, self.settings.app_scale)); self.room_mode = QComboBox(); self.room_mode.addItem("Глобальный", False); self.room_mode.addItem("Приватный", True); self.room_mode.setCurrentIndex(1 if self.room_private else 0); self.room_mode.currentIndexChanged.connect(self.update_room_mode)
        self.generated_room_code = QLineEdit(); self.generated_room_code.setReadOnly(True); self.generated_room_code.setPlaceholderText("Нажмите «Создать»")
        create_buttons = QHBoxLayout(); create_buttons.setContentsMargins(0, 0, 0, 0); create_buttons.setSpacing(s(8, self.settings.app_scale)); self.generate_room_btn = QPushButton("Создать"); self.generate_room_btn.setObjectName("Ghost"); self.generate_room_btn.clicked.connect(self.generate_room_code); self.copy_room_btn = QPushButton("Копировать"); self.copy_room_btn.setObjectName("Ghost"); self.copy_room_btn.clicked.connect(self.copy_room_code); create_buttons.addWidget(self.generate_room_btn); create_buttons.addWidget(self.copy_room_btn); create_buttons.addStretch(1)
        self.generated_room_code.textChanged.connect(lambda text: self.copy_room_btn.setEnabled(bool(text.strip())))
        self.room_code = QLineEdit(self.settings.online_room_code if self.room_private else ""); self.room_code.setPlaceholderText("Вставьте полученный код")
        join_buttons = QHBoxLayout(); join_buttons.setContentsMargins(0, 0, 0, 0); join_buttons.setSpacing(s(8, self.settings.app_scale)); self.apply_room_btn = QPushButton("Применить"); self.apply_room_btn.setObjectName("Primary"); self.apply_room_btn.clicked.connect(self.apply_join_room); self.reset_room_btn = QPushButton("Сбросить"); self.reset_room_btn.setObjectName("Ghost"); self.reset_room_btn.clicked.connect(self.reset_room); join_buttons.addWidget(self.apply_room_btn); join_buttons.addWidget(self.reset_room_btn); join_buttons.addStretch(1)
        room.addRow("Режим", self.room_mode); room.addRow("Приватная комната:", self.generated_room_code); room.addRow("", create_buttons); room.addRow("Вступить в комнату:", self.room_code); room.addRow("", join_buttons); room_section.content_layout.addLayout(room)
        services_section = self.settings_section("Discord вебхуки")
        discord_form = QFormLayout(); discord_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter); discord_form.setHorizontalSpacing(s(12, self.settings.app_scale)); discord_form.addRow("Текст Discord", self.discord_message)
        network_buttons = QHBoxLayout(); network_buttons.setSpacing(s(8, self.settings.app_scale)); webhooks = QPushButton("Discord webhooks"); webhooks.setObjectName("Ghost"); webhooks.clicked.connect(self.open_webhooks); blocked = QPushButton("Чёрный список"); blocked.setObjectName("Ghost"); blocked.clicked.connect(lambda: BlockedUsersDialog(self).exec()); network_buttons.addWidget(webhooks); network_buttons.addWidget(blocked)
        discord_form.addRow(network_buttons); services_section.content_layout.addLayout(discord_form)
        left = QVBoxLayout(); left.setContentsMargins(0, 0, 0, 0); left.setSpacing(s(12, self.settings.app_scale)); left.addWidget(alerts_section); left.addWidget(chat_section)
        right = QVBoxLayout(); right.setContentsMargins(0, 0, 0, 0); right.setSpacing(s(12, self.settings.app_scale)); right.addWidget(room_section); right.addWidget(services_section)
        grid.addLayout(left, 0, 0, Qt.AlignTop); grid.addLayout(right, 0, 1, Qt.AlignTop); grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
        page.layout_box.addLayout(grid); page.layout_box.addStretch(1); self.update_room_mode()
        return page

    def build_scanner_tab(self):
        page = self.tab_page()
        section = self.settings_section("Сканер чата")
        self.tracker_enabled = ToggleButton("Включить сканер чата"); self.tracker_enabled.setChecked(self.settings.chat_tracker_enabled)
        self.chat_auto_timer = ToggleButton("Запускать таймер при точном канале"); self.chat_auto_timer.setChecked(self.settings.chat_auto_timer_enabled)
        self.align_toggles(self.tracker_enabled, self.chat_auto_timer)
        self.tracker_enabled.toggled.connect(self.sync_scanner_options)
        section.content_layout.addWidget(self.tracker_enabled); section.content_layout.addWidget(self.chat_auto_timer)
        self.sync_scanner_options()
        page.layout_box.addWidget(section); page.layout_box.addStretch(1)
        return page

    def sync_scanner_options(self, checked=None):
        enabled = self.tracker_enabled.isChecked()
        if not enabled:
            self.chat_auto_timer.setChecked(False)
        self.chat_auto_timer.setEnabled(enabled)

    def build_overlay_tab(self):
        page = self.tab_page(); grid = QGridLayout(); grid.setHorizontalSpacing(s(36, self.settings.app_scale)); grid.setVerticalSpacing(s(12, self.settings.app_scale))
        self.overlay_enabled = ToggleButton("Включить оверлей"); self.overlay_enabled.setChecked(self.settings.overlay_enabled)
        self.overlay_locked = ToggleButton("Закрепить"); self.overlay_locked.setChecked(self.settings.overlay_locked)
        self.overlay_tree = ToggleButton("Императорское древо"); self.overlay_tree.setChecked(self.settings.overlay_block1)
        self.overlay_event = ToggleButton("Event"); self.overlay_event.setChecked(self.settings.overlay_block2)
        self.overlay_fields = ToggleButton("Полевые боссы"); self.overlay_fields.setChecked(self.settings.overlay_field_bosses)
        self.overlay_world = ToggleButton("Мировой босс"); self.overlay_world.setChecked(self.settings.overlay_block3)
        self.align_toggles(self.overlay_tree, self.overlay_event, self.overlay_fields, self.overlay_world)
        self.align_toggles(self.overlay_enabled, self.overlay_locked)
        blocks = self.settings_section("Таймеры")
        for widget in (self.overlay_tree, self.overlay_event, self.overlay_fields, self.overlay_world): blocks.content_layout.addWidget(widget)
        display = self.settings_section("Отображение")
        display.content_layout.addWidget(self.overlay_enabled); display.content_layout.addWidget(self.overlay_locked)
        scale_percent = round((self.settings.overlay_scale - 0.70) / 0.90 * 100)
        scale_box = QHBoxLayout(); self.overlay_scale = DiscordSlider(self.settings.app_scale); self.overlay_scale.setRange(0, 100); self.overlay_scale.setValue(max(0, min(100, scale_percent))); self.overlay_scale_value = QLabel(f"{self.overlay_scale.value()}%"); self.overlay_scale_value.setFixedWidth(s(46, self.settings.app_scale)); self.overlay_scale.valueChanged.connect(lambda v: self.overlay_scale_value.setText(f"{v}%")); scale_box.addWidget(self.overlay_scale, 1); scale_box.addWidget(self.overlay_scale_value)
        alpha_box = QHBoxLayout(); self.overlay_alpha = DiscordSlider(self.settings.app_scale); self.overlay_alpha.setRange(0, 95); self.overlay_alpha.setValue(min(95, round((1 - self.settings.overlay_alpha) * 100))); self.overlay_alpha_value = QLabel(f"{self.overlay_alpha.value()}%"); self.overlay_alpha_value.setFixedWidth(s(46, self.settings.app_scale)); self.overlay_alpha.valueChanged.connect(lambda v: self.overlay_alpha_value.setText(f"{v}%")); alpha_box.addWidget(self.overlay_alpha, 1); alpha_box.addWidget(self.overlay_alpha_value)
        right = QFormLayout(); right.setVerticalSpacing(s(12, self.settings.app_scale)); right.addRow("Масштаб", scale_box); right.addRow("Прозрачность", alpha_box)
        display.content_layout.addLayout(right)
        grid.addWidget(blocks, 0, 0, Qt.AlignTop); grid.addWidget(display, 0, 1, Qt.AlignTop); grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
        self.sync_overlay_timer_availability()
        page.layout_box.addLayout(grid); page.layout_box.addStretch(1)
        return page

    def sync_overlay_timer_availability(self, checked=None):
        """A timer hidden in the main UI cannot be enabled in the overlay."""
        pairs = (
            ("overlay_tree", "tree_enabled"),
            ("overlay_event", "event_enabled"),
            ("overlay_fields", "field_enabled"),
            ("overlay_world", "world_enabled"),
        )
        for overlay_name, main_name in pairs:
            overlay = getattr(self, overlay_name, None)
            main = getattr(self, main_name, None)
            if overlay is None or main is None:
                continue
            available = main.isChecked()
            if not available:
                overlay.setChecked(False)
            overlay.setEnabled(available)

    def build_hotkeys_tab(self):
        page = self.tab_page(); section = self.settings_section("Горячие клавиши"); self.hotkeys_enabled = ToggleButton("Работать поверх игры"); self.hotkeys_enabled.setChecked(self.settings.hotkeys_enabled); section.content_layout.addWidget(self.hotkeys_enabled)
        grid = QGridLayout(); grid.setHorizontalSpacing(s(18, self.settings.app_scale)); grid.setVerticalSpacing(s(12, self.settings.app_scale)); self.hotkey_edits = {}
        for index, (action, label) in enumerate(HOTKEY_ACTIONS):
            edit = QKeySequenceEdit(QKeySequence(self.settings.hotkeys.get(action, ""))); edit.setClearButtonEnabled(True)
            if hasattr(edit, "setPlaceholderText"): edit.setPlaceholderText("Нажмите сочетание")
            line_edit = edit.findChild(QLineEdit)
            if line_edit is not None: line_edit.setPlaceholderText("Нажмите сочетание")
            grid.addWidget(QLabel(label), index % 4, (index // 4) * 2); grid.addWidget(edit, index % 4, (index // 4) * 2 + 1)
            self.hotkey_edits[action] = edit
        section.content_layout.addLayout(grid); page.layout_box.addWidget(section); page.layout_box.addStretch(1)
        return page

    def update_room_mode(self):
        private = bool(self.room_mode.currentData()) if hasattr(self, "room_mode") else self.room_private
        self.room_private = private
        if hasattr(self, "room_code"): self.room_code.setEnabled(private)
        if hasattr(self, "generated_room_code"): self.generated_room_code.setEnabled(private)
        if hasattr(self, "generate_room_btn"): self.generate_room_btn.setEnabled(private)
        if hasattr(self, "apply_room_btn"): self.apply_room_btn.setEnabled(private)
        if hasattr(self, "reset_room_btn"): self.reset_room_btn.setEnabled(private)
        if hasattr(self, "copy_room_btn"): self.copy_room_btn.setEnabled(private and bool(self.generated_room_code.text().strip()))

    def generate_room_code(self):
        if not self.room_private: return
        self.generated_room_code.setText(secrets.token_urlsafe(15)); self.generated_room_code.selectAll()
        self.copy_room_btn.setEnabled(True)

    def copy_room_code(self):
        if not self.room_private: return
        QApplication.clipboard().setText(self.generated_room_code.text().strip())

    def _set_active_room(self, private: bool, code: str = ""):
        old_room = self.settings.online_room_code if self.settings.online_room_private else ""
        stored_code = str(code or self.room_code.text() or self.settings.online_room_code).strip()[:64]
        effective_room = stored_code if private else ""
        self.room_private = bool(private)
        self.room_mode.setCurrentIndex(1 if private else 0)
        self.room_code.setText(stored_code)
        self.settings.online_room_private = bool(private)
        self.settings.online_room_code = stored_code
        self.settings.save()
        if old_room != effective_room:
            self.app.chat_history.set_room(effective_room)
            self.app.chat_history.prune(self.app._message_allowed)
            self.app.network.set_room(effective_room)
            self.app.notify_chat_changed(unread=False)

    def apply_join_room(self):
        code = self.room_code.text().strip()
        if not code:
            MessageDialog(self, "Приватная комната", "Вставьте код комнаты.").exec(); return
        self._set_active_room(True, code)

    def reset_room(self):
        self._set_active_room(False, "")

    def choose_custom_sound(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать звук", "", "Аудио (*.wav *.mp3 *.ogg *.flac *.m4a *.aac *.wma)")
        if path:
            self.custom_sound_value = path
            self.choose_sound_btn.setText("Выбрано ✓")

    def reset_custom_sound(self):
        self.custom_sound_value = ""
        self.choose_sound_btn.setText("Выбрать звук")

    def test_custom_sound(self):
        play_alert(True, self.custom_sound_value, self.sound_volume.value())

    def open_webhooks(self):
        dialog = WebhooksDialog(self, self.discord_webhooks)
        if dialog.exec() == QDialog.Accepted: self.discord_webhooks = dialog.get_urls()

    def open_network_diagnostics(self):
        self._network_diagnostics = NetworkDiagnosticsDialog(self)
        self._network_diagnostics.show()

    def choose_avatar(self):
        if self._avatar_picker is not None:
            self._avatar_picker.raise_(); self._avatar_picker.activateWindow(); return
        self._avatar_picker = AvatarPickerDialog(self, self.avatar_id)
        result = self._avatar_picker.exec()
        selected = self._avatar_picker.avatar_id()
        picker = self._avatar_picker; self._avatar_picker = None
        picker.setParent(None); picker.deleteLater()
        if result == QDialog.Accepted:
            self.avatar_id = selected
            self.avatar_button.set_avatar(self.avatar_id)

    def reset_all_settings(self):
        dialog = MessageDialog(
            self, "Сброс настроек",
            "Вернуть все настройки программы и чата к значениям по умолчанию?",
            ok_text="Сбросить", cancel_text="Отмена",
        )
        if not dialog.exec_result():
            return
        self.hide()
        old_room = self.settings.online_room_code if self.settings.online_room_private else ""
        self.settings.reset_user_settings()
        self.app.active_timers.clear(); self.app.spawn_effects.clear(); self.app.spawn_start_times.clear(); self.app.alerted.clear()
        if old_room:
            self.app.chat_history.set_room(""); self.app.network.set_room("")
        if self.app.chat_dialog is not None:
            self.app.chat_dialog.close(); self.app.chat_dialog = None
        Style.set_theme(self.settings.ui_theme)
        self.app.settings_dialog = None
        self.app.apply_visual_settings(rebuild=True)
        self.app.apply_overlay_settings()
        self.app.apply_hotkeys()
        self.app.update_sound_button()
        self.deleteLater()

    def apply(self):
        if self.room_private and not self.room_code.text().strip():
            MessageDialog(self, "Код комнаты", "Введите код комнаты.").exec(); return False
        old_visual = (
            self.settings.ui_theme, self.settings.app_scale, self.settings.tree_section_enabled,
            self.settings.event_enabled, self.settings.field_bosses_enabled, self.settings.world_section_enabled,
        )
        old_overlay = (
            self.settings.overlay_enabled, self.settings.overlay_locked, self.settings.overlay_alpha,
            self.settings.overlay_scale, self.settings.overlay_block1, self.settings.overlay_block2,
            self.settings.overlay_field_bosses, self.settings.overlay_block3,
        )
        old_hotkeys = (self.settings.hotkeys_enabled, dict(self.settings.hotkeys))
        old_room = self.settings.online_room_code if self.settings.online_room_private else ""
        if self.tracker_enabled.isChecked() and not self.settings.chat_tracker_enabled:
            if not install_with_prompt(self):
                self.tracker_enabled.setChecked(False)
        self.settings.tree_section_enabled = self.tree_enabled.isChecked()
        self.settings.event_enabled = self.event_enabled.isChecked()
        self.settings.field_bosses_enabled = self.field_enabled.isChecked()
        self.settings.world_section_enabled = self.world_enabled.isChecked()
        self.settings.hide_to_tray = self.hide_to_tray.isChecked()
        self.settings.auto_update_enabled = self.auto_update.isChecked()
        self.settings.ui_theme = self.ui_theme.currentData(); self.settings.theme_choice_version = 1
        self.settings.app_scale = 0.82 + (self.app_scale.value() / 100.0) * 0.40
        self.settings.sound_enabled = self.sound_enabled.isChecked(); self.settings.incoming_alert_sound_enabled = self.incoming_sound.isChecked(); self.settings.ocr_sound_enabled = self.ocr_sound.isChecked()
        self.settings.sound_volume = self.sound_volume.value()
        custom = self.custom_sound_value.strip()
        if custom and custom != self.settings.custom_sound_path and os.path.exists(resolve_audio_path(custom)):
            custom = copy_custom_sound_to_storage(custom) or custom
        self.settings.custom_sound_path = custom
        self.settings.chat_enabled = self.chat_enabled.isChecked(); self.settings.global_notifications = self.global_notifications.isChecked(); self.settings.chat_alerts_enabled = self.chat_alerts.isChecked()
        self.settings.chat_alert_quorum_enabled = self.quorum.isChecked(); self.settings.chat_alert_quorum_count = int(self.quorum_count.currentText())
        self.settings.discord_nickname = self.nickname.text().strip()[:16]; self.settings.chat_avatar_id = self.avatar_id; self.settings.discord_message = self.discord_message.text().strip(); self.settings.discord_webhooks = (self.discord_webhooks + [""] * 10)[:10]
        self.settings.online_room_private = self.room_private; self.settings.online_room_code = self.room_code.text().strip()[:64]
        self.settings.chat_tracker_enabled = self.tracker_enabled.isChecked(); self.settings.chat_auto_timer_enabled = self.chat_auto_timer.isChecked()
        self.settings.overlay_locked = self.overlay_locked.isChecked(); self.settings.overlay_alpha = 1 - self.overlay_alpha.value() / 100; self.settings.overlay_scale = 0.70 + (self.overlay_scale.value() / 100.0) * 0.90
        self.settings.overlay_block1 = self.overlay_tree.isChecked() and self.settings.tree_section_enabled
        self.settings.overlay_block2 = self.overlay_event.isChecked() and self.settings.event_enabled
        self.settings.overlay_field_bosses = self.overlay_fields.isChecked() and self.settings.field_bosses_enabled
        self.settings.overlay_block3 = self.overlay_world.isChecked() and self.settings.world_section_enabled
        self.settings.overlay_enabled = self.overlay_enabled.isChecked() and any((self.settings.overlay_block1, self.settings.overlay_block2, self.settings.overlay_field_bosses, self.settings.overlay_block3))
        self.settings.hotkeys_enabled = self.hotkeys_enabled.isChecked(); self.settings.hotkeys = {action: edit.keySequence().toString(QKeySequence.PortableText) for action, edit in self.hotkey_edits.items() if not edit.keySequence().isEmpty()}
        if not self.settings.tree_section_enabled:
            self.app.active_timers.clear(); self.app.spawn_effects.clear(); self.app.spawn_start_times.clear(); self.app.alerted.clear(); self.settings.active_timers = {}
        self.settings.save(); Style.set_theme(self.settings.ui_theme)
        effective_room = self.settings.online_room_code if self.settings.online_room_private else ""
        if old_room != effective_room:
            self.app.chat_history.set_room(effective_room); self.app.chat_history.prune(self.app._message_allowed); self.app.network.set_room(effective_room); self.app.notify_chat_changed(unread=False)
        new_visual = (
            self.settings.ui_theme, self.settings.app_scale, self.settings.tree_section_enabled,
            self.settings.event_enabled, self.settings.field_bosses_enabled, self.settings.world_section_enabled,
        )
        new_overlay = (
            self.settings.overlay_enabled, self.settings.overlay_locked, self.settings.overlay_alpha,
            self.settings.overlay_scale, self.settings.overlay_block1, self.settings.overlay_block2,
            self.settings.overlay_field_bosses, self.settings.overlay_block3,
        )
        new_hotkeys = (self.settings.hotkeys_enabled, dict(self.settings.hotkeys))
        if old_visual != new_visual:
            self.app.apply_visual_settings(rebuild=True)
        else:
            self.app.tick(); self.app.update_chat_button()
            if hasattr(self.app, "tracker_btn"):
                self.app.tracker_btn.setEnabled(self.settings.chat_tracker_enabled)
        if old_overlay != new_overlay: self.app.apply_overlay_settings()
        if old_hotkeys != new_hotkeys: self.app.apply_hotkeys()
        self.app.refresh_discord_buttons()
        self.app.update_sound_button()
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.update()
        return True

    def export_settings(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт настроек", "bns-neo-settings.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as file: json.dump(self.settings.export_public(), file, ensure_ascii=False, indent=2)

    def import_settings(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт настроек", "", "JSON (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as file: self.settings.import_public(json.load(file))
            self.close(); self.app.apply_visual_settings(rebuild=True); self.app.apply_overlay_settings()
        except Exception as exc: MessageDialog(self, "Импорт", str(exc)).exec()

    def save_and_close(self):
        self.hide()
        QApplication.processEvents()
        if self.apply():
            self.app.settings_dialog = None
            self.deleteLater()
        else:
            self.show(); self.raise_(); self.activateWindow()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()
    def mouseMoveEvent(self, event):
        if self.drag_pos is not None: self.move(event.globalPosition().toPoint() - self.drag_pos); event.accept()
    def mouseReleaseEvent(self, event): self.drag_pos = None; event.accept()
    def closeEvent(self, event): self.app.settings_dialog = None; super().closeEvent(event)
