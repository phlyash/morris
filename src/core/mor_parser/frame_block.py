from typing import List, Tuple, Optional
import bisect

# Тип данных для прямоугольника: (x, y, w, h)
Rect = Tuple[float, float, float, float]


class FrameBlock:
    """Блок непрерывных кадров в памяти"""

    def __init__(self, start_frame: int, rects: List[Rect]):
        self.start_frame = start_frame
        self.rects = rects  # List of tuples (x,y,w,h)

    @property
    def end_frame(self) -> int:
        return self.start_frame + len(self.rects) - 1


class FrameSequence:
    """Менеджер для объединения и разрезания блоков"""

    def __init__(self):
        self._blocks: List[FrameBlock] = []

    @property
    def blocks(self) -> List[FrameBlock]:
        return self._blocks

    def add_frames(self, start_frame: int, rects: List[Rect]):
        if not rects: return
        end_frame = start_frame + len(rects) - 1

        # 1. Удаляем старые данные в этом диапазоне (разрезаем блоки)
        self._clear_range(start_frame, end_frame)

        # 2. Вставляем новый блок
        new_block = FrameBlock(start_frame, rects)
        idx = bisect.bisect_left([b.start_frame for b in self._blocks], start_frame)
        self._blocks.insert(idx, new_block)

        # 3. Склеиваем соседей
        self._merge_blocks()

    def get_rect(self, frame_index: int) -> Optional[Rect]:
        idx = bisect.bisect_right([b.start_frame for b in self._blocks], frame_index)
        if idx > 0:
            block = self._blocks[idx - 1]
            if block.start_frame <= frame_index <= block.end_frame:
                return block.rects[frame_index - block.start_frame]
        return None

    def _clear_range(self, start: int, end: int):
        to_remove_indices = []
        to_add_blocks = []

        for i, block in enumerate(self._blocks):
            if block.end_frame < start: continue
            if block.start_frame > end: break  # Т.к. отсортированы

            to_remove_indices.append(i)

            # Case: Split (блок шире диапазона с обеих сторон)
            if block.start_frame < start and block.end_frame > end:
                left_len = start - block.start_frame
                to_add_blocks.append(FrameBlock(block.start_frame, block.rects[:left_len]))
                right_offset = (end - block.start_frame) + 1
                to_add_blocks.append(FrameBlock(end + 1, block.rects[right_offset:]))
                continue

            # Case: Cut Right
            if block.start_frame < start:
                new_len = start - block.start_frame
                to_add_blocks.append(FrameBlock(block.start_frame, block.rects[:new_len]))
                continue

            # Case: Cut Left
            if block.end_frame > end:
                offset = (end - block.start_frame) + 1
                to_add_blocks.append(FrameBlock(end + 1, block.rects[offset:]))
                continue

        if to_remove_indices:
            min_idx, max_idx = min(to_remove_indices), max(to_remove_indices)
            del self._blocks[min_idx: max_idx + 1]

            # Вставляем огрызки обратно
            # Сортируем, чтобы insert прошел корректно (хотя они и так в порядке)
            for b in reversed(to_add_blocks):
                self._blocks.insert(min_idx, b)
            self._blocks.sort(key=lambda b: b.start_frame)

    def _merge_blocks(self):
        if not self._blocks: return
        merged = [self._blocks[0]]
        for curr in self._blocks[1:]:
            last = merged[-1]
            if last.end_frame + 1 == curr.start_frame:
                last.rects.extend(curr.rects)
            else:
                merged.append(curr)
        self._blocks = merged
