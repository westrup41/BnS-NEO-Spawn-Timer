from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)

from styles import Style
from utils import s


class MessageDialog(QDialog):
    def __init__(
        self,
        parent,
        title: str,
        text: str,
        details: str = "",
        ok_text: str = "OK",
        cancel_text: str | None = None,
        ok_first: bool = False,
        center_buttons: bool = False,
        minimum_width: int | None = None,
    ):
        super().__init__(parent)

        scale = parent.settings.app_scale if parent else 1.0

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setStyleSheet(Style.main(scale))
        self.setMinimumWidth(s(minimum_width or 520, scale))
        self.adjustSize()

        self.result = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)

        layout = QVBoxLayout(shell)
        layout.setContentsMargins(
            s(20, scale),
            s(18, scale),
            s(20, scale),
            s(18, scale),
        )
        layout.setSpacing(s(16, scale))

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label)

        text_label = QLabel(text)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)

        if details:
            details_label = QLabel(details)
            details_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            details_label.setWordWrap(True)
            details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(details_label)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel = None
        if cancel_text:
            cancel = QPushButton(cancel_text)
            cancel.setObjectName("Ghost")
            cancel.clicked.connect(self.reject)

        ok = QPushButton(ok_text)
        ok.setObjectName("Primary")
        ok.clicked.connect(self.accept_dialog)
        self.cancel_button = None
        
        if cancel is not None:
            self.cancel_button = cancel
        if ok_first:
            buttons.addWidget(ok)
            if cancel is not None:
                buttons.addWidget(cancel)
        else:
            if cancel is not None:
                buttons.addWidget(cancel)
            buttons.addWidget(ok)
        if center_buttons:
            buttons.addStretch()

        layout.addLayout(buttons)

    def accept_dialog(self):
        self.result = True
        self.accept()
        
    @staticmethod
    def show(
        parent,
        title,
        text,
        details="",
        ok_text="OK",
        cancel_text=None,
    ):
        dialog = MessageDialog(
            parent,
            title,
            text,
            details,
            ok_text,
            cancel_text,
        )
        dialog.exec()
        return dialog.result
        
    def exec_result(self):
        self.exec()
        return self.result
