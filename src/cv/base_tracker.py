from abc import ABC, abstractmethod

import numpy as np


class BaseTracker(ABC):
    """
    Абстрактный базовый класс для всех трекеров.
    Гарантирует, что у CSRT и YOLO будет одинаковый API.
    """

    @abstractmethod
    def init(self, frame: np.ndarray, bbox: tuple):
        """
        Инициализация трекера.
        :param frame: текущий кадр (BGR изображение)
        :param bbox: кортеж (x, y, w, h) - начальная позиция
        """
        pass

    @abstractmethod
    def update(self, frame: np.ndarray):
        """
        Обновление позиции объекта на новом кадре.
        :param frame: новый кадр
        :return: (success, bbox) -> (bool, (x, y, w, h))
        """
        pass

    def get_name(self):
        return self.__class__.__name__
