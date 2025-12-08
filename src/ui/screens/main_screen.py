from pathlib import Path
from PySide6.QtGui import QFont, Qt
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QFrame,
                               QVBoxLayout, QLabel, QScrollArea, QFileDialog, QMessageBox)
from PySide6.QtCore import Signal

from src.config import get_resource_path
from src.core.app_state import AppState
from src.core.project import Project
from src.ui.components import ModernButton
from src.ui.components.action_card import ActionCard
from src.ui.components.recent_item import RecentItem


class MainWindow(QMainWindow):
    # Сигнал для контроллера: нужно открыть этот проект
    project_request = Signal(Project)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Morris Dashboard")
        self.resize(1000, 700)
        self.setStyleSheet("background-color: #1e1e1e;")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- SIDEBAR (Ваш код без изменений) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("background-color: #252526; border-right: 1px solid #333;")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 20, 0, 20)

        logo_box = QHBoxLayout()
        logo_box.setContentsMargins(20, 0, 0, 20)
        logo_img = QSvgWidget(str(get_resource_path('morris.svg')))
        logo_img.setFixedSize(40, 40)
        logo_text = QLabel("Morris")
        logo_text.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo_text.setStyleSheet("color: white; margin-left: 10px;")
        logo_box.addWidget(logo_img)
        logo_box.addWidget(logo_text)
        sb_layout.addLayout(logo_box)

        # sb_layout.addWidget(ModernButton("Проекты"))
        # sb_layout.addWidget(ModernButton("Документация"))
        # sb_layout.addWidget(ModernButton("Настройки"))
        sb_layout.addStretch()
        # sb_layout.addWidget(ModernButton("Помощь"))

        # --- CONTENT ---
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(40, 40, 40, 40)

        c_layout.addWidget(QLabel("Проекты", styleSheet="color: white; font-size: 24px; font-weight: bold;"))

        # -- КНОПКИ ДЕЙСТВИЙ --
        actions = QHBoxLayout()

        self.card_create = ActionCard("Создать", "+")
        # Делаем кликабельным и привязываем к create_project
        self._make_clickable(self.card_create, self.create_project)
        actions.addWidget(self.card_create)

        self.card_open = ActionCard("Открыть", "●")
        # Делаем кликабельным и привязываем к open_project_dialog
        self._make_clickable(self.card_open, self.open_project_dialog)
        actions.addWidget(self.card_open)

        actions.addStretch()
        c_layout.addLayout(actions)

        # -- НЕДАВНИЕ --
        c_layout.addWidget(QLabel("Недавние", styleSheet="color: #ddd; font-size: 14px; margin-top: 20px;"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        s_content = QWidget()
        s_content.setStyleSheet("background: transparent;")
        self.s_layout = QVBoxLayout(s_content)
        self.s_layout.setSpacing(10)

        recents = AppState.get_recent_projects()
        for project_path in recents:
            item = RecentItem(project_path)
            self.s_layout.addWidget(item)
            # ВАЖНО: Ваш RecentItem имеет сигнал clicked?
            # Если да, AppController его подключит.
            # Если нет (как ActionCard), то можно использовать _make_clickable здесь же.
            # Но ваш контроллер делает это снаружи, так что оставляем.

        self.s_layout.addStretch()
        scroll.setWidget(s_content)
        c_layout.addWidget(scroll)

        layout.addWidget(sidebar)
        layout.addWidget(content)

    def _make_clickable(self, widget, callback):
        """Хак для кликабельности виджетов"""
        original = widget.mousePressEvent

        def new_press(event):
            if event.button() == Qt.LeftButton:
                callback()
            if original: original(event)

        widget.mousePressEvent = new_press
        widget.setCursor(Qt.PointingHandCursor)

    # --- НОВЫЕ МЕТОДЫ ---

    def create_project(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для нового проекта")
        if not folder:
            return

        path = Path(folder)
        morris_dir = path / ".morris"

        if morris_dir.exists() and morris_dir.is_dir():
            QMessageBox.warning(self, "Ошибка", f"Проект уже существует в '{path.name}'")
            return

        try:
            morris_dir.mkdir()
            # Создаем маркер проекта, чтобы он считался валидным
            (morris_dir / ".morproj").touch()

            # Добавляем в историю
            AppState.add_recent(Project(path, path.stem))

            # Запускаем
            self.project_request.emit(Project(path))

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def open_project_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Открыть проект")
        if not folder: return

        path = Path(folder)
        AppState.add_recent(Project(path, path.stem))
        self.project_request.emit(Project(path))
