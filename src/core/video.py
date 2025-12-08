from enum import Enum
from pathlib import Path
import os

import cv2
import numpy as np


class VideoExtension(str, Enum):
    MP4 = 'mp4'
    AVI = 'avi'
    MKV = 'mkv'
    MOV = "mov"


class Video:
    _extension: VideoExtension
    _path: Path

    def __init__(self, path: str | os.PathLike):
        self._path = Path(path)
        extension_string = self._path.suffix.lower().lstrip('.')

        try:
            self._extension = VideoExtension(extension_string)
        except ValueError:
            raise ValueError("Неверный формат файла")

    @property
    def extension(self):
        return self._extension

    @property
    def path(self):
        return self._path

    # Make default values for width and height
    def get_preview(self, width=-1, height=-1) -> np.ndarray | None:
        cap = cv2.VideoCapture(str(self.path))

        if not cap.isOpened():
            return None

        ret, frame = cap.read()
        cap.release()

        if not ret:
            return None

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        h, w = frame.shape[:2]
        new_w, new_h = w, h

        if width == -1 and height == -1:
            pass
        elif width != -1 and height != -1:
            new_w, new_h = width, height
        elif width != -1:
            aspect_ratio = w / h
            new_w = width
            new_h = int(width / aspect_ratio)
        elif height != -1:
            aspect_ratio = w / h
            new_h = height
            new_w = int(height * aspect_ratio)

        if (new_w, new_h) != (w, h):
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        return frame
