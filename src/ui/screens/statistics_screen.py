import math
import csv
import cv2
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QPushButton, QFileDialog, QProgressBar, QFrame)
from PySide6.QtGui import QColor, QCursor
from PySide6.QtCore import Qt, QThread, Signal

from src.core.project import Project
from src.core.mor_parser.morris_file import MorrisFile


class StatisticsLoader(QThread):
    progress = Signal(int)
    finished = Signal(list, list)

    def __init__(self, project: Project):
        super().__init__()
        self.project = project

    def run(self):
        rows = []
        all_zone_names = set()
        morris_dir = self.project.path / ".morris"

        if not self.project.videos:
            self.finished.emit([], [])
            return

        total_vids = len(self.project.videos)

        for i, video in enumerate(self.project.videos):
            row_data = {
                "name": video.path.name,
                "is_marked": False,
                "total_time": 0.0,
                "total_dist": 0.0,
                "zones": {}
            }

            mor_path = morris_dir / f"{video.path.stem}.mor"

            if mor_path.exists():
                try:
                    # 1. FPS
                    cap = cv2.VideoCapture(str(video.path))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    if not fps or math.isnan(fps): fps = 30.0
                    cap.release()

                    # 2. Загрузка
                    mor = MorrisFile(str(mor_path))
                    mor.load()

                    # 3. ПОДГОТОВКА ДАННЫХ ДЛЯ РАСЧЕТА
                    # Собираем все активные зоны из файла
                    active_zones = []
                    for stat in mor.stats_blocks:
                        # stat.geometry - это математический объект (Square, Circle...), у него есть метод contains
                        if getattr(stat, 'is_active', True):
                            all_zone_names.add(stat.name)
                            active_zones.append({
                                "name": stat.name,
                                "geom": stat.geometry,
                                "time": 0.0,
                                "dist": 0.0
                            })

                    # 4. ПРОХОД ПО ТРЕКИНГУ И РАСЧЕТ НА ЛЕТУ
                    total_dist = 0.0
                    total_frames = 0
                    prev_center = None
                    frame_time = 1.0 / fps

                    for block in mor.sequence.blocks:
                        total_frames += len(block.rects)
                        for rect in block.rects:
                            # rect = (x, y, w, h)
                            cx = rect[0] + rect[2] / 2
                            cy = rect[1] + rect[3] / 2

                            step_dist = 0.0
                            if prev_center:
                                step_dist = math.hypot(cx - prev_center[0], cy - prev_center[1])
                                total_dist += step_dist

                            # --- ПРОВЕРКА ЗОН ---
                            for zone in active_zones:
                                if zone["geom"].contains(cx, cy):
                                    zone["time"] += frame_time
                                    zone["dist"] += step_dist

                            prev_center = (cx, cy)

                        # Разрыв блока
                        prev_center = None

                    # 5. ЗАПИСЬ РЕЗУЛЬТАТОВ
                    row_data["is_marked"] = mor.get_marked_status()
                    row_data["total_time"] = total_frames / fps
                    row_data["total_dist"] = total_dist

                    for zone in active_zones:
                        row_data["zones"][zone["name"]] = {
                            "time": zone["time"],
                            "dist": zone["dist"]
                        }

                except Exception as e:
                    print(f"Error calculating stats for {mor_path}: {e}")

            rows.append(row_data)
            self.progress.emit(int((i + 1) / total_vids * 100))

        sorted_zones = sorted(list(all_zone_names))
        self.finished.emit(rows, sorted_zones)


