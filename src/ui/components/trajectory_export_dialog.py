import math
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFontComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# ── Стили ──

COMBOBOX_STYLE = """
    QComboBox {
        background-color: #333; color: white;
        border: 1px solid #444; border-radius: 6px;
        padding: 4px 28px 4px 10px; min-width: 100px; font-size: 13px;
    }
    QComboBox:hover { border: 1px solid #555; }
    QComboBox::drop-down {
        subcontrol-origin: padding; subcontrol-position: center right;
        width: 24px; border: none; background: transparent;
    }
    QComboBox::down-arrow {
        image: none; border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #aaa; margin-right: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #2d2d30; color: white;
        border: 1px solid #3e3e42; selection-background-color: #3e3e42;
        selection-color: white; outline: none; padding: 2px 0px;
    }
    QComboBox QAbstractItemView::item {
        padding: 6px 10px; min-height: 24px;
        background-color: transparent; color: white;
    }
    QComboBox QAbstractItemView::item:hover { background-color: #3e3e42; }
    QComboBox QAbstractItemView::item:selected { background-color: #2ea043; }
"""

FONT_COMBO_STYLE = """
    QFontComboBox {
        background-color: #333; color: white;
        border: 1px solid #444; border-radius: 6px;
        padding: 4px 28px 4px 10px; font-size: 13px;
    }
    QFontComboBox:hover { border: 1px solid #555; }
    QFontComboBox::drop-down {
        subcontrol-origin: padding; subcontrol-position: center right;
        width: 24px; border: none; background: transparent;
    }
    QFontComboBox::down-arrow {
        image: none; border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #aaa; margin-right: 6px;
    }
    QFontComboBox QAbstractItemView {
        background-color: #2d2d30; color: white;
        border: 1px solid #3e3e42; selection-background-color: #3e3e42;
        selection-color: white; outline: none;
    }
    QFontComboBox QAbstractItemView::item {
        padding: 6px 10px; min-height: 24px;
        background-color: transparent; color: white;
    }
    QFontComboBox QAbstractItemView::item:hover { background-color: #3e3e42; }
    QFontComboBox QAbstractItemView::item:selected { background-color: #2ea043; }
"""

CHECKBOX_STYLE = """
    QCheckBox {
        color: #ccc; spacing: 8px; background: transparent;
        border: none; font-size: 13px; padding: 2px 0;
    }
    QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; }
    QCheckBox::indicator:unchecked { background-color: #333; border: 1px solid #555; }
    QCheckBox::indicator:unchecked:hover { border: 1px solid #777; }
    QCheckBox::indicator:checked { background-color: #2ea043; border: 1px solid #2ea043; }
    QCheckBox::indicator:checked:hover { background-color: #3ab654; border: 1px solid #3ab654; }
"""

GROUPBOX_STYLE = """
    QGroupBox {
        color: #ccc; border: 1px solid #3e3e42; border-radius: 6px;
        margin-top: 14px; padding: 16px 10px 10px 10px;
        background-color: transparent; font-size: 13px;
    }
    QGroupBox::title {
        subcontrol-origin: margin; subcontrol-position: top left;
        left: 10px; padding: 0 6px;
        background-color: #252526; color: #aaa;
    }
"""

LABEL_STYLE = "color: #ccc; border: none; background: transparent;"

SPINBOX_STYLE = """
    QSpinBox, QDoubleSpinBox {
        background-color: #333; color: white;
        border: 1px solid #444; border-radius: 6px;
        padding: 4px 8px; font-size: 13px; min-width: 70px;
    }
    QSpinBox:hover, QDoubleSpinBox:hover { border: 1px solid #555; }
    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {
        background: transparent; border: none; width: 16px;
    }
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        image: none; border-left: 4px solid transparent;
        border-right: 4px solid transparent; border-bottom: 5px solid #aaa;
    }
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        image: none; border-left: 4px solid transparent;
        border-right: 4px solid transparent; border-top: 5px solid #aaa;
    }
"""

