import struct
import math
from enum import Enum
from abc import ABC, abstractmethod


class GeometryType(Enum):
    SQUARE = 0
    CIRCLE = 1  # Теперь работает как Эллипс
    DONUT = 2  # Теперь работает как Эллиптический бублик
    POLY = 3


class Geometry(ABC):
    @abstractmethod
    def get_type(self) -> GeometryType:
        pass

    @abstractmethod
    def serialize(self) -> bytes:
        pass

    @abstractmethod
    def contains(self, x: float, y: float) -> bool:
        pass

    @staticmethod
    def from_bytes(g_type_int: int, data: bytes):
        t = GeometryType(g_type_int)
        if t == GeometryType.SQUARE:
            return Square.deserialize(data)
        elif t == GeometryType.CIRCLE:
            return Circle.deserialize(data)
        elif t == GeometryType.DONUT:
            return Donut.deserialize(data)
        return None


# --- 1. ПРЯМОУГОЛЬНИК (SQUARE) ---
class Square(Geometry):
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.width = w
        self.height = h

    def get_type(self):
        return GeometryType.SQUARE

    def serialize(self):
        # 4 float/double
        return struct.pack('<dddd', self.x, self.y, self.width, self.height)

    @staticmethod
    def deserialize(data):
        return Square(*struct.unpack('<dddd', data))

    def contains(self, px, py):
        return self.x <= px <= self.x + self.width and \
            self.y <= py <= self.y + self.height


# --- 2. ЭЛЛИПС (БЫВШИЙ КРУГ) ---
class Circle(Geometry):
    def __init__(self, cx, cy, rx, ry):
        self.cx = cx
        self.cy = cy
        self.rx = rx
        self.ry = ry

    def get_type(self):
        return GeometryType.CIRCLE

    def serialize(self):
        # Теперь храним 4 значения: центр_x, центр_y, радиус_x, радиус_y
        return struct.pack('<dddd', self.cx, self.cy, self.rx, self.ry)

    @staticmethod
    def deserialize(data):
        return Circle(*struct.unpack('<dddd', data))

    def contains(self, px, py):
        # Формула эллипса: (x-cx)^2/rx^2 + (y-cy)^2/ry^2 <= 1
        if self.rx == 0 or self.ry == 0: return False
        dx = px - self.cx
        dy = py - self.cy
        return (dx * dx) / (self.rx * self.rx) + (dy * dy) / (self.ry * self.ry) <= 1.0


# --- 3. ЭЛЛИПТИЧЕСКИЙ БУБЛИК ---
class Donut(Geometry):
    def __init__(self, cx, cy, rx_out, ry_out, rx_in, ry_in):
        self.cx = cx
        self.cy = cy
        self.rx_out = rx_out
        self.ry_out = ry_out
        self.rx_in = rx_in
        self.ry_in = ry_in

    def get_type(self):
        return GeometryType.DONUT

    def serialize(self):
        # Храним 6 значений: центр(2) + внешние радиусы(2) + внутренние радиусы(2)
        return struct.pack('<dddddd', self.cx, self.cy,
                           self.rx_out, self.ry_out,
                           self.rx_in, self.ry_in)

    @staticmethod
    def deserialize(data):
        return Donut(*struct.unpack('<dddddd', data))

    def contains(self, px, py):
        if self.rx_out == 0 or self.ry_out == 0: return False
        dx = px - self.cx
        dy = py - self.cy

        # Проверка внешнего эллипса
        val_out = (dx * dx) / (self.rx_out * self.rx_out) + (dy * dy) / (self.ry_out * self.ry_out)
        if val_out > 1.0:
            return False

        # Проверка внутреннего эллипса (дырки)
        if self.rx_in > 0 and self.ry_in > 0:
            val_in = (dx * dx) / (self.rx_in * self.rx_in) + (dy * dy) / (self.ry_in * self.ry_in)
            if val_in <= 1.0:  # Попали в дырку
                return False

        return True