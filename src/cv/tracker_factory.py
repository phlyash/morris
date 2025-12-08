from src.cv.csrt_tracker import CSRTTracker
from src.cv.yolo_tracker import YOLOTracker


class TrackerFactory:
    @staticmethod
    def create_tracker(tracker_type: str, **kwargs):
        if tracker_type.lower() == "csrt":
            return CSRTTracker()
        elif tracker_type.lower() == "yolo":
            # Можно прокинуть путь к кастомной модели
            model_path = kwargs.get('model_path', 'yolov8n.pt')
            return YOLOTracker(model_path=model_path)
        else:
            raise ValueError(f"Unknown tracker type: {tracker_type}")
