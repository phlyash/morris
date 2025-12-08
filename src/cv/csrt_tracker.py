import cv2

from src.cv.base_tracker import BaseTracker


class CSRTTracker(BaseTracker):
    """
    Классический трекер из OpenCV.
    Плюсы: Точный для медленных движений, не требует GPU.
    Минусы: Теряется при резких движениях, не восстанавливается сам.
    """

    def __init__(self):
        self.tracker = None

    def init(self, frame, bbox):
        # В OpenCV трекеры нужно пересоздавать при новой инициализации
        self.tracker = cv2.TrackerCSRT_create()
        self.tracker.init(frame, bbox)

    def update(self, frame):
        if self.tracker is None:
            return False, (0, 0, 0, 0)

        success, bbox = self.tracker.update(frame)
        # OpenCV возвращает float, приводим к int для удобства UI
        if success:
            bbox = tuple(map(int, bbox))
        return success, bbox
