import collections

import cv2
from PySide6.QtCore import (
    QAbstractListModel,
    QItemSelectionModel,
    QModelIndex,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QListView,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
)

from src.core import Video

MAX_PENDING_REQUESTS = 30
PREFETCH_LOOK_AHEAD = 10
PREFETCH_LOOK_BEHIND = 5


class FrameRequestThread(QThread):
    frame_ready = Signal(int, QPixmap)

    def __init__(self, video_path, width, height, total_frames):
        super().__init__()
        self.video_path = video_path
        self.thumb_w = width
        self.thumb_h = height
        self.total_frames = total_frames
        self._run_flag = True

        self.requests = collections.deque()
        self.pending_indices = set()
        self._lock_requests = False

        self.cap = cv2.VideoCapture(self.video_path)

    def request_frame(self, index):
        if self._lock_requests:
            return
        if index in self._cache:
            return
        if index in self.pending_indices:
            return
        if (
            0 <= index < self.total_frames
            and len(self.pending_indices) < MAX_PENDING_REQUESTS
        ):
            self.pending_indices.add(index)
            self.requests.append(index)

    def request_frames_bulk(self, indices):
        if self._lock_requests:
            return
        for idx in indices:
            if idx in self._cache or idx in self.pending_indices:
                continue
            if (
                0 <= idx < self.total_frames
                and len(self.pending_indices) < MAX_PENDING_REQUESTS
            ):
                self.pending_indices.add(idx)
                self.requests.append(idx)
            if len(self.pending_indices) >= MAX_PENDING_REQUESTS:
                break

    def set_cache(self, cache_ref):
        self._cache = cache_ref

    def clear_pending_except(self, keep_indices):
        keep_set = set(keep_indices)
        self.pending_indices = self.pending_indices & keep_set
        new_requests = collections.deque()
        for idx in self.requests:
            if idx in keep_set:
                new_requests.append(idx)
        self.requests = new_requests

    def lock_requests(self):
        self._lock_requests = True

    def unlock_requests(self):
        self._lock_requests = False

    def run(self):
        while self._run_flag:
            if not self.requests:
                self.msleep(20)
                continue

            idx = self.requests.popleft()

            if idx in self._cache:
                if idx in self.pending_indices:
                    self.pending_indices.remove(idx)
                continue

            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = self.cap.read()

            if ret:
                frame_resized = cv2.resize(
                    frame, (self.thumb_w, self.thumb_h), interpolation=cv2.INTER_NEAREST
                )
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                h, w, ch = frame_rgb.shape
                qt_image = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image).copy()

                self.frame_ready.emit(idx, pixmap)

            if idx in self.pending_indices:
                self.pending_indices.remove(idx)

    def stop(self):
        self._run_flag = False
        self.wait()
        self.cap.release()


