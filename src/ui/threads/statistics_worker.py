from PySide6.QtCore import QObject, Signal, Slot
from src.services.statistics_service import StatisticsService


class StatisticsWorker(QObject):
    # Сигнал завершения: (global_stats, zones_stats)
    calculation_finished = Signal(dict, dict)

    @Slot(dict, list, float, int)
    def process(self, tracking_data, active_zones, fps, current_frame):
        """
        Этот метод будет выполняться в фоновом потоке.
        """
        try:
            g_stats, z_stats = StatisticsService.calculate(
                tracking_data,
                active_zones,
                fps,
                current_frame
            )
            self.calculation_finished.emit(g_stats, z_stats)
        except Exception as e:
            pass