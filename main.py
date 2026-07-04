import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSharedMemory
from app import MainWindow
from config import APP_VERSION

def main():
    app = QApplication(sys.argv)
    
    shared = QSharedMemory("BnSNeoSpawnTimer")
    
    if not shared.create(1):
        print("Программа уже запущена.")
        return
    app.shared_memory = shared
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