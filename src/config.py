import sys
from pathlib import Path

# 1. Пути (как у вас)
_SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SRC_DIR.parent
RESOURCES_DIR = PROJECT_ROOT / "resources"

# Файл, где будем хранить список путей к проектам
RECENT_PROJECTS_FILE = Path.home() / ".morris_config.json"

# Поддерживаемые расширения видео
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}


def get_resource_path(relative_path: str) -> Path:
    if hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
        return base_path / "resources" / relative_path
    else:
        return RESOURCES_DIR / relative_path
