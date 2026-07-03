import sys
from PySide6.QtWidgets import QApplication
from app import MainWindow
from config import APP_VERSION

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("B&S NEO Spawn Timer")
    app.setApplicationDisplayName("B&S NEO Spawn Timer")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("westrup")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()