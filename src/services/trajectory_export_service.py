import math
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtSvg import QSvgGenerator

from src.core.geometry import Circle, Donut, Geometry, Square
from src.ui.components.video.graphics_items import EditableGeometryItem


class TrajectoryExportService:
    SMOOTHING_WINDOWS = {"Нет": 1, "Да": 5}

    @staticmethod
    def calculate_center(bbox: tuple) -> Tuple[float, float]:
        x, y, w, h = bbox
        return (x + w / 2, y + h / 2)

    @staticmethod
    def smooth_trajectory(points, strength):
        window = TrajectoryExportService.SMOOTHING_WINDOWS.get(strength, 1)
        if window <= 1 or len(points) <= 2:
            return points
        hw = window // 2
        smoothed = []
        for i in range(len(points)):
            s, e = max(0, i - hw), min(len(points), i + hw + 1)
            wp = points[s:e]
            smoothed.append(
                (sum(p[0] for p in wp) / len(wp), sum(p[1] for p in wp) / len(wp))
            )
        return smoothed

    @staticmethod
    def _item_to_geometry(item):
        rect = item.rect
        x, y = item.x() + rect.x(), item.y() + rect.y()
        w, h = rect.width(), rect.height()
        if item.shape_type == "square":
            return Square(x, y, w, h)
        elif item.shape_type == "circle":
            return Circle(x + w / 2, y + h / 2, w / 2, h / 2)
        elif item.shape_type == "donut":
            ro_x, ro_y = w / 2, h / 2
            return Donut(
                x + ro_x,
                y + ro_y,
                ro_x,
                ro_y,
                ro_x * item.inner_ratio,
                ro_y * item.inner_ratio,
            )
        return None

    @staticmethod
    def get_trajectory_points(tracking_data, current_frame=None):
        frames = sorted(
            f for f in tracking_data if (current_frame is None or f <= current_frame)
        )
        return [
            TrajectoryExportService.calculate_center(tracking_data[f]) for f in frames
        ]

    @staticmethod
    def _draw_geometry(painter, geometry_items, selected_names, sf):
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.setBrush(Qt.NoBrush)
        for item in geometry_items:
            if item.name not in selected_names:
                continue
            if TrajectoryExportService._item_to_geometry(item) is None:
                continue
            rect = item.rect
            x, y = (item.x() + rect.x()) * sf, (item.y() + rect.y()) * sf
            w, h = rect.width() * sf, rect.height() * sf
            if item.shape_type == "square":
                painter.drawRect(int(x), int(y), int(w), int(h))
            elif item.shape_type == "circle":
                painter.drawEllipse(QPointF(x + w / 2, y + h / 2), w / 2, h / 2)
            elif item.shape_type == "donut":
                cx, cy = x + w / 2, y + h / 2
                path = QPainterPath()
                path.addEllipse(QPointF(cx, cy), w / 2, h / 2)
                path.addEllipse(
                    QPointF(cx, cy), w / 2 * item.inner_ratio, h / 2 * item.inner_ratio
                )
                painter.drawPath(path)

    @staticmethod
    def _draw_trajectory(painter, tracking_data, sf, smoothing, current_frame=None):
        pts = TrajectoryExportService.get_trajectory_points(
            tracking_data, current_frame
        )
        if smoothing != "none":
            pts = TrajectoryExportService.smooth_trajectory(pts, smoothing)
        if len(pts) > 1:
            painter.setPen(QPen(QColor("#000000"), 2))
            painter.setBrush(Qt.NoBrush)
            path = QPainterPath()
            path.moveTo(pts[0][0] * sf, pts[0][1] * sf)
            for p in pts[1:]:
                path.lineTo(p[0] * sf, p[1] * sf)
            painter.drawPath(path)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#00FF00"))
            painter.drawEllipse(QPointF(pts[0][0] * sf, pts[0][1] * sf), 5, 5)
            painter.setBrush(QColor("#FF0000"))
            painter.drawEllipse(QPointF(pts[-1][0] * sf, pts[-1][1] * sf), 5, 5)

    @staticmethod
    def _draw_compass(painter: QPainter, compass: dict, sf: float):
        if compass is None:
            return

        cx = compass["x"] * sf
        cy = compass["y"] * sf
        rx = compass["rx"] * sf
        ry = compass["ry"] * sf
        rotation = compass.get("rotation", 0)
        font_family = compass.get("font_family", "Segoe UI")
        font_size_pt = compass.get("font_size", 0)

        if rx < 3 or ry < 3:
            return

        painter.save()
        painter.translate(QPointF(cx, cy))
        painter.rotate(rotation)

        # Размер шрифта всегда задаём в ПИКСЕЛЯХ через setPixelSize,
        # чтобы SVG и растр вели себя одинаково
        if font_size_pt == 0:
            px_size = max(7, int(min(rx, ry) * 0.35))
        else:
            px_size = max(5, int(font_size_pt * sf))

        font = QFont(font_family)
        font.setPixelSize(px_size)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#000000"))

        fm = painter.fontMetrics()

        for text, pos in [
            ("N", QPointF(0, -ry)),
            ("S", QPointF(0, ry)),
            ("E", QPointF(rx, 0)),
            ("W", QPointF(-rx, 0)),
        ]:
            tw = fm.horizontalAdvance(text)
            th = fm.ascent()
            painter.drawText(QPointF(pos.x() - tw / 2, pos.y() + th / 2 - 1), text)

        painter.restore()

    # ── Рендеринг ──

    @staticmethod
    def render_to_svg(
        tracking_data,
        geometry_items,
        video_size,
        scale,
        show_trajectory,
        show_geometry,
        selected_geometry_names,
        smoothing,
        current_frame=None,
        output_path="",
        compass=None,
    ):
        w, h = video_size
        gen = QSvgGenerator()
        gen.setFileName(output_path)
        gen.setSize(
            QSize(w * scale, h * scale) if hasattr(QPointF, "toPoint") else None
        )
        gen.setResolution(96)

        p = QPainter()
        p.begin(gen)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(0, 0, w * scale, h * scale, QColor("#FFFFFF"))

        if show_geometry and geometry_items:
            TrajectoryExportService._draw_geometry(
                p, geometry_items, selected_geometry_names, scale
            )
        if show_trajectory and tracking_data:
            TrajectoryExportService._draw_trajectory(
                p, tracking_data, scale, smoothing, current_frame
            )
        if compass:
            TrajectoryExportService._draw_compass(p, compass, scale)
        p.end()

    @staticmethod
    def render_image(
        tracking_data,
        geometry_items,
        video_size,
        scale,
        show_trajectory,
        show_geometry,
        selected_geometry_names,
        smoothing,
        current_frame=None,
        format="png",
        compass=None,
    ) -> QImage:
        w, h = video_size
        img = QImage(w * scale, h * scale, QImage.Format_RGB32)
        img.fill(QColor("#FFFFFF"))

        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)

        if show_geometry and geometry_items:
            TrajectoryExportService._draw_geometry(
                p, geometry_items, selected_geometry_names, scale
            )
        if show_trajectory and tracking_data:
            TrajectoryExportService._draw_trajectory(
                p, tracking_data, scale, smoothing, current_frame
            )
        if compass:
            TrajectoryExportService._draw_compass(p, compass, scale)
        p.end()
        return img

    @staticmethod
    def export_image(
        tracking_data,
        geometry_items,
        video_size,
        output_path,
        format,
        scale=1,
        show_trajectory=True,
        show_geometry=True,
        selected_geometry_names=None,
        smoothing="medium",
        current_frame=None,
        compass=None,
    ):
        if selected_geometry_names is None:
            selected_geometry_names = []

        if format.lower() == "svg":
            TrajectoryExportService.render_to_svg(
                tracking_data,
                geometry_items,
                video_size,
                scale,
                show_trajectory,
                show_geometry,
                selected_geometry_names,
                smoothing,
                current_frame,
                output_path,
                compass,
            )
        else:
            img = TrajectoryExportService.render_image(
                tracking_data,
                geometry_items,
                video_size,
                scale,
                show_trajectory,
                show_geometry,
                selected_geometry_names,
                smoothing,
                current_frame,
                format,
                compass,
            )
            fmt = "JPEG" if format.lower() in ["jpg", "jpeg"] else "PNG"
            q = 90 if format.lower() in ["jpg", "jpeg"] else -1
            img.save(output_path, fmt, q)
