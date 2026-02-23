import cv2
import numpy as np

from src.config import get_resource_path


class ONNXTracker:
    def __init__(self, model_path, conf_threshold=0.3):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.net = None
        self.input_size = (640, 640)
        self.last_bbox = None
        self._load_model()

    def _load_model(self):
        self.net = cv2.dnn.readNet(self.model_path)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    def _preprocess(self, frame):
        blob = cv2.dnn.blobFromImage(
            frame, 1/255.0, self.input_size, swapRB=True, crop=False
        )
        return blob

    def _postprocess(self, outputs, orig_shape):
        output = np.array(outputs[0])
        
        if output.shape[0] == 1:
            output = output[0]
        
        bboxes = []
        confs = []
        
        for detection in output.T:
            if len(detection) < 5:
                continue
            
            cx, cy, w, h, obj_conf = detection[:5]
            
            if obj_conf < self.conf_threshold:
                continue
            
            x = cx - w/2
            y = cy - h/2
            
            bboxes.append([x, y, w, h])
            confs.append(float(obj_conf))
        
        if not bboxes:
            return None, None
        
        indices = cv2.dnn.NMSBoxes(
            bboxes, confs, self.conf_threshold, 0.45
        )
        
        if len(indices) > 0:
            i = indices[0]
            bbox = bboxes[i]
            conf = confs[i]
            return bbox, conf
        
        return None, None

    def detect(self, frame):
        blob = self._preprocess(frame)
        self.net.setInput(blob)
        outputs = self.net.forward(self.net.getUnconnectedOutLayersNames())
        
        orig_h, orig_w = frame.shape[:2]
        scale_x = orig_w / self.input_size[0]
        scale_y = orig_h / self.input_size[1]
        
        bbox, conf = self._postprocess(outputs, (orig_h, orig_w))
        
        if bbox:
            x, y, w, h = bbox
            x = x * scale_x
            y = y * scale_y
            w = w * scale_x
            h = h * scale_y
            return True, (int(x), int(y), int(w), int(h))
        
        return False, None


class TrackerWrapper:
    def __init__(self, model_type="csrt", model_path=None):
        if model_path is None:
            self.model_path = str(get_resource_path("best.onnx"))
        else:
            self.model_path = model_path
            
        self.model_type = model_type.lower()
        self.tracker = None
        self.onnx_tracker = None
        self.last_bbox = None

        if "yolo" in self.model_type:
            try:
                self.onnx_tracker = ONNXTracker(self.model_path)
            except Exception as e:
                print(f"Failed to load ONNX model: {e}")
                self.onnx_tracker = None

    def reset(self):
        self.tracker = None
        self.last_bbox = None

    def init(self, frame: np.ndarray, bbox: tuple):
        if bbox:
            bbox = tuple(map(int, bbox))

        self.last_bbox = bbox

        if "csrt" in self.model_type:
            if self.tracker is None:
                self.tracker = cv2.TrackerCSRT_create()
            else:
                self.tracker = cv2.TrackerCSRT_create()

            self.tracker.init(frame, bbox)

    def update(self, frame: np.ndarray):
        if "csrt" in self.model_type:
            if self.tracker is None:
                return False, None
            success, box = self.tracker.update(frame)
            if success:
                return True, tuple(map(int, box))
            return False, None

        elif "yolo" in self.model_type and self.onnx_tracker:
            if self.last_bbox is not None:
                best_bbox = None
                best_iou = 0
                
                success, det_bbox = self.onnx_tracker.detect(frame)
                
                if success:
                    iou = self._calculate_iou(self.last_bbox, det_bbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_bbox = det_bbox
                
                if best_bbox is None or best_iou < 0.1:
                    return False, self.last_bbox
                
                self.last_bbox = best_bbox
                return True, best_bbox
            else:
                success, det_bbox = self.onnx_tracker.detect(frame)
                
                if success:
                    self.last_bbox = det_bbox
                    return True, det_bbox
                
                return False, None

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
