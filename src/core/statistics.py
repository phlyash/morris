class Statistics:
    _time: float
    _distance: float

    def __init__(self, time=0, distance=0):
        self._time = time
        self._distance = distance

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, time: float):
        if time < 0:
            raise ValueError("Time cannot be negative")
        self._time = time

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, distance: float):
        if distance < 0:
            raise ValueError("Distance cannot be negative")
        self._distance = distance
