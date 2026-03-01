import csv
import math
from pathlib import Path

import cv2
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.mor_parser.morris_file import MorrisFile
from src.core.project import Project


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
        project_sf = self.project.scale_factor

        for i, video in enumerate(self.project.videos):
            # Per-video масштаб
            scale_file = morris_dir / f"{video.path.stem}.scale"
            if scale_file.exists():
                try:
                    sf = float(scale_file.read_text().strip())
                except (ValueError, OSError):
                    sf = project_sf
            else:
                sf = project_sf

            calibrated = sf > 0

            row_data = {
                "name": video.path.name,
                "is_marked": False,
                "total_time": 0.0,
                "total_dist": None,
                "zones": {},
            }

            mor_path = morris_dir / f"{video.path.stem}.mor"

            if mor_path.exists():
                try:
                    cap = cv2.VideoCapture(str(video.path))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    if not fps or math.isnan(fps):
                        fps = 30.0
                    cap.release()

                    mor = MorrisFile(str(mor_path))
                    mor.load()

                    active_zones = []
                    for stat in mor.stats_blocks:
                        if getattr(stat, "is_active", True):
                            all_zone_names.add(stat.name)
                            active_zones.append(
                                {
                                    "name": stat.name,
                                    "geom": stat.geometry,
                                    "time": 0.0,
                                    "dist_px": 0.0,
                                }
                            )

                    total_dist_px = 0.0
                    total_frames = 0
                    prev_center = None
                    frame_time = 1.0 / fps

                    for block in mor.sequence.blocks:
                        total_frames += len(block.rects)
                        for rect in block.rects:
                            cx = rect[0] + rect[2] / 2
                            cy = rect[1] + rect[3] / 2
                            step_dist = 0.0
                            if prev_center:
                                step_dist = math.hypot(
                                    cx - prev_center[0], cy - prev_center[1]
                                )
                                total_dist_px += step_dist
                            for zone in active_zones:
                                if zone["geom"].contains(cx, cy):
                                    zone["time"] += frame_time
                                    zone["dist_px"] += step_dist
                            prev_center = (cx, cy)
                        prev_center = None

                    row_data["is_marked"] = mor.get_marked_status()
                    row_data["total_time"] = total_frames / fps

                    if calibrated:
                        row_data["total_dist"] = total_dist_px / sf
                    else:
                        row_data["total_dist"] = None

                    for zone in active_zones:
                        zone_time = zone["time"]
                        if calibrated:
                            zone_dist = zone["dist_px"] / sf
                        else:
                            zone_dist = None

                        pct_time = (
                            (zone_time / row_data["total_time"] * 100)
                            if row_data["total_time"] > 0
                            else 0
                        )
                        if (
                            calibrated
                            and row_data["total_dist"]
                            and row_data["total_dist"] > 0
                        ):
                            pct_dist = zone_dist / row_data["total_dist"] * 100
                        else:
                            pct_dist = None

                        row_data["zones"][zone["name"]] = {
                            "time": zone_time,
                            "dist": zone_dist,
                            "pct_time": pct_time,
                            "pct_dist": pct_dist,
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
        self.table.setFocusPolicy(Qt.NoFocus)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #252526; border: 1px solid #3e3e42;
                color: #ccc; gridline-color: #3e3e42;
                alternate-background-color: #2a2a2e;
                outline: 0; selection-background-color: #444448; selection-color: white;
            }
            QHeaderView::section {
                background-color: #333; color: white; padding: 6px;
                border: none; font-weight: bold; border-right: 1px solid #3e3e42;
            }
            QTableWidget::item { padding: 5px; }
        """)

        self.table.cellDoubleClicked.connect(self._on_table_clicked)
        layout.addWidget(self.table)

        # --- PROGRESS ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #333; border: none; }
            QProgressBar::chunk { background: #d4b765; }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.refresh_data()

    def _on_table_clicked(self, row, col):
        if col == 0:
            item = self.table.item(row, 0)
            if item:
                self.video_requested.emit(item.text())

    def refresh_data(self):
        if self.loader is not None:
            if self.loader.isRunning():
                self.loader.requestInterruption()
                self.loader.wait()
            self.loader.deleteLater()
            self.loader = None

        self.btn_refresh.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.table.setRowCount(0)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.loader = StatisticsLoader(self.project)
        self.loader.progress.connect(self.progress_bar.setValue)
        self.loader.finished.connect(self._on_data_loaded)
        self.loader.start()

    @staticmethod
    def _fmt_dist(val):
        """Форматирует дистанцию: None → '-', число → '1.23'"""
        if val is None:
            return "-"
        return f"{val:.2f}"

    @staticmethod
    def _fmt_pct(val):
        if val is None:
            return "-"
        return f"{val:.1f}"

    def _on_data_loaded(self, rows, unique_zones):
        self.rows_data = rows
        self.zone_columns = unique_zones

        calibrated = self.project.is_calibrated

        # Заголовки
        dist_label = "Дист., м" if calibrated else "Дист."
        headers = ["Видео", "Размечено", "Время, с", dist_label]
        for z in unique_zones:
            headers.append(f"Время, с ({z})")
            headers.append(f"{'Дист., м' if calibrated else 'Дист.'} ({z})")
            headers.append(f"Время, % ({z})")
            headers.append(f"{'Дист., %' if calibrated else 'Дист., %'} ({z})")

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))

        for i, row in enumerate(rows):
            col = 0

            name_item = QTableWidgetItem(row["name"])
            name_item.setForeground(QColor("#4a90e2"))
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(i, col, name_item)
            col += 1

            status_txt = "Да" if row["is_marked"] else "Нет"
            item_status = QTableWidgetItem(status_txt)
            item_status.setForeground(
                QColor("#00FF00") if row["is_marked"] else QColor("#666")
            )
            item_status.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, col, item_status)
            col += 1

            self.table.setItem(i, col, QTableWidgetItem(f"{row['total_time']:.2f}"))
            col += 1

            self.table.setItem(
                i, col, QTableWidgetItem(self._fmt_dist(row["total_dist"]))
            )
            col += 1

            for zone_name in unique_zones:
                if zone_name in row["zones"]:
                    z = row["zones"][zone_name]
                    self.table.setItem(i, col, QTableWidgetItem(f"{z['time']:.2f}"))
                    col += 1
                    self.table.setItem(
                        i, col, QTableWidgetItem(self._fmt_dist(z["dist"]))
                    )
                    col += 1
                    self.table.setItem(i, col, QTableWidgetItem(f"{z['pct_time']:.1f}"))
                    col += 1
                    self.table.setItem(
                        i, col, QTableWidgetItem(self._fmt_pct(z["pct_dist"]))
                    )
                    col += 1
                else:
                    for _ in range(4):
                        self.table.setItem(i, col, QTableWidgetItem("-"))
                        col += 1

        h = self.table.horizontalHeader()
        if self.table.columnCount() > 0:
            h.setSectionResizeMode(0, QHeaderView.Stretch)
            for c in range(1, self.table.columnCount()):
                h.setSectionResizeMode(c, QHeaderView.ResizeToContents)

        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self.btn_export.setEnabled(True)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт статистики", "", "CSV Files (*.csv)"
        )
        if not path:
            return

        calibrated = self.project.is_calibrated
        dist_h = "Distance (m)" if calibrated else "Distance"

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")

                headers = ["Video", "Is Marked", "Total Time (s)", f"Total {dist_h}"]
                for z in self.zone_columns:
                    headers.append(f"Time (s) [{z}]")
                    headers.append(f"{dist_h} [{z}]")
                    headers.append(f"Time % [{z}]")
                    headers.append(f"Dist % [{z}]")
                writer.writerow(headers)

                for row in self.rows_data:
                    csv_row = [
                        row["name"],
                        "Yes" if row["is_marked"] else "No",
                        f"{row['total_time']:.3f}".replace(".", ","),
                    ]

                    if row["total_dist"] is not None:
                        csv_row.append(f"{row['total_dist']:.3f}".replace(".", ","))
                    else:
                        csv_row.append("")

                    for zone_name in self.zone_columns:
                        if zone_name in row["zones"]:
                            z = row["zones"][zone_name]
                            csv_row.append(f"{z['time']:.3f}".replace(".", ","))
                            if z["dist"] is not None:
                                csv_row.append(f"{z['dist']:.3f}".replace(".", ","))
                            else:
                                csv_row.append("")
                            csv_row.append(f"{z['pct_time']:.1f}".replace(".", ","))
                            if z["pct_dist"] is not None:
                                csv_row.append(f"{z['pct_dist']:.1f}".replace(".", ","))
                            else:
                                csv_row.append("")
                        else:
                            csv_row.extend(["", "", "", ""])

                    writer.writerow(csv_row)
        except Exception:
            pass

    def cleanup(self):
        if self.loader is not None and self.loader.isRunning():
            self.loader.requestInterruption()
            self.loader.wait()
