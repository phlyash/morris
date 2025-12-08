from PySide6.QtCore import QSize, QRect, QPoint, Qt
from PySide6.QtWidgets import QLayout


class FlowLayout(QLayout):
    """Кастомный layout, который работает как flex-wrap"""

    def __init__(self, parent=None, margin=0, hSpacing=10, vSpacing=10):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._hSpacing = hSpacing
        self._vSpacing = vSpacing
        self._itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._itemList.append(item)

    def count(self):
        return len(self._itemList)

    def itemAt(self, index):
        if 0 <= index < len(self._itemList):
            return self._itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._itemList):
            return self._itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._itemList:
            size = size.expandedTo(item.minimumSize())
        # В PySide6 contentsMargins() возвращает QMargins, доступ через .top() работает
        margin_top = self.contentsMargins().top()
        size += QSize(2 * margin_top, 2 * margin_top)
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        # Проходим по всем элементам и расставляем их
        for item in self._itemList:
            # wid = item.widget() # В данном алгоритме wid не используется явно, но item.sizeHint() нужен
            spaceX = self.spacing() + self._hSpacing
            spaceY = self.spacing() + self._vSpacing

            nextX = x + item.sizeHint().width() + spaceX

            # Если элемент не влезает в ширину -> перенос строки
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()