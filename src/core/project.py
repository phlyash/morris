import os
from pathlib import Path
from typing import List, Optional

import yaml

from src.config import VIDEO_EXTENSIONS
from src.core import Video


class Project:
    _name: str
    _path: Path
    _videos: List[Video]
    _is_loaded: bool
    _compass_settings: dict
    _scale_factor: float  # пикселей на метр (0 = не задано)

    def __init__(self, project_path: str | os.PathLike, cached_name: str = None):
        self._path = Path(project_path).resolve()
        self._name = cached_name if cached_name else self._path.name
        self._videos = []
        self._is_loaded = False
        self._compass_settings = {}
        self._scale_factor = 0.0
        self._export_settings = {}

        self.__read_config()

        self.reload_videos()

    def __read_config(self):
        config_file = self._path / ".morris" / "project.yaml"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    if "name" in data:
                        self._name = data["name"]
                    if "compass" in data:
                        self._compass_settings = data["compass"]
                    if "scale_factor" in data:
                        self._scale_factor = float(data["scale_factor"])
                    if "export_settings" in data:
                        self._export_settings = data["export_settings"]
            except Exception:
                pass

    def save_config(self):
        config_dir = self._path / ".morris"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "project.yaml"

        existing_data = {}
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    existing_data = yaml.safe_load(f) or {}
            except Exception:
                pass

        existing_data["name"] = self._name
        existing_data["scale_factor"] = self._scale_factor

        if self._compass_settings:
            existing_data["compass"] = self._compass_settings

        # Всегда сохраняем export_settings, даже пустой
        existing_data["export_settings"] = self._export_settings

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(existing_data, f, default_flow_style=False, allow_unicode=True)

    @property
    def export_settings(self) -> dict:
        return self._export_settings

    @export_settings.setter
    def export_settings(self, value: dict):
        self._export_settings = value

    def reload_videos(self):
        self._videos = []
        valid_extensions = {".mp4", ".avi", ".mov", ".mkv"}
        for file_path in self.path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                self._videos.append(Video(file_path))
        self._videos.sort(key=lambda v: v.path.name)

    def load(self):
        if self._is_loaded:
            return
        if not self._path.exists():
            raise FileNotFoundError(f"Project path not found: {self._path}")
        self.__read_config()
        self.__scan_videos()
        self._is_loaded = True

    def __scan_videos(self):
        self._videos = []
        for file_path in self._path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS:
                self._videos.append(Video(str(file_path)))
        self._videos.sort(key=lambda v: Path(v.path).name)

    @property
    def compass_settings(self) -> dict:
        return self._compass_settings

    @compass_settings.setter
    def compass_settings(self, value: dict):
        self._compass_settings = value

    @property
    def scale_factor(self) -> float:
        """Пикселей на метр. 0 = не откалибровано."""
        return self._scale_factor

    @scale_factor.setter
    def scale_factor(self, value: float):
        self._scale_factor = value

    def pixels_to_meters(self, px: float) -> float:
        """Конвертация пикселей в метры. Если не откалибровано — возвращает px."""
        if self._scale_factor > 0:
            return px / self._scale_factor
        return px

    @property
    def is_calibrated(self) -> bool:
        return self._scale_factor > 0

    @staticmethod
    def create(path: str | os.PathLike, name: str) -> "Project":
        project_path = Path(path)
        config_dir = project_path / ".morris"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_data = {"name": name}
        with open(config_dir / "project.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        proj = Project(project_path, name)
        proj._is_loaded = True
        return proj

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
