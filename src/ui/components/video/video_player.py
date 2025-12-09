import math

import cv2
import numpy as np
from PySide6.QtCore import Qt, Slot, QPoint, Signal, QSize
from PySide6.QtGui import QImage, QPixmap, QResizeEvent, QPen, QPainter, QIcon, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QSizePolicy, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                               QGraphicsRectItem)

from src.config import get_resource_path
from src.core import Video
from src.ui.components.video.graphics_items import EditableGeometryItem
from src.ui.components.video.video_thread import VideoThread
from src.ui.components.video.video_view import VideoGraphicsView


def svg_to_pixmap(svg_path: str, width: int, height: int) -> QPixmap:
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def recolor_pixmap(pixmap: QPixmap, color_hex: str) -> QPixmap:
    if pixmap.isNull(): return pixmap
    target = QPixmap(pixmap.size())
    target.fill(Qt.transparent)
    painter = QPainter(target)
    if painter.isActive():
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(target.rect(), QColor(color_hex))
        painter.end()
    return target


def create_icon(path: str, color: str = "#FFFFFF", size: int = 32) -> QIcon:
    """Создает QIcon из SVG заданного цвета"""
    try:
        full_path = str(get_resource_path(path))
        pix = svg_to_pixmap(full_path, size, size)
        pix = recolor_pixmap(pix, color)
        return QIcon(pix)
    except Exception as e:
        print(f"Error loading icon {path}: {e}")
        return QIcon()


