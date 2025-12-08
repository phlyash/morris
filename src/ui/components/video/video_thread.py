import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from src.core import Video
from src.core.tracker import TrackerWrapper


class VideoThread(QThread):
    # Сигналы
    change_pixmap_signal = Signal(np.ndarray)
    frame_changed_signal = Signal(int)
    tracker_update_signal = Signal(bool, object)  # (success, bbox)
    tracker_loading_signal = Signal(bool)
    tracking_error_signal = Signal(str)

    # СИГНАЛ ДЛЯ ТАЙМЛАЙНА (int frame_idx, object bbox)
    frame_data_updated = Signal(int, object)

    def __init__(self, video: Video):
        super().__init__()
        self.video = video
        self._run_flag = True
        self.is_paused = False

        self.cap = cv2.VideoCapture(self.video.path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps == 0 or np.isnan(self.fps):
            self.fps = 30
        self.delay = int(1000 / self.fps)

        self.tracker = None
        self.is_tracking_active = False
        self.last_frame_buffer = None
        self.is_model_loading = False

        self.tracking_data = {}

    def set_tracker_model(self, model_name: str):
        if model_name not in ["CSRT", "YOLO"]:
            self.tracker = None
            self.is_tracking_active = False
            self.tracker_update_signal.emit(False, None)
            return

        self.is_model_loading = True
        self.tracker_loading_signal.emit(True)
        self.msleep(50)

        try:
            self.tracker = TrackerWrapper(model_name)

            # Проверка: если на текущем кадре уже есть разметка, подхватываем её
            current_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current_idx > 0: current_idx -= 1

            if current_idx in self.tracking_data:
                bbox = self.tracking_data[current_idx]
                if self.last_frame_buffer is not None:
                    clean_bbox = tuple(map(int, bbox))
                    self.tracker.init(self.last_frame_buffer, clean_bbox)
                    self.is_tracking_active = True
                    self.tracker_update_signal.emit(True, clean_bbox)
            else:
                self.is_tracking_active = False

        finally:
            self.is_model_loading = False
            self.tracker_loading_signal.emit(False)

    def init_tracker_manually(self, bbox: tuple):
        """Ручная установка bbox на текущем кадре"""
        if self.tracker is None:
            self.tracker = TrackerWrapper("csrt")

        if self.last_frame_buffer is not None:
            clean_bbox = tuple(map(int, bbox))
            self.tracker.init(self.last_frame_buffer, clean_bbox)
            self.is_tracking_active = True

            # Сохраняем
            save_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            # Корректировка индекса, если мы на паузе (обычно pos указывает на следующий)
            if save_idx > 0: save_idx -= 1
            if save_idx < 0: save_idx = 0

            self.tracking_data[save_idx] = clean_bbox

            # --- ВАЖНО: УВЕДОМЛЯЕМ ТАЙМЛАЙН ---
            self.frame_data_updated.emit(save_idx, clean_bbox)

            self.tracker_update_signal.emit(True, clean_bbox)

    def try_yolo_autostart(self) -> bool:
        if not self.tracker or self.last_frame_buffer is None:
            return False

        success, bbox = self.tracker.update(self.last_frame_buffer)

        if success:
            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            if self.is_paused and current_frame > 0:
                current_frame -= 1

            self.tracking_data[current_frame] = bbox

            # --- УВЕДОМЛЯЕМ ТАЙМЛАЙН ---
            self.frame_data_updated.emit(current_frame, bbox)

            self.is_tracking_active = True
            self.tracker_update_signal.emit(True, bbox)
            return True
        return False

    def try_restore_from_history(self) -> bool:
        if not self.tracker or self.last_frame_buffer is None:
            return False

        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        idx_candidates = [current_frame, current_frame - 1]

        found_bbox = None
        for idx in idx_candidates:
            if idx in self.tracking_data:
                found_bbox = self.tracking_data[idx]
                break

        if found_bbox:
            clean_bbox = tuple(map(int, found_bbox))
            self.tracker.init(self.last_frame_buffer, clean_bbox)
            self.is_tracking_active = True
            self.tracker_update_signal.emit(True, clean_bbox)
            return True
        return False

    def run(self):
        while self._run_flag:
            if not self.is_paused:
                ret, cv_img = self.cap.read()
                if ret:
                    self.last_frame_buffer = cv_img
                    current_frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1

                    if self.is_tracking_active and self.tracker:
                        success, bbox = self.tracker.update(cv_img)

                        if success:
                            self.tracking_data[current_frame_idx] = bbox

                            # --- УВЕДОМЛЯЕМ ТАЙМЛАЙН (Здесь этого не хватало) ---
                            self.frame_data_updated.emit(current_frame_idx, bbox)

                            self.tracker_update_signal.emit(True, bbox)
                        else:
                            # Потеряли объект
                            self.is_tracking_active = False
                            self.tracker_update_signal.emit(False, None)
                            self.is_paused = True
                            self.tracking_error_signal.emit("YOLO потерял объект. Разметка остановлена.")

                    elif current_frame_idx in self.tracking_data:
                        bbox = self.tracking_data[current_frame_idx]
                        self.tracker_update_signal.emit(True, bbox)
                    else:
                        self.tracker_update_signal.emit(False, None)

                    self.change_pixmap_signal.emit(cv_img)
                    self.frame_changed_signal.emit(current_frame_idx)
                else:
                    self.is_paused = True
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                self.msleep(50)

            if not self.is_paused:
                self.msleep(self.delay)

    def seek(self, frame_index):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, cv_img = self.cap.read()
        if ret:
            self.last_frame_buffer = cv_img
            self.change_pixmap_signal.emit(cv_img)
            self.frame_changed_signal.emit(frame_index)

            if frame_index in self.tracking_data:
                bbox = self.tracking_data[frame_index]
                self.tracker_update_signal.emit(True, bbox)
                if self.tracker:
                    clean_bbox = tuple(map(int, bbox))
                    self.tracker.init(cv_img, clean_bbox)
                    self.is_tracking_active = True
            else:
                self.tracker_update_signal.emit(False, None)
                self.is_tracking_active = False
                if self.tracker:
                    self.tracker.reset()

    def prev_frame(self):
        """Шаг назад на 1 кадр"""
        if self.is_paused and self.cap.isOpened():
            current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            target_pos = max(0, current_pos - 2)

            self.seek(target_pos)

    def next_frame(self):
        if self.is_paused and self.cap.isOpened():
            ret, cv_img = self.cap.read()
            if ret:
                self.last_frame_buffer = cv_img
                current_frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1

                if self.is_tracking_active and self.tracker:
                    success, bbox = self.tracker.update(cv_img)
                    if success:
                        self.tracking_data[current_frame_idx] = bbox
                        self.frame_data_updated.emit(current_frame_idx, bbox)  # <--
                        self.tracker_update_signal.emit(True, bbox)
                    else:
                        self.is_tracking_active = False
                        self.tracker_update_signal.emit(False, None)

                elif current_frame_idx in self.tracking_data:
                    bbox = self.tracking_data[current_frame_idx]
                    self.tracker_update_signal.emit(True, bbox)
                    if self.tracker:
                        clean_bbox = tuple(map(int, bbox))
                        self.tracker.init(cv_img, clean_bbox)
                        self.is_tracking_active = True
                else:
                    self.tracker_update_signal.emit(False, None)
                    self.is_tracking_active = False
                    if self.tracker:
                        self.tracker.reset()

                self.change_pixmap_signal.emit(cv_img)
                self.frame_changed_signal.emit(current_frame_idx)

    def stop(self):
        self._run_flag = False
        self.wait()
        self.cap.release()

    def get_tracking_data(self):
        return self.tracking_data

    def set_tracking_data(self, data):
        self.tracking_data = data
