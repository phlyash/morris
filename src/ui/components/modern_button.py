from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPushButton


class ModernButton(QPushButton):
    def __init__(self, text, parent=None, is_sidebar=True):
        super().__init__(text, parent)
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 10))

        if is_sidebar:
            self.setCheckable(True)
            self.setStyleSheet("""
                QPushButton { text-align: left; padding-left: 20px; border: none; background-color: transparent; color: #a0a0a0; }
                QPushButton:hover { color: white; }
                QPushButton:checked { background-color: #3e3e42; color: white; border-left: 3px solid white; }
            """)
        else:
            # Стиль для кнопки "Сортировка"
            self.setStyleSheet("""
                QPushButton { background-color: #333337; color: #ccc; border-radius: 5px; padding: 5px 15px; }
                QPushButton:hover { background-color: #3e3e42; color: white; }
            """)