class VideoScreen(QGraphicsView):
    tracker_region_selected = Signal(tuple)
    item_created = Signal(object)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Вместо QLabel.setPixmap мы используем элемент сцены
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        # Зеленый квадрат трекера (программно управляется)
        self.tracker_rect_item = QGraphicsRectItem()
        self.tracker_rect_item.setPen(QPen(Qt.green, 3))
        self.tracker_rect_item.setVisible(False)
        self.scene.addItem(self.tracker_rect_item)

        # Настройки View (убираем скроллы, ставим черный фон)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background: #000; border: none;")
        self.setRenderHint(QPainter.Antialiasing)

        # Состояния
        self.current_shape_type = None  # "square", "donut" и т.д.
        self.is_tracker_setup_mode = False  # Если True - рисуем квадрат для трекера
        self.temp_item = None
        self.start_pos = None
        self.is_paused = True

    def set_shape_type(self, shape_type: str):
        """Слот для смены типа фигуры"""
        self.current_shape_type = shape_type
        # Сбрасываем текущее рисование при смене инструмента
        self.poly_points = []
        self.drawing = False
        self.start_point = None

    def update_image(self, cv_img):
        """Метод совместимый со старым кодом. Принимает кадр от Thread."""
        if cv_img is None: return

        # Конвертация
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        # Обновляем картинку на сцене
        self.pixmap_item.setPixmap(pix)
        self.scene.setSceneRect(0, 0, w, h)
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def update_tracker_box(self, success, bbox):
        """Обновляет зеленый квадрат (вызывается из Thread)"""
        if success and bbox:
            self.tracker_rect_item.setRect(*bbox)
            self.tracker_rect_item.setVisible(True)
        else:
            self.tracker_rect_item.setVisible(False)

    def set_shape_type(self, shape_type: str):
        """Совместимость с вашим кодом. 'tracker' - спец режим."""
        if shape_type == "tracker":
            self.is_tracker_setup_mode = True
            self.current_shape_type = "square"
            self.setCursor(Qt.CrossCursor)
        else:
            self.is_tracker_setup_mode = False
            self.current_shape_type = shape_type
            self.setCursor(Qt.CrossCursor if shape_type else Qt.ArrowCursor)

    def display_frame(self, cv_img):
        if cv_img is None: return
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Используем KeepAspectRatio, чтобы координаты мыши легче считались,
        # или Ignored, если у вас map_qt_to_opencv настроен правильно.
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            self.width(), self.height(), Qt.IgnoreAspectRatio
        )
        self.setPixmap(scaled_pixmap)

    def map_qt_to_opencv(self, qt_point):
        # (Ваш код маппинга координат, оставляю без изменений)
        if self.current_cv_image is None: return None
        pix = self.pixmap()
        if not pix: return None

        # Если используется IgnoreAspectRatio, то просто:
        vid_h, vid_w, _ = self.current_cv_image.shape
        lbl_w, lbl_h = self.width(), self.height()

        x = int(qt_point.x() * (vid_w / lbl_w))
        y = int(qt_point.y() * (vid_h / lbl_h))

        # Clamp
        x = max(0, min(x, vid_w - 1))
        y = max(0, min(y, vid_h - 1))
        return (x, y)

    # --- DRAWING EVENTS ---

    def mousePressEvent(self, event):
        # Если мы просто двигаем существующие фигуры - используем стандартную логику View
        if not self.current_shape_type and not self.is_tracker_setup_mode:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.LeftButton:
            # Начало рисования
            pos = self.mapToScene(event.pos())
            self.start_pos = pos

            # Создаем ваш класс EditableGeometryItem
            self.temp_item = EditableGeometryItem(pos.x(), pos.y(), 0, 0, self.current_shape_type)

            if self.is_tracker_setup_mode:
                # Для трекера делаем его визуально другим (желтый пунктир)
                self.temp_item.pen = QPen(Qt.yellow, 2, Qt.DashLine)

            self.scene.addItem(self.temp_item)

    def mouseMoveEvent(self, event):
        if self.temp_item:
            # Растягивание фигуры
            pos = self.mapToScene(event.pos())
            w = pos.x() - self.start_pos.x()
            h = pos.y() - self.start_pos.y()

            # Нормализация координат (чтобы w, h были > 0)
            x, y = self.start_pos.x(), self.start_pos.y()
            if w < 0: x += w; w = -w
            if h < 0: y += h; h = -h

            self.temp_item.set_geometry_data(x, y, w, h)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.temp_item:
            # Завершение рисования
            rect = self.temp_item.rect
            final_bbox = (int(self.temp_item.x()), int(self.temp_item.y()),
                          int(rect.width()), int(rect.height()))

            if self.is_tracker_setup_mode:
                # Это был квадрат для трекера
                self.tracker_region_selected.emit(final_bbox)
                self.scene.removeItem(self.temp_item)  # Удаляем ручной квадрат, появится зеленый авто
                self.set_shape_type(None)  # Сбрасываем режим
            else:
                # Это была геометрия (бублик)
                self.temp_item.setSelected(True)
                self.item_created.emit(self.temp_item)

            self.temp_item = None

        super().mouseReleaseEvent(event)
    # --- VISUALIZATION ---

    def _draw_preview(self, cursor_pos):
        """Рисуем на копии изображения (не сохраняя)"""
        temp_img = self.current_cv_image.copy()

        color = (0, 255, 255)  # Желтый BGR
        thickness = 2

        if self.current_shape_type == "square":
            if self.start_point:
                cv2.rectangle(temp_img, self.start_point, self.end_point, color, thickness)

        elif self.current_shape_type in ["circle", "donut"]:
            if self.start_point:
                # Радиус = расстояние между нажатием и текущей мышкой
                dx = self.end_point[0] - self.start_point[0]
                dy = self.end_point[1] - self.start_point[1]
                radius = int(math.hypot(dx, dy))

                cv2.circle(temp_img, self.start_point, radius, color, thickness)

                if self.current_shape_type == "donut":
                    # Рисуем внутренний круг (например, 50% радиуса для превью)
                    cv2.circle(temp_img, self.start_point, int(radius * 0.5), color, thickness)

        elif self.current_shape_type == "poly":
            # Рисуем уже поставленные линии
            if len(self.poly_points) > 0:
                pts = np.array(self.poly_points, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(temp_img, [pts], False, color, thickness)

                # Рисуем линию к курсору ("резинка")
                cv2.line(temp_img, self.poly_points[-1], cursor_pos, (0, 255, 0), 1)

        self.display_frame(temp_img)

    def _finalize_shape(self):
        """Рисуем на оригинале (Сохраняем результат)"""
        # В реальном приложении здесь нужно не рисовать на current_cv_image,
        # а сохранять координаты в структуру данных (Statistics/Geometry Model).
        # Но для визуального примера рисуем прямо в буфер кадра.

        img = self.current_cv_image
        color = (0, 0, 255)  # Красный - финал
        thickness = 3

        if self.current_shape_type == "square":
            cv2.rectangle(img, self.start_point, self.end_point, color, thickness)

        elif self.current_shape_type in ["circle", "donut"]:
            dx = self.end_point[0] - self.start_point[0]
            dy = self.end_point[1] - self.start_point[1]
            radius = int(math.hypot(dx, dy))

            cv2.circle(img, self.start_point, radius, color, thickness)
            if self.current_shape_type == "donut":
                cv2.circle(img, self.start_point, int(radius * 0.5), color, thickness)

        elif self.current_shape_type == "poly":
            pts = np.array(self.poly_points, np.int32)
            pts = pts.reshape((-1, 1, 2))
            # True = замкнуть полигон
            cv2.polylines(img, [pts], True, color, thickness)

        self.display_frame(img)


class VideoPlayerWidget(QWidget):
    position_changed = Signal(int)
    error_occurred = Signal(str)

    def __init__(self, video: Video, parent=None):
        super().__init__(parent)
        self.video = video

        # Предзагрузка иконок (чтобы не создавать каждый раз)
        # Цвета: Белый для обычного состояния, Черный для активного Turbo (на желтом фоне)
        self.icon_play = create_icon("play.svg")
        self.icon_pause = create_icon("pause.svg")
        self.icon_prev = create_icon("backward.svg")
        self.icon_next = create_icon("forward.svg")

        self.icon_turbo_white = create_icon("fastforward.svg", "#FFFFFF")
        self.icon_turbo_black = create_icon("fastforward.svg", "#000000")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.view = VideoGraphicsView()
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.view)

        self._init_controls()

        self.thread = VideoThread(self.video)
        self.thread.change_pixmap_signal.connect(self.view.update_image)
        self.thread.tracker_update_signal.connect(self.view.update_tracker_box)
        self.thread.frame_changed_signal.connect(self.position_changed.emit)
        self.thread.tracker_loading_signal.connect(self.on_tracker_loading)
        self.thread.tracking_error_signal.connect(self.on_tracking_error)

        self.thread.is_paused = True
        self.thread.start()

        self._apply_styles()
        self.seek_to_frame(0)

    def _init_controls(self):
        self.controls_container = QWidget()
        self.controls_container.setFixedHeight(60)
        self.controls_container.setObjectName("ControlsContainer")

        cont_layout = QHBoxLayout(self.controls_container)
        cont_layout.setContentsMargins(0, 0, 0, 0)
        cont_layout.addStretch()

        # 2. PREV
        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(self.icon_prev)
        self.btn_prev.setToolTip("Кадр назад")

        # 3. PLAY / PAUSE
        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.icon_play)
        self.btn_play.setToolTip("Старт / Пауза")

        # 4. NEXT
        self.btn_next = QPushButton()
        self.btn_next.setIcon(self.icon_next)
        self.btn_next.setToolTip("Кадр вперед")

        # Добавляем основные кнопки
        for btn in [self.btn_prev, self.btn_play, self.btn_next]:
            btn.setFixedSize(40, 40)
            btn.setIconSize(QSize(20, 20))  # Размер иконки внутри кнопки
            btn.setCursor(Qt.PointingHandCursor)
            cont_layout.addWidget(btn)

        cont_layout.addStretch()

        # 5. TURBO
        self.btn_turbo = QPushButton()
        self.btn_turbo.setIcon(self.icon_turbo_white)
        self.btn_turbo.setCheckable(True)
        self.btn_turbo.setToolTip("Максимальная скорость")
        self.btn_turbo.setFixedSize(40, 40)
        self.btn_turbo.setIconSize(QSize(24, 24))
        self.btn_turbo.setCursor(Qt.PointingHandCursor)
        self.btn_turbo.toggled.connect(self.toggle_turbo)

        # Стиль Turbo (меняем цвет фона и иконку при выборе)
        self.btn_turbo.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                border: 1px solid #666; 
                border-radius: 4px; 
                padding: 8px;
            }
            QPushButton:hover { 
                background-color: rgba(255,255,255,0.1); 
            }
            QPushButton:checked { 
                background-color: #d4b765; 
                border: 1px solid #d4b765; 
            }
        """)

        cont_layout.addWidget(self.btn_turbo)
        cont_layout.setContentsMargins(0, 0, 20, 0)
        self.layout.addWidget(self.controls_container)

        # Подключение
        self.btn_prev.clicked.connect(self.step_backward)
        self.btn_play.clicked.connect(self.toggle_play_pause)
        self.btn_next.clicked.connect(self.step_forward)

    @Slot(str)
    def on_tracking_error(self, message):
        self.btn_play.setIcon(self.icon_play)
        self.error_occurred.emit(message)

    def seek_to_frame(self, frame_index):
        self.thread.seek(frame_index)
        if self.thread.is_paused:
            self.btn_play.setIcon(self.icon_play)

    @Slot(bool)
    def toggle_turbo(self, checked):
        self.thread.set_turbo_mode(checked)
        if checked:
            self.btn_turbo.setIcon(self.icon_turbo_black)
        else:
            self.btn_turbo.setIcon(self.icon_turbo_white)

    @Slot()
    def step_backward(self):
        if not self.thread.is_paused: self.pause_video()
        self.thread.prev_frame()

    @Slot()
    def step_forward(self):
        if not self.thread.is_paused: self.pause_video()
        self.thread.next_frame()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget { font-family: "Segoe UI"; }
            QWidget#ControlsContainer {
                background-color: #2d2d30;
                border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;
            }
            /* Стили для обычных кнопок управления */
            QPushButton {
                background-color: transparent; 
                border: 1px solid #666;
                border-radius: 4px; 
            }
            QPushButton:hover { 
                background-color: rgba(255, 255, 255, 0.1); 
                border-color: #888;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2); 
            }
        """)

    @Slot(bool)
    def on_tracker_loading(self, is_loading):
        self.btn_play.setEnabled(not is_loading)
        if is_loading:
            # Можно поставить иконку часов, если есть
            self.btn_play.setIcon(QIcon()) # Пустая или заглушка
            if not self.thread.is_paused:
                self.pause_video()
        else:
            # Возвращаем Play (так как мы на паузе)
            self.btn_play.setIcon(self.icon_play)

    @Slot()
    def toggle_play_pause(self):
        self.error_occurred.emit("")  # Сброс ошибок

        if self.thread.is_model_loading:
            return

        if self.thread.is_paused:
            tracker = self.thread.tracker

            if tracker is not None:
                model_type = tracker.model_type
                is_active = self.thread.is_tracking_active

                # Если трекер не активен, попробуем восстановить его из bbox на экране
                if not is_active:
                    restored = self.thread.try_restore_from_history()
                    if restored:
                        is_active = True  # Теперь он активен

                # --- ПРОВЕРКИ ---

                # 1. CSRT
                if "csrt" in model_type and not is_active:
                    self.error_occurred.emit("CSRT требует выделения объекта (или загруженных данных).")
                    return

                # 2. YOLO (Автозапуск)
                if "yolo" in model_type and not is_active:
                    found = self.thread.try_yolo_autostart()
                    if not found:
                        self.error_occurred.emit("YOLO не нашел объектов на этом кадре.")
                        return

        self.thread.is_paused = not self.thread.is_paused
        if not self.thread.is_paused:
            self.btn_play.setIcon(self.icon_pause)
        else:
            self.btn_play.setIcon(self.icon_play)

    @Slot()
    def pause_video(self):
        self.thread.is_paused = True
        self.btn_play.setIcon(self.icon_play)

    @Slot()
    def stop_video(self):
        self.thread.is_paused = True
        self.thread.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.btn_play.setIcon(self.icon_play)
        self.thread.next_frame()

    def cleanup(self):
        try:
            if hasattr(self, 'thread') and self.thread and self.thread.isRunning():
                self.thread.stop()
                self.thread.deleteLater()
        except: pass