SCROLLAREA_STYLE = """
    QScrollArea {
        background: transparent; border: none;
    }
    QScrollBar:vertical {
        background: #2d2d30; width: 8px; border: none; border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background: #555; border-radius: 4px; min-height: 30px;
    }
    QScrollBar::handle:vertical:hover { background: #666; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""


class CompassRoseData:
    """Данные компасной розы (эллипс)."""

    def __init__(
        self,
        enabled=False,
        x=50.0,
        y=50.0,
        rx=30.0,
        ry=30.0,
        rotation=0.0,
        font_family="Segoe UI",
        font_size=0,
    ):
        self.enabled = enabled
        self.x = x
        self.y = y
        self.rx = rx  # горизонтальный радиус эллипса
        self.ry = ry  # вертикальный радиус эллипса
        self.rotation = rotation
        self.font_family = font_family
        self.font_size = font_size  # 0 = авто


class PreviewWidget(QWidget):
    """Предпросмотр с интерактивным компасом-эллипсом и 8 ручками."""

    compass_changed = Signal()

    HANDLE_SIZE = 8
    ROTATE_HANDLE_DISTANCE = 22
    ROTATE_HANDLE_RADIUS = 5

    # Индексы ручек: 0-3 углы (TL, TR, BR, BL), 4-7 стороны (T, R, B, L)
    H_TL, H_TR, H_BR, H_BL = 0, 1, 2, 3
    H_T, H_R, H_B, H_L = 4, 5, 6, 7

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(100, 80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        self._preview_image: Optional[QImage] = None
        self._video_size: Tuple[int, int] = (640, 480)
        self.compass = CompassRoseData()

        self._selected = False
        self._dragging = False
        self._resizing = False
        self._rotating = False

        self._drag_offset = QPointF(0, 0)
        self._resize_handle = -1
        self._resize_start_rx = 0.0
        self._resize_start_ry = 0.0
        self._resize_start_pos = QPointF()
        self._rotate_start_angle = 0.0
        self._rotate_start_rotation = 0.0

    def set_preview_image(self, image: QImage):
        self._preview_image = image
        self.update()

    def set_video_size(self, w: int, h: int):
        self._video_size = (w, h)

    # ── Координаты ──

    def _get_transform(self):
        vw, vh = self._video_size
        if vw == 0 or vh == 0:
            return 1.0, 0.0, 0.0
        ww, wh = self.width(), self.height()
        s = min(ww / vw, wh / vh)
        return s, (ww - vw * s) / 2, (wh - vh * s) / 2

    def _v2w(self, vx, vy):
        s, ox, oy = self._get_transform()
        return QPointF(vx * s + ox, vy * s + oy)

    def _w2v(self, wx, wy):
        s, ox, oy = self._get_transform()
        return QPointF((wx - ox) / s, (wy - oy) / s) if s else QPointF(0, 0)

    def _screen_center(self):
        return self._v2w(self.compass.x, self.compass.y)

    def _screen_rx(self):
        s, _, _ = self._get_transform()
        return self.compass.rx * s

    def _screen_ry(self):
        s, _, _ = self._get_transform()
        return self.compass.ry * s

    # ── Ручки ──

    def _handle_positions(self) -> List[QPointF]:
        """8 позиций ручек вокруг bounding box эллипса."""
        c = self._screen_center()
        rx, ry = self._screen_rx(), self._screen_ry()
        cx, cy = c.x(), c.y()
        return [
            QPointF(cx - rx, cy - ry),  # TL
            QPointF(cx + rx, cy - ry),  # TR
            QPointF(cx + rx, cy + ry),  # BR
            QPointF(cx - rx, cy + ry),  # BL
            QPointF(cx, cy - ry),  # T
            QPointF(cx + rx, cy),  # R
            QPointF(cx, cy + ry),  # B
            QPointF(cx - rx, cy),  # L
        ]

    def _handle_rects(self) -> List[QRectF]:
        hs = self.HANDLE_SIZE
        half = hs / 2
        return [
            QRectF(p.x() - half, p.y() - half, hs, hs) for p in self._handle_positions()
        ]

    def _rotate_handle_center(self) -> QPointF:
        c = self._screen_center()
        ry = self._screen_ry()
        return QPointF(c.x(), c.y() - ry - self.ROTATE_HANDLE_DISTANCE)

    # ── Отрисовка ──

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#1e1e1e"))

        s, ox, oy = self._get_transform()
        vw, vh = self._video_size
        img_rect = QRectF(ox, oy, vw * s, vh * s)
        p.fillRect(img_rect, QColor("#FFFFFF"))

        if self._preview_image and not self._preview_image.isNull():
            p.drawImage(img_rect, self._preview_image)

        if self.compass.enabled and self._selected:
            self._draw_handles(p)

        p.end()

    def _draw_handles(self, p: QPainter):
        c = self._screen_center()
        rx, ry = self._screen_rx(), self._screen_ry()

        # Пунктирная рамка
        p.setPen(QPen(QColor("#4a9eff"), 1, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(c.x() - rx, c.y() - ry, rx * 2, ry * 2))

        # 8 ручек
        p.setPen(QPen(QColor("#4a9eff"), 1))
        p.setBrush(QColor("#FFFFFF"))
        for rect in self._handle_rects():
            p.drawRect(rect)

        # Линия к ручке вращения
        rot_c = self._rotate_handle_center()
        p.setPen(QPen(QColor("#4a9eff"), 1))
        p.drawLine(QPointF(c.x(), c.y() - ry), rot_c)

        # Ручка вращения
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(rot_c, self.ROTATE_HANDLE_RADIUS, self.ROTATE_HANDLE_RADIUS)

    # ── Hit test ──

    def _hit_handle(self, pos) -> int:
        if not self._selected:
            return -1
        for i, r in enumerate(self._handle_rects()):
            if r.adjusted(-4, -4, 4, 4).contains(pos):
                return i
        return -1

    def _hit_rotate(self, pos) -> bool:
        if not self._selected:
            return False
        rc = self._rotate_handle_center()
        return (
            math.hypot(pos.x() - rc.x(), pos.y() - rc.y())
            <= self.ROTATE_HANDLE_RADIUS + 5
        )

    def _hit_body(self, pos) -> bool:
        c = self._screen_center()
        rx, ry = self._screen_rx(), self._screen_ry()
        if rx == 0 or ry == 0:
            return False
        dx = (pos.x() - c.x()) / rx
        dy = (pos.y() - c.y()) / ry
        return (dx * dx + dy * dy) <= 1.0

    # ── Курсоры ──

    @staticmethod
    def _cursor_for_handle(h: int):
        if h in (0, 2):
            return Qt.SizeFDiagCursor
        if h in (1, 3):
            return Qt.SizeBDiagCursor
        if h in (4, 6):
            return Qt.SizeVerCursor
        if h in (5, 7):
            return Qt.SizeHorCursor
        return Qt.ArrowCursor

    # ── Мышь ──

    def mousePressEvent(self, ev):
        if not self.compass.enabled or ev.button() != Qt.LeftButton:
            return super().mousePressEvent(ev)

        pos = ev.position()

        if self._hit_rotate(pos):
            self._rotating = True
            c = self._screen_center()
            self._rotate_start_angle = math.degrees(
                math.atan2(pos.y() - c.y(), pos.x() - c.x())
            )
            self._rotate_start_rotation = self.compass.rotation
            self.setCursor(Qt.ClosedHandCursor)
            return

        h = self._hit_handle(pos)
        if h >= 0:
            self._resizing = True
            self._resize_handle = h
            self._resize_start_rx = self.compass.rx
            self._resize_start_ry = self.compass.ry
            self._resize_start_pos = pos
            self.setCursor(self._cursor_for_handle(h))
            return

        if self._hit_body(pos):
            self._selected = True
            self._dragging = True
            vp = self._w2v(pos.x(), pos.y())
            self._drag_offset = QPointF(
                self.compass.x - vp.x(), self.compass.y - vp.y()
            )
            self.setCursor(Qt.ClosedHandCursor)
            self.update()
            return

        self._selected = False
        self.update()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        pos = ev.position()

        if self._dragging:
            vp = self._w2v(pos.x(), pos.y())
            self.compass.x = vp.x() + self._drag_offset.x()
            self.compass.y = vp.y() + self._drag_offset.y()
            self.compass_changed.emit()
            self.update()
            return

        if self._resizing:
            s, _, _ = self._get_transform()
            if s == 0:
                return
            dx = (pos.x() - self._resize_start_pos.x()) / s
            dy = (pos.y() - self._resize_start_pos.y()) / s
            h = self._resize_handle

            new_rx = self._resize_start_rx
            new_ry = self._resize_start_ry

            if h == self.H_TL:
                new_rx = max(10, self._resize_start_rx - dx)
                new_ry = max(10, self._resize_start_ry - dy)
            elif h == self.H_TR:
                new_rx = max(10, self._resize_start_rx + dx)
                new_ry = max(10, self._resize_start_ry - dy)
            elif h == self.H_BR:
                new_rx = max(10, self._resize_start_rx + dx)
                new_ry = max(10, self._resize_start_ry + dy)
            elif h == self.H_BL:
                new_rx = max(10, self._resize_start_rx - dx)
                new_ry = max(10, self._resize_start_ry + dy)
            elif h == self.H_T:
                new_ry = max(10, self._resize_start_ry - dy)
            elif h == self.H_B:
                new_ry = max(10, self._resize_start_ry + dy)
            elif h == self.H_R:
                new_rx = max(10, self._resize_start_rx + dx)
            elif h == self.H_L:
                new_rx = max(10, self._resize_start_rx - dx)

            self.compass.rx = new_rx
            self.compass.ry = new_ry
            self.compass_changed.emit()
            self.update()
            return

        if self._rotating:
            c = self._screen_center()
            angle = math.degrees(math.atan2(pos.y() - c.y(), pos.x() - c.x()))
            self.compass.rotation = (
                self._rotate_start_rotation + angle - self._rotate_start_angle
            ) % 360
            self.compass_changed.emit()
            self.update()
            return

        # Курсоры при наведении
        if self.compass.enabled:
            if self._hit_rotate(pos):
                self.setCursor(Qt.SizeAllCursor)
            else:
                h = self._hit_handle(pos)
                if h >= 0:
                    self.setCursor(self._cursor_for_handle(h))
                elif self._hit_body(pos):
                    self.setCursor(Qt.OpenHandCursor)
                else:
                    self.setCursor(Qt.ArrowCursor)

        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if self._dragging or self._resizing or self._rotating:
            self._dragging = False
            self._resizing = False
            self._rotating = False
            self._resize_handle = -1
            self.setCursor(Qt.ArrowCursor)
            self.compass_changed.emit()
            return
        super().mouseReleaseEvent(ev)


class TrajectoryExportDialog(QDialog):
    export_clicked = Signal(dict)

    _EDGE_MARGIN = 8  # зона захвата для ресайза окна

    def __init__(
        self,
        geometry_items: List,
        tracking_data: Dict = None,
        video_size: Tuple[int, int] = (640, 480),
        current_frame: int = None,
        compass_settings: dict = None,
        parent=None,
    ):
        super().__init__(parent)
        self.geometry_items = geometry_items
        self.geometry_checks = {}
        self.tracking_data = tracking_data or {}
        self.video_size = video_size
        self.current_frame = current_frame

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumSize(700, 450)
        self.resize(960, 580)

        # Для перемещения/ресайза окна
        self._move_drag = False
        self._resize_drag = False
        self._drag_pos = QPointF()
        self._resize_edge = 0  # битовая маска: 1=left, 2=right, 4=top, 8=bottom

        self._init_ui()

        if compass_settings:
            self._apply_compass_settings(compass_settings)

        self._schedule_preview_update()

    # ── Перемещение и ресайз окна ──

    def _edge_at(self, pos) -> int:
        m = self._EDGE_MARGIN
        edge = 0
        if pos.x() < m:
            edge |= 1
        if pos.x() > self.width() - m:
            edge |= 2
        if pos.y() < m:
            edge |= 4
        if pos.y() > self.height() - m:
            edge |= 8
        return edge

    @staticmethod
    def _edge_cursor(edge: int):
        if edge in (1 | 4, 2 | 8):
            return Qt.SizeFDiagCursor
        if edge in (2 | 4, 1 | 8):
            return Qt.SizeBDiagCursor
        if edge in (1, 2):
            return Qt.SizeHorCursor
        if edge in (4, 8):
            return Qt.SizeVerCursor
        return Qt.ArrowCursor

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            edge = self._edge_at(ev.position())
            if edge:
                self._resize_drag = True
                self._resize_edge = edge
                self._drag_pos = ev.globalPosition()
                self._drag_geom = self.geometry()
                return

            # Перетаскивание за верхнюю полосу (40 px)
            if ev.position().y() < 40:
                self._move_drag = True
                self._drag_pos = ev.globalPosition() - QPointF(self.pos())
                return

        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._resize_drag:
            delta = ev.globalPosition() - self._drag_pos
            g = self._drag_geom
            new_geom = QRectF(g)
            e = self._resize_edge
            if e & 1:
                new_geom.setLeft(g.left() + delta.x())
            if e & 2:
                new_geom.setRight(g.right() + delta.x())
            if e & 4:
                new_geom.setTop(g.top() + delta.y())
            if e & 8:
                new_geom.setBottom(g.bottom() + delta.y())
            r = new_geom.toRect()
            if r.width() >= self.minimumWidth() and r.height() >= self.minimumHeight():
                self.setGeometry(r)
            return

        if self._move_drag:
            self.move((ev.globalPosition() - self._drag_pos).toPoint())
            return

        # Курсор при наведении на край
        edge = self._edge_at(ev.position())
        if edge:
            self.setCursor(self._edge_cursor(edge))
        elif ev.position().y() < 40:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        self._move_drag = False
        self._resize_drag = False
        self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(ev)

    # ── Apply saved settings ──

    def _apply_compass_settings(self, s: dict):
        self.chk_compass.setChecked(s.get("enabled", False))
        self.spin_compass_x.setValue(s.get("x", 50))
        self.spin_compass_y.setValue(s.get("y", 50))
        self.spin_compass_rx.setValue(s.get("rx", s.get("size", 60) / 2))
        self.spin_compass_ry.setValue(s.get("ry", s.get("size", 60) / 2))
        self.spin_compass_rotation.setValue(s.get("rotation", 0))
        self.combo_font.setCurrentFont(QFont(s.get("font_family", "Segoe UI")))
        self.spin_font_size.setValue(s.get("font_size", 0))
        self._sync_compass_from_spins()

    # ── Фабрики виджетов ──

    def _make_combo(self, items, default):
        c = QComboBox()
        c.addItems(items)
        c.setCurrentText(default)
        c.setFixedHeight(34)
        c.setMinimumWidth(120)
        c.setStyleSheet(COMBOBOX_STYLE)
        c.setFocusPolicy(Qt.StrongFocus)
        return c

    def _make_row(self, label_text, widget):
        row = QHBoxLayout()
        row.setSpacing(12)
        lbl = QLabel(label_text)
        lbl.setFont(QFont("Segoe UI", 13))
        lbl.setStyleSheet(LABEL_STYLE)
        lbl.setFixedWidth(120)
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        return row

    def _make_spin_int(self, mn, mx, val, suffix=""):
        s = QSpinBox()
        s.setRange(mn, mx)
        s.setValue(val)
        if suffix:
            s.setSuffix(suffix)
        s.setFixedHeight(30)
        s.setStyleSheet(SPINBOX_STYLE)
        return s

    def _make_spin_double(self, mn, mx, val, dec=1, suffix=""):
        s = QDoubleSpinBox()
        s.setRange(mn, mx)
        s.setDecimals(dec)
        s.setValue(val)
        if suffix:
            s.setSuffix(suffix)
        s.setFixedHeight(30)
        s.setStyleSheet(SPINBOX_STYLE)
        return s

    @staticmethod
    def _param_row(label_text, widget):
        row = QHBoxLayout()
        row.setSpacing(6)
        lbl = QLabel(label_text)
        lbl.setFixedWidth(70)
        lbl.setStyleSheet(LABEL_STYLE)
        lbl.setFont(QFont("Segoe UI", 12))
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        return row

    # ── UI ──

    def _init_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Контейнер всего окна (для скруглённых углов)
        shell = QFrame(self)
        shell.setStyleSheet("""
            QFrame#dialogShell {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 12px;
            }
        """)
        shell.setObjectName("dialogShell")
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # ═══ Левая панель: Предпросмотр ═══
        preview_frame = QFrame()
        preview_frame.setStyleSheet(
            "background: #1e1e1e; border: none; border-radius: 12px 0 0 12px;"
        )
        pv_layout = QVBoxLayout(preview_frame)
        pv_layout.setContentsMargins(8, 8, 4, 8)
        pv_layout.setSpacing(4)

        lbl_pv = QLabel("Предпросмотр")
        lbl_pv.setFont(QFont("Segoe UI", 11))
        lbl_pv.setStyleSheet("color:#666; background:transparent;")
        lbl_pv.setAlignment(Qt.AlignCenter)
        pv_layout.addWidget(lbl_pv)

        self.preview_widget = PreviewWidget()
        self.preview_widget.set_video_size(*self.video_size)
        self.preview_widget.compass_changed.connect(self._on_compass_changed_in_preview)
        pv_layout.addWidget(self.preview_widget, 1)

        shell_layout.addWidget(preview_frame, 1)

        # ═══ Правая панель (скроллируемая) ═══
        right_frame = QFrame()
        right_frame.setFixedWidth(420)
        right_frame.setStyleSheet(
            "background: #252526; border: none; border-radius: 0 12px 12px 0;"
        )

        right_outer = QVBoxLayout(right_frame)
        right_outer.setContentsMargins(0, 0, 0, 0)
        right_outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLLAREA_STYLE)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(24, 24, 24, 12)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel("Экспорт траектории")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(title)

        # Формат / Масштаб / Сглаживание
        self.combo_format = self._make_combo(["SVG", "PNG", "JPG"], "SVG")
        self.combo_format.currentTextChanged.connect(self._schedule_preview_update)
        layout.addLayout(self._make_row("Формат:", self.combo_format))

        self.combo_scale = self._make_combo(["1x", "2x", "4x", "8x"], "1x")
        self.combo_scale.currentTextChanged.connect(self._schedule_preview_update)
        layout.addLayout(self._make_row("Масштаб:", self.combo_scale))

        self.combo_smoothing = self._make_combo(["Нет", "Да"], "Да")
        self.combo_smoothing.currentTextChanged.connect(self._schedule_preview_update)
        layout.addLayout(self._make_row("Сглаживание:", self.combo_smoothing))

        # Отображение
        grp_show = QGroupBox("Отображение")
        grp_show.setStyleSheet(GROUPBOX_STYLE)
        gl = QVBoxLayout()
        gl.setSpacing(6)
        gl.setContentsMargins(4, 4, 4, 4)

        self.chk_trajectory = QCheckBox("Траектория")
        self.chk_trajectory.setChecked(True)
        self.chk_trajectory.setStyleSheet(CHECKBOX_STYLE)
        self.chk_trajectory.stateChanged.connect(self._schedule_preview_update)
        gl.addWidget(self.chk_trajectory)

        self.chk_geometry = QCheckBox("Геометрия")
        self.chk_geometry.setChecked(True)
        self.chk_geometry.setStyleSheet(CHECKBOX_STYLE)
        self.chk_geometry.stateChanged.connect(self._schedule_preview_update)
        gl.addWidget(self.chk_geometry)

        grp_show.setLayout(gl)
        layout.addWidget(grp_show)

        # Зоны геометрии
        if self.geometry_items:
            grp_zones = QGroupBox("Зоны геометрии")
            grp_zones.setStyleSheet(GROUPBOX_STYLE)
            zl = QVBoxLayout()
            zl.setSpacing(6)
            zl.setContentsMargins(4, 4, 4, 4)
            for item in self.geometry_items:
                chk = QCheckBox(item.name)
                chk.setChecked(True)
                chk.setStyleSheet(CHECKBOX_STYLE)
                chk.stateChanged.connect(self._schedule_preview_update)
                self.geometry_checks[item.name] = chk
                zl.addWidget(chk)
            grp_zones.setLayout(zl)
            layout.addWidget(grp_zones)

        # ═══ Стороны света ═══
        grp_compass = QGroupBox("Стороны света")
        grp_compass.setStyleSheet(GROUPBOX_STYLE)
        cl = QVBoxLayout()
        cl.setSpacing(6)
        cl.setContentsMargins(4, 4, 4, 4)

        self.chk_compass = QCheckBox("Показать компас")
        self.chk_compass.setChecked(False)
        self.chk_compass.setStyleSheet(CHECKBOX_STYLE)
        self.chk_compass.stateChanged.connect(self._on_compass_enabled_changed)
        cl.addWidget(self.chk_compass)

        # Позиция
        self.spin_compass_x = self._make_spin_int(0, 10000, 50, " px")
        self.spin_compass_x.setEnabled(False)
        self.spin_compass_x.valueChanged.connect(self._on_compass_spin_changed)
        cl.addLayout(self._param_row("X:", self.spin_compass_x))

        self.spin_compass_y = self._make_spin_int(0, 10000, 50, " px")
        self.spin_compass_y.setEnabled(False)
        self.spin_compass_y.valueChanged.connect(self._on_compass_spin_changed)
        cl.addLayout(self._param_row("Y:", self.spin_compass_y))

        # Радиусы эллипса
        self.spin_compass_rx = self._make_spin_int(10, 5000, 30, " px")
        self.spin_compass_rx.setEnabled(False)
        self.spin_compass_rx.valueChanged.connect(self._on_compass_spin_changed)
        cl.addLayout(self._param_row("Радиус X:", self.spin_compass_rx))

        self.spin_compass_ry = self._make_spin_int(10, 5000, 30, " px")
        self.spin_compass_ry.setEnabled(False)
        self.spin_compass_ry.valueChanged.connect(self._on_compass_spin_changed)
        cl.addLayout(self._param_row("Радиус Y:", self.spin_compass_ry))

        self.spin_compass_rotation = self._make_spin_double(0, 359.9, 0, 1, "°")
        self.spin_compass_rotation.setEnabled(False)
        self.spin_compass_rotation.valueChanged.connect(self._on_compass_spin_changed)
        cl.addLayout(self._param_row("Поворот:", self.spin_compass_rotation))

        # Разделитель
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #3e3e42; border: none; max-height: 1px;")
        cl.addWidget(sep)

        # Шрифт
        lbl_fh = QLabel("Шрифт подписей")
        lbl_fh.setStyleSheet(
            "color: #999; background: transparent; font-size: 11px; border: none;"
        )
        cl.addWidget(lbl_fh)

        self.combo_font = QFontComboBox()
        self.combo_font.setCurrentFont(QFont("Segoe UI"))
        self.combo_font.setFixedHeight(30)
        self.combo_font.setEnabled(False)
        self.combo_font.setStyleSheet(FONT_COMBO_STYLE)
        self.combo_font.currentFontChanged.connect(self._on_compass_spin_changed)
        cl.addLayout(self._param_row("Шрифт:", self.combo_font))

        self.spin_font_size = self._make_spin_int(0, 200, 0, " pt")
        self.spin_font_size.setEnabled(False)
        self.spin_font_size.setSpecialValueText("Авто")
        self.spin_font_size.valueChanged.connect(self._on_compass_spin_changed)
        cl.addLayout(self._param_row("Кегль:", self.spin_font_size))

        grp_compass.setLayout(cl)
        layout.addWidget(grp_compass)

        layout.addStretch()

        scroll.setWidget(scroll_content)
        right_outer.addWidget(scroll, 1)

        # Кнопки (вне скролла)
        btn_bar = QWidget()
        btn_bar.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(24, 8, 24, 16)
        btn_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #aaa;
                border: 1px solid #444; border-radius: 6px;
                font-weight: bold; padding: 0 16px;
            }
            QPushButton:hover { background-color: #333; color: white; border: 1px solid #555; }
        """)

        self.btn_export = QPushButton("Экспорт")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setFixedHeight(36)
        self.btn_export.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.btn_export.clicked.connect(self._on_export_clicked)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #2ea043; color: white;
                border: none; border-radius: 6px;
                font-weight: bold; padding: 0 16px;
            }
            QPushButton:hover { background-color: #3ab654; }
            QPushButton:pressed { background-color: #238636; }
        """)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_export)
        right_outer.addWidget(btn_bar)

        shell_layout.addWidget(right_frame)
        outer.addWidget(shell)

    # ── Compass sync ──

    def _on_compass_enabled_changed(self):
        en = self.chk_compass.isChecked()
        for w in (
            self.spin_compass_x,
            self.spin_compass_y,
            self.spin_compass_rx,
            self.spin_compass_ry,
            self.spin_compass_rotation,
            self.combo_font,
            self.spin_font_size,
        ):
            w.setEnabled(en)

        self.preview_widget.compass.enabled = en
        self.preview_widget._selected = en

        if (
            en
            and self.spin_compass_rx.value() <= 10
            and self.spin_compass_ry.value() <= 10
        ):
            vw, vh = self.video_size
            r = min(vw, vh) * 0.06
            self.spin_compass_x.setValue(int(vw * 0.85))
            self.spin_compass_y.setValue(int(vh * 0.15))
            self.spin_compass_rx.setValue(int(max(20, r)))
            self.spin_compass_ry.setValue(int(max(20, r)))
            self.spin_compass_rotation.setValue(0)

        self._sync_compass_from_spins()
        self._schedule_preview_update()

    def _on_compass_spin_changed(self):
        self._sync_compass_from_spins()
        self._schedule_preview_update()

    def _sync_compass_from_spins(self):
        c = self.preview_widget.compass
        c.enabled = self.chk_compass.isChecked()
        c.x = self.spin_compass_x.value()
        c.y = self.spin_compass_y.value()
        c.rx = self.spin_compass_rx.value()
        c.ry = self.spin_compass_ry.value()
        c.rotation = self.spin_compass_rotation.value()
        c.font_family = self.combo_font.currentFont().family()
        c.font_size = self.spin_font_size.value()
        self.preview_widget.update()

    def _on_compass_changed_in_preview(self):
        c = self.preview_widget.compass
        spins = (
            self.spin_compass_x,
            self.spin_compass_y,
            self.spin_compass_rx,
            self.spin_compass_ry,
            self.spin_compass_rotation,
        )
        for s in spins:
            s.blockSignals(True)
        self.spin_compass_x.setValue(int(c.x))
        self.spin_compass_y.setValue(int(c.y))
        self.spin_compass_rx.setValue(int(c.rx))
        self.spin_compass_ry.setValue(int(c.ry))
        self.spin_compass_rotation.setValue(round(c.rotation, 1))
        for s in spins:
            s.blockSignals(False)
        self._schedule_preview_update()

    # ── Preview ──

    def _schedule_preview_update(self):
        QTimer.singleShot(50, self._update_preview)

    def _build_compass_data(self) -> Optional[dict]:
        if not self.chk_compass.isChecked():
            return None
        return {
            "x": self.spin_compass_x.value(),
            "y": self.spin_compass_y.value(),
            "rx": self.spin_compass_rx.value(),
            "ry": self.spin_compass_ry.value(),
            "rotation": self.spin_compass_rotation.value(),
            "font_family": self.combo_font.currentFont().family(),
            "font_size": self.spin_font_size.value(),
        }

    def _update_preview(self):
        from src.services.trajectory_export_service import TrajectoryExportService

        sel = [n for n, ch in self.geometry_checks.items() if ch.isChecked()]

        img = TrajectoryExportService.render_image(
            tracking_data=self.tracking_data,
            geometry_items=self.geometry_items,
            video_size=self.video_size,
            scale=1,
            show_trajectory=self.chk_trajectory.isChecked(),
            show_geometry=self.chk_geometry.isChecked(),
            selected_geometry_names=sel,
            smoothing=self.combo_smoothing.currentText(),
            current_frame=self.current_frame,
            compass=self._build_compass_data(),
        )
        self.preview_widget.set_preview_image(img)

    # ── Export ──

    def get_compass_settings(self) -> dict:
        return {
            "enabled": self.chk_compass.isChecked(),
            "x": self.spin_compass_x.value(),
            "y": self.spin_compass_y.value(),
            "rx": self.spin_compass_rx.value(),
            "ry": self.spin_compass_ry.value(),
            "rotation": self.spin_compass_rotation.value(),
            "font_family": self.combo_font.currentFont().family(),
            "font_size": self.spin_font_size.value(),
        }

    def _on_export_clicked(self):
        fmt = self.combo_format.currentText()
        scale = int(self.combo_scale.currentText().replace("x", ""))
        sel = [n for n, ch in self.geometry_checks.items() if ch.isChecked()]

        ext_map = {
            "SVG": (".svg", "SVG Files (*.svg)"),
            "PNG": (".png", "PNG Files (*.png)"),
            "JPG": (".jpg", "JPG Files (*.jpg)"),
        }
        ext, filt = ext_map[fmt]

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить", f"trajectory{ext}", filt
        )
        if not path:
            return

        options = {
            "format": fmt.lower(),
            "scale": scale,
            "smoothing": self.combo_smoothing.currentText(),
            "show_trajectory": self.chk_trajectory.isChecked(),
            "show_geometry": self.chk_geometry.isChecked(),
            "selected_geometries": sel,
            "output_path": path,
            "compass": self._build_compass_data(),
        }
        self.export_clicked.emit(options)
        self.accept()
