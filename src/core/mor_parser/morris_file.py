import struct
from pathlib import Path
from typing import List
from src.core.geometry import Geometry

from src.core.mor_parser.types import DataType, MAGIC_BYTE, VERSION, BlockType
from src.core.mor_parser.frame_block import Rect, FrameSequence, FrameBlock


class StatBlock:
    def __init__(self, name: str, time: float, distance: float, geometry: Geometry,
                 color_hex: str = "#FFDD78", alpha: int = 100, is_active: bool = True):
        self.name = name
        self.time = time
        self.distance = distance
        self.geometry = geometry
        self.color_hex = color_hex
        self.alpha = alpha
        self.is_active = is_active


class MorrisFile:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.coord_type = DataType.FLOAT
        self.sequence = FrameSequence()
        self.stats_blocks: List[StatBlock] = []

        # Хранилище метаданных
        # Ключ (int 0-255) -> Значение (bool)
        # 1 = IsMarked
        self.metadata = {}

    def set_coordinate_format(self, dtype: DataType):
        self.coord_type = dtype

    # --- API Управления данными ---

    def add_frames(self, start_frame: int, rects: List[Rect]):
        """Добавляет кадры в умный менеджер"""
        self.sequence.add_frames(start_frame, rects)

    def add_stat(self, stat: StatBlock):
        self.stats_blocks.append(stat)

    def set_marked_status(self, is_marked: bool):
        """Установить статус 'Размечено полностью'"""
        self.metadata[1] = is_marked

    def get_marked_status(self) -> bool:
        """Получить статус 'Размечено полностью'"""
        return self.metadata.get(1, False)

    def get_sequence(self) -> FrameSequence:
        """Получить доступ к менеджеру кадров"""
        return self.sequence

    # --- I/O ---

    def save(self):
        with open(self.filepath, 'wb') as f:
            # 1. Header
            f.write(struct.pack('<BBQ B', MAGIC_BYTE, VERSION, 0, self.coord_type.value))
            start_pos = f.tell()

            fmt_char = self.coord_type.to_struct_fmt()
            rect_pack_fmt = f'<{4}{fmt_char}'

            # 2. Frames Block
            for block in self.sequence.blocks:
                f.write(struct.pack('B', BlockType.FRAMES.value))
                count = len(block.rects)
                f.write(struct.pack('<III', block.start_frame, block.end_frame, count))
                for rect in block.rects:
                    f.write(struct.pack(rect_pack_fmt, *rect))

            # 3. Stats Block (Геометрия)
            for stat in self.stats_blocks:
                f.write(struct.pack('B', BlockType.STATS.value))

                # Name
                name_bytes = stat.name.encode('utf-8')
                f.write(struct.pack('<H', len(name_bytes)))
                f.write(name_bytes)

                # Metrics
                f.write(struct.pack('<dd', stat.time, stat.distance))

                # Color & Alpha
                col_bytes = stat.color_hex.encode('utf-8')
                f.write(struct.pack('<H', len(col_bytes)))
                f.write(col_bytes)
                f.write(struct.pack('B', int(stat.alpha)))

                # Flag Active
                f.write(struct.pack('B', 1 if stat.is_active else 0))

                # Geometry Data
                geom_bytes = stat.geometry.serialize()
                f.write(struct.pack('<B H', stat.geometry.get_type().value, len(geom_bytes)))
                f.write(geom_bytes)

            # 4. Metadata Block (Статусы проекта)
            if self.metadata:
                f.write(struct.pack('B', BlockType.METADATA.value))

                # Кол-во записей (1 байт, до 255 ключей)
                f.write(struct.pack('B', len(self.metadata)))

                for key, val in self.metadata.items():
                    # Формат записи: Key(1B) + Value(1B)
                    # Пока поддерживаем только boolean флаги
                    f.write(struct.pack('B', key))
                    val_int = 1 if val else 0
                    f.write(struct.pack('B', val_int))

            # 5. Finalize size
            end_pos = f.tell()
            total_size = end_pos - start_pos
            f.seek(2)
            f.write(struct.pack('<Q', total_size))

    def load(self):
        self.sequence = FrameSequence()
        self.stats_blocks = []
        self.metadata = {}

        if not Path(self.filepath).exists():
            return

        with open(self.filepath, 'rb') as f:
            # Header
            header = f.read(11)
            if len(header) < 11: return
            magic, ver, size, dtype_val = struct.unpack('<BBQ B', header)
            if magic != MAGIC_BYTE: raise ValueError("Invalid magic")

            self.coord_type = DataType(dtype_val)
            rect_fmt = f'<{4}{self.coord_type.to_struct_fmt()}'
            rect_byte_size = 4 * self.coord_type.get_size()

            while True:
                b_type = f.read(1)
                if not b_type: break
                block_type = BlockType(ord(b_type))

                if block_type == BlockType.FRAMES:
                    meta = f.read(12)
                    start, end, count = struct.unpack('<III', meta)
                    rects = []
                    for _ in range(count):
                        rects.append(struct.unpack(rect_fmt, f.read(rect_byte_size)))
                    self.sequence._blocks.append(FrameBlock(start, rects))

                elif block_type == BlockType.STATS:
                    # Name
                    name_len_data = f.read(2)
                    if not name_len_data: break
                    name_len = struct.unpack('<H', name_len_data)[0]
                    name = f.read(name_len).decode('utf-8')

                    # Metrics
                    time_val, dist_val = struct.unpack('<dd', f.read(16))

                    # Color
                    col_len_data = f.read(2)
                    col_len = struct.unpack('<H', col_len_data)[0]
                    color_hex = f.read(col_len).decode('utf-8')
                    alpha = struct.unpack('B', f.read(1))[0]

                    # Active Flag
                    is_active_byte = f.read(1)
                    if is_active_byte:
                        is_active = bool(struct.unpack('B', is_active_byte)[0])
                    else:
                        is_active = True

                    # Geometry
                    g_type_data = f.read(1)
                    if not g_type_data: break
                    g_type = struct.unpack('B', g_type_data)[0]

                    g_len_data = f.read(2)
                    g_len = struct.unpack('<H', g_len_data)[0]
                    g_data = f.read(g_len)
                    geom = Geometry.from_bytes(g_type, g_data)

                    self.stats_blocks.append(StatBlock(name, time_val, dist_val, geom, color_hex, alpha, is_active))

                elif block_type == BlockType.METADATA:
                    # Читаем кол-во записей
                    count_byte = f.read(1)
                    if not count_byte: break
                    count = struct.unpack('B', count_byte)[0]

                    for _ in range(count):
                        key_byte = f.read(1)
                        val_byte = f.read(1)
                        if key_byte and val_byte:
                            key = struct.unpack('B', key_byte)[0]
                            val = struct.unpack('B', val_byte)[0]
                            self.metadata[key] = bool(val)

    def load_meta_only(self) -> bool:
        """
        Читает файл и возвращает статус IsMarked (metadata[1]).
        Пропускает тяжелые блоки FRAMES.
        """
        if not Path(self.filepath).exists(): return False

        is_marked = False

        with open(self.filepath, 'rb') as f:
            # Header (11 bytes)
            header = f.read(11)
            if len(header) < 11: return False

            # Читаем блоки
            while True:
                b_type_byte = f.read(1)
                if not b_type_byte: break
                block_type = BlockType(ord(b_type_byte))

                if block_type == BlockType.FRAMES:
                    # Пропускаем блок FRAMES
                    # Формат: Start(4), End(4), Count(4) + Count * RectSize
                    meta = f.read(12)
                    _, _, count = struct.unpack('<III', meta)
                    # RectSize = 4 * sizeof(datatype)
                    rect_size = 4 * self.coord_type.get_size()
                    # Прыгаем вперед
                    f.seek(count * rect_size, 1)  # 1 = from current position

                elif block_type == BlockType.STATS:
                    # Пропускаем блок STATS
                    # Name
                    name_len = struct.unpack('<H', f.read(2))[0]
                    f.seek(name_len, 1)
                    # Metrics (16) + ColorLen(2)
                    f.seek(16, 1)
                    col_len = struct.unpack('<H', f.read(2))[0]
                    f.seek(col_len + 1, 1)  # +1 alpha
                    # Active(1)
                    f.seek(1, 1)
                    # Geometry
                    f.seek(1, 1)  # type
                    g_len = struct.unpack('<H', f.read(2))[0]
                    f.seek(g_len, 1)

                elif block_type == BlockType.METADATA:
                    # ЧИТАЕМ!
                    count = struct.unpack('B', f.read(1))[0]
                    for _ in range(count):
                        key = struct.unpack('B', f.read(1))[0]
                        val = struct.unpack('B', f.read(1))[0]
                        if key == 1:  # IsMarked
                            is_marked = bool(val)
                    # Можно выходить, если нашли
                    return is_marked

        return is_marked
