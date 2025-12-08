import sys

from PySide6.QtWidgets import QApplication

from src.app_controller import AppController

if __name__ == "__main__":
    app = QApplication(sys.argv)

    controller = AppController()

    sys.exit(app.exec())