class ProjectStatisticsWidget(QWidget):
    video_requested = Signal(str)

    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.rows_data = []
        self.zone_columns = []
        self.loader = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setSpacing(20)

        # --- HEADER ---
        header = QHBoxLayout()

        lbl_title = QLabel("Статистика проекта")
        lbl_title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        header.addWidget(lbl_title)
        header.addStretch()

        btn_style = """
            QPushButton { 
                background-color: #3B3C40; color: white; padding: 8px 15px; 
                border: 1px solid #555; border-radius: 4px; font-size: 13px;
            }
            QPushButton:hover { background-color: #45464a; }
            QPushButton:pressed { background-color: #2d2d30; }
            QPushButton:disabled { color: #666; border-color: #444; }
        """

        self.btn_refresh = QPushButton("↻ Обновить")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet(btn_style)
        self.btn_refresh.clicked.connect(self.refresh_data)
        header.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("⤓ Экспорт CSV")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setStyleSheet(btn_style)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_export.setEnabled(False)
        header.addWidget(self.btn_export)

        layout.addLayout(header)

        # --- TABLE ---
        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setFocusPolicy(Qt.NoFocus)  # Убираем фокус с таблицы, чтобы не было рамок

        # ИСПРАВЛЕННЫЙ СТИЛЬ:
        # 1. outline: 0 - убирает пунктирную рамку фокуса
        # 2. selection-background-color - задает нормальный цвет выделения вместо желтого
        self.table.setStyleSheet("""
            QTableWidget { 
                background-color: #252526; 
                border: 1px solid #3e3e42; 
                color: #ccc;
                gridline-color: #3e3e42;
                alternate-background-color: #2a2a2e;
                outline: 0; 
                selection-background-color: #444448;
                selection-color: white;
            }
            QHeaderView::section { 
                background-color: #333; 
                color: white; 
                padding: 6px; 
                border: none; 
                font-weight: bold;
                border-right: 1px solid #3e3e42;
            }
            QTableWidget::item { padding: 5px; }
        """)

        self.table.setFocusPolicy(Qt.NoFocus)

        self.table.cellDoubleClicked.connect(self._on_table_clicked)

        layout.addWidget(self.table)

        # --- PROGRESS ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        # Сменил цвет чанка на зеленый (#00FF00) или нейтральный, чтобы не раздражал.
        # Если хотите желтый, верните #d4b765.
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #333; border: none; } 
            QProgressBar::chunk { background: #d4b765; } 
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Автозагрузка
        self.refresh_data()

    def _on_table_clicked(self, row, col):
        """Обработка клика по ячейке"""
        # Если кликнули по первой колонке (Имя видео)
        if col == 0:
            item = self.table.item(row, 0)
            if item:
                video_name = item.text()
                self.video_requested.emit(video_name)

    def refresh_data(self):
        if self.loader is not None:
            if self.loader.isRunning():
                self.loader.requestInterruption()
                self.loader.wait()
            self.loader.deleteLater()  # Удаляем объект C++
            self.loader = None

        self.loader = StatisticsLoader(self.project)  # Создаем новый

        self.btn_refresh.setEnabled(False)
        self.btn_export.setEnabled(False)

        # ИСПРАВЛЕНИЕ: Не сбрасываем колонки в 0, чтобы таблица не схлопывалась
        self.table.setRowCount(0)
        # self.table.setColumnCount(0) <-- ЭТО БЫЛО ПРИЧИНОЙ МЕРЦАНИЯ ЛЕЙАУТА

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.loader = StatisticsLoader(self.project)
        self.loader.progress.connect(self.progress_bar.setValue)
        self.loader.finished.connect(self._on_data_loaded)
        self.loader.start()

    def _on_data_loaded(self, rows, unique_zones):
        self.rows_data = rows
        self.zone_columns = unique_zones

        # 1. Заголовки
        headers = ["Видео", "Размечено", "Время (общ)", "Дист. (общ)"]
        for zone_name in unique_zones:
            headers.append(f"Время ({zone_name})")
            headers.append(f"Дист. ({zone_name})")

        # Устанавливаем колонки один раз
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        # 2. Заполнение
        self.table.setRowCount(len(rows))

        for i, row in enumerate(rows):
            col = 0

            # Видео
            name_item = QTableWidgetItem(row['name'])
            # Стилизуем как ссылку (синий, подчеркнутый, курсор-рука)
            name_item.setForeground(QColor("#4a90e2"))
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable) # Разрешаем выделение
            self.table.setItem(i, col, name_item)
            col += 1

            # Статус
            status_txt = "Да" if row['is_marked'] else "Нет"
            item_status = QTableWidgetItem(status_txt)
            if row['is_marked']:
                item_status.setForeground(QColor("#00FF00"))
            else:
                item_status.setForeground(QColor("#666"))
            item_status.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, col, item_status)
            col += 1

            # Общие
            self.table.setItem(i, col, QTableWidgetItem(f"{row['total_time']:.2f}"));
            col += 1
            self.table.setItem(i, col, QTableWidgetItem(f"{row['total_dist']:.0f}"));
            col += 1

            # Зоны
            for zone_name in unique_zones:
                if zone_name in row['zones']:
                    z_data = row['zones'][zone_name]
                    t_val = f"{z_data['time']:.2f}"
                    d_val = f"{z_data['dist']:.0f}"
                else:
                    t_val, d_val = "-", "-"

                self.table.setItem(i, col, QTableWidgetItem(t_val));
                col += 1
                self.table.setItem(i, col, QTableWidgetItem(d_val));
                col += 1

        # Ресайз
        header = self.table.horizontalHeader()
        if self.table.columnCount() > 0:
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            for c in range(1, self.table.columnCount()):
                header.setSectionResizeMode(c, QHeaderView.ResizeToContents)

        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self.btn_export.setEnabled(True)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт статистики", "", "CSV Files (*.csv)")
        if not path: return

        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')

                headers = ["Video", "Is Marked", "Total Time", "Total Distance"]
                for zone in self.zone_columns:
                    headers.append(f"Time [{zone}]")
                    headers.append(f"Dist [{zone}]")
                writer.writerow(headers)

                for row in self.rows_data:
                    csv_row = [
                        row['name'],
                        "Yes" if row['is_marked'] else "No",
                        f"{row['total_time']:.3f}".replace('.', ','),
                        f"{row['total_dist']:.3f}".replace('.', ',')
                    ]

                    for zone_name in self.zone_columns:
                        if zone_name in row['zones']:
                            z_data = row['zones'][zone_name]
                            csv_row.append(f"{z_data['time']:.3f}".replace('.', ','))
                            csv_row.append(f"{z_data['dist']:.3f}".replace('.', ','))
                        else:
                            csv_row.append("0")
                            csv_row.append("0")

                    writer.writerow(csv_row)

        except Exception as e:
            pass

    def cleanup(self):
        if self.loader is not None and self.loader.isRunning():
            self.loader.requestInterruption()
            self.loader.wait()
