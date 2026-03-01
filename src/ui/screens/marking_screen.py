import cv2
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Core
from src.core import Video
from src.core.project import Project

# Services
from src.services.geometry_storage import GeometryStorageService
from src.services.statistics_service import StatisticsService
from src.services.trajectory_export_service import TrajectoryExportService

# Components
from src.ui.components import VideoPlayerWidget
from src.ui.components.confirm_dialog import ConfirmDialog
from src.ui.components.sidebar_tabs import SidebarTabsWidget
from src.ui.components.trajectory_export_dialog import TrajectoryExportDialog
from src.ui.components.video.graphics_items import EditableGeometryItem
from src.ui.components.video.video_timeline_simple import VideoTimelineWidget

# Threads
from src.ui.threads.statistics_worker import StatisticsWorker


class VideoMarkingWidget(QWidget):
    back_clicked = Signal()
    request_stats_calculation = Signal(object, list, float, int)

    def __init__(self, video: Video, project: Project):
        super().__init__()
        self.video = video
        self.project = project
        self.storage_service = GeometryStorageService(project.path)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 30)
        main_layout.setSpacing(20)

        # === ЛЕВАЯ ЧАСТЬ ===
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Хедер
        self._init_header(left_layout)

        # Плеер
        self.player = VideoPlayerWidget(self.video)
        left_layout.addWidget(self.player, stretch=1)

        # Таймлайн
        self.timeline = VideoTimelineWidget(self.video)
        left_layout.addWidget(self.timeline)

        # === ПРАВАЯ ЧАСТЬ ===
        self.right_panel = SidebarTabsWidget()
        self.right_panel.setFixedWidth(360)

        main_layout.addWidget(left_col)
        main_layout.addWidget(self.right_panel)

        # Save Shortcut
        self.shortcut_save = QShortcut(QKeySequence.Save, self)
        self.shortcut_save.activated.connect(self.save_data)

        # =================== ЛОГИКА ===================

        view = self.player.view
        thread = self.player.thread

        # 1. Таймлайн и Плеер
        self.player.position_changed.connect(self.timeline.set_current_frame)
        self.timeline.frame_clicked.connect(self.player.seek_to_frame)
        self.right_panel.tab_changed.connect(self._on_tab_changed)

        # 2. Геометрия
        geom_page = self.right_panel.geometry_page
        geom_page.shape_create_requested.connect(view.set_creation_mode)
        view.creation_cancelled.connect(geom_page.reset_tool_selection)
        view.item_created.connect(geom_page.register_new_item)
        geom_page.items_deleted.connect(view.remove_items)
        view.delete_requested.connect(geom_page.delete_selected_items)
        view.items_selection_changed.connect(geom_page.update_from_scene_selection)
        geom_page.selection_changed_requested.connect(view.select_items_by_list)
        view.items_selection_changed.connect(
            lambda items: self._reconnect_geometry_signals(items, geom_page)
        )

        # 3. Трекер
        tracker_page = self.right_panel.stack.widget(0)
        self.player.error_occurred.connect(tracker_page.show_error)
        view.tracker_region_selected.connect(lambda: tracker_page.show_error(""))
        tracker_page.model_changed.connect(lambda: tracker_page.show_error(""))
        tracker_page.model_changed.connect(thread.set_tracker_model)
        view.tracker_region_selected.connect(thread.init_tracker_manually)
        tracker_page.manual_setup_toggled.connect(self._on_manual_tracker_toggled)
        view.tracker_region_selected.connect(self._on_tracker_region_selected)

        # Обновление данных
        self.player.thread.frame_data_updated.connect(
            self.timeline.model.update_single_frame_bbox
        )
        self.player.thread.frame_data_updated.connect(self._check_completion_status)

        self.timeline.model.set_tracking_data_map(
            self.player.thread.get_tracking_data()
        )

        # 4. Статистика
        self.stats_thread = QThread()
        self.stats_worker = StatisticsWorker()
        self.stats_worker.moveToThread(self.stats_thread)
        self.request_stats_calculation.connect(self.stats_worker.process)
        self.stats_worker.calculation_finished.connect(self._on_stats_ready)
        self.stats_thread.start()

        self.player.position_changed.connect(self._trigger_stats_calculation)
        self.right_panel.tab_changed.connect(self._on_tab_changed_check_stats)
        self.player.thread.frame_data_updated.connect(self._check_completion_status)

        # Старт
        self.load_data()
        self._on_tab_changed(0)

    def _init_header(self, layout):
        header_layout = QHBoxLayout()
        tag = QLabel(f"  {self.project.name}  ")
        tag.setStyleSheet(
            "background-color: #3e3e42; color: white; border-radius: 4px; font-weight: bold;"
        )
        header_layout.addWidget(tag)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        bread_row = QHBoxLayout()
        btn_back = QPushButton("←")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setFixedSize(30, 30)
        btn_back.clicked.connect(self.on_back_pressed)
        btn_back.setStyleSheet(
            "color: white; background: transparent; font-size: 20px; border: none;"
        )
        lbl = QLabel(self.video.path.name)
        lbl.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        bread_row.addWidget(btn_back)
        bread_row.addWidget(lbl)
        bread_row.addStretch()

        # --- НОВАЯ КНОПКА: ОЧИСТИТЬ ---
        self.btn_clear = QPushButton("✖ Сброс")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setFixedSize(80, 30)
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #3B3C40; color: #aaa;
                border: 1px solid #555; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #8b0000; color: white; border-color: #8b0000; }
        """)
        bread_row.addWidget(self.btn_clear)

        bread_row.addSpacing(10)

        # --- КНОПКА: РАЗМЕЧЕНО ---
        self.btn_status = QPushButton("✔ Размечено")
        self.btn_status.setCheckable(True)
        self.btn_status.setCursor(Qt.PointingHandCursor)
        self.btn_status.setFixedSize(120, 30)
        self.btn_status.clicked.connect(self.save_data)
        self.btn_status.setStyleSheet("""
            QPushButton {
                background-color: #3B3C40; color: #aaa;
                border: 1px solid #555; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45464a; }
            QPushButton:checked {
                background-color: #2e7d32; color: white; border: 1px solid #2e7d32;
            }
        """)
        bread_row.addWidget(self.btn_status)

        bread_row.addSpacing(10)

        # --- КНОПКА: ТРАЕКТОРИЯ ---
        self.btn_trajectory = QPushButton("⬡ Траектория")
        self.btn_trajectory.setCursor(Qt.PointingHandCursor)
        self.btn_trajectory.setFixedSize(100, 30)
        self.btn_trajectory.clicked.connect(self._on_trajectory_clicked)
        self.btn_trajectory.setStyleSheet("""
            QPushButton {
                background-color: #3B3C40; color: #aaa;
                border: 1px solid #555; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45464a; color: white; }
        """)
        bread_row.addWidget(self.btn_trajectory)

        layout.addLayout(bread_row)

    # --- ЛОГИКА ОЧИСТКИ ---

    @Slot()
    def _check_completion_status(self):
        if self.btn_status.isChecked():
            return
        if not hasattr(self.player.thread, "total_frames"):
            self.player.thread.total_frames = int(
                self.player.thread.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            )

        if len(self.player.thread.tracking_data) >= self.player.thread.total_frames - 5:
            self.btn_status.blockSignals(True)
            self.btn_status.setChecked(True)
            self.btn_status.blockSignals(False)
            self.save_data()  # Автосохранение при завершении

    @Slot()
    def _on_clear_clicked(self):
        # Создаем кастомный диалог
        dialog = ConfirmDialog(
            "Сброс разметки",
            "Вы уверены, что хотите удалить всю разметку трекера?\nЭто действие необратимо.",
            self,
        )

        # exec() возвращает QDialog.Accepted (1) если нажали "Удалить"
        if dialog.exec():
            self.player.thread.tracking_data = {}
            self.player.thread.is_tracking_active = False
            if self.player.thread.tracker:
                self.player.thread.tracker.reset()

            self.timeline.model.set_tracking_data_map({})
            self.btn_status.setChecked(False)
            self.player.view.update_tracker_box(False, None)
            self.save_data()

    def on_back_pressed(self):
        self.save_data()
        self.back_clicked.emit()

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

    @Slot(int)
    def _on_tab_changed(self, index):
        is_geometry_tab = index == 1
        self.player.view.set_interaction_enabled(is_geometry_tab)
        if not is_geometry_tab:
            self.right_panel.geometry_page.reset_tool_selection()
        if index != 0:
            tracker_page = self.right_panel.stack.widget(0)
            if tracker_page.btn_manual.isChecked():
                tracker_page.btn_manual.setChecked(False)

    @Slot(int)
    def _on_tab_changed_check_stats(self, index):
        if index == 2:
            current_frame = int(self.player.thread.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self._trigger_stats_calculation(current_frame)

    @Slot(int)
    def _trigger_stats_calculation(self, frame_index):
        # Это для асинхронного обновления UI (пока мы внутри виджета)
        if self.right_panel.stack.currentIndex() != 2:
            return
        tracking_data_copy = self.player.thread.tracking_data.copy()
        ui_items = self.right_panel.geometry_page.get_all_items()
        zones_snapshot = StatisticsService.prepare_geometry_snapshot(ui_items)
        fps = self.player.thread.fps
        self.request_stats_calculation.emit(
            tracking_data_copy, zones_snapshot, fps, frame_index
        )

    @Slot(dict, dict)
    def _on_stats_ready(self, global_stats, zones_stats):
        if self.right_panel.stack.currentIndex() == 2:
            self.right_panel.stack.widget(2).update_data(global_stats, zones_stats)

    @Slot(bool)
    def _on_manual_tracker_toggled(self, checked):
        if checked:
            self.player.pause_video()
            self.player.view.set_tracker_setup_mode(True)
        else:
            self.player.view.set_tracker_setup_mode(False)

    @Slot(tuple)
    def _on_tracker_region_selected(self, bbox):
        self.player.thread.init_tracker_manually(bbox)
        self.right_panel.stack.widget(0).btn_manual.setChecked(False)

    def save_data(self):
        """
        Сохраняет данные.
        ВАЖНО: Используем синхронный расчет статистики,
        чтобы данные были готовы ПРЯМО СЕЙЧАС, а не когда-то в потоке.
        """
        # 1. Данные
        items = self.right_panel.geometry_page.get_all_items()
        tracking_data = self.player.thread.tracking_data
        fps = self.player.thread.fps

        # Определяем диапазон
        max_frame = max(tracking_data.keys()) if tracking_data else 0

        # 2. Синхронный расчет статистики (прямой вызов сервиса, без потоков)
        zones_snapshot = StatisticsService.prepare_geometry_snapshot(items)

        # Прямой вызов calculate (займет 10-50мс, но гарантирует результат)
        _, zones_stats_result = StatisticsService.calculate(
            tracking_data, zones_snapshot, fps, max_frame
        )

        # 3. Сохранение
        is_finished = self.btn_status.isChecked()
        self.storage_service.save(
            self.video.path, items, tracking_data, zones_stats_result, is_finished
        )

    def load_data(self):
        items, tracking_data, is_marked = self.storage_service.load_smart(
            self.video.path
        )
        scene = self.player.view.scene
        geom_page = self.right_panel.geometry_page
        for item in scene.items():
            if isinstance(item, EditableGeometryItem):
                scene.removeItem(item)
        geom_page.list_widget.clear()
        is_enabled = self.player.view.is_interaction_enabled
        for item in items:
            scene.addItem(item)
            geom_page.add_existing_item(item)
            item.set_locked(not is_enabled)
        if tracking_data:
            self.player.thread.set_tracking_data(tracking_data)
            self.timeline.model.set_tracking_data_map(tracking_data)
            current_frame = int(self.player.thread.cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current_frame in tracking_data:
                bbox = tracking_data[current_frame]
                self.player.view.update_tracker_box(True, bbox)
        self.btn_status.setChecked(is_marked)

    def _on_trajectory_clicked(self):
        geometry_items = self.right_panel.geometry_page.get_all_items()
        tracking_data = self.player.thread.tracking_data
        current_frame = int(self.player.thread.cap.get(cv2.CAP_PROP_POS_FRAMES))

        # Получаем размер видео
        cap = cv2.VideoCapture(str(self.video.path))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        # Загружаем сохранённые настройки компаса из проекта
        compass_settings = (
            self.project.compass_settings
            if hasattr(self.project, "compass_settings")
            else None
        )

        dialog = TrajectoryExportDialog(
            geometry_items=geometry_items,
            tracking_data=tracking_data,
            video_size=(width, height),
            current_frame=current_frame,
            compass_settings=compass_settings,
            parent=self,
        )
        dialog.export_clicked.connect(
            lambda options: self._on_export_trajectory(options, dialog)
        )
        dialog.exec()

    def _on_export_trajectory(self, options, dialog=None):
        tracking_data = self.player.thread.tracking_data
        geometry_items = self.right_panel.geometry_page.get_all_items()

        cap = cv2.VideoCapture(str(self.video.path))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        video_size = (width, height)

        # Сохраняем настройки компаса в проект
        if dialog is not None:
            compass_settings = dialog.get_compass_settings()
            self.project.compass_settings = compass_settings
            self.project.save_config()

        try:
            TrajectoryExportService.export_image(
                tracking_data=tracking_data,
                geometry_items=geometry_items,
                video_size=video_size,
                output_path=options["output_path"],
                format=options["format"],
                scale=options["scale"],
                show_trajectory=options["show_trajectory"],
                show_geometry=options["show_geometry"],
                selected_geometry_names=options["selected_geometries"],
                smoothing=options["smoothing"],
                current_frame=None,
                compass=options.get("compass"),
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось экспортировать траекторию: {str(e)}"
            )

    def cleanup(self):
        """
        Остановка всех процессов перед удалением виджета.
        Использование wait() обязательно, чтобы предотвратить краш.
        """
        # 1. Останавливаем видео (чтобы поток вышел из цикла run)
        if hasattr(self, "player"):
            self.player.stop_video()  # Сбрасываем флаг run
            self.player.cleanup()  # Ждем завершения потока (wait())

        # 2. Останавливаем поток статистики
        if hasattr(self, "stats_thread") and self.stats_thread.isRunning():
            self.stats_thread.quit()
            self.stats_thread.wait()  # Блокируем GUI пока поток не умрет

        # 3. Останавливаем таймлайн
        self.timeline.cleanup()
