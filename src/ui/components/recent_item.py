from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget, QVBoxLayout

from src.core.project import Project


class RecentItem(QFrame):
    """Элемент списка проектов - теперь с сигналом нажатия"""

    clicked = Signal(Project)

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setFixedHeight(70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QFrame { background-color: #333337; border-radius: 10px; } QFrame:hover { background-color: #3e3e42; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        icon_placeholder = QLabel()
        icon_placeholder.setFixedSize(40, 40)
        icon_placeholder.setStyleSheet("background-color: #666; border-radius: 5px;")

        text_container = QWidget()
        text_container.setStyleSheet("background-color: transparent;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        lbl_title = QLabel(project.name)
        lbl_title.setFont(QFont("Segoe UI", 11))
        lbl_title.setStyleSheet("color: white; background-color: transparent;")
        lbl_path = QLabel(str(project.path))
        lbl_path.setFont(QFont("Segoe UI", 9))
        lbl_path.setStyleSheet("color: #888; background-color: transparent;")

        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_path)

        layout.addWidget(icon_placeholder)
        layout.addWidget(text_container)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project)
        super().mousePressEvent(event)
