import math
from typing import Dict, List, Tuple
from src.core.geometry import Geometry, Square, Circle, Donut
from src.ui.components.video.graphics_items import EditableGeometryItem


class StatisticsService:
    """
    Сервис чистой математики. Не зависит от UI.
    Может работать в любом потоке.
    """

    @staticmethod
    def prepare_geometry_snapshot(items: List[EditableGeometryItem]) -> List[dict]:
        """
        Вспомогательный метод (выполняется в Main Thread).
        Превращает UI объекты в структуры данных для передачи в поток.
        """
        snapshot = []
        for item in items:
            if getattr(item, 'is_stat_zone', True):
                # Конвертация UI -> Math Geometry
                geom = StatisticsService._item_to_geometry(item)
                if geom:
                    snapshot.append({
                        "name": item.name,
                        "geometry": geom,  # Математический объект (thread-safe)
                        "color": item.base_color.name(),
                        "shape": item.shape_type
                    })
        return snapshot

    @staticmethod
    def calculate(tracking_data: Dict[int, tuple],
                  active_zones: List[dict],
                  fps: float,
                  current_frame: int):
        """
        Тяжелые вычисления (выполняется в Worker Thread).
        """
        safe_fps = fps if fps > 0 else 30.0

        global_stats = {
            "total_time": 0.0,
            "total_distance": 0.0
        }

        # Инициализируем нулями
        zones_stats = {}
        for zone in active_zones:
            zones_stats[zone['name']] = {
                "time": 0.0, "dist": 0.0,
                "color": zone['color'], "shape": zone['shape']
            }

        # Сортируем кадры
        sorted_frames = sorted([f for f in tracking_data.keys() if f <= current_frame])
        prev_center = None

        for f_idx in sorted_frames:
            bbox = tracking_data[f_idx]
            cx = bbox[0] + bbox[2] / 2
            cy = bbox[1] + bbox[3] / 2

            step_dist = 0.0
            if prev_center is not None:
                dx = cx - prev_center[0]
                dy = cy - prev_center[1]
                step_dist = math.hypot(dx, dy)

            global_stats["total_distance"] += step_dist
            global_stats["total_time"] += (1.0 / safe_fps)

            # Проверка зон
            for zone in active_zones:
                geom: Geometry = zone['geometry']
                if geom.contains(cx, cy):
                    zones_stats[zone['name']]["time"] += (1.0 / safe_fps)
                    zones_stats[zone['name']]["dist"] += step_dist

            prev_center = (cx, cy)

        return global_stats, zones_stats

    @staticmethod
    def _item_to_geometry(item: EditableGeometryItem):
        """UI -> Math"""
        rect = item.rect
        # Абсолютные координаты сцены
        x = item.x() + rect.x()
        y = item.y() + rect.y()
        w, h = rect.width(), rect.height()

        if item.shape_type == "square":
            return Square(x, y, w, h)
        elif item.shape_type == "circle":
            # Эллипс
            rx, ry = w / 2, h / 2
            return Circle(x + rx, y + ry, rx, ry)
        elif item.shape_type == "donut":
            # Эллиптический бублик
            rx_out, ry_out = w / 2, h / 2
            rx_in = rx_out * item.inner_ratio
            ry_in = ry_out * item.inner_ratio
            return Donut(x + rx_out, y + ry_out, rx_out, ry_out, rx_in, ry_in)

        return None