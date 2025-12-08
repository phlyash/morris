from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QHBoxLayout, QMessageBox

from src.config import get_resource_path
from src.core import Video
from src.ui.components.confirm_dialog import ConfirmDialog
from src.ui.utils import numpy_to_pixmap, round_corners


class VideoCard(QWidget):
    delete_requested = Signal()

    def __init__(self, video: Video | None, is_add_button=False, has_tag=False, parent=None):
        super().__init__(parent)
        self.video = video
        self.is_add_button = is_add_button  # Сохраняем флаг
        self.setFixedSize(200, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 1. Верхняя часть (Превью)
        self.preview_frame = QFrame()
        self.preview_frame.setFixedSize(200, 130)

        if is_add_button:
            # Стиль по умолчанию для кнопки добавления
            self._set_add_btn_style(hover=False)

            preview_layout = QVBoxLayout(self.preview_frame)
            self.plus_label = QLabel("+")
            self.plus_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.plus_label.setFont(QFont("Arial", 30))
            # Стиль плюсика
            self.plus_label.setStyleSheet(
                "color: #666; border: 2px solid #444; border-radius: 25px; width: 50px; height: 50px;")
            preview_layout.addWidget(self.plus_label)
        else:
            self.preview_frame.setStyleSheet("background-color: #3a3a3e; border-radius: 10px;")

            self.image_label = QLabel(self.preview_frame)
            self.image_label.setGeometry(0, 0, 200, 130)
            self.image_label.setScaledContents(True)
            self.image_label.setStyleSheet("border-radius: 10px;")
            self.image_label.lower()

            try:
                raw_frame = video.get_preview(width=200, height=130)
                if raw_frame is not None:
                    pixmap = round_corners(numpy_to_pixmap(raw_frame))
                    self.image_label.setPixmap(pixmap)
            except Exception:
                pass

            overlay_layout = QGridLayout(self.preview_frame)
            overlay_layout.setContentsMargins(10, 10, 10, 10)

            # Тэг "Размечено"
            if has_tag:
                tag_container = QWidget()
                tag_container.setStyleSheet("background-color: #2ea043; border-radius: 4px;")
                tag_container.setFixedHeight(20)
                tag_layout = QHBoxLayout(tag_container)
                tag_layout.setContentsMargins(4, 0, 4, 0)
                tag_layout.setSpacing(4)
                try:
                    tag_mark = QSvgWidget(str(get_resource_path("mark.svg")))
                    tag_mark.setFixedSize(12, 12)
                    tag_layout.addWidget(tag_mark)
                except:
                    pass
                tag_label = QLabel("Размечено")
                tag_label.setStyleSheet(
                    "color: white; font-size: 10px; font-weight: bold; border: none; background: transparent;")
                tag_layout.addWidget(tag_label)
                overlay_layout.addWidget(tag_container, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            else:
                overlay_layout.addWidget(QWidget(), 0, 0)

            # Иконка удаления
            self.trash_btn = QSvgWidget(str(get_resource_path('trash_bin.svg')))
            self.trash_btn.setStyleSheet(
            "QSvgWidget { background-color: #863140; border-radius: 4px; color: white; border: none; } QSvgWidget:hover { background-color: #863140; }"
            )
            self.trash_btn.setFixedSize(22, 22)
            self.trash_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.trash_btn.mousePressEvent = self._on_trash_clicked
            overlay_layout.addWidget(self.trash_btn, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

            overlay_layout.setRowStretch(1, 1)
            overlay_layout.setColumnStretch(0, 1)

        # 2. Нижняя часть (Имя файла)
        if is_add_button:
            self.name_label = QLabel("Добавить видео")
            self.name_label.setStyleSheet("color: #666; font-size: 11px;")
        else:
            self.name_label = QLabel(video.path.name)
            self.name_label.setStyleSheet("color: #ccc; font-size: 11px;")

        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_frame)
        layout.addWidget(self.name_label)

    # --- ХОВЕР ЭФФЕКТЫ ---

    def enterEvent(self, event):
        """Мышь наведена"""
        if self.is_add_button:
            self._set_add_btn_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Мышь ушла"""
        if self.is_add_button:
            self._set_add_btn_style(hover=False)
        super().leaveEvent(event)

    def _set_add_btn_style(self, hover: bool):
        """Меняет цвета кнопки добавления"""
        if hover:
            # Чуть светлее фон и рамка
            self.preview_frame.setStyleSheet("background-color: #3a3a3e; border-radius: 10px; border: 1px solid #555;")
            if hasattr(self, 'plus_label'):
                self.plus_label.setStyleSheet(
                    "color: #fff; border: 2px solid #fff; border-radius: 25px; width: 50px; height: 50px;")
            if hasattr(self, 'name_label'):
                self.name_label.setStyleSheet("color: #fff; font-size: 11px;")
        else:
            # Темный фон
            self.preview_frame.setStyleSheet("background-color: #2d2d30; border-radius: 10px; border: none;")
            if hasattr(self, 'plus_label'):
                self.plus_label.setStyleSheet(
                    "color: #666; border: 2px solid #444; border-radius: 25px; width: 50px; height: 50px;")
            if hasattr(self, 'name_label'):
                self.name_label.setStyleSheet("color: #666; font-size: 11px;")

    # --- ОСТАЛЬНОЕ ---

    def _on_trash_clicked(self, event):
        """Обработчик нажатия на корзину"""
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()

            # --- ЗАМЕНА НА CONFIRM DIALOG ---
            dialog = ConfirmDialog(
                "Удаление видео",
                f"Вы уверены, что хотите удалить файл:\n{self.video.path.name}?\n\nЭто действие удалит файл с диска безвозвратно.",
                self.window() # Используем window() как родителя, чтобы диалог был по центру экрана
            )

            if dialog.exec():
                self._delete_video_files()

    def _delete_video_files(self):
        try:
            mor_dir = self.video.path.parent / ".morris"
            mor_file = mor_dir / f"{self.video.path.stem}.mor"
            if mor_file.exists(): mor_file.unlink()
            if self.video.path.exists(): self.video.path.unlink()
            self.delete_requested.emit()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить файл:\n{e}")