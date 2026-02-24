import cv2
from PySide6.QtCore import (
    QAbstractListModel,
    QItemSelectionModel,
    QModelIndex,
    QRectF,
    QSize,
    Qt,
    QThread,
    Signal,
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


class FullVideoLoaderThread(QThread):
    frame_ready = Signal(int, QPixmap)
    loading_finished = Signal()

    def __init__(self, video_path, width, height, total_frames):
        super().__init__()
        self.video_path = video_path
        self.thumb_w = width
        self.thumb_h = height
        self.total_frames = total_frames
        self._run_flag = True

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        
        idx = 0
        while self._run_flag:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_resized = cv2.resize(
                frame, (self.thumb_w, self.thumb_h), interpolation=cv2.INTER_NEAREST
            )
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            qt_image = QImage(frame_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image).copy()
            
            self.frame_ready.emit(idx, pixmap)
            idx += 1

        cap.release()
        self.loading_finished.emit()

    def stop(self):
        self._run_flag = False
        self.wait()


class FullVideoFramesModel(QAbstractListModel):
    def __init__(self, total_frames, orig_w, orig_h, placeholder, parent=None):
        super().__init__(parent)
        self.total_frames = total_frames
        self.original_video_w = orig_w
        self.original_video_h = orig_h
        self._frames = [None] * total_frames
        self.placeholder = placeholder
        self._tracking_data = {}

    def set_tracking_data_map(self, data_map):
        self._tracking_data = data_map
        self.layoutChanged.emit()

    def update_single_frame_bbox(self, frame_idx, bbox):
        self._tracking_data[frame_idx] = bbox
        idx_obj = self.index(frame_idx)
        if idx_obj.isValid():
            self.dataChanged.emit(idx_obj, idx_obj, [Qt.UserRole])

    def set_frame(self, index, pixmap):
        if 0 <= index < self.total_frames:
            self._frames[index] = pixmap
            idx_obj = self.index(index)
            if idx_obj.isValid():
                self.dataChanged.emit(idx_obj, idx_obj, [Qt.ItemDataRole.DecorationRole])

    def rowCount(self, parent=None):
        return self.total_frames

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        idx = index.row()

        if role == Qt.DecorationRole:
            if 0 <= idx < self.total_frames:
                return self._frames[idx] if self._frames[idx] is not None else self.placeholder

        if role == Qt.UserRole:
            return self._tracking_data.get(idx, None)

        return None


class FrameDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()

        pixmap = index.data(Qt.ItemDataRole.DecorationRole)
        if pixmap:
            painter.drawPixmap(option.rect, pixmap)

        bbox = index.data(Qt.ItemDataRole.UserRole)
        if bbox:
            model = index.model()
            if model and model.original_video_w > 0:
                scale_x = option.rect.width() / model.original_video_w
                scale_y = option.rect.height() / model.original_video_h

                x, y, w, h = bbox

                scaled_rect = QRectF(
                    option.rect.x() + x * scale_x,
                    option.rect.y() + y * scale_y,
                    w * scale_x,
                    h * scale_y,
                )

                pen_box = QPen(QColor("#00FF00"))
                pen_box.setWidth(2)
                painter.setPen(pen_box)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(scaled_rect)

        if option.state & QStyle.StateFlag.State_Selected:
            pen = QPen(QColor("#FFDD78"))
            pen.setWidth(3)
            pen.setJoinStyle(Qt.JoinStyle.MiterJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            border_rect = option.rect.adjusted(1, 1, -1, -1)
            painter.drawRect(border_rect)

        painter.restore()


class VideoTimelineWidget(QFrame):
    frame_clicked = Signal(int)

    def __init__(self, video: Video):
        super().__init__()
        self.setFixedHeight(140)
        self.setStyleSheet("background-color: #34353C; border-radius: 12px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.thumb_w, self.thumb_h = 160, 90

        cap = cv2.VideoCapture(str(video.path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        orig_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        cap.release()

        self.placeholder = QPixmap(self.thumb_w, self.thumb_h)
        self.placeholder.fill(QColor("#333333"))
        painter = QPainter(self.placeholder)
        painter.setPen(QColor("#666"))
        painter.drawText(self.placeholder.rect(), Qt.AlignmentFlag.AlignCenter, "Loading...")
        painter.end()

        self.loader = FullVideoLoaderThread(
            str(video.path), self.thumb_w, self.thumb_h, total_frames
        )

        self.model = FullVideoFramesModel(
            total_frames, orig_w, orig_h, self.placeholder
        )

        self.loader.frame_ready.connect(self.model.set_frame)
        self.loader.loading_finished.connect(self._on_loading_finished)
        self.loader.start()

        self.list_view = QListView()
        self.list_view.setFlow(QListView.Flow.LeftToRight)
        self.list_view.setWrapping(False)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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

    def _on_item_clicked(self, index):
        frame_idx = index.row()
        self.frame_clicked.emit(frame_idx)

    def set_current_frame(self, frame_index):
        idx = self.model.index(frame_index, 0)
        if idx.isValid():
            flag = QItemSelectionModel.SelectionFlag.ClearAndSelect
            self.list_view.selectionModel().select(idx, flag)
            self.list_view.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)

    def on_scroll(self, value):
        item_width = self.thumb_w
        center_pixel = value + (self.list_view.width() / 2)
        center_index = int(center_pixel / item_width)

    def _on_loading_finished(self):
        pass

    def cleanup(self):
        try:
            if self.loader.isRunning():
                self.loader.stop()
                self.loader.deleteLater()
        except:
            pass
