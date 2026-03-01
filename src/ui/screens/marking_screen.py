import math

import cv2
from PySide6.QtCore import QPointF, Qt, QThread, QTimer, Signal, Slot
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
from src.ui.components.ruler_dialog import RulerInputDialog
from src.ui.components.ruler_item import RulerLineItem
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

        # Per-video масштаб (0 = используется проектный)
        self._video_scale_factor = 0.0
        self._load_video_scale()

        # Состояние линейки
        self._ruler_mode = False
        self._ruler_start = None
        self._ruler_item = None

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

        self._update_ruler_ui()

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
        geom_page.shape_create_requested.connect(self._on_shape_requested)
        view.creation_cancelled.connect(geom_page.reset_tool_selection)
        view.item_created.connect(geom_page.register_new_item)
        geom_page.items_deleted.connect(view.remove_items)
        view.delete_requested.connect(geom_page.delete_selected_items)
        view.items_selection_changed.connect(geom_page.update_from_scene_selection)
        geom_page.selection_changed_requested.connect(view.select_items_by_list)
        view.items_selection_changed.connect(
            lambda items: self._reconnect_geometry_signals(items, geom_page)
        )

        # Линейка (из GeometryPage)
        geom_page.ruler_toggled.connect(self._on_ruler_toggled)
        geom_page.ruler_reset.connect(self._on_reset_video_scale)

        # 3. Трекер
        tracker_page = self.right_panel.stack.widget(0)
        self.player.error_occurred.connect(tracker_page.show_error)
        view.tracker_region_selected.connect(lambda: tracker_page.show_error(""))
        tracker_page.model_changed.connect(lambda: tracker_page.show_error(""))
        tracker_page.model_changed.connect(thread.set_tracker_model)
        view.tracker_region_selected.connect(thread.init_tracker_manually)
        tracker_page.manual_setup_toggled.connect(self._on_manual_tracker_toggled)
        view.tracker_region_selected.connect(self._on_tracker_region_selected)

        # Передаём масштаб в статистику
        stats_page = self.right_panel.stack.widget(2)
        if hasattr(stats_page, "set_scale_factor"):
            stats_page.set_scale_factor(self.project.scale_factor)

        # Обновление данных
        self.player.thread.frame_data_updated.connect(
            self.timeline.model.update_single_frame_bbox
        )
        self.player.thread.frame_data_updated.connect(self._check_completion_status)

        self.timeline.model.set_tracking_data_map(
            self.player.thread.get_tracking_data()
        )

        # Клики по сцене для линейки
        view.scene_clicked.connect(self._on_scene_click_for_ruler)

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

    # ── Масштаб ──

    def _effective_scale_factor(self) -> float:
        """Возвращает актуальный масштаб: per-video если задан, иначе проектный."""
        if self._video_scale_factor > 0:
            return self._video_scale_factor
        return self.project.scale_factor

    def _is_scale_overridden(self) -> bool:
        """True если для этого видео задан свой масштаб, отличный от проектного."""
        return (
            self._video_scale_factor > 0
            and self._video_scale_factor != self.project.scale_factor
        )

    def _load_video_scale(self):
        """Загружает per-video масштаб из .morris/<video>.scale"""
        scale_file = self.project.path / ".morris" / f"{self.video.path.stem}.scale"
        if scale_file.exists():
            try:
                self._video_scale_factor = float(scale_file.read_text().strip())
            except (ValueError, OSError):
                self._video_scale_factor = 0.0

    def _save_video_scale(self):
        """Сохраняет per-video масштаб."""
        scale_file = self.project.path / ".morris" / f"{self.video.path.stem}.scale"
        morris_dir = self.project.path / ".morris"
        morris_dir.mkdir(parents=True, exist_ok=True)
        if self._video_scale_factor > 0:
            scale_file.write_text(str(self._video_scale_factor))
        else:
            if scale_file.exists():
                scale_file.unlink()

    def _update_ruler_ui(self):
        self._update_scale_label_only()
        if hasattr(self, "right_panel"):
            stats_page = self.right_panel.stack.widget(2)
            if hasattr(stats_page, "set_scale_factor"):
                stats_page.set_scale_factor(self._effective_scale_factor())

    # ── Header ──

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

        # Сброс разметки
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

        # Размечено
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

        # Траектория
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

    def _update_scale_label_only(self):
        """Обновляет лейбл масштаба в GeometryPage."""
        if not hasattr(self, "right_panel"):
            return
        geom_page = self.right_panel.geometry_page
        sf = self._effective_scale_factor()
        if sf > 0:
            if self._is_scale_overridden():
                geom_page.update_scale_label(
                    "⚠ Свой масштаб",
                    "#d4b765",
                    "Масштаб этого видео отличается от проектного",
                )
            else:
                geom_page.update_scale_label("✔ Масштаб задан", "#2ea043")
        else:
            geom_page.update_scale_label("Масштаб не задан", "#888")

    # ── Линейка ──
    def _on_shape_requested(self, shape_type):
        geom_page = self.right_panel.geometry_page
        if geom_page.btn_ruler.isChecked():
            geom_page.btn_ruler.setChecked(False)
        self.player.view.set_creation_mode(shape_type)

    def _on_ruler_toggled(self, checked):
        self._ruler_mode = checked
        if checked:
            self.player.view.set_creation_mode(None)
            self.player.pause_video()
            for item in self.player.view.scene.items():
                if isinstance(item, EditableGeometryItem):
                    item.set_locked(True)
            self.player.view.setCursor(Qt.CrossCursor)
            self._ruler_start = None
            self._remove_ruler_item()
        else:
            is_geom_tab = self.right_panel.stack.currentIndex() == 1
            for item in self.player.view.scene.items():
                if isinstance(item, EditableGeometryItem):
                    item.set_locked(not is_geom_tab)
            self.player.view.setCursor(Qt.ArrowCursor)
            self._ruler_start = None

    def _on_scene_click_for_ruler(self, scene_pos):
        if not self._ruler_mode:
            return
        if self._ruler_start is None:
            self._ruler_start = scene_pos
            self._remove_ruler_item()
        else:
            end = scene_pos
            self._remove_ruler_item()
            self._ruler_item = RulerLineItem(self._ruler_start, end)
            self.player.view.scene.addItem(self._ruler_item)
            pixel_len = self._ruler_item.pixel_length()
            self._ruler_start = None
            self.right_panel.geometry_page.btn_ruler.setChecked(False)
            if pixel_len > 1:
                self._show_ruler_dialog(pixel_len)

    def _show_ruler_dialog(self, pixel_length):
        dialog = RulerInputDialog(pixel_length, self)

        def on_confirmed(real_meters):
            if real_meters > 0:
                self._video_scale_factor = pixel_length / real_meters
                self._save_video_scale()
                self._update_ruler_ui()
                QTimer.singleShot(2000, self._remove_ruler_item)

        dialog.value_confirmed.connect(on_confirmed)
        dialog.exec()

    def _remove_ruler_item(self):
        if self._ruler_item and self._ruler_item.scene():
            self._ruler_item.scene().removeItem(self._ruler_item)
        self._ruler_item = None

    def _on_reset_video_scale(self):
        self._video_scale_factor = 0.0
        self._save_video_scale()
        self._remove_ruler_item()
        self._update_ruler_ui()

    # ── Логика ──

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
            self.save_data()

    @Slot()
    def _on_clear_clicked(self):
        dialog = ConfirmDialog(
            "Сброс разметки",
            "Вы уверены, что хотите удалить всю разметку трекера?\nЭто действие необратимо.",
            self,
        )
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
        items = self.right_panel.geometry_page.get_all_items()
        tracking_data = self.player.thread.tracking_data
        fps = self.player.thread.fps
        max_frame = max(tracking_data.keys()) if tracking_data else 0
        zones_snapshot = StatisticsService.prepare_geometry_snapshot(items)
        _, zones_stats_result = StatisticsService.calculate(
            tracking_data, zones_snapshot, fps, max_frame
        )
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

        cap = cv2.VideoCapture(str(self.video.path))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

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
        export_size = (
            options.get("export_width", width),
            options.get("export_height", height),
        )

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
                export_size=export_size,
                show_trajectory=options["show_trajectory"],
                show_geometry=options["show_geometry"],
                selected_geometry_names=options["selected_geometries"],
                smoothing=options["smoothing"],
                current_frame=None,
                compass=options.get("compass"),
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать: {str(e)}")

    def cleanup(self):
        if hasattr(self, "player"):
            self.player.stop_video()
            self.player.cleanup()
        if hasattr(self, "stats_thread") and self.stats_thread.isRunning():
            self.stats_thread.quit()
            self.stats_thread.wait()
        self.timeline.cleanup()
