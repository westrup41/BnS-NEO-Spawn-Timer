from config import COLORS
from utils import s
from resources import combo_arrow_asset

class Style:
    @staticmethod
    def main(scale: float) -> str:
        arrow_path = combo_arrow_asset()
        return f"""
        QWidget {{ background: transparent; color: {COLORS['text_main']}; font-family: "Segoe UI"; font-size: {s(11, scale)}px; }}
        QFrame#Shell {{ background: {COLORS['bg_main']}; border: 1px solid #26292F; border-radius: {s(14, scale)}px; }}
        QFrame#TopBar {{ background: transparent; border: none; }}
        QFrame#Logo {{ background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; border-radius: {s(10, scale)}px; }}
        QLabel#LogoText {{ color: {COLORS['accent']}; font-size: {s(11, scale)}px; font-weight: 900; }}
        QLabel#AppTitle {{ color: #FFFFFF; font-size: {s(14, scale)}px; font-weight: 850; }}
        QLabel#AppSubtitle {{ color: {COLORS['text_muted']}; font-size: {s(10, scale)}px; font-weight: 600; }}
        QFrame#Card {{ background: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; border-radius: {s(14, scale)}px; }}
        QFrame#AccentLine {{ background: {COLORS['accent']}; border-radius: {s(2, scale)}px; }}
        QLabel#SectionTitle {{ color: #FFFFFF; font-size: {s(15, scale)}px; font-weight: 850; }}
        QLabel#FormLabel {{ color: {COLORS['text_muted']}; font-size: {s(10, scale)}px; font-weight: 700; }}
        QFrame#TimerBubble {{ background: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_soft']}; border-radius: {s(12, scale)}px; }}
        QFrame#TimerBubble[active="true"] {{ background: #252A33; border: 1px solid #4650A8; }}
        QLabel#TimerName {{ color: #FFFFFF; font-size: {s(12, scale)}px; font-weight: 850; }}
        QLabel#TimerSub {{ color: {COLORS['text_soft']}; font-size: {s(11, scale)}px; font-weight: 750; }}
        QLabel#TimerValue {{ color: {COLORS['text_main']}; font-size: {s(18, scale)}px; font-weight: 900; letter-spacing: 0.5px; }}
        QLabel#WorldName {{ color: #FFFFFF; font-size: {s(18, scale)}px; font-weight: 900; }}
        QLabel#WorldTimer {{ color: {COLORS['text_main']}; font-size: {s(34, scale)}px; font-weight: 900; letter-spacing: 1.0px; }}
        QLineEdit, QTextEdit, QComboBox {{ background: {COLORS['bg_input']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; border-radius: {s(9, scale)}px; padding: {s(7, scale)}px {s(10, scale)}px; font-weight: 750; selection-background-color: {COLORS['accent']}; }}
        QLineEdit, QTextEdit {{ placeholder-text-color: {COLORS['text_disabled']}; }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: {COLORS['accent']}; }}
        QComboBox::drop-down {{ border: none; width: {s(34, scale)}px; subcontrol-origin: padding; subcontrol-position: top right; }}
        QComboBox::down-arrow {{ image: url("{arrow_path}"); width: {s(12, scale)}px; height: {s(8, scale)}px; margin-right: {s(10, scale)}px; }}
        QComboBox QAbstractItemView {{ background: {COLORS['bg_input']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; border-radius: {s(10, scale)}px; padding: {s(6, scale)}px; selection-background-color: transparent; outline: none; }}
        QComboBox QAbstractItemView::item {{ min-height: {s(30, scale)}px; padding: {s(6, scale)}px {s(12, scale)}px; }}
        QPushButton {{ border: none; border-radius: {s(9, scale)}px; padding: {s(8, scale)}px {s(14, scale)}px; color: #FFFFFF; font-weight: 850; }}
        QPushButton#Primary {{ background: {COLORS['accent']}; }}
        QPushButton#Primary:hover {{ background: {COLORS['accent_hover']}; }}
        QPushButton#Danger {{ background: {COLORS['danger']}; }}
        QPushButton#Danger:hover {{ background: {COLORS['danger_hover']}; }}
        QPushButton#Danger:disabled, QPushButton#Danger:disabled:hover, QPushButton#Danger[cooldown="true"], QPushButton#Danger[cooldown="true"]:hover, QPushButton#Danger[no_webhook="true"], QPushButton#Danger[no_webhook="true"]:hover {{ background: #3D414A; color: #8D939E; border: none; }}
        QPushButton#Success {{ background: {COLORS['success']}; }}
        QPushButton#Success:hover {{ background: {COLORS['success_hover']}; }}
        QPushButton#Ghost {{ background: {COLORS['bg_input']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; }}
        QPushButton#Ghost:hover {{ background: #2A2D34; border-color: #4A4E58; }}
        QPushButton#Chrome {{ background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; color: {COLORS['text_soft']}; padding: 0; }}
        QPushButton#Chrome:hover {{ background: #2A2D34; color: #FFFFFF; }}
        QPushButton#Close {{ background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; color: {COLORS['text_soft']}; padding: 0; font-size: {s(14, scale)}px; font-weight: 900; }}
        QPushButton#Close:hover {{ background: {COLORS['danger']}; border-color: {COLORS['danger']}; color: #FFFFFF; }}
        QPushButton:disabled {{ background: #3D414A; color: #8D939E; border: none; }}
        QCheckBox {{ color: {COLORS['text_main']}; font-weight: 700; spacing: {s(9, scale)}px; }}
        QCheckBox::indicator {{ width: {s(17, scale)}px; height: {s(17, scale)}px; border-radius: {s(5, scale)}px; background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; }}
        QCheckBox::indicator:checked {{ background: {COLORS['accent']}; border: 1px solid {COLORS['accent']}; }}
        QSlider {{ min-height: {s(34, scale)}px; }}
        QSlider::groove:horizontal {{ height: {s(5, scale)}px; background: #191B20; border: 1px solid #3B404A; border-radius: {s(3, scale)}px; }}
        QSlider::sub-page:horizontal {{ background: {COLORS['accent']}; border: 1px solid {COLORS['accent']}; border-radius: {s(3, scale)}px; }}
        QSlider::add-page:horizontal {{ background: #191B20; border: 1px solid #3B404A; border-radius: {s(3, scale)}px; }}
        QSlider::handle:horizontal {{ width: {s(22, scale)}px; height: {s(22, scale)}px; margin: {s(-10, scale)}px 0; border-radius: {s(11, scale)}px; background: {COLORS['accent']}; border: {s(3, scale)}px solid #252A33; }}
        QSlider::handle:horizontal:hover {{ background: #6B74FF; border: {s(3, scale)}px solid #3C427A; }}
        QFrame#SettingsGroup {{ background: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_soft']}; border-radius: {s(12, scale)}px; }}
        QScrollArea#SettingsScroll {{ background: transparent; border: none; }}
        QWidget#SettingsScrollContent {{ background: transparent; }}
        QScrollBar:vertical {{ background: #191B20; width: {s(12, scale)}px; margin: {s(2, scale)}px 0 {s(2, scale)}px {s(4, scale)}px; border-radius: {s(6, scale)}px; }}
        QScrollBar::handle:vertical {{ background: #5865F2; border-radius: {s(6, scale)}px; min-height: {s(42, scale)}px; }}
        QScrollBar::handle:vertical:hover {{ background: #6B74FF; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: transparent; border: none; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QLabel#GroupTitle {{ color: #FFFFFF; font-size: {s(12, scale)}px; font-weight: 900; }}
        """

    @staticmethod
    def overlay(scale: float) -> str:
        return f"""
        QWidget {{ background: transparent; color: {COLORS['text_main']}; font-family: "Segoe UI"; }}
        QFrame#OverlayBubble {{ background: rgba(43,45,49,0.94); border: 1px solid rgba(76,82,96,0.95); border-radius: {s(18, scale)}px; }}
        QLabel#OverlayTitle {{ color: {COLORS['accent']}; font-size: {s(13, scale)}px; font-weight: 900; }}
        QFrame#OverlayLine {{ background: rgba(148,155,164,0.30); }}
        QLabel#OverlayName {{ color: #FFFFFF; font-size: {s(12, scale)}px; font-weight: 850; }}
        QLabel#OverlayInterval {{ color: {COLORS['text_soft']}; font-size: {s(10, scale)}px; font-weight: 750; }}
        QLabel#OverlayTimer {{ color: {COLORS['text_main']}; font-size: {s(16, scale)}px; font-weight: 900; letter-spacing: 0.2px; }}
        QLabel#OverlayWorldName {{ color: #FFFFFF; font-size: {s(14, scale)}px; font-weight: 900; }}
        QLabel#OverlayWorldTimer {{ color: {COLORS['text_main']}; font-size: {s(24, scale)}px; font-weight: 900; letter-spacing: 0.8px; }}
        """

def system_tray_menu_stylesheet() -> str:
    return """
    QMenu { background-color: #F0F0F0; color: #000000; border: 1px solid #A0A0A0; padding: 1px 0; font-family: "Segoe UI"; font-size: 9pt; }
    QMenu::item { background-color: transparent; padding: 4px 34px 4px 28px; min-width: 92px; }
    QMenu::item:selected { background-color: #91C9F7; color: #000000; }
    QMenu::separator { height: 1px; background: #D0D0D0; margin: 3px 0; }
    """