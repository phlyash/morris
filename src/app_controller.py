from src.core.project import Project
from src.ui.components.recent_item import RecentItem
from src.ui.screens import MainWindow, ProjectWindow


class AppController:
    def __init__(self):
        self.main_window = MainWindow()
        self.project_window = None

        # 1. Сигналы из главного меню
        self.main_window.project_request.connect(self.open_project)
        self.connect_projects()  # Недавние

        self.main_window.show()

    def connect_projects(self):
        layout = self.main_window.s_layout
        for i in range(layout.count()):
            item = layout.itemAt(i).widget()
            if isinstance(item, RecentItem):
                item.clicked.connect(self.open_project)

    def open_project(self, project: Project):
        # Если проект уже открыт, закрываем его (на всякий случай)
        if self.project_window:
            self.project_window.close()
            self.project_window.deleteLater()

        project.load()  # Загрузка базовых данных проекта

        self.project_window = ProjectWindow(project)

        # --- ПОДКЛЮЧЕНИЕ ВОЗВРАТА ДОМОЙ ---
        self.project_window.home_clicked.connect(self.return_to_main)

        self.project_window.show()
        self.main_window.close()  # Скрываем главное меню

    def return_to_main(self):
        """Возврат к выбору проектов"""
        if self.project_window:
            # Метод close() вызывает closeEvent внутри ProjectWindow,
            # что гарантирует сохранение данных и остановку потоков (cleanup).
            self.project_window.close()
            self.project_window.deleteLater()  # Очищаем память
            self.project_window = None

        # Обновляем список недавних (если проект был новым)
        # Для этого пересоздаем MainWindow или обновляем его список
        self.main_window.close()  # Закрываем старое
        self.main_window = MainWindow()  # Создаем свежее (с обновленным списком Recents)

        # Заново подключаем сигналы
        self.main_window.project_request.connect(self.open_project)
        self.connect_projects()

        self.main_window.show()