from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

# Общие стили, вынесенные в константы для удобства
COMBOBOX_STYLE = """
    QComboBox {
        background-color: #333;
        color: white;
        border: 1px solid #444;
        border-radius: 6px;
        padding: 4px 28px 4px 10px;
        min-width: 100px;
        font-size: 13px;
    }
    QComboBox:hover {
        border: 1px solid #555;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 24px;
        border: none;
        background: transparent;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #aaa;
        margin-right: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #2d2d30;
        color: white;
        border: 1px solid #3e3e42;
        border-radius: 0px;
        selection-background-color: #3e3e42;
        selection-color: white;
        outline: none;
        padding: 2px 0px;
    }
    QComboBox QAbstractItemView::item {
        padding: 6px 10px;
        min-height: 24px;
        background-color: transparent;
        color: white;
        border: none;
        border-radius: 0px;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: #3e3e42;
    }
    QComboBox QAbstractItemView::item:selected {
        background-color: #2ea043;
    }
"""

CHECKBOX_STYLE = """
    QCheckBox {
        color: #ccc;
        spacing: 8px;
        background: transparent;
        border: none;
        font-size: 13px;
        padding: 2px 0;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border-radius: 3px;
    }
    QCheckBox::indicator:unchecked {
        background-color: #333;
        border: 1px solid #555;
    }
    QCheckBox::indicator:unchecked:hover {
        border: 1px solid #777;
    }
    QCheckBox::indicator:checked {
        background-color: #2ea043;
        border: 1px solid #2ea043;
    }
    QCheckBox::indicator:checked:hover {
        background-color: #3ab654;
        border: 1px solid #3ab654;
    }
"""

GROUPBOX_STYLE = """
    QGroupBox {
        color: #ccc;
        border: 1px solid #3e3e42;
        border-radius: 6px;
        margin-top: 14px;
        padding: 16px 10px 10px 10px;
        background-color: transparent;
        font-size: 13px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 6px;
        background-color: #252526;
        color: #aaa;
    }
"""

LABEL_STYLE = "color: #ccc; border: none; background: transparent;"


class TrajectoryExportDialog(QDialog):
    export_clicked = Signal(dict)

    def __init__(self, geometry_items: List, parent=None):
        super().__init__(parent)
        self.geometry_items = geometry_items
        self.geometry_checks = {}

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        self._init_ui()

    def _make_combo(self, items: list, default: str) -> QComboBox:
        """Фабрика для единообразных комбобоксов."""
        combo = QComboBox()
        combo.addItems(items)
        combo.setCurrentText(default)
        combo.setFixedHeight(34)
        combo.setMinimumWidth(120)
        combo.setStyleSheet(COMBOBOX_STYLE)
        # Важно для macOS — отключаем нативный рендеринг
        combo.setFocusPolicy(Qt.StrongFocus)
        return combo

    def _make_row(self, label_text: str, widget) -> QHBoxLayout:
        """Создаёт горизонтальный ряд: метка + виджет."""
        row = QHBoxLayout()
        row.setSpacing(12)

        lbl = QLabel(label_text)
        lbl.setFont(QFont("Segoe UI", 13))
        lbl.setStyleSheet(LABEL_STYLE)
        lbl.setFixedWidth(120)

        row.addWidget(lbl)
        row.addWidget(widget, 1)
        return row

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ─── Контейнер ───
        container = QFrame(self)
        container.setFixedWidth(420)
        container.setMinimumHeight(200)
        container.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.setSizeConstraint(QVBoxLayout.SetMinAndMaxSize)

        # ─── Заголовок ───
        lbl_title = QLabel("Экспорт траектории")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet("color: white; border: none; background: transparent;")
        layout.addWidget(lbl_title)

        # ─── Формат ───
        self.combo_format = self._make_combo(["SVG", "PNG", "JPG"], "SVG")
        layout.addLayout(self._make_row("Формат:", self.combo_format))

        # ─── Масштаб ───
        self.combo_scale = self._make_combo(["1x", "2x", "4x", "8x"], "1x")
        layout.addLayout(self._make_row("Масштаб:", self.combo_scale))

        # ─── Сглаживание ───
        self.combo_smoothing = self._make_combo(["Нет", "Да"], "Да")
        layout.addLayout(self._make_row("Сглаживание:", self.combo_smoothing))

        # ─── Группа «Отображение» ───
        options_group = QGroupBox("Отображение")
        options_group.setStyleSheet(GROUPBOX_STYLE)

        options_layout = QVBoxLayout()
        options_layout.setSpacing(6)
        options_layout.setContentsMargins(4, 4, 4, 4)

        self.chk_trajectory = QCheckBox("Траектория")
        self.chk_trajectory.setChecked(True)
        self.chk_trajectory.setStyleSheet(CHECKBOX_STYLE)
        options_layout.addWidget(self.chk_trajectory)

        self.chk_geometry = QCheckBox("Геометрия")
        self.chk_geometry.setChecked(True)
        self.chk_geometry.setStyleSheet(CHECKBOX_STYLE)
        options_layout.addWidget(self.chk_geometry)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # ─── Группа «Зоны геометрии» ───
        if self.geometry_items:
            geometry_group = QGroupBox("Зоны геометрии")
            geometry_group.setStyleSheet(GROUPBOX_STYLE)

            geometry_layout = QVBoxLayout()
            geometry_layout.setSpacing(6)
            geometry_layout.setContentsMargins(4, 4, 4, 4)

            for item in self.geometry_items:
                check = QCheckBox(item.name)
                check.setChecked(True)
                check.setStyleSheet(CHECKBOX_STYLE)
                self.geometry_checks[item.name] = check
                geometry_layout.addWidget(check)

            geometry_group.setLayout(geometry_layout)
            layout.addWidget(geometry_group)

        # ─── Пружина ───
        layout.addStretch()

        # ─── Кнопки ───
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #aaa;
                border: 1px solid #444;
                border-radius: 6px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #333;
                color: white;
                border: 1px solid #555;
            }
        """)

        self.btn_export = QPushButton("Экспорт")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setFixedHeight(36)
        self.btn_export.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.btn_export.clicked.connect(self._on_export_clicked)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #2ea043;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #3ab654;
            }
            QPushButton:pressed {
                background-color: #238636;
            }
        """)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_export)
        layout.addLayout(btn_layout)

        main_layout.addWidget(container)

    def _on_export_clicked(self):
        format_text = self.combo_format.currentText()
        scale_text = self.combo_scale.currentText()
        smoothing_text = self.combo_smoothing.currentText()

        scale = int(scale_text.replace("x", ""))

        selected_geometries = []
        for name, check in self.geometry_checks.items():
            if check.isChecked():
                selected_geometries.append(name)

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
            self,
            "Сохранить траекторию",
            f"trajectory{default_ext}",
            file_filter,
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
