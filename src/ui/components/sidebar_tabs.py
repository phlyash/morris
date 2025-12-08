import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QStackedWidget, QFrame, QComboBox,
                               QLineEdit, QButtonGroup, QApplication, QDoubleSpinBox,
                               QListWidget, QListWidgetItem, QAbstractItemView, QColorDialog, QCheckBox, QTableWidget,
                               QHeaderView, QTableWidgetItem)
from PySide6.QtCore import Qt, Signal, QSize, QEvent
from PySide6.QtGui import QIcon, QPainter, QColor, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Пытаемся импортировать конфиг, если нет - заглушка
try:
    from src.config import get_resource_path
except ImportError:
    get_resource_path = lambda x: x

# --- КОНСТАНТЫ ---
CONTENT_BG = "#3e3e42"
HEADER_BG = "#2d2d30"
INPUT_BG = "#252526"
LIST_BG = "#2d2d30"
TEXT_WHITE = "#ffffff"
TEXT_GREY = "#aaaaaa"
ACCENT_YELLOW = "#d4b765"

BTN_BG_UNCHECKED = "#3B3C40"
BTN_BG_CHECKED = "#FFDD78"
ICON_COLOR_UNCHECKED = "#CECECE"
ICON_COLOR_CHECKED = "#3B3C40"

FIXED_ALPHA = 30


# --- ГРАФИЧЕСКИЕ УТИЛИТЫ ---

def svg_to_pixmap(svg_path: str, width: int, height: int) -> QPixmap:
    """
    Рендерит SVG.
    ВАЖНО: Рендерим в высоком разрешении, чтобы при уменьшении не было 'мыла'.
    """
    renderer = QSvgRenderer(svg_path)

    # Рендерим в 2x или 4x разрешении от требуемого, если нужно супер качество,
    # но здесь просто рендерим в заданный размер.
    # Для иконок списка мы будем запрашивать размер побольше (например 128),
    # а потом сжимать.
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()

    return pixmap


def recolor_pixmap(pixmap: QPixmap, color_hex: str) -> QPixmap:
    if pixmap.isNull(): return pixmap
    target = QPixmap(pixmap.size())
    target.fill(Qt.transparent)
    painter = QPainter(target)
    if painter.isActive():
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(target.rect(), QColor(color_hex))
        painter.end()
    return target


# --- ВИДЖЕТ СТРОКИ СПИСКА ---

