import shutil
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, Qt, QMouseEvent
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (QStackedWidget, QMainWindow, QWidget, QHBoxLayout,
                               QFrame, QVBoxLayout, QLabel, QScrollArea, QButtonGroup, QFileDialog, QMenu)

from src.config import get_resource_path
from src.core import Video
from src.core.project import Project
from src.services.geometry_storage import GeometryStorageService
from src.ui.components import ModernButton, FlowLayout
from src.ui.components.video import VideoCard
from src.ui.screens.geometry_screen import ProjectGeometryWidget
from src.ui.screens.marking_screen import VideoMarkingWidget
from src.ui.screens.statistics_screen import ProjectStatisticsWidget


# --- Заглушка для новых страниц ---
class PlaceholderPage(QWidget):
    def __init__(self, text):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #555; font-size: 24px; font-weight: bold;")
        layout.addWidget(label)


class ProjectWindow(QMainWindow):
    home_clicked = Signal()

    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.setWindowTitle(f"Morris - {project.name}")
        self.resize(1200, 800)
        self.setStyleSheet("background-color: #1e1e1e;")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 1. SIDEBAR ===
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("background-color: #252526; border-right: 1px solid #333;")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 20, 0, 20)
        sb_layout.setSpacing(5)  # Добавил отступ между кнопками

        # --- ЛООТИП (КЛИКАБЕЛЬНЫЙ) ---
        self.logo_container = QWidget()

        # 1. Устанавливаем курсор-руку
        self.logo_container.setCursor(Qt.CursorShape.PointingHandCursor)

        # 2. Перехватываем клик
        self.logo_container.mousePressEvent = self._on_logo_clicked

        logo_box = QHBoxLayout(self.logo_container)
        logo_box.setContentsMargins(20, 0, 0, 20)
        try:
            logo_img = QSvgWidget(str(get_resource_path('morris.svg')))
            logo_img.setFixedSize(40, 40)

            # 3. ВАЖНО: Делаем картинку прозрачной для мыши,
            # чтобы курсор брался от родителя (logo_container)
            logo_img.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            logo_img.setCursor(Qt.CursorShape.PointingHandCursor)
            logo_box.addWidget(logo_img)
        except:
            pass

        logo_text = QLabel("Morris")
        logo_text.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo_text.setStyleSheet("color: white; margin-left: 10px;")

        logo_text.setCursor(Qt.CursorShape.PointingHandCursor)

        # 4. ВАЖНО: Делаем текст прозрачным для мыши
        logo_text.setAttribute(Qt.WA_TransparentForMouseEvents)

        logo_box.addWidget(logo_text)

        sb_layout.addWidget(self.logo_container)

        # --- НАВИГАЦИЯ (С ГРУППОЙ КНОПОК) ---
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.idClicked.connect(self._on_nav_button_clicked)

        # Кнопка Видео (ID 0)
        self.btn_video = ModernButton("Видео", is_sidebar=True)
        self.btn_video.setCheckable(True)
        self.btn_video.setChecked(True)  # По умолчанию выбрана
        self.nav_group.addButton(self.btn_video, 0)
        sb_layout.addWidget(self.btn_video)

        # Кнопка Геометрия (ID 1) - НОВАЯ
        self.btn_geom = ModernButton("Геометрия", is_sidebar=True)
        self.btn_geom.setCheckable(True)
        self.nav_group.addButton(self.btn_geom, 1)
        sb_layout.addWidget(self.btn_geom)

        # Кнопка Статистика (ID 2)
        self.btn_stats = ModernButton("Статистика", is_sidebar=True)
        self.btn_stats.setCheckable(True)
        self.nav_group.addButton(self.btn_stats, 2)
        sb_layout.addWidget(self.btn_stats)

        sb_layout.addStretch()

        self.storage_service = GeometryStorageService(self.project.path)
        self.videos_meta = self.storage_service.get_videos_metadata(self.project.videos)

        # Кнопка Помощь (ID 3)
        self.btn_help = ModernButton("Помощь", is_sidebar=True)
        self.btn_help.setCheckable(True)
        self.nav_group.addButton(self.btn_help, 3)
        sb_layout.addWidget(self.btn_help)

        main_layout.addWidget(sidebar)

        # === 2. CONTENT AREA ===
        self.content_stack = QStackedWidget()

        # INDEX 0: Сетка
        self.grid_view_widget = self.create_grid_view(project.name)
        self.content_stack.addWidget(self.grid_view_widget)

        # INDEX 1: ЭКРАН ГЕОМЕТРИИ (ЗАМЕНА ЗАГЛУШКИ)
        self.geometry_screen = ProjectGeometryWidget(project)
        self.content_stack.addWidget(self.geometry_screen)

        # INDEX 2: Статистика
        self.statistics_screen = ProjectStatisticsWidget(project)
        self.statistics_screen.video_requested.connect(self.open_video_by_name)
        self.content_stack.addWidget(self.statistics_screen)

        # INDEX 3: Страница Помощи (Заглушка)
        self.content_stack.addWidget(PlaceholderPage("Справка и документация"))

        # INDEX 4: Страница Редактора Видео (Динамическая)
        # Изначально добавляем пустышку, чтобы занять индекс 4
        self.editor_placeholder = QWidget()
        self.content_stack.addWidget(self.editor_placeholder)

        main_layout.addWidget(self.content_stack)

        # Храним ссылку на редактор, чтобы знать, куда возвращаться
        self.current_video_editor = None

    def _on_logo_clicked(self, event: QMouseEvent):
        """Обработчик клика по логотипу"""
        if event.button() == Qt.LeftButton:
            self.home_clicked.emit()

    def _on_nav_button_clicked(self, btn_id):
        """Обработчик переключения вкладок сайдбара"""
        if btn_id == 0:
            # Вкладка "Видео": Либо сетка, либо открытый редактор
            if self.current_video_editor:
                self.content_stack.setCurrentIndex(4)  # Редактор
            else:
                self.content_stack.setCurrentIndex(0)  # Сетка
        elif btn_id == 2:  # Статистика
            self.content_stack.setCurrentIndex(btn_id)
            # Автообновление при входе
            self.statistics_screen.refresh_data()

        else:
            # Вкладки Геометрия (1), Статистика (2), Помощь (3)
            self.content_stack.setCurrentIndex(btn_id)

    def open_video_by_name(self, video_name: str):
        """
        Слот: вызывается из статистики при клике на имя файла.
        """
        # 1. Ищем объект Video по имени
        target_video = None
        for vid in self.project.videos:
            if vid.path.name == video_name:
                target_video = vid
                break

        if target_video:
            # 2. Открываем редактор
            self.open_video_editor(target_video)

    def open_video_editor(self, video: Video):
        # 1. ОЧИСТКА ТЕКУЩЕГО
        if self.current_video_editor:
            self.current_video_editor.save_data()  # Сохраняем
            self.current_video_editor.cleanup()  # Останавливаем потоки (wait)

            # ВАЖНО: Удаляем из стека, если он там есть
            # Если мы переходим из статистики, то в стеке (индекс 4) может лежать
            # как раз этот self.current_video_editor

            if self.content_stack.indexOf(self.current_video_editor) != -1:
                self.content_stack.removeWidget(self.current_video_editor)

            # Явное удаление
            self.current_video_editor.deleteLater()
            self.current_video_editor = None

        # 2. УДАЛЕНИЕ МУСОРА С ИНДЕКСА 4
        # Даже если мы удалили current_video_editor, на индексе 4 мог остаться placeholder
        old_widget = self.content_stack.widget(4)
        if old_widget:
            self.content_stack.removeWidget(old_widget)
            old_widget.deleteLater()

        # 3. СОЗДАНИЕ НОВОГО
        editor = VideoMarkingWidget(video, self.project)
        editor.back_clicked.connect(self.show_grid_view)

        self.current_video_editor = editor
        self.content_stack.insertWidget(4, editor)
        self.content_stack.setCurrentIndex(4)
        self.btn_video.setChecked(True)

    def create_grid_view(self, project_name):
        """Создает виджет со списком видео"""
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(20)

        # Хлебные крошки
        bread_label = QLabel(project_name)
        bread_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        bread_label.setStyleSheet("color: #ccc;")
        content_layout.addWidget(bread_label)

        # Хедер
        header_box = QHBoxLayout()
        h1 = QLabel("Видео")
        h1.setFont(QFont("Segoe UI", 24, QFont.Bold))
        h1.setStyleSheet("color: white;")
        sort_btn = ModernButton("⇅ Сортировка", is_sidebar=False)

        sort_menu = QMenu(sort_btn)
        sort_menu.setStyleSheet("""
                    QMenu { background-color: #2d2d30; color: white; border: 1px solid #444; }
                    QMenu::item { padding: 5px 20px; }
                    QMenu::item:selected { background-color: #3e3e42; }
                """)

        a1 = sort_menu.addAction("По имени (А-Я)")
        a1.triggered.connect(lambda: self.sort_videos("name_asc"))

        a2 = sort_menu.addAction("По статусу (Размеченные первые)")
        a2.triggered.connect(lambda: self.sort_videos("marked_first"))

        a3 = sort_menu.addAction("По длительности (По убыванию)")
        a3.triggered.connect(lambda: self.sort_videos("duration_desc"))

        sort_btn.setMenu(sort_menu)
        header_box.addStretch()
        header_box.addWidget(sort_btn)
        content_layout.addLayout(header_box)

        # Скролл зона
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")

        # FlowLayout
        self.flow_layout = FlowLayout(grid_widget, margin=0, hSpacing=20, vSpacing=20)

        self.storage_service = GeometryStorageService(self.project.path)
        self.videos_meta = self.storage_service.get_videos_metadata(self.project.videos)

        # Кнопка добавления
        add_card = VideoCard(None, is_add_button=True)
        self.flow_layout.addWidget(add_card)
        self._bind_add_action(add_card)

        status_service = GeometryStorageService(self.project.path)

        for video in self.project.videos:
            # Проверяем статус видео
            is_marked = status_service.get_marked_status(video.path.name)

            # Создаем карточку
            card = VideoCard(video, has_tag=is_marked)  # <--- ПЕРЕДАЕМ СТАТУС

            card.delete_requested.connect(self.on_video_deleted)

            self.flow_layout.addWidget(card)
            self.bind_click_to_card(card, video)

        scroll_area.setWidget(grid_widget)
        content_layout.addWidget(scroll_area)

        self.refresh_grid_content()

        return content_frame

    def _bind_add_action(self, card_widget):
        """Привязывает диалог добавления к карточке плюса"""
        original_mouse_press = card_widget.mousePressEvent

        def new_mouse_press(event):
            if event.button() == Qt.LeftButton:
                self.add_videos_dialog()
            if original_mouse_press:
                original_mouse_press(event)
            else:
                QWidget.mousePressEvent(card_widget, event)

        card_widget.mousePressEvent = new_mouse_press
        card_widget.setCursor(Qt.PointingHandCursor)

    def add_videos_dialog(self):
        """Диалог выбора и копирования видео"""
        file_dialog = QFileDialog(self, "Добавить видео")
        file_dialog.setNameFilters(["Videos (*.mp4 *.avi)", "All Files (*)"])
        file_dialog.setFileMode(QFileDialog.ExistingFiles)  # Множественный выбор

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self._import_videos(selected_files)

    def _import_videos(self, file_paths):
        """Копирует файлы в папку проекта и обновляет UI"""
        destination_dir = self.project.path

        new_videos_count = 0

        for file_path_str in file_paths:
            src_path = Path(file_path_str)
            dest_path = destination_dir / src_path.name

            # Проверка на дубликаты
            if dest_path.exists():
                print(f"Skipping {src_path.name}: already exists in project.")
                continue

            try:
                shutil.copy2(src_path, dest_path)
                new_videos_count += 1
            except Exception as e:
                print(f"Error copying {src_path.name}: {e}")

        if new_videos_count > 0:
            # Обновляем объект проекта (пересканируем папку)
            self.project.reload_videos()

            # Обновляем сетку (пересоздаем её, как при кнопке Назад)
            self.show_grid_view()

    def bind_click_to_card(self, card_widget, video: Video):
        """Привязывает событие клика к карточке"""
        original_mouse_press = card_widget.mousePressEvent

        def new_mouse_press(event):
            if event.button() == Qt.LeftButton:
                self.open_video_editor(video)
            if original_mouse_press:
                original_mouse_press(event)
            else:
                QWidget.mousePressEvent(card_widget, event)

        card_widget.mousePressEvent = new_mouse_press

    def show_grid_view(self):
        """Возвращает интерфейс к сетке видео"""
        if self.current_video_editor:
            self.current_video_editor.cleanup()
            self.current_video_editor = None

        # Удаляем старую сетку (она на индексе 0)
        old_grid = self.content_stack.widget(0)
        self.content_stack.removeWidget(old_grid)
        old_grid.deleteLater()

        # Создаем новую сетку (с актуальными статусами)
        new_grid = self.create_grid_view(self.project.name)
        self.content_stack.insertWidget(0, new_grid)

        # Переключаемся
        self.content_stack.setCurrentIndex(0)
        self.btn_video.setChecked(True)

    def go_back(self):
        # Метод дублирует show_grid_view, оставлен для совместимости если используется где-то еще
        self.show_grid_view()

    def closeEvent(self, event):
        """Вызывается при закрытии окна приложения"""
        # Останавливаем редактор видео
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if hasattr(widget, 'cleanup'):
                widget.cleanup()

        # Останавливаем загрузчик статистики (если он есть)
        if hasattr(self, 'statistics_screen'):
            self.statistics_screen.cleanup()

        event.accept()
        super().closeEvent(event)

    def refresh_grid_content(self):
        """Перерисовывает карточки в flow_layout"""
        # 1. Очистка
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 2. Кнопка Добавить
        add_card = VideoCard(None, is_add_button=True)
        self.flow_layout.addWidget(add_card)
        self._bind_add_action(add_card)

        # 3. Карточки Видео
        for video in self.project.videos:
            meta = self.videos_meta.get(video.path.name, {})
            is_marked = meta.get("is_marked", False)

            card = VideoCard(video, has_tag=is_marked)

            # --- ВАЖНО: ПОДКЛЮЧАЕМ СИГНАЛ УДАЛЕНИЯ ---
            card.delete_requested.connect(self.on_video_deleted)
            # ----------------------------------------

            self.flow_layout.addWidget(card)
            self.bind_click_to_card(card, video)

    def sort_videos(self, criteria):
        """Сортирует список self.project.videos и обновляет UI"""
        if criteria == "name_asc":
            self.project.videos.sort(key=lambda v: v.path.name)

        elif criteria == "marked_first":
            # True > False, поэтому reverse=True поставит размеченные (True) первыми
            self.project.videos.sort(
                key=lambda v: self.videos_meta.get(v.path.name, {}).get("is_marked", False),
                reverse=True
            )

        elif criteria == "duration_desc":
            self.project.videos.sort(
                key=lambda v: self.videos_meta.get(v.path.name, {}).get("duration", 0),
                reverse=True
            )

        self.refresh_grid_content()

    def on_video_deleted(self):
        """Вызывается, когда VideoCard удалила файл"""
        # Пересканируем папку
        self.project.reload_videos()
        # Обновляем метаданные (так как файл удален)
        self.videos_meta = self.storage_service.get_videos_metadata(self.project.videos)
        # Перерисовываем сетку
        self.refresh_grid_content()
