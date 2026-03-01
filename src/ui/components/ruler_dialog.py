from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class RulerInputDialog(QDialog):
    """Диалог ввода реальной длины нарисованной линии."""

    value_confirmed = Signal(float)

    def __init__(self, pixel_length: float, parent=None):
        super().__init__(parent)
        self.pixel_length = pixel_length

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(360, 200)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Калибровка масштаба")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: white; border: none; background: transparent;")
        layout.addWidget(title)

        info = QLabel("Укажите реальную длину отрезка:")
        info.setWordWrap(True)
        info.setStyleSheet(
            "color: #ccc; border: none; background: transparent; font-size: 13px;"
        )
        layout.addWidget(info)

        self.spin_length = QDoubleSpinBox()
        self.spin_length.setRange(0.001, 99999)
        self.spin_length.setDecimals(3)
        self.spin_length.setValue(1.0)
        self.spin_length.setSuffix(" м")
        self.spin_length.setFixedHeight(34)
        self.spin_length.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #333; color: white;
                border: 1px solid #444; border-radius: 6px;
                padding: 4px 8px; font-size: 14px;
            }
            QDoubleSpinBox:hover { border: 1px solid #555; }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background: transparent; border: none; width: 16px;
            }
            QDoubleSpinBox::up-arrow {
                image: none; border-left: 4px solid transparent;
                border-right: 4px solid transparent; border-bottom: 5px solid #aaa;
            }
            QDoubleSpinBox::down-arrow {
                image: none; border-left: 4px solid transparent;
                border-right: 4px solid transparent; border-top: 5px solid #aaa;
            }
        """)
        layout.addWidget(self.spin_length)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(36)
        btn_cancel.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #aaa;
                border: 1px solid #444; border-radius: 6px;
                font-weight: bold; padding: 0 16px;
            }
            QPushButton:hover { background-color: #333; color: white; border: 1px solid #555; }
        """)

        btn_ok = QPushButton("Применить")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setFixedHeight(36)
        btn_ok.setFont(QFont("Segoe UI", 13, QFont.Bold))
        btn_ok.clicked.connect(self._on_confirm)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #2ea043; color: white;
                border: none; border-radius: 6px;
                font-weight: bold; padding: 0 16px;
            }
            QPushButton:hover { background-color: #3ab654; }
            QPushButton:pressed { background-color: #238636; }
        """)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

        outer.addWidget(container)

    def _on_confirm(self):
        val = self.spin_length.value()
        if val > 0:
            self.value_confirmed.emit(val)
            self.accept()