class GeometryListRow(QWidget):
    # Сигнал удаления
    delete_requested = Signal()
    # НОВЫЙ СИГНАЛ: Изменение статуса статистики
    stat_toggled = Signal(bool)

    def __init__(self, name: str, color_hex: str, svg_path: str, is_stat: bool):
        super().__init__()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # 1. Иконка фигуры
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setStyleSheet("border: none;")
        self.icon_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.svg_path = svg_path

        # 2. Имя
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 13px; border: none;")
        self.name_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # 3. Checkbox "Статистика"
        self.chk_stat = QCheckBox("Статистика")
        self.chk_stat.setCursor(Qt.PointingHandCursor)
        self.chk_stat.setStyleSheet(f"""
            QCheckBox {{ color: #888; font-size: 11px; }}
            QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid #666; background: #333; }}
            QCheckBox::indicator:checked {{ background-color: {ACCENT_YELLOW}; border: 1px solid {ACCENT_YELLOW}; image: url(none); }}
        """)
        self.chk_stat.setChecked(is_stat)
        self.chk_stat.toggled.connect(self.stat_toggled.emit)

        # 4. Кнопка удаления
        self.btn_delete = QPushButton()
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        trash_path = str(get_resource_path("trash_bin.svg"))
        pix_trash = svg_to_pixmap(trash_path, 64, 64)
        icon_trash = QIcon(recolor_pixmap(pix_trash, "#888888"))
        self.btn_delete.setIcon(icon_trash)
        self.btn_delete.setIconSize(QSize(16, 16))
        self.btn_delete.clicked.connect(self.delete_requested.emit)
        self.btn_delete.setStyleSheet("""
            QPushButton { background: transparent; border: none; border-radius: 4px; }
            QPushButton:hover { background-color: #444; }
        """)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.chk_stat)  # Добавляем чекбокс
        layout.addWidget(self.btn_delete)

        self.update_visuals(name, color_hex, is_stat)

    def update_visuals(self, name, color_hex, is_stat):
        self.name_label.setText(name)
        base = svg_to_pixmap(self.svg_path, 128, 128)
        colored = recolor_pixmap(base, color_hex)
        self.icon_label.setPixmap(colored.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Блокируем сигналы, чтобы не вызвать зацикливание при программном обновлении
        self.chk_stat.blockSignals(True)
        self.chk_stat.setChecked(is_stat)
        self.chk_stat.blockSignals(False)


class TabButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: none; color: {TEXT_GREY};
                font-family: 'Segoe UI'; font-size: 14px; font-weight: 600;
                border-top-left-radius: 8px; border-top-right-radius: 8px;
                padding: 8px 16px; margin-top: 4px; margin-bottom: 0px;
            }}
            QPushButton:hover {{ color: {TEXT_WHITE}; background-color: rgba(255,255,255,0.05); }}
            QPushButton:checked {{ background-color: {CONTENT_BG}; color: {TEXT_WHITE}; }}
        """)


class ShapeButton(QPushButton):
    def __init__(self, svg_path: str):
        super().__init__()
        self.setCheckable(True)
        self.setFixedSize(50, 50)
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(28, 28))

        # Тоже используем больший размер для качества кнопок
        base_pixmap = svg_to_pixmap(svg_path, 128, 128)
        self.icon_unchecked = QIcon(recolor_pixmap(base_pixmap, ICON_COLOR_UNCHECKED))
        self.icon_checked = QIcon(recolor_pixmap(base_pixmap, ICON_COLOR_CHECKED))

        self.setIcon(self.icon_unchecked)
        self.toggled.connect(self.update_icon_state)

        self.setStyleSheet(f"""
            QPushButton {{ background-color: {BTN_BG_UNCHECKED}; border: none; border-radius: 4px; }}
            QPushButton:hover {{ background-color: #45464a; }}
            QPushButton:checked {{ background-color: {BTN_BG_CHECKED}; border: none; }}
        """)

    def update_icon_state(self, checked):
        self.setIcon(self.icon_checked if checked else self.icon_unchecked)


class BasePage(QWidget):
    def __init__(self):
        super().__init__()
        # Обновленный стиль списка для правильного выделения строки целиком
        self.setStyleSheet(f"""
            QWidget {{ font-family: 'Segoe UI'; font-size: 13px; color: {TEXT_WHITE}; }}
            QLabel {{ color: {TEXT_WHITE}; }}
            QLineEdit, QComboBox {{
                background-color: {INPUT_BG}; border: 1px solid #444;
                border-radius: 6px; padding: 8px; color: white;
            }}

            /* СТИЛЬ СПИСКА */
            QListWidget {{
                background-color: {LIST_BG}; 
                border: 1px solid #444; 
                border-radius: 6px; 
                outline: 0; /* Убирает пунктирную обводку фокуса */
            }}
            QListWidget::item {{ 
                border-bottom: 1px solid #3a3a3a; 
                margin: 0px;
            }}
            /* ВЫДЕЛЕННАЯ СТРОКА: Задает фон для всего элемента списка */
            QListWidget::item:selected {{ 
                background-color: #444448; 
                border: 1px solid {ACCENT_YELLOW}; /* Желтая рамка активного элемента */
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: #3a3a3e;
            }}
        """)


class GeometryPage(BasePage):
    shape_create_requested = Signal(str)
    selection_changed_requested = Signal(list)
    items_deleted = Signal(list)

    def __init__(self):
        super().__init__()
        self.selected_items = []
        self._block_signals = False
        self.fixed_alpha = FIXED_ALPHA
        self.shape_paths = {
            "donut": str(get_resource_path("donut.svg")),
            "circle": str(get_resource_path("circle.svg")),
            "square": str(get_resource_path("square.svg")),
            "poly": str(get_resource_path("poly.svg"))
        }

        layout = QVBoxLayout(self)

        # 1. Формы
        layout.addWidget(QLabel("Задать форму геометрии", styleSheet="font-weight: bold;"))
        shapes_layout = QHBoxLayout()
        self.shape_group = QButtonGroup(self)
        self.shape_group.setExclusive(True)
        self.shape_group.buttonClicked.connect(self._on_shape_tool_clicked)
        for i, (stype, path) in enumerate(self.shape_paths.items()):
            btn = ShapeButton(path)
            btn.setProperty("shape_type", stype)
            self.shape_group.addButton(btn, i)
            shapes_layout.addWidget(btn)
        layout.addLayout(shapes_layout)

        # 2. Имя
        layout.addWidget(QLabel("Имя объекта", styleSheet="font-weight: bold; margin-top: 10px;"))
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Название зоны")
        self.inp_name.textChanged.connect(self._on_ui_changed)
        layout.addWidget(self.inp_name)

        # 3. Цвет
        layout.addWidget(QLabel("Цвет", styleSheet="font-weight: bold; margin-top: 10px;"))
        color_layout = QHBoxLayout()
        self.btn_color_preview = QPushButton()
        self.btn_color_preview.setFixedSize(40, 35)
        self.btn_color_preview.clicked.connect(self._open_color_dialog)
        self.inp_hex = QLineEdit("FFDD78")
        self.inp_hex.textChanged.connect(self._on_ui_changed)
        color_layout.addWidget(self.btn_color_preview)
        color_layout.addWidget(self.inp_hex)
        layout.addLayout(color_layout)

        # 4. СПИСОК ОБЪЕКТОВ
        layout.addWidget(QLabel("Список объектов", styleSheet="font-weight: bold; margin-top: 10px;"))
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self._on_list_selection_changed)
        self.list_widget.installEventFilter(self)
        layout.addWidget(self.list_widget)

        # 5. Координаты
        layout.addWidget(QLabel("Координаты", styleSheet="color: #777; font-size: 11px; margin-top: 10px;"))
        pos_layout = QHBoxLayout()
        self.inp_x = QDoubleSpinBox(); self.inp_x.setRange(-9999, 9999)
        self.inp_y = QDoubleSpinBox(); self.inp_y.setRange(-9999, 9999)
        self.inp_w = QDoubleSpinBox(); self.inp_w.setRange(0, 9999)
        self.inp_h = QDoubleSpinBox(); self.inp_h.setRange(0, 9999)
        for w in [self.inp_x, self.inp_y, self.inp_w, self.inp_h]:
            w.valueChanged.connect(self._on_ui_changed)
            w.setStyleSheet(f"background-color: {INPUT_BG}; color: #ccc; border: 1px solid #444; border-radius: 4px;")
            pos_layout.addWidget(w)
        layout.addLayout(pos_layout)

        self._update_color_preview("FFDD78")

    # --- Event Filter для удаления по Delete в списке ---
    def eventFilter(self, source, event):
        if source == self.list_widget:
            # Сравниваем тип события с константой класса QEvent
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
                    self.delete_selected_items()
                    return True
        return super().eventFilter(source, event)
    # --- ЛОГИКА ---
    def _on_shape_tool_clicked(self, btn):
        self.shape_create_requested.emit(btn.property("shape_type"))

    def _open_color_dialog(self):
        init_c = self.inp_hex.text()
        if not init_c.startswith("#"): init_c = "#" + init_c
        color = QColorDialog.getColor(QColor(init_c), self, "Выберите цвет")
        if color.isValid(): self.inp_hex.setText(color.name().upper().replace("#", ""))

    def _update_color_preview(self, hex_code):
        if not hex_code.startswith("#"): hex_code = "#" + hex_code
        self.btn_color_preview.setStyleSheet(
            f"background-color: {hex_code}; border: 1px solid #666; border-radius: 4px;")

    # --- УДАЛЕНИЕ ---

    def delete_selected_items(self):
        """Удаляет все объекты, выбранные сейчас в списке"""
        if not self.selected_items: return

        items_to_delete = list(self.selected_items)  # Копия списка
        self.items_deleted.emit(items_to_delete)  # Сообщаем View удалить их со сцены

        # Удаляем из списка UI
        for item in items_to_delete:
            self._remove_from_list_by_item(item)

        self.selected_items = []
        self._clear_ui_fields()

    def _remove_from_list_by_item(self, item_obj):
        for i in range(self.list_widget.count()):
            li = self.list_widget.item(i)
            if li.data(Qt.UserRole) == item_obj:
                self.list_widget.takeItem(i)
                break

    def delete_specific_item(self, item_obj):
        """Удаляет один конкретный объект (по кнопке корзины)"""
        self.items_deleted.emit([item_obj])
        self._remove_from_list_by_item(item_obj)

        if item_obj in self.selected_items:
            self.selected_items.remove(item_obj)

    def _clear_ui_fields(self):
        self._block_signals = True
        self.inp_name.clear()
        self.inp_x.setValue(0);
        self.inp_y.setValue(0)
        self.inp_w.setValue(0);
        self.inp_h.setValue(0)
        self._block_signals = False

    # --- СИНХРОНИЗАЦИЯ ---

    def register_new_item(self, item):
        current_hex = self.inp_hex.text()
        if len(current_hex) != 6: current_hex = "FFDD78"
        name = self.inp_name.text().strip()

        item.set_color_data(f"#{current_hex}", self.fixed_alpha)
        item.name = name

        # Инициализируем флаг статистики, если его нет
        if not hasattr(item, 'is_stat_zone'):
            item.is_stat_zone = True  # По умолчанию включено

        self._add_to_list(item)
        self.reset_tool_selection()

    def _add_to_list(self, item):
        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(0, 40))
        list_item.setData(Qt.UserRole, item)

        c = item.base_color.name().upper()
        # Создаем виджет строки, передавая состояние is_stat_zone
        row_widget = GeometryListRow(item.name, c, self.shape_paths.get(item.shape_type, ""),
                                     getattr(item, 'is_stat_zone', True))

        # Подключаем сигналы
        row_widget.delete_requested.connect(lambda i=item: self.delete_specific_item(i))

        # Обновляем item при клике на чекбокс
        row_widget.stat_toggled.connect(lambda state, i=item: self._on_item_stat_changed(i, state))

        self.list_widget.insertItem(0, list_item)
        self.list_widget.setItemWidget(list_item, row_widget)
        self.list_widget.setCurrentItem(list_item)

    def _on_item_stat_changed(self, item, state):
        """Обработка клика по чекбоксу Stat"""
        item.is_stat_zone = state
        # Здесь можно добавить логику, если нужно обновить UI при изменении флага

    def _on_list_selection_changed(self):
        if self._block_signals: return
        list_items = self.list_widget.selectedItems()
        items = [li.data(Qt.UserRole) for li in list_items]
        self.selected_items = items
        self.selection_changed_requested.emit(items)
        if items: self._load_data_to_ui(items[-1])

    def load_item_data(self, item):
        if not item: return
        self._block_signals = True
        self.current_item = item

        r = item.rect;
        pos = item.pos()
        self.inp_x.setValue(pos.x());
        self.inp_y.setValue(pos.y())
        self.inp_w.setValue(r.width());
        self.inp_h.setValue(r.height())

        c = item.base_color
        hex_c = c.name().upper().replace("#", "")
        self.inp_hex.setText(hex_c)
        self._update_color_preview(hex_c)

        if hasattr(item, 'name'):
            self.inp_name.setText(item.name)

        # Выделяем в списке
        for i in range(self.list_widget.count()):
            li = self.list_widget.item(i)
            if li.data(Qt.UserRole) == item:
                self.list_widget.setCurrentItem(li)
                break
        self._block_signals = False

    def update_from_scene_selection(self, items):
        self._block_signals = True
        self.selected_items = items
        self.list_widget.blockSignals(True)
        self.list_widget.clearSelection()

        for i in range(self.list_widget.count()):
            li = self.list_widget.item(i)
            item_data = li.data(Qt.UserRole)
            if item_data in items:
                li.setSelected(True)
                if item_data == items[-1]: self.list_widget.scrollToItem(li)

        self.list_widget.blockSignals(False)
        if items:
            self._load_data_to_ui(items[-1])
        else:
            self._clear_ui_fields()
        self._block_signals = False

    def reset_tool_selection(self):
        self.shape_group.setExclusive(False)
        for btn in self.shape_group.buttons(): btn.setChecked(False)
        self.shape_group.setExclusive(True)

    def _load_data_to_ui(self, item):
        self._block_signals = True
        count = len(self.selected_items)
        if count == 0:
            self._clear_ui_fields()
            self._set_inputs_enabled(False)
            self._block_signals = False
            return

        c = item.base_color
        hex_c = c.name().upper().replace("#", "")
        self.inp_hex.setText(hex_c)
        self._update_color_preview(hex_c)

        if count > 1:
            self.inp_name.setText("group")
            self.inp_name.setEnabled(False)
            self.inp_x.clear();
            self.inp_y.clear()
            self.inp_w.clear();
            self.inp_h.clear()
            self.inp_x.setEnabled(False);
            self.inp_y.setEnabled(False)
            self.inp_w.setEnabled(False);
            self.inp_h.setEnabled(False)
        else:
            self._set_inputs_enabled(True)
            r = item.rect;
            pos = item.pos()
            self.inp_x.setValue(pos.x());
            self.inp_y.setValue(pos.y())
            self.inp_w.setValue(r.width());
            self.inp_h.setValue(r.height())
            if hasattr(item, 'name'): self.inp_name.setText(item.name)
        self._block_signals = False

    def _set_inputs_enabled(self, enabled: bool):
        self.inp_name.setEnabled(enabled)
        self.inp_x.setEnabled(enabled);
        self.inp_y.setEnabled(enabled)
        self.inp_w.setEnabled(enabled);
        self.inp_h.setEnabled(enabled)

    def _on_ui_changed(self):
        if self._block_signals or not self.selected_items: return
        x = self.inp_x.value();
        y = self.inp_y.value()
        w = self.inp_w.value();
        h = self.inp_h.value()
        hex_c = self.inp_hex.text()
        if len(hex_c) != 6: hex_c = "FFDD78"
        self._update_color_preview(hex_c)

        for item in self.selected_items:
            if len(self.selected_items) == 1:
                item.set_geometry_data(x, y, w, h)
                item.name = self.inp_name.text()
            item.set_color_data(f"#{hex_c}", self.fixed_alpha)

        # Обновляем виджеты в списке
        for i in range(self.list_widget.count()):
            li = self.list_widget.item(i)
            it = li.data(Qt.UserRole)
            if it in self.selected_items:
                widget = self.list_widget.itemWidget(li)
                if widget:
                    display_name = item.name if len(self.selected_items) == 1 else it.name
                    # Обновляем визуал, передавая текущее состояние is_stat_zone
                    widget.update_visuals(display_name, f"#{hex_c}", getattr(it, 'is_stat_zone', True))

    def get_all_items(self) -> list:
        items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i).data(Qt.UserRole)
            if item: items.append(item)
        return items

    def add_existing_item(self, item):
        self._add_to_list(item)


class TrackerPage(BasePage):
    # Сигналы для контроллера
    model_changed = Signal(str)      # "CSRT" / "YOLO"
    manual_setup_toggled = Signal(bool)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Заголовок
        lbl = QLabel("Выберите модель трекера")
        lbl.setStyleSheet("font-weight: bold; color: white;")
        layout.addWidget(lbl)

        # Выбор модели
        self.combo = QComboBox()
        self.combo.addItems(["Нет модели", "CSRT", "YOLO"])
        self.combo.currentTextChanged.connect(self.model_changed.emit)
        layout.addWidget(self.combo)

        self.lbl_error = QLabel()
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setStyleSheet("color: #ff5555; font-size: 12px; font-weight: bold;")
        self.lbl_error.setVisible(False) # Скрыто по умолчанию
        layout.addWidget(self.lbl_error)

        # Описание
        info = QLabel("• CSRT: Точный, требует ручной инициализации.\n• YOLO: Автоматический поиск, поддерживает дообучение.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(info)

        layout.addSpacing(20)

        lbl_man = QLabel("Ручная коррекция")
        lbl_man.setStyleSheet("font-weight: bold; color: white;")
        layout.addWidget(lbl_man)

        self.btn_manual = QPushButton("Выделить объект")
        self.btn_manual.setCheckable(True)  # <--- ВАЖНО: Делаем кнопку триггерной
        self.btn_manual.setCursor(Qt.PointingHandCursor)

        # Стили: добавляем состояние :checked (Желтый фон, черный текст)
        self.btn_manual.setStyleSheet("""
                    QPushButton { 
                        background-color: #3B3C40; color: white; padding: 10px; 
                        border: 1px solid #555; border-radius: 4px; text-align: left;
                    }
                    QPushButton:hover { background-color: #45464a; }

                    /* Стиль для нажатого состояния */
                    QPushButton:checked { 
                        background-color: #d4b765; /* Желтый акцент */
                        color: #1e1e1e; 
                        border: 1px solid #d4b765;
                    }
                """)

        # Подключаем сигнал toggled (передает True/False)
        self.btn_manual.toggled.connect(self.manual_setup_toggled.emit)
        layout.addWidget(self.btn_manual)

        layout.addStretch()

    def show_error(self, message: str):
        """Показать ошибку"""
        if message:
            self.lbl_error.setText(f"⚠ {message}")
            self.lbl_error.setVisible(True)
        else:
            self.lbl_error.setVisible(False)


class StatisticsPage(BasePage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 20, 15, 20)

        # Кеш путей к иконкам (копия из GeometryPage)
        self.shape_paths = {
            "donut": str(get_resource_path("donut.svg")),
            "circle": str(get_resource_path("circle.svg")),
            "square": str(get_resource_path("square.svg")),
            "poly": str(get_resource_path("poly.svg"))
        }

        # 1. Заголовок
        lbl_global = QLabel("Общая статистика")
        lbl_global.setStyleSheet("font-weight: bold; font-size: 14px; color: #FFDD78;")
        layout.addWidget(lbl_global)

        # Данные
        self.lbl_total_time = QLabel("Время: 0.00 с")
        self.lbl_total_dist = QLabel("Дистанция: 0.00 px")
        layout.addWidget(self.lbl_total_time)
        layout.addWidget(self.lbl_total_dist)

        layout.addSpacing(15)

        # 2. Таблица
        lbl_zones = QLabel("По зонам")
        lbl_zones.setStyleSheet("font-weight: bold; font-size: 14px; color: #FFDD78;")
        layout.addWidget(lbl_zones)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Зона", "Время", "Дист."])

        # Стиль: убираем сетку, делаем прозрачный фон, чтобы выглядело как список
        self.table.setStyleSheet("""
            QTableWidget { 
                background-color: #2d2d30; 
                border: 1px solid #444; 
                gridline-color: #3a3a3a;
                font-family: 'Segoe UI'; font-size: 13px;
            }
            QHeaderView::section { 
                background-color: #333; 
                color: #aaa; 
                padding: 4px; 
                border: none; 
                font-weight: bold;
            }
            QTableWidget::item { 
                padding: 5px; 
                color: white; 
            }
        """)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.table.verticalHeader().setVisible(False)
        # Убираем возможность выделять ячейки
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)

        layout.addWidget(self.table)

    def update_data(self, global_stats, zones_stats):
        """Метод обновления UI"""
        t = global_stats["total_time"]
        d = global_stats["total_distance"]
        self.lbl_total_time.setText(f"Время: {t:.2f} с")
        self.lbl_total_dist.setText(f"Дистанция: {d:.1f} px")

        self.table.setRowCount(len(zones_stats))

        # Сортируем по имени для стабильности отображения
        sorted_zones = sorted(zones_stats.items(), key=lambda x: x[0])

        for row, (name, data) in enumerate(sorted_zones):
            # 1. КОЛОНКА ИМЕНИ С ИКОНКОЙ
            item_name = QTableWidgetItem(name)

            # Генерируем иконку
            shape_type = data.get('shape', 'square')
            color_hex = data.get('color', '#ffffff')
            path = self.shape_paths.get(shape_type, "")

            if path:
                base_pix = svg_to_pixmap(path, 64, 64)
                colored_pix = recolor_pixmap(base_pix, color_hex)
                icon = QIcon(colored_pix)
                item_name.setIcon(icon)

            item_name.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 0, item_name)

            # 2. ВРЕМЯ
            item_time = QTableWidgetItem(f"{data['time']:.2f} с")
            item_time.setTextAlignment(Qt.AlignCenter)
            item_time.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, item_time)

            # 3. ДИСТАНЦИЯ
            item_dist = QTableWidgetItem(f"{data['dist']:.0f}")
            item_dist.setTextAlignment(Qt.AlignCenter)
            item_dist.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 2, item_dist)


# ... (импорты те же)

class SidebarTabsWidget(QFrame):
    tab_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(350)
        self.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.header = QFrame()
        self.header.setFixedHeight(44)
        self.header.setStyleSheet(
            f"background:{HEADER_BG}; border-radius:12px; border-bottom-left-radius:0; border-bottom-right-radius:0;")

        self.header_layout = QHBoxLayout(self.header)  # Сохраняем layout в self
        self.header_layout.setContentsMargins(10, 0, 10, 0)
        self.header_layout.setSpacing(4)
        self.header_layout.setAlignment(Qt.AlignBottom)

        self.grp = QButtonGroup(self)
        self.grp.setExclusive(True)
        self.grp.buttonClicked.connect(self.sw)
        self.grp.buttonClicked.connect(self.on_tab_clicked)

        self.header_layout.addStretch()

        # Сохраняем кнопки в словарь для доступа
        self.tabs = {}

        # Создаем кнопки
        # 0: Трекер, 1: Геометрия, 2: Статистика
        btn_tracker = TabButton("Трекер")
        self.grp.addButton(btn_tracker, 0)
        self.header_layout.addWidget(btn_tracker)
        self.tabs[0] = btn_tracker

        btn_geom = TabButton("Геометрия")
        self.grp.addButton(btn_geom, 1)
        self.header_layout.addWidget(btn_geom)
        self.tabs[1] = btn_geom

        btn_stats = TabButton("Статистика")
        self.grp.addButton(btn_stats, 2)
        self.header_layout.addWidget(btn_stats)
        self.tabs[2] = btn_stats

        self.header_layout.addStretch()
        self.main_layout.addWidget(self.header)

        self.cont = QFrame()
        self.cont.setStyleSheet(
            f"background:{CONTENT_BG}; border-radius:12px; border-top-left-radius:0; border-top-right-radius:0;")
        cl = QVBoxLayout(self.cont)
        cl.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()

        self.geometry_page = GeometryPage()

        self.stack.addWidget(TrackerPage())  # Index 0
        self.stack.addWidget(self.geometry_page)  # Index 1
        self.stack.addWidget(StatisticsPage())  # Index 2

        cl.addWidget(self.stack)
        self.main_layout.addWidget(self.cont)

        # По умолчанию выбираем 0
        self.grp.button(0).setChecked(True)
        self.stack.setCurrentIndex(0)

    def sw(self, b):
        self.stack.setCurrentIndex(self.grp.id(b))

    def on_tab_clicked(self, btn):
        idx = self.grp.id(btn)
        self.stack.setCurrentIndex(idx)
        self.tab_changed.emit(idx)

    def set_tabs_visible(self, tracker=True, geometry=True, stats=True):
        """Управляет видимостью вкладок"""
        # Скрываем/показываем кнопки
        self.tabs[0].setVisible(tracker)
        self.tabs[1].setVisible(geometry)
        self.tabs[2].setVisible(stats)

        # Логика переключения на первую доступную вкладку
        if geometry and not tracker:
            self.grp.button(1).setChecked(True)
            self.stack.setCurrentIndex(1)
        elif tracker:
            self.grp.button(0).setChecked(True)
            self.stack.setCurrentIndex(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SidebarTabsWidget()
    w.show()
    sys.exit(app.exec())
