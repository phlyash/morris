import os
import yaml
from pathlib import Path
from typing import List, Optional

from src.config import VIDEO_EXTENSIONS
from src.core import Video  # Ваш класс Video


class Project:
    _name: str
    _path: Path
    _videos: List[Video]
    _is_loaded: bool

    def __init__(self, project_path: str | os.PathLike, cached_name: str = None):
        """
        Инициализация легкого объекта.
        :param project_path: Путь к папке проекта.
        :param cached_name: Имя проекта, если известно (например, из истории).
        """
        self._path = Path(project_path).resolve()
        # Если имя передали (из кэша), используем его. Иначе временно имя папки.
        self._name = cached_name if cached_name else self._path.name
        self._videos = []
        self._is_loaded = False

        self.reload_videos()  # Вызываем при старте

    def reload_videos(self):
        """Сканирует папку на наличие видео"""
        self._videos = []
        # Ищем mp4 и avi
        valid_extensions = {'.mp4', '.avi', '.mov', '.mkv'}

        # Проходим по файлам в корне проекта
        for file_path in self.path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                self._videos.append(Video(file_path))

        # Сортируем по имени
        self._videos.sort(key=lambda v: v.path.name)

    def load(self):
        """
        ТЯЖЕЛАЯ ОПЕРАЦИЯ.
        Считывает project.yaml и сканирует папку на наличие видео.
        Вызывать только при фактическом открытии проекта в UI.
        """
        if self._is_loaded:
            return

        if not self._path.exists():
            raise FileNotFoundError(f"Project path not found: {self._path}")

        # 1. Читаем конфиг (обновляем имя, если оно изменилось в файле)
        self.__read_config()

        # 2. Сканируем видео
        self.__scan_videos()

        self._is_loaded = True

    def __read_config(self):
        config_file = self._path / ".morris" / "project.yaml"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    # Обновляем имя на актуальное из файла
                    if 'name' in data:
                        self._name = data['name']
            except Exception as e:
                pass

    def __scan_videos(self):
        self._videos = []
        for file_path in self._path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS:
                self._videos.append(Video(str(file_path)))
        # Сортировка по имени файла
        self._videos.sort(key=lambda v: Path(v.path).name)

    # --- Static Factory ---
    @staticmethod
    def create(path: str | os.PathLike, name: str) -> 'Project':
        """Создает новый проект на диске и возвращает объект (уже загруженный)"""
        project_path = Path(path)
        config_dir = project_path / ".morris"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_data = {'name': name}

        with open(config_dir / "project.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Возвращаем объект, считаем его сразу "загруженным", т.к. видео там еще нет
        proj = Project(project_path, name)
        proj._is_loaded = True
        return proj

    # --- Properties ---
    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def videos(self):
        if not self._is_loaded:
            self.load()
        return self._videos

    @property
    def is_loaded(self):
        return self._is_loaded
