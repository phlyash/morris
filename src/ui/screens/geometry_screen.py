import math

import cv2
from PySide6.QtCore import QPointF, Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.project import Project
from src.services.geometry_storage import GeometryStorageService
from src.ui.components.ruler_dialog import RulerInputDialog
from src.ui.components.ruler_item import RulerLineItem
from src.ui.components.sidebar_tabs import SidebarTabsWidget
from src.ui.components.video.graphics_items import EditableGeometryItem
from src.ui.components.video.video_view import VideoGraphicsView


class ProjectGeometryWidget(QWidget):
    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.storage_service = GeometryStorageService(project.path)

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

        header_layout = QHBoxLayout()
        header_label = QLabel("Базовая геометрия проекта")
        header_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        left_layout.addLayout(header_layout)

        sub_label = QLabel("Настройка зон на примере первого видео")
        sub_label.setStyleSheet("color: #aaa; font-size: 14px;")
        left_layout.addWidget(sub_label)

        self.view = VideoGraphicsView()
        left_layout.addWidget(self.view)

        main_layout.addWidget(left_col, stretch=1)

        # === ПРАВАЯ ЧАСТЬ ===
        self.sidebar = SidebarTabsWidget()
        self.sidebar.setFixedWidth(360)
        self.sidebar.set_tabs_visible(tracker=False, geometry=True, stats=False)
        main_layout.addWidget(self.sidebar)

        # === ЗАГРУЗКА ===
        self.current_video_path = None
        self._load_first_video_frame()

        # === ЛОГИКА ГЕОМЕТРИИ ===
        geom_page = self.sidebar.geometry_page
        geom_page.shape_create_requested.connect(self._on_shape_requested)
        self.view.creation_cancelled.connect(geom_page.reset_tool_selection)
        self.view.item_created.connect(geom_page.register_new_item)
        geom_page.items_deleted.connect(self.view.remove_items)
        self.view.delete_requested.connect(geom_page.delete_selected_items)
        self.view.items_selection_changed.connect(geom_page.update_from_scene_selection)
        geom_page.selection_changed_requested.connect(self.view.select_items_by_list)
        self.view.items_selection_changed.connect(
            lambda items: self._reconnect_geometry_signals(items, geom_page)
        )

        # Линейка
        geom_page.ruler_toggled.connect(self._on_ruler_toggled)
        geom_page.ruler_reset.connect(self._on_reset_calibration)

        self.view.set_interaction_enabled(True)
        self.view.scene_clicked.connect(self._on_scene_click_for_ruler)

        self.load_data()
        self._update_calibration_label()

    def _on_shape_requested(self, shape_type):
        geom_page = self.sidebar.geometry_page
        if geom_page.btn_ruler.isChecked():
            geom_page.btn_ruler.setChecked(False)
        self.view.set_creation_mode(shape_type)

    def _load_first_video_frame(self):
        if not self.project.videos:
            return
        sorted_videos = sorted(self.project.videos, key=lambda v: v.path.name)
        first_video = sorted_videos[0]
        self.current_video_path = first_video.path
        cap = cv2.VideoCapture(str(self.current_video_path))
        ret, frame = cap.read()
        cap.release()
        if ret:
            self.view.update_image(frame)

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

    # ── Линейка ──

    def _on_ruler_toggled(self, checked):
        self._ruler_mode = checked
        if checked:
            self.view.set_creation_mode(None)
            for item in self.view.scene.items():
                if isinstance(item, EditableGeometryItem):
                    item.set_locked(True)
            self.view.setCursor(Qt.CrossCursor)
            self._ruler_start = None
            self._remove_ruler_item()
        else:
            for item in self.view.scene.items():
                if isinstance(item, EditableGeometryItem):
                    item.set_locked(False)
            self.view.setCursor(Qt.ArrowCursor)
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
            self.view.scene.addItem(self._ruler_item)
            pixel_len = self._ruler_item.pixel_length()
            self._ruler_start = None
            self.sidebar.geometry_page.btn_ruler.setChecked(False)
            if pixel_len > 1:
                self._show_ruler_dialog(pixel_len)

    def _show_ruler_dialog(self, pixel_length):
        dialog = RulerInputDialog(pixel_length, self)

        def on_confirmed(real_meters):
            if real_meters > 0:
                self.project.scale_factor = pixel_length / real_meters
                self.project.save_config()
                self._update_calibration_label()
                from PySide6.QtCore import QTimer

                QTimer.singleShot(2000, self._remove_ruler_item)

        dialog.value_confirmed.connect(on_confirmed)
        dialog.exec()

    def _remove_ruler_item(self):
        if self._ruler_item and self._ruler_item.scene():
            self._ruler_item.scene().removeItem(self._ruler_item)
        self._ruler_item = None

    def _on_reset_calibration(self):
        self.project.scale_factor = 0.0
        self.project.save_config()
        self._remove_ruler_item()
        self._update_calibration_label()

    def _update_calibration_label(self):
        geom_page = self.sidebar.geometry_page
        if self.project.is_calibrated:
            geom_page.update_scale_label("✔ Масштаб задан", "#2ea043")
        else:
            geom_page.update_scale_label("Масштаб не задан", "#888")

    def save_data(self):
        items = self.sidebar.geometry_page.get_all_items()
        self.storage_service.propagate_base_geometry(items)

    def load_data(self):
        items = self.storage_service.load_project_settings()
        scene = self.view.scene
        geom_page = self.sidebar.geometry_page
        for item in scene.items():
            if isinstance(item, EditableGeometryItem):
                scene.removeItem(item)
        geom_page.list_widget.clear()
        for item in items:
            scene.addItem(item)
            geom_page.add_existing_item(item)
            item.set_locked(False)

    def hideEvent(self, event):
        self.save_data()
        super().hideEvent(event)
