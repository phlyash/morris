import sys
import os
from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap, QPainter, QImage, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtSvg import QSvgRenderer
from PIL import Image


def convert_icons(svg_path: str, output_dir: str):
    """
    Конвертирует SVG в .ico (Windows) и .icns (macOS).
    """
    app = QApplication(sys.argv)  # Нужен для рендеринга SVG

    path = Path(svg_path)
    if not path.exists():
        print(f"Error: File {svg_path} not found")
        return

    out_dir = Path(output_dir)
    out_dir.mkdir(exist_ok=True)

    # 1. Рендерим SVG в большие PNG (1024x1024)
    # macOS требует 1024px для Retina
    max_size = 1024

    renderer = QSvgRenderer(str(path))
    image = QImage(max_size, max_size, QImage.Format_ARGB32)
    image.fill(0)  # Прозрачный фон

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    # Сохраняем временный PNG
    png_path = out_dir / "temp_icon.png"
    image.save(str(png_path))

    # 2. Конвертация в ICO
    # ICO поддерживает слои: 16, 32, 48, 64, 128, 256
    print("Creating .ico...")
    img = Image.open(png_path)
    ico_path = out_dir / f"icon.ico"
    img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Saved: {ico_path}")

    # 3. Конвертация в ICNS
    # Для ICNS лучше всего использовать утилиту 'iconutil' на macOS,
    # так как чистый Python не всегда корректно собирает .icns структуру.
    # Но мы попробуем создать iconset и скомпилировать его.

    if sys.platform == 'darwin':
        print("Creating .icns (macOS only)...")
        iconset_dir = out_dir / f"icon.iconset"
        iconset_dir.mkdir(exist_ok=True)

        sizes = [16, 32, 128, 256, 512]
        for s in sizes:
            # Обычный (1x)
            qimg = image.scaled(s, s, mode=Qt.SmoothTransformation)
            qimg.save(str(iconset_dir / f"icon_{s}x{s}.png"))

            # Retina (2x)
            s2 = s * 2
            qimg2 = image.scaled(s2, s2, mode=Qt.SmoothTransformation)
            qimg2.save(str(iconset_dir / f"icon_{s}x{s}@2x.png"))

        # Компиляция через iconutil
        os.system(f"iconutil -c icns '{str(iconset_dir)}'")
        print(f"Saved: {out_dir}/icon.icns")

        # Удаляем временную папку
        import shutil
        shutil.rmtree(iconset_dir)

    else:
        print("Skipping .icns creation (requires macOS 'iconutil').")

    # Удаляем temp png
    os.remove(png_path)


if __name__ == "__main__":
    # Пример использования:
    # python scripts/convert_icons.py resources/morris.svg resources/

    if len(sys.argv) < 2:
        print("Usage: python convert_icons.py <path_to_svg> [output_dir]")
    else:
        svg = sys.argv[1]
        out = sys.argv[2] if len(sys.argv) > 2 else "resources"
        convert_icons(svg, out)
