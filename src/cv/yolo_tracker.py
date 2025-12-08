from src.cv.base_tracker import BaseTracker

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class YOLOTracker(BaseTracker):
    def __init__(self, model_path='yolov8n.pt'):
        if YOLO is None: raise ImportError("Install ultralytics: pip install ultralytics")
        self.model = YOLO(model_path)
        self.last_bbox = None

    def init(self, frame, bbox):
        self.last_bbox = bbox  # Просто запоминаем, что искать

    def update(self, frame):
        if self.last_bbox is None: return False, (0, 0, 0, 0)
        # Упрощенная логика: ищем объект с максимальным IoU с предыдущим кадром
        results = self.model(frame, verbose=False, conf=0.3)
        best_iou = 0
        best_bbox = self.last_bbox
        found = False

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                curr_box = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                iou = self._get_iou(self.last_bbox, curr_box)
                if iou > best_iou:
                    best_iou = iou
                    best_bbox = curr_box
                    found = True

        if found or best_iou > 0.1:
            self.last_bbox = best_bbox
            return True, best_bbox
        return False, self.last_bbox

    def _get_iou(self, boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
        yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = boxA[2] * boxA[3]
        boxBArea = boxB[2] * boxB[3]
        return interArea / float(boxAArea + boxBArea - interArea + 1e-6)
