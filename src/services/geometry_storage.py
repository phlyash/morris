from pathlib import Path
from typing import List, Dict, Tuple

import cv2

from src.core.mor_parser.morris_file import MorrisFile, StatBlock
from src.core.geometry import Square, Circle, Donut, GeometryType
from src.ui.components.video.graphics_items import EditableGeometryItem


class GeometryStorageService:
    PROJECT_FILE_NAME = ".morproj"

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.morris_dir = self.project_path / ".morris"
        self.morris_dir.mkdir(exist_ok=True)

    def get_video_file_path(self, video_name: str) -> Path:
        return self.morris_dir / f"{video_name}.mor"

    def get_project_file_path(self) -> Path:
        return self.morris_dir / self.PROJECT_FILE_NAME

    # --- НОВЫЙ МЕТОД: МАССОВОЕ ОБНОВЛЕНИЕ ---

    def propagate_base_geometry(self, items: List[EditableGeometryItem]):
        """
        1. Сохраняет настройки в .morproj.
        2. Проходит по всем .mor файлам в папке и заменяет их геометрию на новую базовую.
        При этом трекинг и статусы в файлах сохраняются.
        """
        # 1. Сохраняем шаблон
        self.save_project_settings(items)

        # 2. Подготавливаем список блоков статистики из UI-элементов
        new_stat_blocks = self._create_stat_blocks(items)

        # 3. Проходим по всем .mor файлам (кроме самого шаблона)
        for file_path in self.morris_dir.glob("*.mor"):
            if file_path.name == self.PROJECT_FILE_NAME:
                continue

            try:
                # Загружаем существующий файл
                mor = MorrisFile(str(file_path))
                mor.load()

                # ВАЖНО: Полностью заменяем список геометрий на новый базовый
                # При этом старые значения времени/дистанции сбрасываются в 0.0,
                # так как геометрия изменилась и старая статистика неактуальна.
                # Она пересчитается автоматически при открытии видео или статистики.

                # Однако, мы используем new_stat_blocks как шаблон.
                # StatBlock - это mutable объект? В Python да.
                # Нам нужно создавать НОВЫЕ экземпляры StatBlock для каждого файла,
                # чтобы не было проблем со ссылками.

                file_specific_blocks = self._create_stat_blocks(items)
                mor.stats_blocks = file_specific_blocks

                # Трекинг (mor.sequence) и Метаданные (mor.metadata) остаются нетронутыми

                mor.save()

            except Exception as e:
                pass

    # --- СОХРАНЕНИЕ ---

    def save(self, video_path: Path,
             items: List[EditableGeometryItem],
             tracking_data: Dict[int, tuple] = None,
             zones_stats: Dict[str, dict] = None,
             is_marked_finished: bool = False):

        path = self.get_video_file_path(video_path.stem)
        self._write_to_file(path, items, tracking_data, zones_stats, is_marked_finished)

    def save_project_settings(self, items: List[EditableGeometryItem]):
        path = self.get_project_file_path()
        self._write_to_file(path, items, None, None, False)

    def _write_to_file(self, path: Path,
                       items: List[EditableGeometryItem],
                       tracking_data: Dict[int, tuple],
                       zones_stats: Dict[str, dict] = None,
                       is_marked: bool = False):

        mor_file = MorrisFile(str(path))
        mor_file.set_marked_status(is_marked)

        # Генерируем блоки статистики
        mor_file.stats_blocks = self._create_stat_blocks(items, zones_stats)

        # Трекинг
        if tracking_data:
            sorted_frames = sorted(tracking_data.keys())
            if sorted_frames:
                start_frame = sorted_frames[0]
                current_block = []
                prev_frame = start_frame - 1

                for frame_idx in sorted_frames:
                    if frame_idx != prev_frame + 1:
                        if current_block:
                            mor_file.add_frames(start_frame, current_block)
                        start_frame = frame_idx
                        current_block = []
                    current_block.append(tracking_data[frame_idx])
                    prev_frame = frame_idx

                if current_block:
                    mor_file.add_frames(start_frame, current_block)

        mor_file.save()

    # --- ВСПОМОГАТЕЛЬНЫЙ МЕТОД ---

    def _create_stat_blocks(self, items: List[EditableGeometryItem], zones_stats: Dict[str, dict] = None) -> List[
        StatBlock]:
        blocks = []
        for item in items:
            rect = item.rect
            abs_x = item.x() + rect.x()
            abs_y = item.y() + rect.y()
            w, h = rect.width(), rect.height()

            geometry_data = self._item_to_geometry(item, abs_x, abs_y, w, h)
            is_stat_active = getattr(item, 'is_stat_zone', True)

            # Статистика (если есть)
            t_val, d_val = 0.0, 0.0
            if zones_stats and item.name in zones_stats:
                t_val = zones_stats[item.name].get('time', 0.0)
                d_val = zones_stats[item.name].get('dist', 0.0)

            if geometry_data:
                stat = StatBlock(
                    name=item.name,
                    time=t_val,
                    distance=d_val,
                    geometry=geometry_data,
                    color_hex=item.base_color.name().upper(),
                    alpha=int(item.alpha_percent),
                    is_active=is_stat_active
                )
                blocks.append(stat)
        return blocks

    # --- ЗАГРУЗКА ---

    def load_smart(self, video_path: Path) -> Tuple[List[EditableGeometryItem], Dict[int, tuple], bool]:
        video_mor_path = self.get_video_file_path(video_path.stem)
        if video_mor_path.exists():
            return self._read_from_file(video_mor_path)

        project_mor_path = self.get_project_file_path()
        if project_mor_path.exists():
            items, _, _ = self._read_from_file(project_mor_path)
            return items, {}, False

        return [], {}, False

    def load_project_settings(self) -> List[EditableGeometryItem]:
        path = self.get_project_file_path()
        if not path.exists():
            return []
        items, _, _ = self._read_from_file(path)
        return items

    def get_marked_status(self, video_name: str) -> bool:
        video_stem = Path(video_name).stem
        path = self.get_video_file_path(video_stem)
        if not path.exists(): return False
        try:
            mor = MorrisFile(str(path))
            return mor.load_meta_only()
        except:
            return False

    def _read_from_file(self, path: Path):
        mor_file = MorrisFile(str(path))
        try:
            mor_file.load()
        except Exception as e:
            return [], {}, False

        items = []
        for stat in mor_file.stats_blocks:
            item = self._geometry_to_item(stat.geometry)
            if item:
                item.name = stat.name
                item.set_color_data(stat.color_hex, stat.alpha)
                item.is_stat_zone = getattr(stat, 'is_active', True)
                items.append(item)

        tracking_data = {}
        for block in mor_file.sequence.blocks:
            for i, rect in enumerate(block.rects):
                frame_idx = block.start_frame + i
                tracking_data[frame_idx] = rect

        is_marked = mor_file.get_marked_status()

        return items, tracking_data, is_marked

    # --- CONVERTERS (Оставляем как есть) ---
    def _item_to_geometry(self, item: EditableGeometryItem, x, y, w, h):
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

    def _geometry_to_item(self, g) -> EditableGeometryItem:
        if g.get_type() == GeometryType.SQUARE:
            return EditableGeometryItem(g.x, g.y, g.width, g.height, "square")
        elif g.get_type() == GeometryType.CIRCLE:
            if hasattr(g, 'rx'):
                w, h = g.rx * 2, g.ry * 2
                x, y = g.cx - g.rx, g.cy - g.ry
            else:
                r = getattr(g, 'radius', getattr(g, 'r', 0))
                w, h = r * 2, r * 2
                x, y = g.cx - r, g.cy - r
            return EditableGeometryItem(x, y, w, h, "circle")
        elif g.get_type() == GeometryType.DONUT:
            if hasattr(g, 'rx_out'):
                w, h = g.rx_out * 2, g.ry_out * 2
                x, y = g.cx - g.rx_out, g.cy - g.ry_out
                item = EditableGeometryItem(x, y, w, h, "donut")
                if g.rx_out > 0: item.inner_ratio = g.rx_in / g.rx_out
                return item
            else:
                r_out = getattr(g, 'r_out', getattr(g, 'outer_radius', 0))
                r_in = getattr(g, 'r_in', getattr(g, 'inner_radius', 0))
                item = EditableGeometryItem(g.cx - r_out, g.cy - r_out, 2 * r_out, 2 * r_out, "donut")
                if r_out > 0: item.inner_ratio = r_in / r_out
                return item
        return None

    def get_videos_metadata(self, videos_list) -> dict:
        """
        Возвращает словарь: { "video_name": {"is_marked": bool, "duration": float} }
        """
        metadata = {}

        for video in videos_list:
            stem = video.path.stem
            mor_path = self.get_video_file_path(stem)

            is_marked = False
            # Длительность пока возьмем из cv2 (это может быть медленно при первом запуске)
            # В идеале, длительность стоит кешировать в .morproj или в отдельном json
            duration = 0.0

            # 1. Статус из .mor
            if mor_path.exists():
                try:
                    mor = MorrisFile(str(mor_path))
                    is_marked = mor.load_meta_only()
                except:
                    pass

            # 2. Длительность (быстрый способ через OpenCV)
            try:
                cap = cv2.VideoCapture(str(video.path))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if fps > 0:
                    duration = frames / fps
                cap.release()
            except:
                pass

            metadata[video.path.name] = {
                "is_marked": is_marked,
                "duration": duration
            }

        return metadata