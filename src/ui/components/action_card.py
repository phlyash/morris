from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ActionCard(QWidget):
    """
    Виджет кнопки действия:
    [ Прямоугольник с иконкой внутри круга ]
              Текст под ним
    """

    def __init__(self, title, symbol, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 120)  # Общий размер (блок + текст)
        self.setCursor(Qt.PointingHandCursor)

        # Основной вертикальный лейаут
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 1. Верхний блок (Сама кнопка)
        self.card_body = QFrame()
        self.card_body.setFixedSize(160, 90)

        # Лейаут для центрирования круга внутри блока
        body_layout = QVBoxLayout(self.card_body)
        body_layout.setAlignment(Qt.AlignCenter)
        body_layout.setContentsMargins(0, 0, 0, 0)

        # 2. Круглый фон для иконки
        self.icon_circle = QLabel(symbol)
        self.icon_circle.setFixedSize(44, 44)
        self.icon_circle.setAlignment(Qt.AlignCenter)
        self.icon_circle.setFont(QFont("Arial", 24))

        # Добавляем круг в блок
        body_layout.addWidget(self.icon_circle)
        layout.addWidget(self.card_body)

        # 3. Текст под блоком
        self.text_label = QLabel(title)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(self.text_label)

        # Применяем начальный стиль
        self._update_style(hover=False)

    def enterEvent(self, event):
        self._update_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style(hover=False)
        super().leaveEvent(event)

    def _update_style(self, hover: bool):
        if hover:
            # Стиль при наведении (чуть светлее)
            self.card_body.setStyleSheet("""
                QFrame {
                    background-color: #454549; 
                    border-radius: 16px;
                }
            """)
            # Круг внутри становится светлее
            self.icon_circle.setStyleSheet("""
                QLabel {
                    background-color: #555559;
                    color: #ffffff;
                    border-radius: 22px; /* Половина от 44px */
                }
            """)
            self.text_label.setStyleSheet("color: #ffffff;")
        else:
            # Обычный стиль (как на скрине)
            self.card_body.setStyleSheet("""
                QFrame {
                    background-color: #3a3a3e;
                    border-radius: 16px;
                }
            """)
            # Круг темнее фона, иконка серая
            self.icon_circle.setStyleSheet("""
                QLabel {
                    background-color: #48484c;
                    color: #aaa;
                    border-radius: 22px;
                }
            """)
            self.text_label.setStyleSheet("color: #ffffff;")