# --- 2. МОДЕЛЬ ---
class CachedFramesModel(QAbstractListModel):
    def __init__(self, total_frames, placeholder, loader, orig_w, orig_h, parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.placeholder = placeholder
        self.loader = loader

        self.original_video_w = orig_w
        self.original_video_h = orig_h

        self._cache = {}

        self.loader.set_cache(self._cache)

        self._tracking_data = {}

        self.CACHE_SIZE_LIMIT = 150
        self.center_index = 0

    def set_tracking_data_map(self, data_map):
        self._tracking_data = data_map
        self.layoutChanged.emit()

    @Slot(int, tuple)
    def update_single_frame_bbox(self, frame_idx, bbox):
        self._tracking_data[frame_idx] = bbox
        idx_obj = self.index(frame_idx)
        if idx_obj.isValid():
            self.dataChanged.emit(idx_obj, idx_obj, [Qt.UserRole])

    def prefetch(
        self,
        center_index,
        look_ahead=PREFETCH_LOOK_AHEAD,
        look_behind=PREFETCH_LOOK_BEHIND,
    ):
        indices_to_load = []

        start_behind = max(0, center_index - look_behind)
        end_ahead = min(center_index + look_ahead, self.total_frames)

        for i in range(start_behind, end_ahead):
            if i not in self._cache and i not in self.loader.pending_indices:
                indices_to_load.append(i)

        if indices_to_load:
            keep_range = set(range(start_behind, end_ahead))
            self.loader.clear_pending_except(keep_range)
            self.loader.request_frames_bulk(indices_to_load)

    def prefetch_from_scroll(self, center_index):
        self.prefetch(center_index, PREFETCH_LOOK_AHEAD, PREFETCH_LOOK_BEHIND)

    def rowCount(self, parent=QModelIndex()):
        return self.total_frames

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        idx = index.row()

        if role == Qt.DecorationRole:
            if idx in self._cache:
                return self._cache[idx]
            self.loader.request_frame(idx)
            return self.placeholder

        if role == Qt.UserRole:
            return self._tracking_data.get(idx, None)

        return None

    @Slot(int, QPixmap)
    def on_frame_loaded(self, index, pixmap):
        self._cache[index] = pixmap
        idx_obj = self.index(index)
        self.dataChanged.emit(idx_obj, idx_obj, [Qt.DecorationRole])
        self.cleanup_cache()

    def update_scroll_center(self, center_idx):
        self.center_index = center_idx

    def cleanup_cache(self):
        if len(self._cache) <= self.CACHE_SIZE_LIMIT:
            return
        keys_sorted = sorted(
            self._cache.keys(), key=lambda k: abs(k - self.center_index), reverse=True
        )
        to_remove_count = len(self._cache) - self.CACHE_SIZE_LIMIT
        for i in range(to_remove_count):
            del self._cache[keys_sorted[i]]


# --- 3. ДЕЛЕГАТ (ОТРИСОВКА) ---
class FrameDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()

        # 1. Рисуем картинку
        pixmap = index.data(Qt.DecorationRole)
        if pixmap:
            painter.drawPixmap(option.rect, pixmap)

        # 2. Рисуем BBOX (если есть)
        bbox = index.data(Qt.UserRole)
        if bbox:
            # Получаем доступ к модели, чтобы узнать оригинальные размеры
            model = index.model()
            if model and model.original_video_w > 0:
                # Коэффициенты масштабирования
                # option.rect.width() - ширина ячейки (160px)
                # model.original_video_w - ширина видео (например 1920px)
                scale_x = option.rect.width() / model.original_video_w
                scale_y = option.rect.height() / model.original_video_h

                x, y, w, h = bbox

                # Считаем прямоугольник на миниатюре
                scaled_rect = QRectF(
                    option.rect.x() + x * scale_x,
                    option.rect.y() + y * scale_y,
                    w * scale_x,
                    h * scale_y,
                )

                # Рисуем ярко-зеленую рамку
                pen_box = QPen(QColor("#00FF00"))
                pen_box.setWidth(2)
                painter.setPen(pen_box)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(scaled_rect)

        # 3. Рамка выделения (Текущий кадр)
        if option.state & QStyle.State_Selected:
            pen = QPen(QColor("#FFDD78"))
            pen.setWidth(3)
            pen.setJoinStyle(Qt.MiterJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            border_rect = option.rect.adjusted(1, 1, -1, -1)
            painter.drawRect(border_rect)

        painter.restore()


# --- 4. ВИДЖЕТ ТАЙМЛАЙНА ---
DEBOUNCE_DELAY_MS = 50


class VideoTimelineWidget(QFrame):
    frame_clicked = Signal(int)

    def __init__(self, video: Video):
        super().__init__()
        self.setFixedHeight(140)
        self.setStyleSheet("background-color: #34353C; border-radius: 12px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.thumb_w, self.thumb_h = 160, 90

        cap = cv2.VideoCapture(video.path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        orig_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        cap.release()

        self.placeholder = QPixmap(self.thumb_w, self.thumb_h)
        self.placeholder.fill(QColor("#333333"))
        painter = QPainter(self.placeholder)
        painter.setPen(QColor("#666"))
        painter.drawText(self.placeholder.rect(), Qt.AlignCenter, "Loading...")
        painter.end()

        self.loader = FrameRequestThread(
            video.path, self.thumb_w, self.thumb_h, total_frames
        )

        self.model = CachedFramesModel(
            total_frames, self.placeholder, self.loader, orig_w, orig_h
        )

        self.loader.frame_ready.connect(self.model.on_frame_loaded)
        self.loader.start()

        self.list_view = QListView()
        self.list_view.setFlow(QListView.LeftToRight)
        self.list_view.setWrapping(False)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_view.setIconSize(QSize(self.thumb_w, self.thumb_h))
        self.list_view.setUniformItemSizes(True)
        self.list_view.setSpacing(0)

        self.delegate = FrameDelegate()
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setModel(self.model)

        self.list_view.setStyleSheet("""
            QListView { background: transparent; border: none; outline: 0; }
            QListView::item { border: none; padding: 0px; margin: 0px; }
        """)

        layout.addWidget(self.list_view)

        self.scroll_bar = self.list_view.horizontalScrollBar()
        self.scroll_bar.valueChanged.connect(self.on_scroll)
        self.list_view.clicked.connect(self._on_item_clicked)

        self._scroll_timer = QTimer()
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self._do_scroll_prefetch)

        self._current_frame_timer = QTimer()
        self._current_frame_timer.setSingleShot(True)
        self._current_frame_timer.timeout.connect(self._do_current_frame_prefetch)
        self._pending_frame_index = 0

    def _on_item_clicked(self, index):
        frame_idx = index.row()
        self.frame_clicked.emit(frame_idx)

    @Slot(int)
    def set_current_frame(self, frame_index):
        self._pending_frame_index = frame_index
        if not self._current_frame_timer.isActive():
            self._current_frame_timer.start(DEBOUNCE_DELAY_MS)

    def _do_current_frame_prefetch(self):
        frame_index = self._pending_frame_index
        idx = self.model.index(frame_index, 0)
        if idx.isValid():
            flag = QItemSelectionModel.SelectionFlag.ClearAndSelect
            self.list_view.selectionModel().select(idx, flag)
            self.list_view.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)
            self.model.prefetch(frame_index, PREFETCH_LOOK_AHEAD, PREFETCH_LOOK_BEHIND)

    def on_scroll(self, value):
        item_width = self.thumb_w
        center_pixel = value + (self.list_view.width() / 2)
        center_index = int(center_pixel / item_width)
        self.model.update_scroll_center(center_index)

        self._scroll_timer.stop()
        self._scroll_timer.start(DEBOUNCE_DELAY_MS)
        self._pending_scroll_index = center_index

    def _do_scroll_prefetch(self):
        self.model.prefetch_from_scroll(self._pending_scroll_index)

    def cleanup(self):
        try:
            if self.loader.isRunning():
                self.loader.stop()
                self.loader.deleteLater()
        except:
            pass
