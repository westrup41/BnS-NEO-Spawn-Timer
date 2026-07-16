from PySide6.QtWidgets import QPushButton

class TrackerButton(QPushButton):
    def __init__(self, app, parent):
        super().__init__('🔎\nBETA', parent); self.app=app; self.setObjectName('TrackerButton')
