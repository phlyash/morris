import cv2
import numpy as np

from src.config import get_resource_path

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class TrackerWrapper:
    def __init__(self, model_type="csrt", model_path=None):
        if model_path is None:
            self.model_path = get_resource_path("best.pt")
        self.model_type = model_type.lower()
        self.tracker = None
        self.yolo_model = None
        self.last_bbox = None

        if "yolo" in self.model_type:
            if YOLO:
                # Загружаем веса один раз при старте
                self.yolo_model = YOLO(self.model_path)
            else:
                pass

    def reset(self):
        """
        Полный сброс состояния.
        Вызывается при переходе на неразмеченную область.
        """
        self.tracker = None
        self.last_bbox = None

    def init(self, frame: np.ndarray, bbox: tuple):
        """
        Инициализация трекера.
        """
        # --- ИСПРАВЛЕНИЕ ---
        # Принудительно конвертируем в int, чтобы OpenCV не ругался на float
        if bbox:
            bbox = tuple(map(int, bbox))

        self.last_bbox = bbox

        if "csrt" in self.model_type:
            if self.tracker is None:  # Или пересоздаем всегда
                self.tracker = cv2.TrackerCSRT_create()
            else:
                # Для CSRT лучше пересоздавать, но можно попробовать и так
                self.tracker = cv2.TrackerCSRT_create()

            self.tracker.init(frame, bbox)

    def update(self, frame: np.ndarray):
        # --- CSRT ---
        if "csrt" in self.model_type:
            if self.tracker is None:
                return False, None
            success, box = self.tracker.update(frame)
            if success:
                return True, tuple(map(int, box))
            return False, None

        # --- YOLO ---
        elif "yolo" in self.model_type and self.yolo_model:
            # Запускаем детекцию
            results = self.yolo_model(frame, verbose=False, conf=0.3)

            best_bbox = None

            # СЦЕНАРИЙ 1: У нас уже есть объект, за которым следим (last_bbox существует)
            if self.last_bbox is not None:
                best_iou = 0
                # Ищем объект по IoU (геометрическому пересечению)
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        curr_box = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))

                        iou = self._calculate_iou(self.last_bbox, curr_box)
                        if iou > best_iou:
                            best_iou = iou
                            best_bbox = curr_box

                # Если IoU слишком маленький, возможно объект потерян
                if best_bbox is None or best_iou < 0.1:
                    # Возвращаем False, но НЕ сбрасываем last_bbox полностью,
                    # вдруг он появится в следующем кадре рядом.
                    return False, self.last_bbox

            # СЦЕНАРИЙ 2: Мы запускаемся с нуля (last_bbox is None)
            else:
                max_conf = 0
                # Ищем объект с максимальной уверенностью (Confidence)
                for r in results:
                    for box in r.boxes:
                        if box.conf.item() > max_conf:
                            max_conf = box.conf.item()
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            best_bbox = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))

            # Если нашли подходящий объект (в любом из сценариев)
            if best_bbox:
                self.last_bbox = best_bbox
                return True, best_bbox

            return False, None

    def _calculate_iou(self, boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
        yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = boxA[2] * boxA[3]
        boxBArea = boxB[2] * boxB[3]
        denom = float(boxAArea + boxBArea - interArea + 1e-6)
        return interArea / denom