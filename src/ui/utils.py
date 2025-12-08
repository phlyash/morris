from PySide6.QtGui import QImage, QPixmap, Qt, QPainter, QPainterPath
import numpy as np


def numpy_to_pixmap(array: np.ndarray) -> QPixmap:
    """Превращает RGB numpy array в QPixmap для отображения в QLabel."""
    if array is None:
        return QPixmap()  # Возвращаем пустую картинку

    height, width, channels = array.shape
    bytes_per_line = channels * width

    # Создаем QImage из байтов.
    # Важно: array.data должно жить, пока используется QImage.
    # Но мы сразу делаем копию в QPixmap, так что это безопасно.
    q_img = QImage(
        array.data,
        width,
        height,
        bytes_per_line,
        QImage.Format_RGB888
    )

    return QPixmap.fromImage(q_img)


def round_corners(pixmap: QPixmap, radius=10):
    rounded = QPixmap(pixmap.size())
    rounded.fill(Qt.GlobalColor.transparent)

    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.Antialiasing)

    path = QPainterPath()
    path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)

    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()

    return rounded
