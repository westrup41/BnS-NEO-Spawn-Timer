from config import COLORS
from utils import s
from resources import combo_arrow_asset

class Style:
    active_theme = "classic"
    classic_palette = dict(COLORS)
    midnight_palette = {
        "bg_main": "#090B10", "bg_card": "#10141D", "bg_panel": "#0C1017",
        "bg_input": "#080B11", "border": "#252B38", "border_soft": "#1B2230",
        "text_main": "#F2F5F9", "text_soft": "#B9C1CE", "text_muted": "#778196",
        "text_disabled": "#4F586B", "accent": "#9B7BFF", "accent_hover": "#B198FF",
        "danger": "#F0445E", "danger_hover": "#FF647A", "success": "#27D3A2",
        "success_hover": "#42E6B8", "timer_hot": "#FF6379",
    }
    starlight_palette = {
        "bg_main": "#EEF1F6", "bg_card": "#FFFFFF", "bg_panel": "#F7F8FB",
        "bg_input": "#FFFFFF", "border": "#CAD1DE", "border_soft": "#DDE2EA",
        "text_main": "#171A23", "text_soft": "#3F4858", "text_muted": "#667085",
        "text_disabled": "#9AA3B2", "accent": "#6555D9", "accent_hover": "#5142C2",
        "danger": "#D92D4B", "danger_hover": "#B4233C", "success": "#14866D",
        "success_hover": "#0F705B", "timer_hot": "#D92D4B",
    }

    @classmethod
    def set_theme(cls, theme: str):
        cls.active_theme = str(theme) if str(theme) in {"midnight", "starlight"} else "classic"
        palette = {
            "classic": cls.classic_palette,
            "midnight": cls.midnight_palette,
            "starlight": cls.starlight_palette,
        }[cls.active_theme]
        COLORS.clear()
        COLORS.update(palette)

    @classmethod
    def _themed(cls, css: str) -> str:
        if cls.active_theme == "classic":
            return css
        if cls.active_theme == "midnight":
            return css + """
        QFrame#Shell { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #090B10, stop:0.55 #0B0E15, stop:1 #10101A); border: 1px solid #2A3040; }
        QFrame#Card { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #121720, stop:1 #0E121A); border-color: #252D3B; }
        QFrame#TimerBubble { background: rgba(7,10,16,205); border-color: #202838; }
        QFrame#TimerBubble:hover { border-color: #35415A; background: rgba(12,16,25,235); }
        QLineEdit, QTextEdit, QComboBox, QSpinBox { background: #090C12; border-color: #262D3B; }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #8D73FF; background: #0D1019; }
        QPushButton#Primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6D4DF4, stop:1 #8C68FF); border: 1px solid #9A83FF; }
        QPushButton#Primary:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #805FFF, stop:1 #9D80FF); }
        QPushButton#Success { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #159A79, stop:1 #27D3A2); color: #031711; }
        QPushButton#Ghost { background: rgba(12,16,24,210); border-color: #262E3D; }
        QPushButton#Ghost:hover { background: #161C27; border-color: #46526B; }
        QFrame#SettingsGroup, QFrame#ChatMessage { background: #0D1119; border-color: #202736; }
        QPushButton#ChatButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #6D4DF4, stop:1 #A475FF); border-color: #B197FF; }
        """
        return css + """
        QWidget { color: #171A23; }
        QFrame#Shell { background: #EEF1F6; border: 1px solid #C8D0DC; }
        QLabel#AppTitle, QLabel#SectionTitle, QLabel#GroupTitle, QLabel#TimerName,
        QLabel#WorldName, QLabel#ChatNick { color: #171A23; }
        QFrame#Card { background: #FFFFFF; border-color: #D4DAE4; }
        QFrame#TimerBubble { background: #F7F8FB; border-color: #DDE2EA; }
        QFrame#TimerBubble:hover { background: #F0F2F7; border-color: #B8C1CF; }
        QFrame#TimerBubble[active="true"] { background: #F0EEFF; border-color: #7A69E8; }
        QLineEdit, QTextEdit, QComboBox, QSpinBox { background: #FFFFFF; color: #171A23; border-color: #C9D0DC; }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus { background: #FFFFFF; border-color: #6555D9; }
        QComboBox QAbstractItemView, QMenu { background: #FFFFFF; color: #171A23; border-color: #C9D0DC; }
        QComboBox QAbstractItemView::item:selected, QMenu::item:selected { background: #E9E5FF; color: #332A80; }
        QPushButton#Ghost, QPushButton#Chrome, QPushButton#Close, QPushButton#SocialButton,
        QPushButton#EmojiButton, QPushButton#EmojiPickerButton { background: #FFFFFF; color: #242936; border-color: #C9D0DC; }
        QPushButton#Ghost:hover, QPushButton#Chrome:hover, QPushButton#SocialButton:hover,
        QPushButton#EmojiButton:hover, QPushButton#EmojiPickerButton:hover { background: #F0F2F7; border-color: #9DA8B8; }
        QPushButton#Primary { background: #6555D9; color: #FFFFFF; border: 1px solid #5748C5; }
        QPushButton#Primary:hover { background: #5142C2; }
        QPushButton#Success { background: #14866D; color: #FFFFFF; }
        QPushButton#Danger, QPushButton#RoomSegment[active="true"] { color: #FFFFFF; }
        QPushButton:disabled { background: #E2E6EC; color: #98A2B3; }
        QCheckBox { color: #242936; }
        QCheckBox::indicator { background: #FFFFFF; border-color: #B8C1CF; }
        QFrame#SettingsGroup, QFrame#ChatMessage, QFrame#EmojiPanel, QFrame#ContactPopover {
            background: #FFFFFF; border-color: #D7DDE7;
        }
        QScrollBar:vertical { background: #E0E4EB; }
        QScrollBar::handle:vertical { background: #8A7BE5; }
        QLabel#ChatBadge { border-color: #EEF1F6; }
        QFrame#OverlayBubble { background: #FFFFFF; border-color: #BEC6D3; }
        QLabel#OverlayName, QLabel#OverlayWorldName { color: #171A23; }
        QFrame#OverlayLine { background: rgba(102,112,133,0.28); }
        """

    @staticmethod
    def main(scale: float) -> str:
        arrow_path = combo_arrow_asset()
        css = f"""
        QWidget {{ background: transparent; color: {COLORS['text_main']}; font-family: "Segoe UI"; font-size: {s(11, scale)}px; }}
        QDialog#ChatTrackerDialog {{ background: {COLORS['bg_main']}; border: 1px solid {COLORS['border']}; border-radius: {s(14, scale)}px; }}
        QDialog#StandaloneDialog {{ background: {COLORS['bg_main']}; }}
        QFrame#Shell {{ background: {COLORS['bg_main']}; border: 1px solid #26292F; border-radius: {s(14, scale)}px; }}
        QFrame#TopBar {{ background: transparent; border: none; }}
        QFrame#Logo {{ background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; border-radius: {s(10, scale)}px; }}
        QLabel#LogoText {{ color: {COLORS['accent']}; font-size: {s(11, scale)}px; font-weight: 900; }}
        QLabel#AppTitle {{ color: #FFFFFF; font-size: {s(14, scale)}px; font-weight: 850; }}
        QLabel#AppSubtitle {{ color: {COLORS['text_muted']}; font-size: {s(10, scale)}px; font-weight: 600; }}
        QFrame#Card {{ background: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; border-radius: {s(14, scale)}px; }}
        QFrame#Card[chat_alert="true"] {{ background: #3B2226; border: 3px solid {COLORS['danger']}; }}
        QFrame#AccentLine {{ background: {COLORS['accent']}; border-radius: {s(2, scale)}px; }}
        QLabel#SectionTitle {{ color: #FFFFFF; font-size: {s(15, scale)}px; font-weight: 850; }}
        QLabel#FormLabel {{ color: {COLORS['text_muted']}; font-size: {s(10, scale)}px; font-weight: 700; }}
        QFrame#TimerBubble {{ background: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_soft']}; border-radius: {s(12, scale)}px; }}
        QFrame#TimerBubble[active="true"] {{ background: #252A33; border: 1px solid #4650A8; }}
        QFrame#TimerBubble[spawn_alert="true"] {{ background: #3B2226; border: 2px solid {COLORS['danger']}; }}
        QLabel#TimerName {{ color: #FFFFFF; font-size: {s(12, scale)}px; font-weight: 850; }}
        QLabel#TimerSub {{ color: {COLORS['text_soft']}; font-size: {s(11, scale)}px; font-weight: 750; }}
        QLabel#TimerValue {{ color: {COLORS['text_main']}; font-size: {s(18, scale)}px; font-weight: 900; letter-spacing: 0.5px; }}
        QLabel#WorldName {{ color: #FFFFFF; font-size: {s(18, scale)}px; font-weight: 900; }}
        QLabel#WorldTimer {{ color: {COLORS['text_main']}; font-size: {s(34, scale)}px; font-weight: 900; letter-spacing: 1.0px; }}
        QLabel#DayBadge {{ background: {COLORS['accent']}; color: #FFFFFF; border: 1px solid #7780FF; border-radius: {s(8, scale)}px; padding: {s(5, scale)}px {s(8, scale)}px; font-size: {s(10, scale)}px; font-weight: 900; }}
        QLineEdit, QTextEdit, QComboBox, QSpinBox {{ background: {COLORS['bg_input']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; border-radius: {s(9, scale)}px; padding: {s(7, scale)}px {s(10, scale)}px; font-weight: 750; selection-background-color: {COLORS['accent']}; }}
        QLineEdit, QTextEdit {{ placeholder-text-color: {COLORS['text_disabled']}; }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: {COLORS['accent']}; }}
        QComboBox::drop-down {{ border: none; width: {s(34, scale)}px; subcontrol-origin: padding; subcontrol-position: top right; }}
        QComboBox::down-arrow {{ image: url("{arrow_path}"); width: {s(12, scale)}px; height: {s(8, scale)}px; margin-right: {s(10, scale)}px; }}
        QComboBox QAbstractItemView {{ background: {COLORS['bg_input']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; border-radius: {s(10, scale)}px; padding: {s(6, scale)}px; selection-background-color: transparent; outline: none; }}
        QComboBox QAbstractItemView::item {{ min-height: {s(30, scale)}px; padding: {s(6, scale)}px {s(12, scale)}px; }}
        QMenu {{ background: {COLORS['bg_input']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; padding: {s(5, scale)}px; }}
        QMenu::item {{ padding: {s(8, scale)}px {s(14, scale)}px; border-radius: {s(5, scale)}px; }}
        QMenu::item:selected {{ background: {COLORS['accent']}; color: #FFFFFF; }}
        QPushButton {{ border: none; border-radius: {s(9, scale)}px; padding: {s(8, scale)}px {s(14, scale)}px; color: #FFFFFF; font-weight: 850; }}
        QPushButton#Primary {{ background: {COLORS['accent']}; }}
        QPushButton#Primary:hover {{ background: {COLORS['accent_hover']}; }}
        QPushButton#Danger {{ background: {COLORS['danger']}; }}
        QPushButton#Danger:hover {{ background: {COLORS['danger_hover']}; }}
        QPushButton#Danger:disabled, QPushButton#Danger:disabled:hover, QPushButton#Danger[cooldown="true"], QPushButton#Danger[cooldown="true"]:hover, QPushButton#Danger[no_internet="true"], QPushButton#Danger[no_internet="true"]:hover {{ background: #3D414A; color: #8D939E; border: none; }}
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
        QCheckBox:disabled {{ color: {COLORS['text_disabled']}; }}
        QSlider {{ min-height: {s(34, scale)}px; }}
        QSlider::groove:horizontal {{ height: {s(5, scale)}px; background: #191B20; border: 1px solid #3B404A; border-radius: {s(3, scale)}px; }}
        QSlider::sub-page:horizontal {{ background: {COLORS['accent']}; border: 1px solid {COLORS['accent']}; border-radius: {s(3, scale)}px; }}
        QSlider::add-page:horizontal {{ background: #191B20; border: 1px solid #3B404A; border-radius: {s(3, scale)}px; }}
        QSlider::handle:horizontal {{ width: {s(22, scale)}px; height: {s(22, scale)}px; margin: {s(-10, scale)}px 0; border-radius: {s(11, scale)}px; background: {COLORS['accent']}; border: {s(3, scale)}px solid #252A33; }}
        QSlider::handle:horizontal:hover {{ background: #6B74FF; border: {s(3, scale)}px solid #3C427A; }}
        QFrame#SettingsGroup {{ background: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_soft']}; border-radius: {s(12, scale)}px; }}
        QScrollArea#SettingsScroll {{ background: transparent; border: none; }}
        QScrollArea#MainScroll {{ background: transparent; border: none; }}
        QWidget#MainContent {{ background: transparent; }}
        QWidget#SettingsScrollContent {{ background: transparent; }}
        QScrollBar:vertical {{ background: #191B20; width: {s(12, scale)}px; margin: {s(2, scale)}px 0 {s(2, scale)}px {s(4, scale)}px; border-radius: {s(6, scale)}px; }}
        QScrollBar::handle:vertical {{ background: #5865F2; border-radius: {s(6, scale)}px; min-height: {s(42, scale)}px; }}
        QScrollBar::handle:vertical:hover {{ background: #6B74FF; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: transparent; border: none; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QLabel#GroupTitle {{ color: #FFFFFF; font-size: {s(12, scale)}px; font-weight: 900; }}
        QFrame#RoomSwitch {{ background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; border-radius: {s(12, scale)}px; }}
        QPushButton#RoomSegment {{ background: transparent; color: {COLORS['text_disabled']}; border: 1px solid transparent; border-radius: {s(9, scale)}px; padding: 0; }}
        QPushButton#RoomSegment[active="true"] {{ background: {COLORS['accent']}; color: #FFFFFF; border-color: {COLORS['accent_hover']}; }}
        QPushButton#RoomSegment[active="false"] {{ background: transparent; opacity: 0.65; }}
        QPushButton#RoomSegment:hover {{ border-color: {COLORS['border']}; }}
        QPushButton#ChatButton {{ background: {COLORS['accent']}; border: 1px solid #7780FF; border-radius: {s(24, scale)}px; padding: 0; }}
        QPushButton#TrackerButton {{ background: {COLORS['bg_input']}; color: #FFFFFF; border: 1px solid {COLORS['accent']}; border-radius: {s(13, scale)}px; padding: 0; font-family: "Segoe UI Emoji"; font-size: {s(15, scale)}px; font-weight: 900; }}
        QPushButton#TrackerButton:hover {{ background: {COLORS['accent']}; }}
        QLabel#TrackerPreview {{ background: #111318; border: 1px solid {COLORS['border']}; border-radius: {s(10, scale)}px; color: {COLORS['text_muted']}; }}
        QPushButton#ChatButton:hover {{ background: {COLORS['accent_hover']}; }}
        QPushButton#ChatButton:disabled {{ background: #3D414A; border-color: #555A64; }}
        QPushButton#ChatButton[missing_nickname="true"] {{ background: #3D414A; border-color: #555A64; }}
        QPushButton#ChatButton[missing_nickname="true"]:hover {{ background: #484D58; border-color: #69707E; }}
        QLabel#ChatBadge {{ background: {COLORS['danger']}; border: 2px solid {COLORS['bg_main']}; border-radius: {s(5, scale)}px; }}
        QScrollArea#ChatScroll {{ background: transparent; border: none; }}
        QWidget#ChatContent {{ background: transparent; }}
        QFrame#ChatMessage {{ background: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_soft']}; border-radius: {s(10, scale)}px; }}
        QFrame#EmojiPanel, QFrame#ContactPopover {{ background: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_soft']}; border-radius: {s(10, scale)}px; }}
        QPushButton#EmojiButton {{ background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; padding: 0; font-size: {s(15, scale)}px; }}
        QPushButton#EmojiButton:hover {{ background: #2A2D34; border-color: {COLORS['accent']}; }}
        QPushButton#EmojiPickerButton {{ background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; padding: 0; font-family: "Segoe UI Emoji"; font-size: {s(19, scale)}px; }}
        QPushButton#EmojiPickerButton:hover {{ background: #2A2D34; border-color: {COLORS['accent']}; }}
        QPushButton#SocialButton {{ background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; padding: {s(8, scale)}px {s(12, scale)}px; }}
        QPushButton#SocialButton:hover {{ background: #2A2D34; border-color: {COLORS['accent']}; }}
        QLabel#ChatNick {{ color: #FFFFFF; font-size: {s(11, scale)}px; font-weight: 900; }}
        QLabel#ChatText {{ color: {COLORS['text_main']}; font-size: {s(11, scale)}px; font-weight: 650; }}
        """
        return Style._themed(css)

    @staticmethod
    def overlay(scale: float) -> str:
        css = f"""
        QWidget {{ background: transparent; color: {COLORS['text_main']}; font-family: "Segoe UI"; }}
        QFrame#OverlayBubble {{ background: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; border-radius: {s(18, scale)}px; }}
        QFrame#OverlayBubble[chat_alert="true"] {{ background: #3B2226; border: 3px solid {COLORS['danger']}; }}
        QFrame#OverlayTimerRow {{ background: transparent; border: 1px solid transparent; border-radius: {s(9, scale)}px; }}
        QFrame#OverlayTimerRow[spawn_alert="true"] {{ background: rgba(218,55,60,0.24); border: 2px solid {COLORS['danger']}; }}
        QLabel#OverlayTitle {{ color: {COLORS['accent']}; font-size: {s(13, scale)}px; font-weight: 900; }}
        QFrame#OverlayLine {{ background: rgba(148,155,164,0.30); }}
        QLabel#OverlayName {{ color: #FFFFFF; font-size: {s(12, scale)}px; font-weight: 850; }}
        QLabel#OverlayInterval {{ color: {COLORS['text_soft']}; font-size: {s(10, scale)}px; font-weight: 750; }}
        QLabel#OverlayTimer {{ color: {COLORS['text_main']}; font-size: {s(16, scale)}px; font-weight: 900; letter-spacing: 0.2px; }}
        QLabel#OverlayWorldName {{ color: #FFFFFF; font-size: {s(14, scale)}px; font-weight: 900; }}
        QLabel#OverlayWorldTimer {{ color: {COLORS['text_main']}; font-size: {s(24, scale)}px; font-weight: 900; letter-spacing: 0.8px; }}
        QLabel#OverlayDayBadge {{ background: {COLORS['accent']}; color: #FFFFFF; border: 1px solid #7780FF; border-radius: {s(6, scale)}px; padding: {s(3, scale)}px {s(5, scale)}px; font-size: {s(8, scale)}px; font-weight: 900; }}
        """
        return Style._themed(css)

def system_tray_menu_stylesheet() -> str:
    return """
    QMenu { background-color: #F0F0F0; color: #000000; border: 1px solid #A0A0A0; padding: 1px 0; font-family: "Segoe UI"; font-size: 9pt; }
    QMenu::item { background-color: transparent; padding: 4px 34px 4px 28px; min-width: 92px; }
    QMenu::item:selected { background-color: #91C9F7; color: #000000; }
    QMenu::separator { height: 1px; background: #D0D0D0; margin: 3px 0; }
    """
