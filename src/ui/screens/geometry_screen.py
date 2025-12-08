import cv2
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel)
from PySide6.QtCore import Qt, Slot

# Core
from src.core.project import Project
# Services
from src.services.geometry_storage import GeometryStorageService
# Components
from src.ui.components.video.video_view import VideoGraphicsView
from src.ui.components.sidebar_tabs import SidebarTabsWidget
from src.ui.components.video.graphics_items import EditableGeometryItem


class ProjectGeometryWidget(QWidget):
    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.storage_service = GeometryStorageService(project.path)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 30)
        main_layout.setSpacing(20)

        # === ЛЕВАЯ ЧАСТЬ (Только View) ===
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Хедер
        header_label = QLabel("Базовая геометрия проекта")
        header_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        left_layout.addWidget(header_label)

        # Подзаголовок
        sub_label = QLabel("Настройка зон на примере первого видео")
        sub_label.setStyleSheet("color: #aaa; font-size: 14px;")
        left_layout.addWidget(sub_label)

        # Графическая сцена (без плеера и таймлайна)
        self.view = VideoGraphicsView()
        left_layout.addWidget(self.view)

        main_layout.addWidget(left_col, stretch=1)

        # === ПРАВАЯ ЧАСТЬ (Сайдбар) ===
        self.sidebar = SidebarTabsWidget()
        self.sidebar.setFixedWidth(360)

        # НАСТРОЙКА: Оставляем только вкладку Геометрии
        self.sidebar.set_tabs_visible(tracker=False, geometry=True, stats=False)

        main_layout.addWidget(self.sidebar)

        # === ЗАГРУЗКА ПЕРВОГО КАДРА ===
        self.current_video_path = None
        self._load_first_video_frame()

        # === ЛОГИКА ГЕОМЕТРИИ ===
        # Подключаем сигналы так же, как в MarkingScreen, но только для геометрии
        geom_page = self.sidebar.geometry_page

        # Инструменты
        geom_page.shape_create_requested.connect(self.view.set_creation_mode)
        self.view.creation_cancelled.connect(geom_page.reset_tool_selection)

        # Создание/Удаление
        self.view.item_created.connect(geom_page.register_new_item)
        geom_page.items_deleted.connect(self.view.remove_items)
        self.view.delete_requested.connect(geom_page.delete_selected_items)

        # Синхронизация выделения
        self.view.items_selection_changed.connect(geom_page.update_from_scene_selection)
        geom_page.selection_changed_requested.connect(self.view.select_items_by_list)

        # Обновление координат
        self.view.items_selection_changed.connect(lambda items: self._reconnect_geometry_signals(items, geom_page))

        # Включаем взаимодействие (так как вкладка геометрии активна всегда)
        self.view.set_interaction_enabled(True)

        # Загружаем существующие данные
        self.load_data()

        # Автосохранение при любых изменениях (опционально)
        # Или добавить кнопку сохранения.
        # Для простоты используем ту же логику сохранения, что и раньше,
        # но можно добавить кнопку "Сохранить" в header_label layout.

    def _load_first_video_frame(self):
        if not self.project.videos:
            return  # Нет видео в проекте

        # Сортируем по имени и берем первое
        sorted_videos = sorted(self.project.videos, key=lambda v: v.path.name)
        first_video = sorted_videos[0]
        self.current_video_path = first_video.path

        # Читаем 0-й кадр
        cap = cv2.VideoCapture(self.current_video_path)
        ret, frame = cap.read()
        cap.release()

        if ret:
            self.view.update_image(frame)
        else:
            pass

    def _reconnect_geometry_signals(self, items, geom_page):
        if len(items) == 1:
            item = items[0]
            try:
                item.geometry_changed.disconnect()
            except:
                pass
            item.geometry_changed.connect(lambda r: geom_page.load_item_data(item))
        else:
            for item in items:
                try:
                    item.geometry_changed.disconnect()
                except:
                    pass

    def save_data(self):
        """Сохраняем геометрию в .morproj И ВО ВСЕ .mor файлы проекта"""
        items = self.sidebar.geometry_page.get_all_items()

        # Используем метод распространения
        self.storage_service.propagate_base_geometry(items)

    def load_data(self):
        """Загружаем из .morproj"""
        # Используем специальный метод для загрузки шаблона
        items = self.storage_service.load_project_settings()

        scene = self.view.scene
        geom_page = self.sidebar.geometry_page

        # Очистка
        for item in scene.items():
            if isinstance(item, EditableGeometryItem): scene.removeItem(item)
        geom_page.list_widget.clear()

        # Добавление
        for item in items:
            scene.addItem(item)
            geom_page.add_existing_item(item)
            item.set_locked(False)

    def hideEvent(self, event):
        self.save_data()
        super().hideEvent(event)