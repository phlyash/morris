from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class TrajectoryExportDialog(QDialog):
    export_clicked = Signal(dict)

    def __init__(self, geometry_items: List, parent=None):
        super().__init__(parent)
        self.geometry_items = geometry_items

        self.setWindowTitle("Экспорт траектории")
        self.setMinimumWidth(350)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        format_layout = QHBoxLayout()
        lbl_format = QLabel("Формат:")
        self.combo_format = QComboBox()
        self.combo_format.addItems(["SVG", "PNG", "JPG"])
        self.combo_format.setCurrentText("SVG")
        format_layout.addWidget(lbl_format)
        format_layout.addWidget(self.combo_format)
        format_layout.addStretch()
        layout.addLayout(format_layout)

        scale_layout = QHBoxLayout()
        lbl_scale = QLabel("Масштаб:")
        self.combo_scale = QComboBox()
        self.combo_scale.addItems(["1x", "2x", "4x", "8x"])
        self.combo_scale.setCurrentText("1x")
        scale_layout.addWidget(lbl_scale)
        scale_layout.addWidget(self.combo_scale)
        scale_layout.addStretch()
        layout.addLayout(scale_layout)

        smoothing_layout = QHBoxLayout()
        lbl_smoothing = QLabel("Сглаживание:")
        self.combo_smoothing = QComboBox()
        self.combo_smoothing.addItems(["none", "light", "medium", "strong"])
        self.combo_smoothing.setCurrentText("medium")
        smoothing_layout.addWidget(lbl_smoothing)
        smoothing_layout.addWidget(self.combo_smoothing)
        smoothing_layout.addStretch()
        layout.addLayout(smoothing_layout)

        options_group = QGroupBox("Отображение")
        options_layout = QVBoxLayout()

        self.chk_trajectory = QCheckBox("Траектория")
        self.chk_trajectory.setChecked(True)
        options_layout.addWidget(self.chk_trajectory)

        self.chk_geometry = QCheckBox("Геометрия")
        self.chk_geometry.setChecked(True)
        options_layout.addWidget(self.chk_geometry)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        if self.geometry_items:
            geometry_group = QGroupBox("Зоны геометрии")
            geometry_layout = QVBoxLayout()

            self.geometry_checks = {}
            for item in self.geometry_items:
                check = QCheckBox(item.name)
                check.setChecked(True)
                check.setStyleSheet("color: #000000;")
                self.geometry_checks[item.name] = check
                geometry_layout.addWidget(check)

            geometry_group.setLayout(geometry_layout)
            layout.addWidget(geometry_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_export = QPushButton("Экспорт")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._on_export_clicked)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_export)

        layout.addLayout(btn_layout)

        self.setStyleSheet("""
            QDialog { background-color: #2d2d30; }
            QLabel { color: #cccccc; }
            QGroupBox { color: #cccccc; border: 1px solid #444; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QCheckBox { color: #cccccc; spacing: 5px; }
            QCheckBox::indicator { width: 16px; height: 16px; }
            QPushButton {
                background-color: #3B3C40; color: white; padding: 8px 20px;
                border: 1px solid #555; border-radius: 4px; font-size: 13px;
            }
            QPushButton:hover { background-color: #45464a; }
            QPushButton:pressed { background-color: #2d2d30; }
            QComboBox {
                background-color: #3B3C40; color: white; padding: 5px;
                border: 1px solid #555; border-radius: 4px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #3B3C40; color: white; selection-background-color: #555;
            }
        """)

    def _on_export_clicked(self):
        format_text = self.combo_format.currentText()
        scale_text = self.combo_scale.currentText()
        smoothing_text = self.combo_smoothing.currentText()

        scale = int(scale_text.replace("x", ""))

        selected_geometries = []
        for name, check in self.geometry_checks.items():
            if check.isChecked():
                selected_geometries.append(name)

        file_filter = ""
        if format_text == "SVG":
            file_filter = "SVG Files (*.svg)"
            default_ext = ".svg"
        elif format_text == "PNG":
            file_filter = "PNG Files (*.png)"
            default_ext = ".png"
        else:
            file_filter = "JPG Files (*.jpg)"
            default_ext = ".jpg"

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить траекторию", f"trajectory{default_ext}", file_filter
        )

        if not path:
            return

        options = {
            "format": format_text.lower(),
            "scale": scale,
            "smoothing": smoothing_text,
            "show_trajectory": self.chk_trajectory.isChecked(),
            "show_geometry": self.chk_geometry.isChecked(),
            "selected_geometries": selected_geometries,
            "output_path": path,
        }

        self.export_clicked.emit(options)
        self.accept()
