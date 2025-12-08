import cv2
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush

from src.ui.components.video.graphics_items import EditableGeometryItem


class VideoGraphicsView(QGraphicsView):
    # --- СИГНАЛЫ ---
    tracker_region_selected = Signal(tuple)
    item_created = Signal(object)
    items_selection_changed = Signal(list)
    delete_requested = Signal()
    creation_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Слой видео
        self.pixmap_item = QGraphicsPixmapItem()
        self.pixmap_item.setZValue(-100)
        self.scene.addItem(self.pixmap_item)

        # Зеленый квадрат (Трекер)
        self.tracker_rect_item = QGraphicsRectItem()
        self.tracker_rect_item.setPen(QPen(Qt.green, 3))
        self.tracker_rect_item.setVisible(False)
        self.scene.addItem(self.tracker_rect_item)

        # Настройки
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background: #000; border: none;")

        # ВАЖНО: Якорь при изменении размера - центр
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)

        # Состояния
        self.current_shape_type = None
        self.is_tracker_setup_mode = False
        self.temp_item = None
        self.start_pos = None
        self.is_interaction_enabled = True

        self.scene.selectionChanged.connect(self._on_selection_changed)

    def update_image(self, cv_img):
        """Обновление изображения из потока"""
        if cv_img is None: return

        # Конвертация BGR -> RGB
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Обновляем размер сцены под размер видео
        self.scene.setSceneRect(0, 0, w, h)
        self.pixmap_item.setPixmap(QPixmap.fromImage(qimg))

        # ВАЖНО: Подгоняем видео под текущий размер окна
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    # --- ИСПРАВЛЕНИЕ: ОБРАБОТКА ИЗМЕНЕНИЯ РАЗМЕРА ОКНА ---
    def resizeEvent(self, event):
        """
        Вызывается, когда виджет меняет размер (при открытии или растягивании окна).
        Пересчитываем масштаб видео.
        """
        super().resizeEvent(event)
        if self.pixmap_item.pixmap() and not self.pixmap_item.pixmap().isNull():
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def update_tracker_box(self, success, bbox):
        if success and bbox:
            self.tracker_rect_item.setRect(*bbox)
            self.tracker_rect_item.setVisible(True)
        else:
            self.tracker_rect_item.setVisible(False)

    @Slot(str)
    def set_creation_mode(self, shape_type: str):
        self.is_tracker_setup_mode = False
        self.current_shape_type = shape_type
        self.scene.clearSelection()
        self.setCursor(Qt.CrossCursor)

    def set_tracker_setup_mode(self, active: bool):
        self.is_tracker_setup_mode = active
        if active:
            self.current_shape_type = "square"
            self.scene.clearSelection()
            self.setCursor(Qt.CrossCursor)
        else:
            self._reset_mode()

    def mousePressEvent(self, event):
        if not self.is_interaction_enabled and not self.is_tracker_setup_mode:
            super().mousePressEvent(event)
            return

        if self.current_shape_type or self.is_tracker_setup_mode:
            if event.button() == Qt.LeftButton:
                pos = self.mapToScene(event.pos())
                self.start_pos = pos

                if self.is_tracker_setup_mode:
                    # Простой квадрат для трекера
                    self.temp_item = QGraphicsRectItem()
                    self.temp_item.setPen(QPen(QColor("#00FF00"), 3, Qt.SolidLine))
                    self.temp_item.setBrush(Qt.NoBrush)
                    self.temp_item.setRect(pos.x(), pos.y(), 0, 0)
                else:
                    # Геометрия
                    self.temp_item = EditableGeometryItem(pos.x(), pos.y(), 0, 0, self.current_shape_type)

                self.scene.addItem(self.temp_item)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.temp_item:
            pos = self.mapToScene(event.pos())
            w = pos.x() - self.start_pos.x()
            h = pos.y() - self.start_pos.y()

            x, y = self.start_pos.x(), self.start_pos.y()
            if w < 0: x += w; w = -w
            if h < 0: y += h; h = -h

            if self.is_tracker_setup_mode:
                self.temp_item.setRect(x, y, w, h)
            else:
                self.temp_item.set_geometry_data(x, y, w, h)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.temp_item:
            if self.is_tracker_setup_mode:
                rect = self.temp_item.rect()
                final_bbox = (int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()))
            else:
                rect = self.temp_item.rect
                final_bbox = (int(self.temp_item.x()), int(self.temp_item.y()),
                              int(rect.width()), int(rect.height()))

            if rect.width() > 5 and rect.height() > 5:
                if self.is_tracker_setup_mode:
                    self.tracker_region_selected.emit(final_bbox)
                    self.scene.removeItem(self.temp_item)
                    self._reset_mode()
                else:
                    self.temp_item.setSelected(True)
                    self.item_created.emit(self.temp_item)
                    self._reset_mode()
            else:
                self.scene.removeItem(self.temp_item)

            self.temp_item = None

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.temp_item:
                self.scene.removeItem(self.temp_item)
                self.temp_item = None
            self._reset_mode()
            self.creation_cancelled.emit()
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            if self.is_interaction_enabled:
                self.delete_requested.emit()
        else:
            super().keyPressEvent(event)

    def _reset_mode(self):
        self.current_shape_type = None
        self.is_tracker_setup_mode = False
        self.setCursor(Qt.ArrowCursor)

    def _on_selection_changed(self):
        selected = self.scene.selectedItems()
        geom_items = [i for i in selected if isinstance(i, EditableGeometryItem)]
        self.items_selection_changed.emit(geom_items)

    def select_items_by_list(self, items):
        self.scene.blockSignals(True)
        self.scene.clearSelection()
        for i in items: i.setSelected(True)
        self.scene.blockSignals(False)

    def remove_items(self, items):
        for i in items:
            if i in self.scene.items(): self.scene.removeItem(i)

    def set_interaction_enabled(self, enabled: bool):
        self.is_interaction_enabled = enabled

        for item in self.scene.items():
            if isinstance(item, EditableGeometryItem):
                item.set_locked(not enabled)

        if not enabled:
            self.scene.clearSelection()
            self._reset_mode()
            self.setCursor(Qt.ArrowCursor)