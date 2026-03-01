import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem


class RulerLineItem(QGraphicsLineItem):
    """Линия-линейка на сцене для калибровки масштаба."""

    def __init__(self, p1: QPointF, p2: QPointF, parent=None):
        super().__init__(parent)
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())
        self.setPen(QPen(QColor("#FF6B6B"), 2, Qt.DashLine))
        self.setZValue(9999)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)

    def pixel_length(self) -> float:
        line = self.line()
        return math.hypot(line.x2() - line.x1(), line.y2() - line.y1())

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)

        # Рисуем длину в пикселях рядом с линией
        line = self.line()
        mid = QPointF((line.x1() + line.x2()) / 2, (line.y1() + line.y2()) / 2)

        painter.setPen(QColor("#FF6B6B"))
        font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(mid + QPointF(5, -8), f"{self.pixel_length():.1f} px")

        # Засечки на концах
        painter.setPen(QPen(QColor("#FF6B6B"), 2))
        dx = line.x2() - line.x1()
        dy = line.y2() - line.y1()
        length = math.hypot(dx, dy)
        if length > 0:
            nx, ny = -dy / length, dx / length
            tick = 8
            for px, py in [(line.x1(), line.y1()), (line.x2(), line.y2())]:
                painter.drawLine(
                    QPointF(px + nx * tick, py + ny * tick),
                    QPointF(px - nx * tick, py - ny * tick),
                )
