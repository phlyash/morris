from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class ConfirmDialog(QDialog):
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Контейнер
        container = QFrame(self)
        container.setFixedWidth(360)
        # 1. Задаем минимальную высоту, чтобы диалог не схлопывался слишком сильно
        container.setMinimumHeight(180)

        container.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(15)

        # 2. ВАЖНО: Заставляем layout подгонять размер контейнера под содержимое
        # Это не даст тексту "сплющиться"
        layout.setSizeConstraint(QVBoxLayout.SetMinAndMaxSize)

        # Заголовок
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet("color: white; border: none; background: transparent;")
        lbl_title.setWordWrap(True)
        layout.addWidget(lbl_title)

        # Текст
        lbl_text = QLabel(text)
        lbl_text.setFont(QFont("Segoe UI", 13))
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet("color: #ccc; border: none; background: transparent;")
        layout.addWidget(lbl_text)

        # Распорка (пружина), чтобы кнопки всегда были прижаты к низу,
        # если текста мало, но при этом диалог растягивался, если текста много.
        layout.addStretch()

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #aaa; border: 1px solid #444; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #333; color: white; }
        """)

        self.btn_yes = QPushButton("Удалить")
        self.btn_yes.setCursor(Qt.PointingHandCursor)
        self.btn_yes.setFixedHeight(36)
        self.btn_yes.clicked.connect(self.accept)
        self.btn_yes.setStyleSheet("""
            QPushButton {
                background-color: #8b0000; color: white; border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #a30000; }
        """)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_yes)
        layout.addLayout(btn_layout)

        main_layout.addWidget(container)
