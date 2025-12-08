import math
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem
from PySide6.QtCore import Qt, QRectF, Signal, QPointF
from PySide6.QtGui import QBrush, QPen, QColor, QPainter, QPainterPath, QCursor

# --- КОНСТАНТЫ РЕЖИМОВ ---
MODE_NONE = 0
MODE_MOVE = 1

# Стороны
MODE_RESIZE_L = 2
MODE_RESIZE_R = 3
MODE_RESIZE_T = 4
MODE_RESIZE_B = 5

# Углы
MODE_RESIZE_TL = 6
MODE_RESIZE_TR = 7
MODE_RESIZE_BL = 8
MODE_RESIZE_BR = 9

# Спец. режимы
MODE_RESIZE_INNER_RADIUS = 10

# Настройки чувствительности
HANDLE_MARGIN = 12


class EditableGeometryItem(QGraphicsObject):
    geometry_changed = Signal(QRectF)

    def __init__(self, x, y, w, h, shape_type="square", color="#FFDD78", alpha=100):
        super().__init__()
        self.setPos(x, y)
        self.rect = QRectF(0, 0, w, h)
        self.shape_type = shape_type
        self.name = "Object"
        self.inner_ratio = 0.5

        self.is_locked = False  # Флаг блокировки

        self.base_color = QColor(color)
        self.alpha_percent = alpha

        # Флаги
        self.setFlags(QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self.mode = MODE_NONE
        self.start_mouse_pos = QPointF()
        self.start_rect = QRectF()
        self.start_pos = QPointF()
        self.start_ratio = 0.5
        self.group_start_positions = {}

        # Инициализация кисти
        self._update_brush()

    def _update_brush(self):
        alpha_255 = int((self.alpha_percent / 100.0) * 255)
        c = QColor(self.base_color)
        c.setAlpha(alpha_255)
        self.brush = QBrush(c)

        # Рисуем бирюзовую рамку ТОЛЬКО если выделен И НЕ заблокирован
        if self.isSelected() and not self.is_locked:
            self.pen = QPen(Qt.cyan, 2, Qt.DashLine)
        else:
            self.pen = QPen(Qt.NoPen)

    def boundingRect(self):
        return self.rect.adjusted(-HANDLE_MARGIN, -HANDLE_MARGIN, HANDLE_MARGIN, HANDLE_MARGIN)

    def paint(self, painter, option, widget):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)

        if self.is_locked:
            painter.setPen(Qt.NoPen)

        if self.shape_type == "square":
            painter.drawRect(self.rect)
        elif self.shape_type == "circle":
            painter.drawEllipse(self.rect)
        elif self.shape_type == "donut":
            path = QPainterPath()
            path.addEllipse(self.rect)
            center = self.rect.center()
            w = self.rect.width() * self.inner_ratio
            h = self.rect.height() * self.inner_ratio
            inner_rect = QRectF(0, 0, w, h)
            inner_rect.moveCenter(center)
            path.addEllipse(inner_rect)
            path.setFillRule(Qt.OddEvenFill)
            painter.drawPath(path)
            if self.isSelected():
                # Рисуем внутренний контур только если это ОДИНОЧНОЕ выделение
                # (чтобы не засорять вид при мульти-выделении)
                if self.scene() and len(self.scene().selectedItems()) == 1:
                    painter.setBrush(Qt.NoBrush)
                    painter.setPen(QPen(Qt.yellow, 1, Qt.DotLine))
                    painter.drawEllipse(inner_rect)

    def itemChange(self, change, value):
        # Если объект выделили/сняли выделение -> перерисовать рамку
        if change == QGraphicsItem.ItemSelectedChange:
            # Вызываем update чуть позже, т.к. внутри itemChange isSelected еще может быть старым
            # Но _update_brush проверит isSelected().
            # value (bool) - это новое состояние выделения.
            if value == True and not self.is_locked:
                self.pen = QPen(Qt.cyan, 2, Qt.DashLine)
            else:
                self.pen = QPen(Qt.NoPen)
            self.update()

        if change == QGraphicsItem.ItemPositionChange and self.scene():
            self.geometry_changed.emit(self.rect)

        return super().itemChange(change, value)

    def set_geometry_data(self, x, y, w, h):
        self.setPos(x, y)
        self.rect = QRectF(0, 0, w, h)
        self.prepareGeometryChange()
        self.update()

    def set_color_data(self, hex_color, alpha):
        self.base_color = QColor(hex_color)
        self.alpha_percent = float(alpha)
        self._update_brush()
        self.update()

    # --- АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ UI ---
    def itemChange(self, change, value):
        # Если позиция изменилась (даже программно или через группу), шлем сигнал
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            self.geometry_changed.emit(self.rect)
        return super().itemChange(change, value)

    # --- МЫШЬ ---

    def hoverMoveEvent(self, event):
        if self.is_locked:
            self.setCursor(Qt.ArrowCursor)
            return
        if self.isSelected():
            mode = self._get_mode_at_pos(event.pos())
            self.setCursor(self._get_cursor_for_mode(mode))
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if self.is_locked:
            event.ignore()
            return

        if event.button() == Qt.LeftButton:
            modifiers = event.modifiers()
            scene = self.scene()

            if modifiers & Qt.ControlModifier:
                self.setSelected(not self.isSelected())
            elif modifiers & Qt.ShiftModifier:
                self.setSelected(True)
            else:
                if not self.isSelected():
                    if scene:
                        # Блокируем сигналы, чтобы не вызывать перерисовку 100 раз
                        scene.blockSignals(True)
                        for item in scene.selectedItems():
                            item.setSelected(False)
                        scene.blockSignals(False)
                    self.setSelected(True)

            if not self.isSelected():
                self.mode = MODE_NONE
                event.accept()
                return

            self.mode = self._get_mode_at_pos(event.pos())
            self.start_mouse_pos = event.scenePos()
            self.start_pos = self.pos()
            self.start_rect = QRectF(self.rect)
            self.start_ratio = self.inner_ratio

            self.group_start_positions = {}
            if scene:
                sel = scene.selectedItems()
                if len(sel) > 1:
                    for item in sel:
                        if isinstance(item, EditableGeometryItem):
                            self.group_start_positions[item] = item.pos()

            self._update_brush()
            self.update()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_locked: return
        if self.mode == MODE_NONE:
            super().mouseMoveEvent(event)
            return

        diff = event.scenePos() - self.start_mouse_pos
        dx, dy = diff.x(), diff.y()

        if self.mode == MODE_MOVE:
            if self.group_start_positions:
                for item, initial_pos in self.group_start_positions.items():
                    item.setPos(initial_pos + diff)
            else:
                self.setPos(self.start_pos + diff)
            return

        if self.mode == MODE_RESIZE_INNER_RADIUS:
            center = self.rect.center()
            rx = self.rect.width() / 2
            ry = self.rect.height() / 2
            if rx > 0 and ry > 0:
                local_pos = event.pos()
                dist = math.hypot((local_pos.x() - center.x()) / rx, (local_pos.y() - center.y()) / ry)
                self.inner_ratio = max(0.1, min(0.9, dist))
                self.update()
            return

        # Resize Logic
        new_rect = QRectF(self.start_rect)
        new_pos = QPointF(self.start_pos)

        if self.mode in [MODE_RESIZE_L, MODE_RESIZE_TL, MODE_RESIZE_BL]:
            new_rect.setLeft(0)
            new_rect.setWidth(self.start_rect.width() - dx)
            new_pos.setX(self.start_pos.x() + dx)

        if self.mode in [MODE_RESIZE_R, MODE_RESIZE_TR, MODE_RESIZE_BR]:
            new_rect.setWidth(self.start_rect.width() + dx)

        if self.mode in [MODE_RESIZE_T, MODE_RESIZE_TL, MODE_RESIZE_TR]:
            new_rect.setTop(0)
            new_rect.setHeight(self.start_rect.height() - dy)
            new_pos.setY(self.start_pos.y() + dy)

        if self.mode in [MODE_RESIZE_B, MODE_RESIZE_BL, MODE_RESIZE_BR]:
            new_rect.setHeight(self.start_rect.height() + dy)

        if new_rect.width() < 10:
            new_rect.setWidth(10)
            if self.mode in [MODE_RESIZE_L, MODE_RESIZE_TL, MODE_RESIZE_BL]:
                new_pos.setX(self.start_pos.x() + self.start_rect.width() - 10)

        if new_rect.height() < 10:
            new_rect.setHeight(10)
            if self.mode in [MODE_RESIZE_T, MODE_RESIZE_TL, MODE_RESIZE_TR]:
                new_pos.setY(self.start_pos.y() + self.start_rect.height() - 10)

        self.prepareGeometryChange()
        self.rect = new_rect
        self.setPos(new_pos)
        self.update()
        self.geometry_changed.emit(self.rect)

    def mouseReleaseEvent(self, event):
        self.mode = MODE_NONE
        self.group_start_positions = {}
        self._update_brush()
        self.update()
        super().mouseReleaseEvent(event)

    # --- ХИТ-ТЕСТ ---

    def _get_mode_at_pos(self, pos):
        """
        Определяет режим редактирования.
        ЕСЛИ ВЫДЕЛЕНО НЕСКОЛЬКО ОБЪЕКТОВ -> ЗАПРЕЩАЕМ РЕСАЙЗ.
        """
        is_multi_selection = False
        if self.scene() and len(self.scene().selectedItems()) > 1:
            is_multi_selection = True

        r = self.rect

        # Если это мульти-выделение, проверяем только попадание внутрь
        if is_multi_selection:
            if r.contains(pos):
                return MODE_MOVE
            else:
                return MODE_NONE  # Края игнорируем

        # --- Стандартная логика для одиночного объекта ---

        x, y = pos.x(), pos.y()
        m = HANDLE_MARGIN

        # 1. Бублик
        if self.shape_type == "donut":
            center = r.center()
            rx = r.width() / 2
            ry = r.height() / 2
            if rx > 0 and ry > 0:
                dist_norm = math.hypot((x - center.x()) / rx, (y - center.y()) / ry)
                m_norm = m / (min(rx, ry) * 2)
                if abs(dist_norm - self.inner_ratio) < max(0.1, m_norm):
                    return MODE_RESIZE_INNER_RADIUS

        # 2. Границы
        on_left = abs(x - r.left()) < m
        on_right = abs(x - r.right()) < m
        on_top = abs(y - r.top()) < m
        on_bottom = abs(y - r.bottom()) < m

        if on_left and on_top: return MODE_RESIZE_TL
        if on_right and on_top: return MODE_RESIZE_TR
        if on_left and on_bottom: return MODE_RESIZE_BL
        if on_right and on_bottom: return MODE_RESIZE_BR

        if on_left: return MODE_RESIZE_L
        if on_right: return MODE_RESIZE_R
        if on_top: return MODE_RESIZE_T
        if on_bottom: return MODE_RESIZE_B

        # 3. Центр
        if r.contains(pos):
            return MODE_MOVE

        return MODE_NONE

    def _get_cursor_for_mode(self, mode):
        # Если режим NONE (например, край при мультиселекте), показываем обычную стрелку
        if mode == MODE_NONE:
            return Qt.ArrowCursor

        mapping = {
            MODE_MOVE: Qt.SizeAllCursor,
            MODE_RESIZE_L: Qt.SizeHorCursor,
            MODE_RESIZE_R: Qt.SizeHorCursor,
            MODE_RESIZE_T: Qt.SizeVerCursor,
            MODE_RESIZE_B: Qt.SizeVerCursor,
            MODE_RESIZE_TL: Qt.SizeFDiagCursor,
            MODE_RESIZE_BR: Qt.SizeFDiagCursor,
            MODE_RESIZE_TR: Qt.SizeBDiagCursor,
            MODE_RESIZE_BL: Qt.SizeBDiagCursor,
            MODE_RESIZE_INNER_RADIUS: Qt.SizeVerCursor
        }
        return mapping.get(mode, Qt.ArrowCursor)

    def set_locked(self, locked: bool):
        self.is_locked = locked
        # print(f"Item locked: {locked}") # Debug

        if locked:
            # Снимаем флаги, которые позволяют Qt обрабатывать клики
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)
            # self.setFlag(QGraphicsItem.ItemIsMovable, False) # Если он был
            self.setAcceptHoverEvents(False)

            self.setSelected(False)
            self.setCursor(Qt.ArrowCursor)
            self.mode = MODE_NONE
        else:
            # Возвращаем флаги обратно
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
            self.setAcceptHoverEvents(True)

        self._update_brush()
        self.update()
