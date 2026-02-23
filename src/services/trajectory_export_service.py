from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtSvg import QSvgGenerator

from src.core.geometry import Circle, Donut, Geometry, Square
from src.ui.components.video.graphics_items import EditableGeometryItem


class TrajectoryExportService:
    SMOOTHING_WINDOWS = {"none": 1, "light": 3, "medium": 5, "strong": 9}

    @staticmethod
    def calculate_center(bbox: tuple) -> Tuple[float, float]:
        x, y, w, h = bbox
        return (x + w / 2, y + h / 2)

    @staticmethod
    def smooth_trajectory(
        points: List[Tuple[float, float]], strength: str
    ) -> List[Tuple[float, float]]:
        window = TrajectoryExportService.SMOOTHING_WINDOWS.get(strength, 1)

        if window <= 1 or len(points) <= 2:
            return points

        smoothed = []
        half_window = window // 2

        for i in range(len(points)):
            start = max(0, i - half_window)
            end = min(len(points), i + half_window + 1)

            window_points = points[start:end]
            avg_x = sum(p[0] for p in window_points) / len(window_points)
            avg_y = sum(p[1] for p in window_points) / len(window_points)

            smoothed.append((avg_x, avg_y))

        return smoothed

    @staticmethod
    def _item_to_geometry(item: EditableGeometryItem) -> Optional[Geometry]:
        rect = item.rect
        x = item.x() + rect.x()
        y = item.y() + rect.y()
        w, h = rect.width(), rect.height()

        if item.shape_type == "square":
            return Square(x, y, w, h)
        elif item.shape_type == "circle":
            rx, ry = w / 2, h / 2
            return Circle(x + rx, y + ry, rx, ry)
        elif item.shape_type == "donut":
            rx_out, ry_out = w / 2, h / 2
            rx_in = rx_out * item.inner_ratio
            ry_in = ry_out * item.inner_ratio
            return Donut(x + rx_out, y + ry_out, rx_out, ry_out, rx_in, ry_in)

        return None

    @staticmethod
    def get_trajectory_points(
        tracking_data: Dict[int, tuple], current_frame: Optional[int] = None
    ) -> List[Tuple[float, float]]:
        if current_frame is not None:
            frames_to_use = [f for f in tracking_data.keys() if f <= current_frame]
        else:
            frames_to_use = list(tracking_data.keys())

        sorted_frames = sorted(frames_to_use)
        points = []

        for frame_idx in sorted_frames:
            bbox = tracking_data[frame_idx]
            cx, cy = TrajectoryExportService.calculate_center(bbox)
            points.append((cx, cy))

        return points

    @staticmethod
    def render_to_svg(tracking_data: Dict[int, tuple],
                     geometry_items: List[EditableGeometryItem],
                     video_size: Tuple[int, int],
                     scale: int,
                     show_trajectory: bool,
                     show_geometry: bool,
                     selected_geometry_names: List[str],
                     smoothing: str,
                     current_frame: Optional[int] = None,
                     output_path: str = ""):
        
        width, height = video_size
        scaled_width = width * scale
        scaled_height = height * scale
        
        generator = QSvgGenerator()
        generator.setFileName(output_path)
        generator.setResolution(96)
        
        painter = QPainter()
        painter.begin(generator)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(0, 0, scaled_width, scaled_height, QColor("#FFFFFF"))
        
        scale_factor = scale
        
        if show_geometry and geometry_items:
            pen = QPen(QColor("#000000"), 1)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            for item in geometry_items:
                if item.name not in selected_geometry_names:
                    continue
                
                geom = TrajectoryExportService._item_to_geometry(item)
                if geom is None:
                    continue
                
                rect = item.rect
                x = (item.x() + rect.x()) * scale_factor
                y = (item.y() + rect.y()) * scale_factor
                w = rect.width() * scale_factor
                h = rect.height() * scale_factor
                
                if item.shape_type == "square":
                    painter.drawRect(int(x), int(y), int(w), int(h))
                elif item.shape_type == "circle":
                    cx = x + w / 2
                    cy = y + h / 2
                    rx = w / 2
                    ry = h / 2
                    painter.drawEllipse(QPointF(cx, cy), rx, ry)
                elif item.shape_type == "donut":
                    cx = x + w / 2
                    cy = y + h / 2
                    rx_out = w / 2
                    ry_out = h / 2
                    rx_in = rx_out * item.inner_ratio
                    ry_in = ry_out * item.inner_ratio
                    
                    path = QPainterPath()
                    path.addEllipse(QPointF(cx, cy), rx_out, ry_out)
                    path.addEllipse(QPointF(cx, cy), rx_in, ry_in)
                    painter.drawPath(path)
        
        if show_trajectory and tracking_data:
            points = TrajectoryExportService.get_trajectory_points(tracking_data, current_frame)
            
            if smoothing != "none":
                points = TrajectoryExportService.smooth_trajectory(points, smoothing)
            
            if len(points) > 1:
                pen = QPen(QColor("#000000"), 2)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                
                path = QPainterPath()
                path.moveTo(points[0][0] * scale_factor, points[0][1] * scale_factor)
                
                for i in range(1, len(points)):
                    path.lineTo(points[i][0] * scale_factor, points[i][1] * scale_factor)
                
                painter.drawPath(path)
                
                start_point = points[0]
                end_point = points[-1]
                
                painter.setBrush(QColor("#00FF00"))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(start_point[0] * scale_factor, 
                                          start_point[1] * scale_factor), 5, 5)
                
                painter.setBrush(QColor("#FF0000"))
                painter.drawEllipse(QPointF(end_point[0] * scale_factor, 
                                          end_point[1] * scale_factor), 5, 5)
        
        painter.end()

    @staticmethod
    def render_image(
        tracking_data: Dict[int, tuple],
        geometry_items: List[EditableGeometryItem],
        video_size: Tuple[int, int],
        scale: int,
        show_trajectory: bool,
        show_geometry: bool,
        selected_geometry_names: List[str],
        smoothing: str,
        current_frame: Optional[int] = None,
        format: str = "png",
    ) -> QImage:

        width, height = video_size
        scaled_width = width * scale
        scaled_height = height * scale

        image = QImage(scaled_width, scaled_height, QImage.Format_RGB32)
        image.fill(QColor("#FFFFFF"))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)

        scale_factor = scale

        if show_geometry and geometry_items:
            pen = QPen(QColor("#000000"), 1)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            for item in geometry_items:
                if item.name not in selected_geometry_names:
                    continue

                geom = TrajectoryExportService._item_to_geometry(item)
                if geom is None:
                    continue

                rect = item.rect
                x = (item.x() + rect.x()) * scale_factor
                y = (item.y() + rect.y()) * scale_factor
                w = rect.width() * scale_factor
                h = rect.height() * scale_factor

                if item.shape_type == "square":
                    painter.drawRect(int(x), int(y), int(w), int(h))
                elif item.shape_type == "circle":
                    cx = x + w / 2
                    cy = y + h / 2
                    rx = w / 2
                    ry = h / 2
                    painter.drawEllipse(QPointF(cx, cy), rx, ry)
                elif item.shape_type == "donut":
                    cx = x + w / 2
                    cy = y + h / 2
                    rx_out = w / 2
                    ry_out = h / 2
                    rx_in = rx_out * item.inner_ratio
                    ry_in = ry_out * item.inner_ratio

                    path = QPainterPath()
                    path.addEllipse(QPointF(cx, cy), rx_out, ry_out)
                    path.addEllipse(QPointF(cx, cy), rx_in, ry_in)
                    painter.drawPath(path)

        if show_trajectory and tracking_data:
            points = TrajectoryExportService.get_trajectory_points(
                tracking_data, current_frame
            )

            if smoothing != "none":
                points = TrajectoryExportService.smooth_trajectory(points, smoothing)

            if len(points) > 1:
                pen = QPen(QColor("#000000"), 2)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)

                path = QPainterPath()
                path.moveTo(points[0][0] * scale_factor, points[0][1] * scale_factor)

                for i in range(1, len(points)):
                    path.lineTo(
                        points[i][0] * scale_factor, points[i][1] * scale_factor
                    )

                painter.drawPath(path)

                start_point = points[0]
                end_point = points[-1]

                painter.setBrush(QColor("#00FF00"))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(
                    QPointF(
                        start_point[0] * scale_factor, start_point[1] * scale_factor
                    ),
                    5,
                    5,
                )

                painter.setBrush(QColor("#FF0000"))
                painter.drawEllipse(
                    QPointF(end_point[0] * scale_factor, end_point[1] * scale_factor),
                    5,
                    5,
                )

        painter.end()

        return image

    @staticmethod
    def export_image(
        tracking_data: Dict[int, tuple],
        geometry_items: List[EditableGeometryItem],
        video_size: Tuple[int, int],
        output_path: str,
        format: str,
        scale: int = 1,
        show_trajectory: bool = True,
        show_geometry: bool = True,
        selected_geometry_names: List[str] = None,
        smoothing: str = "medium",
        current_frame: Optional[int] = None,
    ):

        if selected_geometry_names is None:
            selected_geometry_names = []

        image = TrajectoryExportService.render_image(
            tracking_data=tracking_data,
            geometry_items=geometry_items,
            video_size=video_size,
            scale=scale,
            show_trajectory=show_trajectory,
            show_geometry=show_geometry,
            selected_geometry_names=selected_geometry_names,
            smoothing=smoothing,
            current_frame=current_frame,
            format=format,
        )

        if format.lower() == "svg":
            TrajectoryExportService.render_to_svg(
                tracking_data=tracking_data,
                geometry_items=geometry_items,
                video_size=video_size,
                scale=scale,
                show_trajectory=show_trajectory,
                show_geometry=show_geometry,
                selected_geometry_names=selected_geometry_names,
                smoothing=smoothing,
                current_frame=current_frame,
                output_path=output_path
            )
        else:
            img_format = "JPEG" if format.lower() in ["jpg", "jpeg"] else "PNG"
            quality = 90 if format.lower() in ["jpg", "jpeg"] else -1
            image.save(output_path, img_format, quality)
